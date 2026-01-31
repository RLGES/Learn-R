"""
Tier 1 peephole rewrite rule: MOV overwrite elimination.
"""
from ..rule_base import InstructionPattern, RewriteRule


def mov_overwrite_precondition(match: dict) -> bool:
    """
    Ensure both MOVs write to the same register.
    The first MOV is dead because r1 is immediately overwritten.
    """
    return 'r1' in match


# MOV r1, r2
# MOV r1, r3
# →
# MOV r1, r3
mov_overwrite_rule = RewriteRule(
    name="mov_overwrite_elimination",
    tier=1,
    lhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["r2"]),
        InstructionPattern(opcode="MOV", dst="r1", srcs=["r3"])
    ],
    rhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["r3"])
    ],
    precondition=mov_overwrite_precondition
)
