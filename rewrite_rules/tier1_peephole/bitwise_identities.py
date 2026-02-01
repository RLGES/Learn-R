"""
Tier 1 peephole rewrite rules: Bitwise identity optimizations.

These rules eliminate redundant bitwise operations:
- AND with 0 always results in 0
- OR with 0 is a no-op (identity)
- XOR with 0 is a no-op (identity)
- XOR with self results in 0
- Shifts by 0 are no-ops
"""
from ..rule_base import InstructionPattern, RewriteRule


# AND r, 0 → MOV r, 0
# Bitwise AND with 0 always produces 0
and_with_zero_rule = RewriteRule(
    name="and_with_zero",
    tier=1,
    lhs=[
        InstructionPattern(opcode="AND", dst="r1", srcs=["0"])
    ],
    rhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["0"])
    ],
    precondition=lambda match: True
)


# OR r, 0 → (eliminate - no-op)
# Bitwise OR with 0 leaves the value unchanged
or_with_zero_rule = RewriteRule(
    name="or_with_zero",
    tier=1,
    lhs=[
        InstructionPattern(opcode="OR", dst="r1", srcs=["0"])
    ],
    rhs=[
        # Empty RHS means eliminate the instruction
    ],
    precondition=lambda match: True
)


# XOR r, 0 → (eliminate - no-op)
# Bitwise XOR with 0 leaves the value unchanged
xor_with_zero_rule = RewriteRule(
    name="xor_with_zero",
    tier=1,
    lhs=[
        InstructionPattern(opcode="XOR", dst="r1", srcs=["0"])
    ],
    rhs=[
        # Empty RHS means eliminate the instruction
    ],
    precondition=lambda match: True
)


def xor_self_precondition(match: dict) -> bool:
    """
    Ensure that XOR is operating on the same register.
    
    Args:
        match: Dictionary with bindings for r1 (dst) and r2 (src)
    
    Returns:
        True if dst == src (XOR r, r)
    """
    r1 = match.get('r1')
    r2 = match.get('r2')
    
    return r1 == r2


# XOR r, r → MOV r, 0
# XOR of a value with itself always produces 0
xor_self_rule = RewriteRule(
    name="xor_self",
    tier=1,
    lhs=[
        InstructionPattern(opcode="XOR", dst="r1", srcs=["r2"])
    ],
    rhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["0"])
    ],
    precondition=xor_self_precondition
)


# SHL r, 0 → (eliminate - no-op)
# Left shift by 0 leaves the value unchanged
shl_by_zero_rule = RewriteRule(
    name="shl_by_zero",
    tier=1,
    lhs=[
        InstructionPattern(opcode="SHL", dst="r1", srcs=["0"])
    ],
    rhs=[
        # Empty RHS means eliminate the instruction
    ],
    precondition=lambda match: True
)


# SHR r, 0 → (eliminate - no-op)
# Right shift by 0 leaves the value unchanged
shr_by_zero_rule = RewriteRule(
    name="shr_by_zero",
    tier=1,
    lhs=[
        InstructionPattern(opcode="SHR", dst="r1", srcs=["0"])
    ],
    rhs=[
        # Empty RHS means eliminate the instruction
    ],
    precondition=lambda match: True
)


# Export all rules
__all__ = [
    'and_with_zero_rule',
    'or_with_zero_rule',
    'xor_with_zero_rule',
    'xor_self_rule',
    'shl_by_zero_rule',
    'shr_by_zero_rule',
]
