"""
Tier 1 peephole rewrite rule: Double ADD constant folding.
"""
from ..rule_base import InstructionPattern, RewriteRule


def double_add_precondition(match: dict) -> bool:
    """
    Ensure both ADDs use the same destination register and have numeric immediates.
    """
    if 'r1' not in match or 'imm1' not in match or 'imm2' not in match:
        return False
    
    # Check that both immediates are numeric
    try:
        int(match['imm1'])
        int(match['imm2'])
        return True
    except (ValueError, TypeError):
        return False


def double_add_transform(match: dict) -> list:
    """
    Transform the matched pattern by adding the two immediates.
    Returns the RHS pattern with the sum.
    """
    try:
        sum_val = int(match['imm1']) + int(match['imm2'])
        return [InstructionPattern(opcode="ADD", dst=match['r1'], srcs=[str(sum_val)])]
    except (ValueError, TypeError):
        # Fallback: return original if something goes wrong
        return [
            InstructionPattern(opcode="ADD", dst="r1", srcs=["imm1"]),
            InstructionPattern(opcode="ADD", dst="r1", srcs=["imm2"])
        ]


# ADD r1, imm1
# ADD r1, imm2
# →
# ADD r1, (imm1 + imm2)
# 
# Note: For pattern matching, we use variable names for immediates
# The actual transformation would need to be done dynamically
double_add_rule = RewriteRule(
    name="double_add_folding",
    tier=1,
    lhs=[
        InstructionPattern(opcode="ADD", dst="r1", srcs=["imm1"]),
        InstructionPattern(opcode="ADD", dst="r1", srcs=["imm2"])
    ],
    rhs=[
        # This is a simplified RHS - in a real implementation,
        # the actual sum would be computed during rule application
        InstructionPattern(opcode="ADD", dst="r1", srcs=["imm_sum"])
    ],
    precondition=double_add_precondition
)
