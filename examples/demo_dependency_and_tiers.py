"""
Demo: Dependency analysis and tier scheduling features.

This demonstrates:
1. Dependency checking utilities
2. Tier 2 structural rules
3. Tier scheduler configuration
4. Enhanced statistics
"""
from asm_ir import Instruction, BasicBlock
from hierarchical_engine import (
    has_register_dependency,
    has_flag_dependency,
    are_independent,
    MAX_ITERATIONS,
    get_tier_description
)


def demo_dependency_analysis():
    """Demonstrate dependency analysis utilities."""
    print("=" * 60)
    print("DEMO 1: Dependency Analysis")
    print("=" * 60)
    
    # Independent instructions
    inst1 = Instruction(opcode="MOV", dst="eax", srcs=["ebx"])
    inst2 = Instruction(opcode="MOV", dst="ecx", srcs=["edx"])
    
    print("\nTest 1: Independent instructions")
    print(f"  {inst1}")
    print(f"  {inst2}")
    print(f"  Register dependency: {has_register_dependency(inst1, inst2)}")
    print(f"  Flag dependency: {has_flag_dependency(inst1, inst2)}")
    print(f"  Are independent: {are_independent(inst1, inst2)}")
    
    # Dependent instructions (register)
    inst3 = Instruction(opcode="MOV", dst="eax", srcs=["ebx"])
    inst4 = Instruction(opcode="ADD", dst="ecx", srcs=["eax"])
    
    print("\nTest 2: Register-dependent instructions")
    print(f"  {inst3}")
    print(f"  {inst4}")
    print(f"  Register dependency: {has_register_dependency(inst3, inst4)}")
    print(f"  Flag dependency: {has_flag_dependency(inst3, inst4)}")
    print(f"  Are independent: {are_independent(inst3, inst4)}")
    
    # Write-after-write dependency
    inst5 = Instruction(opcode="MOV", dst="eax", srcs=["5"])
    inst6 = Instruction(opcode="MOV", dst="eax", srcs=["10"])
    
    print("\nTest 3: Write-after-write dependency")
    print(f"  {inst5}")
    print(f"  {inst6}")
    print(f"  Register dependency: {has_register_dependency(inst5, inst6)}")
    print(f"  Flag dependency: {has_flag_dependency(inst5, inst6)}")
    print(f"  Are independent: {are_independent(inst5, inst6)}")
    
    # Flag dependency
    inst7 = Instruction(opcode="CMP", dst=None, srcs=["eax", "ebx"],
                       flags_written={'ZF', 'CF'})
    inst8 = Instruction(opcode="MOV", dst="ecx", srcs=["5"],
                       flags_read={'ZF'})
    
    print("\nTest 4: Flag dependency")
    print(f"  {inst7} (writes ZF, CF)")
    print(f"  {inst8} (reads ZF)")
    print(f"  Register dependency: {has_register_dependency(inst7, inst8)}")
    print(f"  Flag dependency: {has_flag_dependency(inst7, inst8)}")
    print(f"  Are independent: {are_independent(inst7, inst8)}")


def demo_tier_scheduler():
    """Demonstrate tier scheduler configuration."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Tier Scheduler Configuration")
    print("=" * 60)
    
    print("\nConfigured iteration limits:")
    for tier in sorted(MAX_ITERATIONS.keys()):
        print(f"  Tier {tier}: {MAX_ITERATIONS[tier]} iteration(s)")
        print(f"          {get_tier_description(tier)}")
    
    print("\nPurpose:")
    print("  - Controls e-graph explosion")
    print("  - Limits exploration per tier")
    print("  - Tier 0: Quick normalization")
    print("  - Tier 1: Moderate peephole search")
    print("  - Tier 2: Conservative structural rewrites")
    print("  - Tier 3: Minimal advanced optimizations")


def demo_graph_growth_stats():
    """Demonstrate graph growth statistics."""
    print("\n\n" + "=" * 60)
    print("DEMO 3: Enhanced Statistics Tracking")
    print("=" * 60)
    
    print("\nThe engine now tracks:")
    print("  1. Matches per tier")
    print("  2. Rewrites applied per tier")
    print("  3. Iterations per tier")
    print("  4. ✨ Instruction sequences added to e-graph")
    print("  5. ✨ Preconditions failed (skipped rewrites)")
    
    print("\nExample output:")
    print("  ============================================================")
    print("  REWRITE ENGINE STATISTICS")
    print("  ============================================================")
    print("  Overall:")
    print("    Total matches found: 20")
    print("    Total rewrites applied: 18")
    print("    Instruction sequences added: 18")
    print("    Preconditions failed: 2")
    print("  ============================================================")


def demo_structural_rules():
    """Demonstrate Tier 2 structural rules."""
    print("\n\n" + "=" * 60)
    print("DEMO 4: Tier 2 Structural Rules")
    print("=" * 60)
    
    print("\nNew rule: Swap Independent Instructions")
    print("  Pattern:")
    print("    instA")
    print("    instB")
    print("  →")
    print("    instB")
    print("    instA")
    
    print("\n  Precondition:")
    print("    - No register dependencies between instA and instB")
    print("    - No flag dependencies between instA and instB")
    
    print("\n  Example:")
    inst1 = Instruction(opcode="MOV", dst="eax", srcs=["5"])
    inst2 = Instruction(opcode="MOV", dst="ebx", srcs=["10"])
    
    print(f"    Original:")
    print(f"      {inst1}")
    print(f"      {inst2}")
    print(f"    Can swap: {are_independent(inst1, inst2)}")
    print(f"    Swapped:")
    print(f"      {inst2}")
    print(f"      {inst1}")


def main():
    """Run all demos."""
    demo_dependency_analysis()
    demo_tier_scheduler()
    demo_graph_growth_stats()
    demo_structural_rules()
    
    print("\n\n" + "=" * 60)
    print("All demos complete!")
    print("Run pipeline/main.py to see the full system with tier scheduling.")
    print("=" * 60)


if __name__ == "__main__":
    main()
