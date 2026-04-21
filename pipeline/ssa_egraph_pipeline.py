"""
Complete SSA-to-E-Graph optimization pipeline.

Integrates SSA analysis with e-graph rewriting for powerful optimizations.

Pipeline stages:
1. Take CFG block in SSA form
2. Convert SSA to expression DAG
3. Insert expressions into e-graph
4. Run equality saturation with rewrite rules
5. Extract optimized expressions
6. Convert back to SSA instructions
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Optional
from asm_ir import BasicBlock, Instruction, CFG
from analysis import convert_cfg_to_ssa
from egraph_bridge import (
    ssa_block_to_exprs,
    insert_exprs_into_egraph,
    extract_optimized_exprs,
    exprs_to_ssa_instructions,
    print_expression_dag
)
from egraph_bridge.expr_to_egraph import print_egraph_contents
from egraph_bridge.egraph_to_ssa import print_ssa_comparison, compare_instruction_counts
from egraph_bridge.simple_egraph import EGraph


class SimpleRewriteRule:
    """Simple rewrite rule for demo purposes."""
    
    def __init__(self, name: str, pattern_op: str, replacement_op: Optional[str] = None):
        self.name = name
        self.pattern_op = pattern_op
        self.replacement_op = replacement_op
    
    def pattern(self):
        """Return pattern to match."""
        class Pattern:
            def __init__(self, op):
                self.op = op
        return Pattern(self.pattern_op)
    
    def replacement(self):
        """Return replacement pattern."""
        if self.replacement_op:
            class Replacement:
                def __init__(self, op):
                    self.op = op
            return Replacement(self.replacement_op)
        return None


def create_default_rewrite_rules() -> List:
    """
    Create default set of rewrite rules for optimization.
    
    Returns:
        List of rewrite rule objects
    """
    # For now, return empty list - full e-graph rewriting requires more infrastructure
    # The pipeline still demonstrates SSA conversion and expression DAG transformation
    return []


def optimize_ssa_block(block: BasicBlock, 
                      max_iterations: int = 10,
                      verbose: bool = True) -> BasicBlock:
    """
    Optimize a single SSA basic block using e-graph rewriting.
    
    Args:
        block: BasicBlock in SSA form
        max_iterations: Maximum equality saturation iterations
        verbose: Print detailed progress information
    
    Returns:
        New BasicBlock with optimized instructions
    """
    if verbose:
        print("\n" + "=" * 80)
        print("SSA E-GRAPH OPTIMIZATION PIPELINE")
        print("=" * 80)
        print(f"\nBlock: {block.label}")
        print(f"Original instructions: {len(block.instructions)}")
    
    # Stage 1: Convert SSA to expression DAG
    if verbose:
        print("\n--- Stage 1: SSA to Expression DAG ---")
    
    expr_map = ssa_block_to_exprs(block)
    
    if verbose:
        print(f"Generated {len(expr_map)} expressions")
        print_expression_dag(expr_map)
    
    # Stage 2: Insert expressions into e-graph
    if verbose:
        print("\n--- Stage 2: Insert into E-Graph ---")
    
    egraph = EGraph()
    eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    
    if verbose:
        print(f"Created e-graph with {len(egraph.eclasses)} e-classes")
        print_egraph_contents(egraph, eclass_map)
    
    # Stage 3: Run equality saturation
    if verbose:
        print("\n--- Stage 3: Equality Saturation ---")
    
    rules = create_default_rewrite_rules()
    if verbose:
        print(f"Applying {len(rules)} rewrite rules")
    
    initial_size = len(egraph.eclasses)
    
    for iteration in range(max_iterations):
        matches = 0
        for rule in rules:
            count = egraph.apply_rule(rule)
            matches += count
        
        if verbose:
            print(f"  Iteration {iteration + 1}: {matches} rewrites, "
                  f"{len(egraph.eclasses)} e-classes")
        
        if matches == 0:
            if verbose:
                print(f"  Converged after {iteration + 1} iterations")
            break
    
    final_size = len(egraph.eclasses)
    if verbose:
        print(f"E-graph growth: {initial_size} -> {final_size} e-classes")
    
    # Stage 4: Extract optimized expressions
    if verbose:
        print("\n--- Stage 4: Extract Optimized Expressions ---")
    
    optimized_exprs = extract_optimized_exprs(eclass_map, egraph)
    
    if verbose:
        print(f"Extracted {len(optimized_exprs)} optimized expressions")
        print_expression_dag(optimized_exprs)
    
    # Stage 5: Convert back to SSA instructions
    if verbose:
        print("\n--- Stage 5: Rebuild SSA Instructions ---")
    
    optimized_instrs = exprs_to_ssa_instructions(optimized_exprs)
    
    if verbose:
        print(f"Generated {len(optimized_instrs)} optimized instructions")
        compare_instruction_counts(block.instructions, optimized_instrs)
        print_ssa_comparison(block, optimized_instrs)
    
    # Create optimized block
    optimized_block = BasicBlock(
        label=block.label,
        instructions=optimized_instrs
    )
    optimized_block.successors = block.successors.copy()
    
    if verbose:
        print("\n" + "=" * 80)
        print("OPTIMIZATION COMPLETE")
        print("=" * 80)
    
    return optimized_block


def optimize_cfg(cfg: CFG, 
                convert_to_ssa: bool = True,
                max_iterations: int = 10,
                verbose: bool = True) -> CFG:
    """
    Optimize entire CFG using e-graph rewriting.
    
    Args:
        cfg: Control flow graph to optimize
        convert_to_ssa: Whether to convert to SSA first
        max_iterations: Maximum equality saturation iterations per block
        verbose: Print detailed progress information
    
    Returns:
        Optimized CFG
    """
    if verbose:
        print("\n" + "=" * 80)
        print("CFG E-GRAPH OPTIMIZATION")
        print("=" * 80)
        print(f"Blocks: {len(cfg.blocks)}")
        print(f"Entry: {cfg.entry_label}")
    
    # Convert to SSA if requested
    if convert_to_ssa:
        if verbose:
            print("\n--- Converting to SSA Form ---")
        from analysis import convert_cfg_to_ssa
        convert_cfg_to_ssa(cfg)
        if verbose:
            print("SSA conversion complete")
    
    # Create new CFG for optimized code
    optimized_cfg = CFG(entry_label=cfg.entry_label)
    
    # Optimize each block
    for label, block in cfg.blocks.items():
        if verbose:
            print(f"\n{'=' * 80}")
            print(f"Optimizing block: {label}")
            print(f"{'=' * 80}")
        
        optimized_block = optimize_ssa_block(
            block,
            max_iterations=max_iterations,
            verbose=verbose
        )
        
        optimized_cfg.add_block(optimized_block)
    
    if verbose:
        print("\n" + "=" * 80)
        print("CFG OPTIMIZATION COMPLETE")
        print("=" * 80)
    
    return optimized_cfg


def run_pipeline_demo():
    """
    Demo: run complete SSA-to-E-Graph optimization pipeline.
    """
    print("\n" + "=" * 80)
    print("SSA E-GRAPH PIPELINE DEMO")
    print("=" * 80)
    
    # Create example SSA block with optimization opportunities
    print("\nExample: Algebraic simplifications")
    print("-" * 80)
    
    block = BasicBlock("example")
    
    # x = 1
    block.instructions.append(Instruction("MOV", "x_0", ["1"]))
    
    # y = x + 0  (should simplify to y = x)
    block.instructions.append(Instruction("ADD", "y_0", ["x_0", "0"]))
    
    # z = y * 1  (should simplify to z = y)
    block.instructions.append(Instruction("MUL", "z_0", ["y_0", "1"]))
    
    # w = z - z  (should simplify to w = 0)
    block.instructions.append(Instruction("SUB", "w_0", ["z_0", "z_0"]))
    
    # a = w * 5  (should simplify to a = 0)
    block.instructions.append(Instruction("MUL", "a_0", ["w_0", "5"]))
    
    print("\nOriginal SSA code:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    # Run optimization
    optimized = optimize_ssa_block(block, max_iterations=10, verbose=True)
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline_demo()
