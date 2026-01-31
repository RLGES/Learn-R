"""
Parser for LLM-generated rewrite rules.

Parses raw text output from LLMs into structured rule objects.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedRule:
    """Represents a parsed rewrite rule from LLM output."""
    lhs_seq: list[str] = field(default_factory=list)
    rhs_seq: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """String representation of the parsed rule."""
        lhs = '\n  '.join(self.lhs_seq) if self.lhs_seq else '(empty)'
        rhs = '\n  '.join(self.rhs_seq) if self.rhs_seq else '(empty)'
        cond = ', '.join(self.conditions) if self.conditions else 'None'
        return f"ParsedRule:\n  LHS:\n  {lhs}\n  RHS:\n  {rhs}\n  Conditions: {cond}"


def parse_llm_output(raw_text: str) -> list[ParsedRule]:
    """
    Parse LLM-generated text into structured rewrite rules.
    
    Expected format:
        LHS:
        instruction1
        instruction2
        RHS:
        instruction3
        Condition: optional text
    
    Args:
        raw_text: Raw text output from LLM
    
    Returns:
        List of ParsedRule objects (ignores malformed rules)
    """
    rules = []
    lines = raw_text.strip().split('\n')
    
    current_rule: Optional[ParsedRule] = None
    current_section = None  # 'lhs', 'rhs', or None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check for section markers
        if line.upper().startswith('LHS:'):
            # Save previous rule if exists
            if current_rule and (current_rule.lhs_seq or current_rule.rhs_seq):
                rules.append(current_rule)
            
            # Start new rule
            current_rule = ParsedRule()
            current_section = 'lhs'
            continue
        
        elif line.upper().startswith('RHS:'):
            if current_rule:
                current_section = 'rhs'
            continue
        
        elif line.upper().startswith('CONDITION:'):
            if current_rule:
                # Extract condition text after "Condition:"
                condition_text = line[10:].strip()
                if condition_text and condition_text.lower() not in ['none', '(none)', 'null']:
                    current_rule.conditions.append(condition_text)
                current_section = None
            continue
        
        # Add instruction to current section
        if current_rule and current_section:
            # Skip comments and invalid lines
            if line.startswith('#') or line.startswith('//'):
                continue
            
            # Handle special markers
            if '(empty)' in line.lower() or 'empty' == line.lower():
                continue
            
            # Add to appropriate section
            if current_section == 'lhs':
                current_rule.lhs_seq.append(line)
            elif current_section == 'rhs':
                current_rule.rhs_seq.append(line)
    
    # Don't forget the last rule
    if current_rule and (current_rule.lhs_seq or current_rule.rhs_seq):
        rules.append(current_rule)
    
    # Filter out malformed rules (must have at least LHS)
    valid_rules = [rule for rule in rules if rule.lhs_seq]
    
    return valid_rules


def rule_to_string(rule: ParsedRule) -> str:
    """
    Convert a ParsedRule back to readable string format.
    
    Args:
        rule: The parsed rule
    
    Returns:
        Formatted string representation
    """
    result = "LHS:\n"
    for instr in rule.lhs_seq:
        result += f"  {instr}\n"
    
    result += "RHS:\n"
    if rule.rhs_seq:
        for instr in rule.rhs_seq:
            result += f"  {instr}\n"
    else:
        result += "  (empty)\n"
    
    if rule.conditions:
        result += f"Condition: {'; '.join(rule.conditions)}\n"
    
    return result
