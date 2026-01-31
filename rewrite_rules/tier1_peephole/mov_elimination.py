"""
Tier 1 peephole rewrite rule: MOV elimination.
"""
from ..rule_base import InstructionPattern, RewriteRule


def mov_chain_precondition(match: dict) -> bool:
    """
    Ensure the intermediate register is not used elsewhere.
    For now, this is a placeholder - full liveness analysis would be needed.
    """
    # Basic check: ensure r1 != r2 and r1 != r3 to avoid trivial cases
    r1 = match.get('r1')
    r2 = match.get('r2')
    r3 = match.get('r3')
    
    if r1 == r2 or r1 == r3:
        return False
    
    return True


# MOV r1, r2
# MOV r3, r1
# →
# MOV r3, r2
mov_elimination_rule = RewriteRule(
    name="mov_chain_elimination",
    tier=1,
    lhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["r2"]),
        InstructionPattern(opcode="MOV", dst="r3", srcs=["r1"])
    ],
    rhs=[
        InstructionPattern(opcode="MOV", dst="r3", srcs=["r2"])
    ],
    precondition=mov_chain_precondition
)
