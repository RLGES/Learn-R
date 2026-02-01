"""
E-graph bridge for SSA optimization.

Connects SSA-form intermediate representation with the equality saturation
e-graph rewriting engine for powerful optimizations.
"""
from .ssa_to_expr import (
    ExprNode,
    ssa_block_to_exprs,
    print_expression_dag,
    parse_operand,
    simplify_expression,
    topological_sort_exprs
)
from .expr_to_egraph import (
    insert_expr_into_egraph,
    insert_exprs_into_egraph,
    extract_expr_from_egraph,
    print_egraph_contents
)
from .egraph_to_ssa import (
    exprs_to_ssa_instructions,
    extract_optimized_exprs,
    print_ssa_comparison,
    compare_instruction_counts
)
from .simple_egraph import EGraph, EClass, ENode

__all__ = [
    # Expression nodes
    'ExprNode',
    'parse_operand',
    'simplify_expression',
    
    # SSA to expression
    'ssa_block_to_exprs',
    'print_expression_dag',
    'topological_sort_exprs',
    
    # Expression to e-graph
    'insert_expr_into_egraph',
    'insert_exprs_into_egraph',
    'extract_expr_from_egraph',
    'print_egraph_contents',
    
    # E-graph to SSA
    'exprs_to_ssa_instructions',
    'extract_optimized_exprs',
    'print_ssa_comparison',
    'compare_instruction_counts',
    
    # E-graph structures
    'EGraph',
    'EClass',
    'ENode',
]
