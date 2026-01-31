"""
Tier 1 peephole rewrite rule: ADD/SUB cancellation.
"""
from ..rule_base import InstructionPattern, RewriteRule


def add_sub_cancel_precondition(match: dict) -> bool:
    """
    Ensure both operations use the same registers.
    r1 must match and r2 must match across both instructions.
    """
    # Pattern variables r1 and r2 are already bound by the matcher
    # Just ensure they exist
    return 'r1' in match and 'r2' in match


# ADD r1, r2
# SUB r1, r2
# → remove both (they cancel out)
add_sub_cancel_rule = RewriteRule(
    name="add_sub_cancellation",
    tier=1,
    lhs=[
        InstructionPattern(opcode="ADD", dst="r1", srcs=["r2"]),
        InstructionPattern(opcode="SUB", dst="r1", srcs=["r2"])
    ],
    rhs=[],  # Empty RHS means remove both instructions
    precondition=add_sub_cancel_precondition
)
