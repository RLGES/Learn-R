"""
Rule filtering module for candidate rewrite rules.

Filters out invalid, duplicate, or suboptimal candidate rules.
"""
from .rule_parser import ParsedRule


# Supported opcodes in our minimal instruction set
SUPPORTED_OPCODES = {'MOV', 'ADD', 'SUB', 'MUL', 'CMP'}


def extract_opcode(instruction: str) -> str:
    """
    Extract the opcode from an instruction string.
    
    Args:
        instruction: Instruction string (e.g., "MOV eax, ebx")
    
    Returns:
        Opcode in uppercase (e.g., "MOV")
    """
    parts = instruction.strip().split()
    if parts:
        return parts[0].upper()
    return ""


def filter_candidate_rules(
    parsed_rules: list[ParsedRule],
    existing_rule_names: set[str] = None
) -> list[ParsedRule]:
    """
    Filter candidate rewrite rules based on validity criteria.
    
    Removes rules that:
    - Duplicate existing rule names (if provided)
    - Increase instruction count (len(rhs) > len(lhs))
    - Contain unsupported opcodes
    - Have empty LHS
    
    Args:
        parsed_rules: List of parsed candidate rules
        existing_rule_names: Set of existing rule names to avoid duplicates
    
    Returns:
        Filtered list of valid rules
    """
    if existing_rule_names is None:
        existing_rule_names = set()
    
    filtered_rules = []
    
    for rule in parsed_rules:
        # Skip rules with empty LHS
        if not rule.lhs_seq:
            continue
        
        # Filter 1: Check for instruction count increase
        # Allow equal or reduced instruction count
        if len(rule.rhs_seq) > len(rule.lhs_seq):
            # Rule increases code size - skip
            continue
        
        # Filter 2: Check for unsupported opcodes
        has_unsupported = False
        
        for instr in rule.lhs_seq:
            opcode = extract_opcode(instr)
            if opcode and opcode not in SUPPORTED_OPCODES:
                has_unsupported = True
                break
        
        if not has_unsupported:
            for instr in rule.rhs_seq:
                opcode = extract_opcode(instr)
                if opcode and opcode not in SUPPORTED_OPCODES:
                    has_unsupported = True
                    break
        
        if has_unsupported:
            continue
        
        # Filter 3: Generate a rule name and check for duplicates
        # Simple naming: based on opcodes in LHS
        rule_opcodes = [extract_opcode(instr) for instr in rule.lhs_seq]
        rule_name = '_'.join(rule_opcodes).lower() + '_learned'
        
        if rule_name in existing_rule_names:
            continue
        
        # Rule passed all filters
        filtered_rules.append(rule)
    
    return filtered_rules


def validate_rule_safety(rule: ParsedRule) -> bool:
    """
    Perform additional safety checks on a rule.
    
    This is a placeholder for more sophisticated validation:
    - Type checking
    - Register consistency
    - No memory corruption
    
    Args:
        rule: The parsed rule to validate
    
    Returns:
        True if rule appears safe, False otherwise
    """
    # Basic check: LHS must exist
    if not rule.lhs_seq:
        return False
    
    # Check: RHS shouldn't be longer than LHS (optimization, not pessimization)
    if len(rule.rhs_seq) > len(rule.lhs_seq):
        return False
    
    # Additional checks could be added here:
    # - Register name consistency
    # - No undefined behavior
    # - Operand count validation
    
    return True


def prioritize_by_reduction(rules: list[ParsedRule]) -> list[ParsedRule]:
    """
    Sort rules by code size reduction (most reduction first).
    
    Args:
        rules: List of parsed rules
    
    Returns:
        Sorted list (most aggressive reduction first)
    """
    def reduction_amount(rule: ParsedRule) -> int:
        """Calculate how many instructions are removed."""
        return len(rule.lhs_seq) - len(rule.rhs_seq)
    
    return sorted(rules, key=reduction_amount, reverse=True)
