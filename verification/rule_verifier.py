"""
Rule verifier using SMT-based equivalence checking.

Verifies that learned rules are semantically correct.
"""
import re
from typing import Optional
from asm_ir import Instruction
from learned_rules.rule_parser import ParsedRule
from .equivalence_checker import are_sequences_equivalent, are_sequences_equivalent_with_model


# Cache for memory address to variable name mapping
_mem_var_counter = [0]
_mem_var_map = {}


def normalize_operand(operand: str) -> str:
    """
    Normalize an operand for Z3 verification.
    
    Converts memory addresses like 'DWORD PTR [rbp-4]' to simple variable names
    that Z3 can understand. Also handles pattern variables and immediates.
    
    Args:
        operand: Raw operand string
    
    Returns:
        Normalized operand string
    """
    operand = operand.strip()
    
    # Remove comments (anything after semicolon)
    if ';' in operand:
        operand = operand.split(';')[0].strip()
    
    # Handle memory references: DWORD PTR [rbp-4], BYTE PTR [rax], etc.
    mem_pattern = r'(BYTE|WORD|DWORD|QWORD)\s+PTR\s*\[([^\]]+)\]'
    mem_match = re.match(mem_pattern, operand, re.IGNORECASE)
    if mem_match:
        # Convert to a symbolic variable name
        addr_expr = mem_match.group(2).strip()
        # Create a consistent variable name for this memory location
        normalized_addr = re.sub(r'[^a-zA-Z0-9]', '_', addr_expr)
        var_name = f"mem_{normalized_addr}"
        return var_name
    
    # Handle simple bracket memory: [rbp-4]
    bracket_pattern = r'\[([^\]]+)\]'
    bracket_match = re.match(bracket_pattern, operand)
    if bracket_match:
        addr_expr = bracket_match.group(1).strip()
        normalized_addr = re.sub(r'[^a-zA-Z0-9]', '_', addr_expr)
        return f"mem_{normalized_addr}"
    
    # Handle labels like .L2, .L3 - convert to symbolic
    if operand.startswith('.'):
        return f"label_{operand[1:]}"
    
    # Handle pattern variables (r1, r2, src, dst, imm)
    pattern_vars = ['r1', 'r2', 'r3', 'src', 'dst', 'imm', 'imm1', 'imm2']
    if operand.lower() in pattern_vars:
        return operand.lower()
    
    # Return as-is for simple registers (eax, ebx, etc.) and immediates
    return operand


def parse_instruction_string(instr_str: str) -> Optional[Instruction]:
    """
    Parse an instruction string into an Instruction object.
    
    Args:
        instr_str: Instruction string like "MOV EAX, EBX"
    
    Returns:
        Instruction object or None if parsing fails
    """
    # Remove comments
    if ';' in instr_str:
        instr_str = instr_str.split(';')[0]
    
    instr_str = instr_str.strip()
    if not instr_str:
        return None
    
    parts = instr_str.split()
    if not parts:
        return None
    
    opcode = parts[0].upper()
    
    # Skip labels (lines ending with :)
    if opcode.endswith(':'):
        return None
    
    # Parse operands (simplified)
    if len(parts) < 2:
        # No operands
        return Instruction(opcode, None, [])
    
    # Join remaining parts and split by comma
    operands_str = ' '.join(parts[1:])
    operands = [op.strip() for op in operands_str.split(',')]
    
    if not operands:
        return Instruction(opcode, None, [])
    
    # Normalize operands for Z3
    normalized_operands = [normalize_operand(op) for op in operands]
    
    # First operand is typically the destination
    dst = normalized_operands[0] if normalized_operands else None
    srcs = normalized_operands[1:] if len(normalized_operands) > 1 else []
    
    return Instruction(opcode, dst, srcs)


def verify_rule(parsed_rule: ParsedRule, 
                timeout_ms: int = 5000,
                return_counterexample: bool = False) -> bool | tuple[bool, dict]:
    """
    Verify that a parsed rule is semantically correct using SMT.
    
    Args:
        parsed_rule: The rule to verify
        timeout_ms: Solver timeout in milliseconds
        return_counterexample: If True, return (result, counterexample) tuple
    
    Returns:
        True if rule is verified correct, False otherwise
        If return_counterexample=True, returns (bool, dict)
    """
    try:
        # Convert LHS strings to Instruction objects
        lhs_instrs = []
        for instr_str in parsed_rule.lhs_seq:
            instr = parse_instruction_string(instr_str)
            if instr is None:
                print(f"Warning: Failed to parse LHS instruction: {instr_str}")
                return (False, {"error": "Parse failed"}) if return_counterexample else False
            lhs_instrs.append(instr)
        
        # Convert RHS strings to Instruction objects
        rhs_instrs = []
        for instr_str in parsed_rule.rhs_seq:
            instr = parse_instruction_string(instr_str)
            if instr is None:
                print(f"Warning: Failed to parse RHS instruction: {instr_str}")
                return (False, {"error": "Parse failed"}) if return_counterexample else False
            rhs_instrs.append(instr)
        
        # Check equivalence
        if return_counterexample:
            return are_sequences_equivalent_with_model(lhs_instrs, rhs_instrs, timeout_ms)
        else:
            return are_sequences_equivalent(lhs_instrs, rhs_instrs, timeout_ms)
    
    except Exception as e:
        print(f"Warning: Rule verification failed with exception: {e}")
        return (False, {"error": str(e)}) if return_counterexample else False


def verify_rule_with_details(parsed_rule: ParsedRule, 
                             timeout_ms: int = 5000) -> dict:
    """
    Verify a rule and return detailed results.
    
    Args:
        parsed_rule: The rule to verify
        timeout_ms: Solver timeout in milliseconds
    
    Returns:
        Dictionary with verification results:
        {
            'verified': bool,
            'lhs': list[str],
            'rhs': list[str],
            'counterexample': dict (if not verified),
            'error': str (if error occurred)
        }
    """
    result = {
        'verified': False,
        'lhs': parsed_rule.lhs_seq,
        'rhs': parsed_rule.rhs_seq,
    }
    
    try:
        verified, counterexample = verify_rule(parsed_rule, timeout_ms, return_counterexample=True)
        result['verified'] = verified
        
        if not verified and counterexample:
            result['counterexample'] = counterexample
        
    except Exception as e:
        result['error'] = str(e)
    
    return result
