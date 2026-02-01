"""
End-to-end compilation pipeline.

Pipeline stages:
1. Parse high-level code → AST
2. Lower AST → three-address IR
3. Generate assembly from IR
4. Optimize with hierarchical rewrite engine
5. Display results
"""
from typing import List
from asm_ir import Instruction, BasicBlock
from frontend import parse, lower_to_ir, ir_to_assembly
from hierarchical_engine import HierarchicalEngine
from hierarchical_engine.egraph_api import EGraphAPI
from rewrite_rules.tier1_peephole import (
    mov_elimination_rule,
    add_sub_cancel_rule,
    mov_overwrite_rule,
    double_add_rule
)


class StubEGraph(EGraphAPI):
    """
    Stub e-graph implementation that applies rewrites directly.
    
    This modifies the block in place rather than building an e-graph.
    Sufficient for demonstrating the frontend pipeline.
    """
    
    def __init__(self):
        self.block = None  # Will be set by the engine
        self.applied_rules = []
    
    def add_sequence(self, instructions: List[Instruction]):
        """Store reference - actual modifications happen via block."""
        pass
    
    def apply_rewrite(self, rule, match):
        """
        Apply a rewrite rule by modifying the block's instructions in place.
        
        Args:
            rule: RewriteRule object with lhs and rhs patterns
            match: Match object with start_index and bindings
        """
        from rewrite_rules.rule_base import InstructionPattern
        from asm_ir import Instruction
        
        self.applied_rules.append(rule.name)
        
        # Convert RHS patterns to actual instructions using bindings
        rhs_instructions = []
        for pattern in rule.rhs:
            # Substitute variables in pattern with values from bindings
            dst = pattern.dst
            srcs = list(pattern.srcs) if pattern.srcs else []
            
            # Replace variables with bound values
            if dst and dst in match.bindings:
                dst = match.bindings[dst]
            srcs = [match.bindings.get(s, s) for s in srcs]
            
            rhs_instructions.append(Instruction(pattern.opcode, dst, srcs))
        
        # Apply replacement in the block (hacky but works for demo)
        # Get the block from the match object (it has a reference)
        if hasattr(match, 'block'):
            target_block = match.block
        else:
            # Fallback: assume we're working with a global block
            # This is set by the run_full_pipeline function
            target_block = self.block
        
        if target_block:
            start_idx = match.start_index
            lhs_len = len(rule.lhs)
            
            # Remove LHS instructions
            for _ in range(lhs_len):
                if start_idx < len(target_block.instructions):
                    target_block.instructions.pop(start_idx)
            
            # Insert RHS instructions
            for i, instr in enumerate(rhs_instructions):
                target_block.instructions.insert(start_idx + i, instr)
    
    def get_recent_eclasses(self):
        """Return empty - no e-classes in stub."""
        return []
    
    def extract_best(self) -> List[Instruction]:
        """Return the block's instructions (which we've been modifying)."""
        if self.block:
            return self.block.instructions
        return []
    
    def get_applied_rules(self) -> List[str]:
        """Return list of applied rule names."""
        return self.applied_rules


def format_instruction(instr: Instruction) -> str:
    """Format an instruction for display."""
    if instr.srcs:
        return f"{instr.opcode} {instr.dst}, {', '.join(instr.srcs)}"
    else:
        return f"{instr.opcode} {instr.dst if instr.dst else ''}"


def print_instructions(instructions: List[Instruction], title: str = "Instructions"):
    """Pretty-print a list of instructions."""
    print(f"\n{title} ({len(instructions)} instructions):")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  {i:2d}. {format_instruction(instr)}")


def run_full_pipeline(source_code: str, verbose: bool = True):
    """
    Run the complete compilation and optimization pipeline.
    
    Args:
        source_code: High-level source code string
        verbose: If True, print intermediate results
    
    Returns:
        Tuple of (original_assembly, optimized_assembly)
    """
    if verbose:
        print("=" * 70)
        print("FULL COMPILATION PIPELINE")
        print("=" * 70)
        print("\nSource Code:")
        print("-" * 50)
        print(source_code)
    
    # Stage 1: Parse
    if verbose:
        print("\nStage 1: Parsing...")
    ast = parse(source_code)
    if verbose:
        print(f"  - Generated AST with {len(ast.statements)} statements")
        for stmt in ast.statements:
            print(f"    {stmt}")
    
    # Stage 2: Lower to IR
    if verbose:
        print("\nStage 2: Lowering to IR...")
    ir_instructions = lower_to_ir(ast)
    if verbose:
        print(f"  - Generated {len(ir_instructions)} IR instructions")
        for ir_instr in ir_instructions:
            print(f"    {ir_instr}")
    
    # Stage 3: Generate assembly
    if verbose:
        print("\nStage 3: Assembly generation...")
    asm_instructions = ir_to_assembly(ir_instructions)
    if verbose:
        print(f"  - Generated {len(asm_instructions)} assembly instructions")
    
    print_instructions(asm_instructions, "Original Assembly")
    
    # Stage 4: Optimize with rewrite engine
    if verbose:
        print("\nStage 4: Optimization (hierarchical rewrite)...")
    
    # Create basic block
    basic_block = BasicBlock(asm_instructions)
    
    # Get optimization rules
    tier1_rules = [
        mov_elimination_rule,
        add_sub_cancel_rule,
        mov_overwrite_rule,
        double_add_rule
    ]
    
    # Create e-graph API (stub implementation)
    egraph_api = StubEGraph()
    egraph_api.block = basic_block  # Give stub access to block
    
    # Create and run engine
    engine = HierarchicalEngine(
        egraph_api=egraph_api,
        rules_by_tier={1: tier1_rules}
    )
    
    if verbose:
        print(f"  Running engine with {len(tier1_rules)} optimization rules...")
    
    optimized_block = engine.run(basic_block)
    
    # Stage 5: Results
    print_instructions(optimized_block.instructions, "Optimized Assembly")
    
    # Summary
    print("\n" + "=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    original_count = len(asm_instructions)
    optimized_count = len(optimized_block.instructions)
    reduction = original_count - optimized_count
    reduction_pct = (reduction / original_count * 100) if original_count > 0 else 0
    
    print(f"  Original:  {original_count} instructions")
    print(f"  Optimized: {optimized_count} instructions")
    print(f"  Reduction: {reduction} instructions ({reduction_pct:.1f}%)")
    
    if reduction > 0:
        print(f"  >> Successfully reduced code size!")
    elif reduction == 0:
        print(f"  >> No optimizations applied (already optimal)")
    
    print("=" * 70)
    
    return asm_instructions, optimized_block.instructions


def main():
    """Run example programs through the pipeline."""
    
    # Example 1: Simple arithmetic
    example1 = """a = 5
b = a + 3
c = b + 1"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 1: Simple Arithmetic")
    print("=" * 70)
    run_full_pipeline(example1)
    
    # Example 2: MOV chain optimization
    example2 = """x = 10
y = x
z = y
w = z"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: MOV Chain Elimination")
    print("=" * 70)
    run_full_pipeline(example2)
    
    # Example 3: Complex expression
    example3 = """a = 5
b = 3
c = a + b
d = c * 2
e = d - 1"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: Complex Expression")
    print("=" * 70)
    run_full_pipeline(example3)


if __name__ == "__main__":
    main()
