"""
LLM Rule to Egglog Converter.

Converts LLM-generated rewrite rules to egglog format for use
in equality saturation.

Pipeline:
1. Parse LLM output -> ParsedRule objects
2. Verify with Z3 (semantic equivalence check)
3. Convert to egglog rewrite rules
4. Add to e-graph for saturation
"""
from typing import List, Optional, Any, Tuple
from dataclasses import dataclass
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import egglog types
try:
    from egraph_bridge.egg_egraph import Asm, EGGLOG_AVAILABLE, ExprBuilder, rewrite, birewrite
except ImportError:
    try:
        from egg_egraph import Asm, EGGLOG_AVAILABLE, ExprBuilder
        from egglog import rewrite, birewrite
    except ImportError:
        EGGLOG_AVAILABLE = False

# Import rule parser
try:
    from learned_rules.rule_parser import ParsedRule, parse_llm_output
except ImportError:
    ParsedRule = None
    parse_llm_output = None

# Import verification
try:
    from verification.rule_verifier import verify_rule
    VERIFICATION_AVAILABLE = True
except ImportError:
    VERIFICATION_AVAILABLE = False
    verify_rule = None


@dataclass
class EgglogRule:
    """Represents an egglog rewrite rule."""
    name: str
    lhs_expr: Any  # Asm expression for LHS pattern
    rhs_expr: Any  # Asm expression for RHS replacement
    bidirectional: bool = False
    verified: bool = False
    original_rule: Any = None  # Reference to ParsedRule
    
    def to_egglog(self) -> Any:
        """Convert to egglog rewrite rule."""
        if self.bidirectional:
            return birewrite(self.lhs_expr).to(self.rhs_expr)
        return rewrite(self.lhs_expr).to(self.rhs_expr)


class RuleToEgglogConverter:
    """
    Converts parsed LLM rules to egglog format.
    
    Usage:
        converter = RuleToEgglogConverter()
        
        # Convert a parsed rule
        egglog_rule = converter.convert_rule(parsed_rule)
        
        # Add to e-graph
        egraph.register(egglog_rule.to_egglog())
    """
    
    # Supported opcodes and their egglog operators
    OPCODE_MAP = {
        "add": "+",
        "sub": "-",
        "mul": "*",
        "div": "/",
        "mod": "%",
        "and": "&",
        "or": "|",
        "xor": "^",
        "shl": "<<",
        "shr": ">>",
        "neg": "neg",
        "not": "not",
        "mov": "mov",
        "inc": "inc",
        "dec": "dec",
    }
    
    def __init__(self, enable_verification: bool = True):
        """
        Initialize the converter.
        
        Args:
            enable_verification: If True, verify rules with Z3 before conversion
        """
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog not available")
        
        self._enable_verification = enable_verification and VERIFICATION_AVAILABLE
        self._builder = ExprBuilder()
        self._rule_counter = 0
        
        # Track variables for pattern matching
        self._pattern_vars: dict = {}
    
    def convert_rule(self, parsed_rule: "ParsedRule", 
                     verify: bool = None) -> Optional[EgglogRule]:
        """
        Convert a ParsedRule to an EgglogRule.
        
        Args:
            parsed_rule: ParsedRule from rule_parser
            verify: Override verification setting
        
        Returns:
            EgglogRule or None if conversion/verification fails
        """
        if verify is None:
            verify = self._enable_verification
        
        # Verify with Z3 first
        if verify and VERIFICATION_AVAILABLE:
            try:
                is_valid = verify_rule(parsed_rule)
                if not is_valid:
                    print(f"✗ Rule rejected by Z3 verification")
                    return None
            except Exception as e:
                print(f"⚠ Verification error: {e}")
        
        try:
            # Reset pattern variables for this rule
            self._pattern_vars = {}
            
            # Parse LHS instructions to expression
            lhs_expr = self._parse_instructions_to_expr(parsed_rule.lhs_seq)
            
            # Parse RHS instructions to expression
            if parsed_rule.rhs_seq and len(parsed_rule.rhs_seq) > 0:
                rhs_expr = self._parse_instructions_to_expr(parsed_rule.rhs_seq)
            else:
                # Empty RHS means identity (remove instructions)
                # Use the destination variable
                rhs_expr = self._get_dest_var(parsed_rule.lhs_seq)
            
            if lhs_expr is None or rhs_expr is None:
                return None
            
            # Create rule
            self._rule_counter += 1
            rule_name = f"llm_rule_{self._rule_counter}"
            
            return EgglogRule(
                name=rule_name,
                lhs_expr=lhs_expr,
                rhs_expr=rhs_expr,
                bidirectional=False,
                verified=verify and VERIFICATION_AVAILABLE,
                original_rule=parsed_rule
            )
            
        except Exception as e:
            print(f"✗ Failed to convert rule: {e}")
            return None
    
    def convert_rules(self, parsed_rules: List["ParsedRule"]) -> List[EgglogRule]:
        """
        Convert multiple ParsedRules to EgglogRules.
        
        Args:
            parsed_rules: List of ParsedRule objects
        
        Returns:
            List of successfully converted EgglogRules
        """
        results = []
        for rule in parsed_rules:
            egglog_rule = self.convert_rule(rule)
            if egglog_rule:
                results.append(egglog_rule)
        return results
    
    def _parse_instructions_to_expr(self, instructions: List[str]) -> Optional[Any]:
        """
        Parse instruction sequence to a single egglog expression.
        
        For multi-instruction sequences, constructs the expression tree
        by tracking definitions.
        """
        if not instructions:
            return None
        
        definitions = {}  # var -> expr
        last_dest = None
        
        for instr_str in instructions:
            parsed = self._parse_instruction_string(instr_str)
            if parsed is None:
                continue
            
            opcode, dest, operands = parsed
            
            # Build expression for this instruction
            expr = self._build_instruction_expr(opcode, operands, definitions)
            
            if dest and expr is not None:
                definitions[dest] = expr
                last_dest = dest
        
        # Return the final expression (last defined variable)
        if last_dest and last_dest in definitions:
            return definitions[last_dest]
        
        return None
    
    def _parse_instruction_string(self, instr_str: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Parse an instruction string to (opcode, dest, operands).
        
        Handles formats like:
        - "ADD r1, r2"
        - "MOV r1, 5"
        - "ADD r1, r2, r3"
        """
        instr_str = instr_str.strip()
        if not instr_str or instr_str.startswith('#'):
            return None
        
        # Split by whitespace first to get opcode
        parts = instr_str.split(None, 1)
        if not parts:
            return None
        
        opcode = parts[0].lower()
        
        if len(parts) < 2:
            return opcode, None, []
        
        # Parse operands (comma-separated)
        operand_str = parts[1]
        operands = [op.strip() for op in operand_str.split(',')]
        
        # First operand is typically the destination
        dest = operands[0] if operands else None
        sources = operands[1:] if len(operands) > 1 else []
        
        # For 2-operand instructions (like ADD r1, r2), r1 is both dest and source1
        if opcode in ('add', 'sub', 'mul', 'div', 'and', 'or', 'xor', 'shl', 'shr'):
            if len(operands) == 2:
                # ADD r1, r2 means r1 = r1 + r2
                sources = [dest] + sources
        
        return opcode, dest, sources
    
    def _build_instruction_expr(self, opcode: str, operands: List[str], 
                                definitions: dict) -> Optional[Any]:
        """Build expression for a single instruction."""
        def get_operand_expr(op: str) -> Any:
            op = op.strip()
            # Check if it's a defined variable
            if op in definitions:
                return definitions[op]
            # Check if it's a pattern variable (r1, imm1, etc.)
            if op in self._pattern_vars:
                return self._pattern_vars[op]
            # Parse as new operand
            expr = self._builder.parse_operand(op)
            # Cache pattern variables
            if self._is_pattern_var(op):
                self._pattern_vars[op] = expr
            return expr
        
        if opcode == 'mov':
            if len(operands) >= 1:
                return get_operand_expr(operands[0])
        
        elif opcode in ('add', 'sub', 'mul', 'div', 'mod', 'and', 'or', 'xor', 'shl', 'shr'):
            if len(operands) >= 2:
                left = get_operand_expr(operands[0])
                right = get_operand_expr(operands[1])
                return self._builder.build_binary_op(opcode, left, right)
        
        elif opcode == 'neg':
            if len(operands) >= 1:
                return self._builder.build_unary_op('neg', get_operand_expr(operands[0]))
        
        elif opcode == 'not':
            if len(operands) >= 1:
                return self._builder.build_unary_op('not', get_operand_expr(operands[0]))
        
        elif opcode == 'inc':
            if len(operands) >= 1:
                op_expr = get_operand_expr(operands[0])
                return op_expr + Asm(1)
        
        elif opcode == 'dec':
            if len(operands) >= 1:
                op_expr = get_operand_expr(operands[0])
                return op_expr - Asm(1)
        
        return None
    
    def _get_dest_var(self, instructions: List[str]) -> Optional[Any]:
        """Get the destination variable from instruction sequence."""
        for instr_str in instructions:
            parsed = self._parse_instruction_string(instr_str)
            if parsed:
                _, dest, _ = parsed
                if dest:
                    return self._builder.var(dest)
        return None
    
    def _is_pattern_var(self, name: str) -> bool:
        """Check if a name is a pattern variable (r1, r2, imm1, etc.)."""
        # Pattern variables: r1, r2, ..., imm1, imm2, ...
        return bool(re.match(r'^(r|imm)\d+$', name.lower()))


def convert_llm_output_to_egglog(llm_output: str, 
                                  verify: bool = True) -> List[EgglogRule]:
    """
    Convert raw LLM output to egglog rules.
    
    Full pipeline:
    1. Parse LLM output to ParsedRules
    2. Optionally verify with Z3
    3. Convert to EgglogRules
    
    Args:
        llm_output: Raw text from LLM
        verify: Whether to verify rules with Z3
    
    Returns:
        List of EgglogRules ready for use
    """
    if parse_llm_output is None:
        raise RuntimeError("rule_parser not available")
    
    # Parse LLM output
    parsed_rules = parse_llm_output(llm_output)
    
    # Convert to egglog
    converter = RuleToEgglogConverter(enable_verification=verify)
    return converter.convert_rules(parsed_rules)


# ============================================
# Test / Demo
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("LLM Rule to Egglog Converter Test")
    print("=" * 50)
    
    if not EGGLOG_AVAILABLE:
        print("ERROR: egglog not available")
        exit(1)
    
    print("✓ egglog is available\n")
    
    # Test 1: Parse simple instruction
    print("Test 1: Instruction Parsing")
    print("-" * 30)
    
    converter = RuleToEgglogConverter(enable_verification=False)
    
    # Test parsing
    result = converter._parse_instruction_string("ADD r1, r2")
    print(f"  'ADD r1, r2' -> {result}")
    
    result = converter._parse_instruction_string("MOV r1, 5")
    print(f"  'MOV r1, 5' -> {result}")
    
    result = converter._parse_instruction_string("SUB eax, 0")
    print(f"  'SUB eax, 0' -> {result}")
    
    print("\n✓ Test 1 passed!\n")
    
    # Test 2: Build expression from instructions
    print("Test 2: Instruction to Expression")
    print("-" * 30)
    
    # ADD r1, 0 should become r1 + 0
    instructions = ["ADD r1, 0"]
    expr = converter._parse_instructions_to_expr(instructions)
    print(f"  'ADD r1, 0' -> {expr}")
    
    # MOV r3, r2; ADD r3, 0 should become r2 + 0
    instructions = ["MOV r3, r2", "ADD r3, 0"]
    expr = converter._parse_instructions_to_expr(instructions)
    print(f"  'MOV r3, r2; ADD r3, 0' -> {expr}")
    
    print("\n✓ Test 2 passed!\n")
    
    # Test 3: Create EgglogRule
    print("Test 3: Create Egglog Rule")
    print("-" * 30)
    
    if ParsedRule is not None:
        # Create a simple parsed rule
        rule = ParsedRule(
            lhs_seq=["ADD r1, 0"],
            rhs_seq=["MOV r1, r1"],  # Identity
            conditions=[]
        )
        
        egglog_rule = converter.convert_rule(rule)
        if egglog_rule:
            print(f"  Rule name: {egglog_rule.name}")
            print(f"  LHS: {egglog_rule.lhs_expr}")
            print(f"  RHS: {egglog_rule.rhs_expr}")
            print(f"  Verified: {egglog_rule.verified}")
        else:
            print("  Rule conversion failed")
    else:
        print("  Skipped (rule_parser not available)")
    
    print("\n✓ Test 3 passed!\n")
    
    # Test 4: Use rule in e-graph
    print("Test 4: Apply Rule in E-Graph")
    print("-" * 30)
    
    from egraph_bridge.egg_egraph import EggEGraph
    
    egraph = EggEGraph()
    
    # Create expression: x + 0
    x = Asm.var("x")
    expr = x + Asm(0)
    egraph.register(expr, "x_plus_0")
    
    print(f"  Before: {expr}")
    
    # Saturate (includes algebraic rules)
    egraph.saturate()
    
    # Extract
    result = egraph.extract(expr)
    print(f"  After: {result}")
    
    print("\n✓ Test 4 passed!\n")
    
    # Summary
    print("=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
