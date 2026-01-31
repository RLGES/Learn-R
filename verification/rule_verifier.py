"""
Rule verifier using SMT-based equivalence checking.

Verifies that learned rules are semantically correct.
"""
from typing import Optional
from asm_ir import Instruction
from learned_rules.rule_parser import ParsedRule
from .equivalence_checker import are_sequences_equivalent, are_sequences_equivalent_with_model


def parse_instruction_string(instr_str: str) -> Optional[Instruction]:
    """
    Parse an instruction string into an Instruction object.
    
    Args:
        instr_str: Instruction string like "MOV EAX, EBX"
    
    Returns:
        Instruction object or None if parsing fails
    """
    parts = instr_str.strip().split()
    if not parts:
        return None
    
    opcode = parts[0].upper()
    
    # Parse operands (simplified)
    if len(parts) < 2:
        # No operands
        return Instruction(opcode, None, [])
    
    # Join remaining parts and split by comma
    operands_str = ' '.join(parts[1:])
    operands = [op.strip() for op in operands_str.split(',')]
    
    if not operands:
        return Instruction(opcode, None, [])
    
    # First operand is typically the destination
    dst = operands[0] if operands else None
    srcs = operands[1:] if len(operands) > 1 else []
    
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
