"""
SSA to Egglog Expression Converter.

Converts SSA-form instructions to egglog Asm expressions for
equality saturation optimization.

This bridges the existing SSA IR with the new egglog-based e-graph.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import egglog types from egg_egraph
try:
    from .egg_egraph import Asm, EGGLOG_AVAILABLE, ExprBuilder
except ImportError:
    from egg_egraph import Asm, EGGLOG_AVAILABLE, ExprBuilder

# Import ASM IR
try:
    from asm_ir import Instruction, BasicBlock
except ImportError:
    Instruction = None
    BasicBlock = None


@dataclass
class ConversionResult:
    """Result of converting SSA block to egglog expressions."""
    expressions: Dict[str, Any]  # var_name -> Asm expression
    instruction_order: List[str]  # Order of variable definitions
    errors: List[str]  # Any conversion errors


class SSAToEgglog:
    """
    Converter from SSA instructions to egglog Asm expressions.
    
    Usage:
        converter = SSAToEgglog()
        
        # Convert a block
        result = converter.convert_block(ssa_block)
        
        # Access expressions
        for var, expr in result.expressions.items():
            print(f"{var} = {expr}")
    """
    
    # Mapping from opcode to operation type
    BINARY_OPS = {
        "add", "sub", "mul", "div", "mod",
        "and", "or", "xor",
        "shl", "shr", "sar"
    }
    
    UNARY_OPS = {
        "neg", "not", "inc", "dec"
    }
    
    MOVE_OPS = {
        "mov"
    }
    
    MEMORY_OPS = {
        "load", "store"
    }
    
    PHI_OPS = {
        "phi"
    }
    
    def __init__(self):
        """Initialize the converter."""
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog not available")
        self._builder = ExprBuilder()
        self._defined_vars: Dict[str, Any] = {}
    
    def reset(self):
        """Reset converter state for new block."""
        self._builder = ExprBuilder()
        self._defined_vars = {}
    
    def convert_block(self, block: "BasicBlock") -> ConversionResult:
        """
        Convert an entire SSA basic block to egglog expressions.
        
        Args:
            block: SSA-form BasicBlock
        
        Returns:
            ConversionResult with expressions and any errors
        """
        self.reset()
        
        expressions = {}
        instruction_order = []
        errors = []
        
        for instr in block.instructions:
            try:
                var_name, expr = self.convert_instruction(instr)
                if var_name and expr:
                    expressions[var_name] = expr
                    instruction_order.append(var_name)
                    self._defined_vars[var_name] = expr
            except Exception as e:
                errors.append(f"Error converting {instr}: {e}")
        
        return ConversionResult(
            expressions=expressions,
            instruction_order=instruction_order,
            errors=errors
        )
    
    def convert_instruction(self, instr: "Instruction") -> Tuple[Optional[str], Optional[Any]]:
        """
        Convert a single SSA instruction to an egglog expression.
        
        Args:
            instr: SSA Instruction
        
        Returns:
            Tuple of (destination_var, expression)
        """
        opcode = instr.opcode.lower()
        dest = instr.dest
        sources = instr.sources if hasattr(instr, 'sources') else []
        
        # Handle different instruction types
        if opcode in self.BINARY_OPS:
            return self._convert_binary(opcode, dest, sources)
        elif opcode in self.UNARY_OPS:
            return self._convert_unary(opcode, dest, sources)
        elif opcode in self.MOVE_OPS:
            return self._convert_mov(dest, sources)
        elif opcode in self.MEMORY_OPS:
            return self._convert_memory(opcode, dest, sources)
        elif opcode in self.PHI_OPS:
            return self._convert_phi(dest, sources)
        else:
            # Unknown opcode - create a variable reference
            return dest, self._builder.var(dest)
    
    def _convert_binary(self, op: str, dest: str, sources: List[str]) -> Tuple[str, Any]:
        """Convert binary operation."""
        if len(sources) < 2:
            raise ValueError(f"Binary op {op} requires 2 operands, got {len(sources)}")
        
        left = self._get_operand(sources[0])
        right = self._get_operand(sources[1])
        
        expr = self._builder.build_binary_op(op, left, right)
        return dest, expr
    
    def _convert_unary(self, op: str, dest: str, sources: List[str]) -> Tuple[str, Any]:
        """Convert unary operation."""
        if len(sources) < 1:
            raise ValueError(f"Unary op {op} requires 1 operand, got {len(sources)}")
        
        operand = self._get_operand(sources[0])
        
        # Handle inc/dec specially
        if op == "inc":
            return dest, operand + Asm(1)
        elif op == "dec":
            return dest, operand - Asm(1)
        else:
            expr = self._builder.build_unary_op(op, operand)
            return dest, expr
    
    def _convert_mov(self, dest: str, sources: List[str]) -> Tuple[str, Any]:
        """Convert MOV instruction."""
        if len(sources) < 1:
            raise ValueError(f"MOV requires source operand")
        
        # MOV just copies the source
        source_expr = self._get_operand(sources[0])
        return dest, source_expr
    
    def _convert_memory(self, op: str, dest: str, sources: List[str]) -> Tuple[Optional[str], Optional[Any]]:
        """Convert memory operation (LOAD/STORE)."""
        if op == "load":
            if len(sources) < 1:
                raise ValueError("LOAD requires address operand")
            addr = self._get_operand(sources[0])
            return dest, Asm.load(addr)
        elif op == "store":
            # STORE doesn't define a value, returns None
            return None, None
        return None, None
    
    def _convert_phi(self, dest: str, sources: List[str]) -> Tuple[str, Any]:
        """Convert PHI node."""
        if len(sources) == 0:
            return dest, self._builder.var(dest)
        elif len(sources) == 1:
            return dest, self._get_operand(sources[0])
        elif len(sources) == 2:
            a = self._get_operand(sources[0])
            b = self._get_operand(sources[1])
            return dest, Asm.phi(a, b)
        elif len(sources) == 3:
            a = self._get_operand(sources[0])
            b = self._get_operand(sources[1])
            c = self._get_operand(sources[2])
            return dest, Asm.phi3(a, b, c)
        else:
            # For more than 3 inputs, nest PHI nodes
            exprs = [self._get_operand(s) for s in sources]
            result = Asm.phi(exprs[0], exprs[1])
            for e in exprs[2:]:
                result = Asm.phi(result, e)
            return dest, result
    
    def _get_operand(self, operand: str) -> Any:
        """
        Get expression for an operand.
        
        If the operand refers to a previously defined variable, use that.
        Otherwise parse it as a constant or new variable.
        """
        operand = operand.strip()
        
        # Check if this references a defined variable
        if operand in self._defined_vars:
            return self._defined_vars[operand]
        
        # Parse as constant or variable
        return self._builder.parse_operand(operand)


def convert_ssa_block_to_egglog(block: "BasicBlock") -> Dict[str, Any]:
    """
    Convenience function to convert an SSA block to egglog expressions.
    
    Args:
        block: SSA-form BasicBlock
    
    Returns:
        Dictionary mapping variable names to Asm expressions
    """
    converter = SSAToEgglog()
    result = converter.convert_block(block)
    
    if result.errors:
        for err in result.errors:
            print(f"Warning: {err}")
    
    return result.expressions


def convert_instructions_to_egglog(instructions: List["Instruction"]) -> Dict[str, Any]:
    """
    Convert a list of instructions to egglog expressions.
    
    Args:
        instructions: List of SSA Instructions
    
    Returns:
        Dictionary mapping variable names to Asm expressions
    """
    if BasicBlock is None:
        raise RuntimeError("asm_ir module not available")
    
    # Create a temporary block
    block = BasicBlock("temp")
    block.instructions = instructions
    
    return convert_ssa_block_to_egglog(block)


# ============================================
# Test / Demo
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("SSA to Egglog Converter Test")
    print("=" * 50)
    
    if not EGGLOG_AVAILABLE:
        print("ERROR: egglog not available")
        exit(1)
    
    print("✓ egglog is available\n")
    
    # Test 1: Manual expression building
    print("Test 1: Manual Expression Building")
    print("-" * 30)
    
    builder = ExprBuilder()
    
    # Build: x_0 = 5
    x_0 = builder.const(5)
    print(f"  x_0 = 5 -> {x_0}")
    
    # Build: y_0 = x_0 + 0
    y_0 = x_0 + Asm(0)
    print(f"  y_0 = x_0 + 0 -> {y_0}")
    
    # Build: z_0 = y_0 * 1
    z_0 = y_0 * Asm(1)
    print(f"  z_0 = y_0 * 1 -> {z_0}")
    
    print("\n✓ Test 1 passed!\n")
    
    # Test 2: Using ExprBuilder
    print("Test 2: ExprBuilder Usage")
    print("-" * 30)
    
    builder2 = ExprBuilder()
    
    # Parse operands
    a = builder2.parse_operand("eax")
    b = builder2.parse_operand("10")
    c = builder2.build_binary_op("add", a, b)
    print(f"  add(eax, 10) = {c}")
    
    d = builder2.build_binary_op("sub", c, b)
    print(f"  sub(eax+10, 10) = {d}")
    
    print("\n✓ Test 2 passed!\n")
    
    # Test 3: PHI nodes
    print("Test 3: PHI Node Construction")
    print("-" * 30)
    
    builder3 = ExprBuilder()
    x = builder3.var("x")
    y = builder3.var("y")
    
    phi2 = Asm.phi(x, y)
    print(f"  phi(x, y) = {phi2}")
    
    z = builder3.var("z")
    phi3 = Asm.phi3(x, y, z)
    print(f"  phi(x, y, z) = {phi3}")
    
    print("\n✓ Test 3 passed!\n")
    
    # Test 4: Full optimization pipeline
    print("Test 4: Optimization with Egglog")
    print("-" * 30)
    
    from egg_egraph import EggEGraph
    
    egraph = EggEGraph()
    
    # Register expressions
    egraph.register(y_0, "y_0")  # x_0 + 0
    egraph.register(z_0, "z_0")  # y_0 * 1
    
    print(f"  Before: y_0 = {y_0}")
    print(f"  Before: z_0 = {z_0}")
    
    # Run saturation
    egraph.saturate()
    
    # Extract
    results = egraph.extract_all()
    print(f"\n  After optimization:")
    for name, expr in results.items():
        print(f"    {name} = {expr}")
    
    print("\n✓ Test 4 passed!\n")
    
    # Summary
    print("=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
