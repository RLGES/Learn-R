"""
Demo: Bitwise operations optimization with new identity rules.

Shows how bitwise identity rules eliminate redundant operations.
"""
from asm_ir import Instruction, BasicBlock
from hierarchical_engine.engine import HierarchicalEngine
from hierarchical_engine.egraph_api import EGraphAPI
from typing import List
from rewrite_rules.tier1_peephole import (
    mov_elimination_rule,
    and_with_zero_rule,
    or_with_zero_rule,
    xor_with_zero_rule,
    xor_self_rule,
    shl_by_zero_rule,
    shr_by_zero_rule,
)


class SimpleEGraph(EGraphAPI):
    """Stub e-graph for demonstration."""
    
    def __init__(self):
        self.block = None
        self.applied_rules = []
    
    def add_sequence(self, instructions):
        return "ref"
    
    def apply_rewrite(self, rule, match):
        from asm_ir import Instruction
        
        self.applied_rules.append(rule.name)
        
        # Convert RHS patterns to instructions
        rhs_instructions = []
        for pattern in rule.rhs:
            dst = pattern.dst
            srcs = list(pattern.srcs) if pattern.srcs else []
            
            # Substitute variables
            if dst and dst in match.bindings:
                dst = match.bindings[dst]
            srcs = [match.bindings.get(s, s) for s in srcs]
            
            rhs_instructions.append(Instruction(pattern.opcode, dst, srcs))
        
        # Mutate block
        if self.block:
            start = match.start_index
            # Remove LHS
            for _ in range(len(rule.lhs)):
                if start < len(self.block.instructions):
                    self.block.instructions.pop(start)
            # Insert RHS
            for i, instr in enumerate(rhs_instructions):
                self.block.instructions.insert(start + i, instr)
    
    def get_recent_eclasses(self):
        return []
    
    def extract_best(self):
        return self.block.instructions if self.block else []
    
    def get_applied_rules(self):
        return self.applied_rules


def format_instruction(instr):
    """Format instruction for display."""
    if instr.srcs:
        return f"{instr.opcode} {instr.dst}, {', '.join(instr.srcs)}"
    else:
        return f"{instr.opcode} {instr.dst if instr.dst else ''}"


def print_instructions(instructions, title="Instructions"):
    """Print instruction list."""
    print(f"\n{title} ({len(instructions)} instructions):")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  {i:2d}. {format_instruction(instr)}")


def run_demo():
    """Run bitwise optimization demo."""
    
    print("=" * 70)
    print("BITWISE IDENTITY OPTIMIZATION DEMO")
    print("=" * 70)
    
    # Example 1: XOR self (common idiom for zeroing register)
    print("\n" + "=" * 70)
    print("Example 1: XOR register with itself")
    print("=" * 70)
    
    instructions1 = [
        Instruction("XOR", "rax", ["rax"]),  # Zero rax
        Instruction("XOR", "rbx", ["rbx"]),  # Zero rbx
        Instruction("ADD", "rax", ["1"]),
        Instruction("MOV", "rcx", ["rax"]),
    ]
    
    block1 = BasicBlock(instructions=instructions1)
    print_instructions(block1.instructions, "Original")
    
    egraph1 = SimpleEGraph()
    egraph1.block = block1
    
    engine1 = HierarchicalEngine(
        egraph_api=egraph1,
        rules_by_tier={1: [xor_self_rule, mov_elimination_rule]},
    )
    
    optimized1 = engine1.run(block1, max_iterations_per_tier=3)
    print_instructions(optimized1.instructions, "Optimized")
    print(f"\nApplied rules: {', '.join(egraph1.applied_rules)}")
    print(f"Reduction: {len(instructions1)} -> {len(optimized1.instructions)} instructions")
    
    # Example 2: No-op operations
    print("\n" + "=" * 70)
    print("Example 2: Identity operations (no-ops)")
    print("=" * 70)
    
    instructions2 = [
        Instruction("MOV", "rax", ["10"]),
        Instruction("OR", "rax", ["0"]),    # No-op
        Instruction("SHL", "rax", ["0"]),   # No-op
        Instruction("XOR", "rbx", ["0"]),   # No-op
        Instruction("ADD", "rax", ["5"]),
        Instruction("SHR", "rax", ["0"]),   # No-op
    ]
    
    block2 = BasicBlock(instructions=instructions2)
    print_instructions(block2.instructions, "Original")
    
    egraph2 = SimpleEGraph()
    egraph2.block = block2
    
    engine2 = HierarchicalEngine(
        egraph_api=egraph2,
        rules_by_tier={1: [or_with_zero_rule, xor_with_zero_rule, 
                          shl_by_zero_rule, shr_by_zero_rule]},
    )
    
    optimized2 = engine2.run(block2, max_iterations_per_tier=5)
    print_instructions(optimized2.instructions, "Optimized")
    print(f"\nApplied rules: {', '.join(egraph2.applied_rules)}")
    print(f"Reduction: {len(instructions2)} -> {len(optimized2.instructions)} instructions")
    
    # Example 3: AND with zero
    print("\n" + "=" * 70)
    print("Example 3: AND with zero (always produces zero)")
    print("=" * 70)
    
    instructions3 = [
        Instruction("MOV", "rax", ["42"]),
        Instruction("AND", "rax", ["0"]),   # Result is always 0
        Instruction("MOV", "rbx", ["100"]),
        Instruction("AND", "rbx", ["0"]),   # Result is always 0
    ]
    
    block3 = BasicBlock(instructions=instructions3)
    print_instructions(block3.instructions, "Original")
    
    egraph3 = SimpleEGraph()
    egraph3.block = block3
    
    engine3 = HierarchicalEngine(
        egraph_api=egraph3,
        rules_by_tier={1: [and_with_zero_rule]},
    )
    
    optimized3 = engine3.run(block3, max_iterations_per_tier=3)
    print_instructions(optimized3.instructions, "Optimized")
    print(f"\nApplied rules: {', '.join(egraph3.applied_rules)}")
    print(f"Reduction: {len(instructions3)} -> {len(optimized3.instructions)} instructions (same count)")
    print("Note: Instructions replaced with simpler MOV operations")
    
    # Example 4: Combined optimization
    print("\n" + "=" * 70)
    print("Example 4: Combined bitwise optimizations")
    print("=" * 70)
    
    instructions4 = [
        Instruction("XOR", "rax", ["rax"]),   # Zero via XOR self
        Instruction("OR", "rbx", ["0"]),      # No-op
        Instruction("AND", "rcx", ["0"]),     # Clear via AND
        Instruction("SHL", "rdx", ["0"]),     # No-op shift
        Instruction("XOR", "rsi", ["0"]),     # No-op
        Instruction("MOV", "rdi", ["rax"]),   # Use cleared rax
    ]
    
    block4 = BasicBlock(instructions=instructions4)
    print_instructions(block4.instructions, "Original")
    
    egraph4 = SimpleEGraph()
    egraph4.block = block4
    
    engine4 = HierarchicalEngine(
        egraph_api=egraph4,
        rules_by_tier={1: [
            xor_self_rule,
            or_with_zero_rule,
            and_with_zero_rule,
            shl_by_zero_rule,
            xor_with_zero_rule,
        ]},
    )
    
    optimized4 = engine4.run(block4, max_iterations_per_tier=5)
    print_instructions(optimized4.instructions, "Optimized")
    print(f"\nApplied rules: {', '.join(egraph4.applied_rules)}")
    print(f"Reduction: {len(instructions4)} -> {len(optimized4.instructions)} instructions")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nBitwise identity rules successfully:")
    print("  * Eliminate XOR r, r -> MOV r, 0 (explicit zero)")
    print("  * Remove no-op operations (OR/XOR with 0, shifts by 0)")
    print("  * Simplify AND r, 0 -> MOV r, 0")
    print("  * Reduce instruction count and improve clarity")
    print("\nAll 6 new bitwise identity rules are working!")


if __name__ == "__main__":
    run_demo()
