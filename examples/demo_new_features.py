"""
Demo: All new features of the hierarchical assembly rewrite system.

This demonstrates:
1. Instruction read/write metadata
2. Tier 0 normalization
3. New Tier 1 peephole rules
4. Statistics logging
"""
from asm_ir import Instruction, BasicBlock
from rewrite_rules.tier0_normalization import normalize_block
from rewrite_rules.tier1_peephole import (
    mov_elimination_rule,
    add_sub_cancel_rule,
    mov_overwrite_rule,
    double_add_rule
)


def demo_read_write_metadata():
    """Demonstrate instruction read/write metadata."""
    print("=" * 60)
    print("DEMO 1: Instruction Read/Write Metadata")
    print("=" * 60)
    
    instructions = [
        Instruction(opcode="MOV", dst="eax", srcs=["ebx"]),
        Instruction(opcode="ADD", dst="ecx", srcs=["5"]),
        Instruction(opcode="SUB", dst="edx", srcs=["esi"]),
        Instruction(opcode="MUL", dst="edi", srcs=["2"]),
        Instruction(opcode="CMP", dst=None, srcs=["eax", "ebx"]),
    ]
    
    for instr in instructions:
        print(f"\n{instr}")
        print(f"  Reads:  {instr.reads()}")
        print(f"  Writes: {instr.writes()}")


def demo_tier0_normalization():
    """Demonstrate Tier 0 normalization."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Tier 0 Normalization")
    print("=" * 60)
    
    instructions = [
        Instruction(opcode="MOV", dst="EAX", srcs=["EBX"]),  # Uppercase
        Instruction(opcode="MOV", dst="ecx", srcs=["ecx"]),  # Self-move
        Instruction(opcode="ADD", dst="EDX", srcs=["0"]),    # ADD zero
        Instruction(opcode="SUB", dst="ESI", srcs=["0"]),    # SUB zero
        Instruction(opcode="MUL", dst="EDI", srcs=["2"]),
    ]
    
    block = BasicBlock(instructions)
    print("\nOriginal:")
    print(block)
    
    normalized = normalize_block(block)
    print(f"\nNormalized ({len(normalized)} instructions):")
    print(normalized)
    print("\nChanges:")
    print("  - Converted to lowercase")
    print("  - Removed MOV ecx, ecx (self-move)")
    print("  - Removed ADD edx, 0")
    print("  - Removed SUB esi, 0")


def demo_new_peephole_rules():
    """Demonstrate new Tier 1 peephole rules."""
    print("\n\n" + "=" * 60)
    print("DEMO 3: New Tier 1 Peephole Rules")
    print("=" * 60)
    
    # Rule 1: ADD/SUB cancellation
    print("\n--- Rule 1: ADD/SUB Cancellation ---")
    print("Pattern: ADD r1, r2; SUB r1, r2 → (remove both)")
    print(f"Rule: {add_sub_cancel_rule.name}")
    
    # Rule 2: MOV overwrite
    print("\n--- Rule 2: MOV Overwrite Elimination ---")
    print("Pattern: MOV r1, r2; MOV r1, r3 → MOV r1, r3")
    print(f"Rule: {mov_overwrite_rule.name}")
    
    # Rule 3: Double ADD
    print("\n--- Rule 3: Double ADD Folding ---")
    print("Pattern: ADD r1, 1; ADD r1, 1 → ADD r1, 2")
    print(f"Rule: {double_add_rule.name}")


def demo_statistics():
    """Demonstrate statistics logging."""
    print("\n\n" + "=" * 60)
    print("DEMO 4: Statistics Logging")
    print("=" * 60)
    print("\nThe engine now tracks:")
    print("  - Total matches found")
    print("  - Total rewrites applied")
    print("  - Per-tier breakdown:")
    print("    • Matches per tier")
    print("    • Rewrites per tier")
    print("    • Iterations per tier")
    print("\nSee main.py output for example statistics.")


def main():
    """Run all demos."""
    demo_read_write_metadata()
    demo_tier0_normalization()
    demo_new_peephole_rules()
    demo_statistics()
    
    print("\n\n" + "=" * 60)
    print("All demos complete!")
    print("Run pipeline/main.py to see the full system in action.")
    print("=" * 60)


if __name__ == "__main__":
    main()
