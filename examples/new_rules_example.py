"""
Example: Adding a new rewrite rule to the system.

This demonstrates how to extend the system with additional optimization rules.
"""
from asm_ir import Instruction, BasicBlock
from rewrite_rules import InstructionPattern, RewriteRule
from hierarchical_engine import HierarchicalEngine, Matcher


# Define a new rule: Identity move elimination
# MOV r1, r1 → (remove)
identity_mov_rule = RewriteRule(
    name="identity_mov_elimination",
    tier=1,
    lhs=[
        InstructionPattern(opcode="MOV", dst="r1", srcs=["r1"])
    ],
    rhs=[],  # Empty RHS means delete the instruction
    precondition=lambda match: True
)


# Define another rule: ADD with zero
# ADD r1, 0 → (remove, r1 unchanged)
add_zero_rule = RewriteRule(
    name="add_zero_elimination",
    tier=1,
    lhs=[
        InstructionPattern(opcode="ADD", dst="r1", srcs=["0"])
    ],
    rhs=[],
    precondition=lambda match: True
)


def test_new_rules():
    """Test the new rules."""
    print("Testing new optimization rules\n")
    
    # Test case 1: Identity MOV
    print("Test 1: Identity MOV elimination")
    instructions = [
        Instruction(opcode="MOV", dst="eax", srcs=["ebx"]),
        Instruction(opcode="MOV", dst="ecx", srcs=["ecx"]),  # Identity
        Instruction(opcode="ADD", dst="eax", srcs=["ecx"]),
    ]
    block = BasicBlock(instructions)
    print(f"Original:\n{block}\n")
    
    matcher = Matcher()
    matches = matcher.find_matches(identity_mov_rule.lhs, block)
    print(f"Found {len(matches)} identity MOV(s):")
    for match in matches:
        print(f"  {match}")
    
    # Test case 2: ADD with zero
    print("\n\nTest 2: ADD zero elimination")
    instructions = [
        Instruction(opcode="MOV", dst="eax", srcs=["5"]),
        Instruction(opcode="ADD", dst="eax", srcs=["0"]),  # No-op
        Instruction(opcode="MUL", dst="eax", srcs=["2"]),
    ]
    block = BasicBlock(instructions)
    print(f"Original:\n{block}\n")
    
    matches = matcher.find_matches(add_zero_rule.lhs, block)
    print(f"Found {len(matches)} ADD-zero operation(s):")
    for match in matches:
        print(f"  {match}")


if __name__ == "__main__":
    test_new_rules()
