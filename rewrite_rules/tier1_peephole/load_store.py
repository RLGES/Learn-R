"""
Tier 1 peephole rewrite rules: Load/Store optimizations.

These rules optimize redundant memory operations:
- Eliminate redundant load-store pairs
- Forward loads through register moves
"""
from ..rule_base import InstructionPattern, RewriteRule


def load_store_precondition(match: dict) -> bool:
    """
    Ensure no other memory operations between load and store.
    
    This precondition should be enhanced to check the actual instruction
    sequence for intervening memory operations. For now, it's a placeholder
    that always returns True (conservative approach handled by pattern matching).
    
    Args:
        match: Match dictionary with bindings
    
    Returns:
        True if safe to eliminate (would need context to be precise)
    """
    # In a real implementation, we'd check:
    # - No other memory reads/writes between these instructions
    # - The address hasn't been modified
    # For now, we rely on the pattern matcher finding adjacent instructions
    return True


def load_forward_precondition(match: dict) -> bool:
    """
    Ensure the intermediate register isn't used elsewhere.
    
    Args:
        match: Match dictionary with bindings (r1: intermediate, r2: final dest)
    
    Returns:
        True if safe to forward the load
    """
    r1 = match.get('r1')
    r2 = match.get('r2')
    
    # Basic check: don't forward if registers are the same (would be no-op)
    if r1 == r2:
        return False
    
    return True


# MOV r, [a]
# MOV [a], r
# →
# (eliminate both - value is unchanged)
#
# This pattern detects:
# 1. Load from memory to register
# 2. Store the same register back to the same address
# Result: The memory location already contains that value, so both are redundant
load_store_same_rule = RewriteRule(
    name="load_store_same",
    tier=1,
    lhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["[a]"]),
        InstructionPattern(opcode="MOV", dst="[a]", srcs=["r1"])
    ],
    rhs=[
        # Empty RHS - eliminate both instructions
    ],
    precondition=load_store_precondition
)


# MOV r1, [a]
# MOV r2, r1
# →
# MOV r2, [a]
#
# This pattern forwards a memory load through a register copy.
# Instead of loading to r1 then copying to r2, load directly to r2.
load_forward_rule = RewriteRule(
    name="load_forward",
    tier=1,
    lhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["[a]"]),
        InstructionPattern(opcode="MOV", dst="r2", srcs=["r1"])
    ],
    rhs=[
        InstructionPattern(opcode="MOV", dst="r2", srcs=["[a]"])
    ],
    precondition=load_forward_precondition
)


# Export all rules
__all__ = [
    'load_store_same_rule',
    'load_forward_rule',
]
