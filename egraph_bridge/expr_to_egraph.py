"""
Insert expression DAG nodes into an e-graph for optimization.

Recursively inserts expression trees into the e-graph, creating ENodes
and tracking their e-classes.
"""
from typing import Dict, Optional
from .ssa_to_expr import ExprNode
from .simple_egraph import EGraph, EClass, ENode


def insert_expr_into_egraph(expr: ExprNode, egraph: EGraph, 
                            memo: Optional[Dict[ExprNode, int]] = None) -> int:
    """
    Insert an expression into the e-graph recursively.
    
    Args:
        expr: Expression node to insert
        egraph: E-graph to insert into
        memo: Memoization dictionary to avoid duplicates
    
    Returns:
        E-class ID representing the expression
    
    Example:
        >>> expr = ExprNode("add", [
        ...     ExprNode("const", value=1),
        ...     ExprNode("const", value=2)
        ... ])
        >>> eclass_id = insert_expr_into_egraph(expr, egraph)
    """
    if memo is None:
        memo = {}
    
    # Check if we've already inserted this expression
    if expr in memo:
        return memo[expr]
    
    # Handle constants
    if expr.is_constant():
        # Create constant ENode
        enode = ENode("const", [expr.value])
        eclass_id = egraph.add(enode)
        memo[expr] = eclass_id
        return eclass_id
    
    # Handle variables
    if expr.is_variable():
        # Create variable ENode
        enode = ENode("var", [expr.value])
        eclass_id = egraph.add(enode)
        memo[expr] = eclass_id
        return eclass_id
    
    # Handle operations - recursively insert children first
    child_eclasses = []
    for child in expr.children:
        child_eclass = insert_expr_into_egraph(child, egraph, memo)
        child_eclasses.append(child_eclass)
    
    # Create ENode for this operation
    enode = ENode(expr.op, child_eclasses)
    eclass_id = egraph.add(enode)
    memo[expr] = eclass_id
    
    return eclass_id


def insert_exprs_into_egraph(expr_map: Dict[str, ExprNode], egraph: EGraph) -> Dict[str, int]:
    """
    Insert multiple expressions into e-graph.
    
    Args:
        expr_map: Dictionary mapping variable names to expressions
        egraph: E-graph to insert into
    
    Returns:
        Dictionary mapping variable names to their e-class IDs
    
    Example:
        >>> expr_map = {
        ...     "x_0": ExprNode("const", value=1),
        ...     "x_1": ExprNode("add", [ExprNode("var", value="x_0"), ...])
        ... }
        >>> eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    """
    eclass_map: Dict[str, int] = {}
    memo: Dict[ExprNode, int] = {}
    
    # Insert each expression
    for var_name, expr in expr_map.items():
        eclass_id = insert_expr_into_egraph(expr, egraph, memo)
        eclass_map[var_name] = eclass_id
    
    return eclass_map


def extract_expr_from_egraph(eclass_id: int, egraph: EGraph, 
                             cost_fn=None) -> ExprNode:
    """
    Extract the best expression from an e-class.
    
    Args:
        eclass_id: E-class ID to extract from
        egraph: E-graph containing the e-class
        cost_fn: Optional cost function for choosing best representation
    
    Returns:
        ExprNode representing the best expression in the e-class
    """
    if cost_fn is None:
        cost_fn = default_cost
    
    eclass = egraph.eclasses[eclass_id]
    
    # Find best (lowest cost) ENode in this e-class
    best_node = None
    best_cost = float('inf')
    
    for enode in eclass.nodes:
        # Calculate cost of this node
        node_cost = cost_fn(enode, egraph)
        if node_cost < best_cost:
            best_cost = node_cost
            best_node = enode
    
    if best_node is None:
        raise ValueError(f"No nodes found in e-class {eclass_id}")
    
    # Convert ENode back to ExprNode
    return enode_to_expr(best_node, egraph, cost_fn)


def enode_to_expr(enode: ENode, egraph: EGraph, cost_fn) -> ExprNode:
    """
    Convert an ENode back to an ExprNode.
    
    Args:
        enode: ENode to convert
        egraph: E-graph containing related nodes
        cost_fn: Cost function for extracting child expressions
    
    Returns:
        ExprNode representation
    """
    op = enode.op
    
    # Handle constants
    if op == "const":
        return ExprNode(op="const", value=enode.children[0])
    
    # Handle variables
    if op == "var":
        return ExprNode(op="var", value=enode.children[0])
    
    # Handle operations - recursively extract children
    child_exprs = []
    for child_eclass_id in enode.children:
        child_expr = extract_expr_from_egraph(child_eclass_id, egraph, cost_fn)
        child_exprs.append(child_expr)
    
    return ExprNode(op=op, children=child_exprs)


def default_cost(enode: ENode, egraph: EGraph) -> float:
    """
    Default cost function for expression extraction.
    
    Prefers simpler expressions (fewer nodes, constants over variables).
    
    Args:
        enode: ENode to compute cost for
        egraph: E-graph containing the node
    
    Returns:
        Cost value (lower is better)
    """
    # Constants have cost 1
    if enode.op == "const":
        return 1.0
    
    # Variables have cost 2
    if enode.op == "var":
        return 2.0
    
    # Operations: base cost + sum of child costs
    base_cost = 10.0
    child_cost = 0.0
    
    for child_eclass_id in enode.children:
        if isinstance(child_eclass_id, int):
            # Get minimum cost from child e-class
            eclass = egraph.eclasses[child_eclass_id]
            min_child_cost = float('inf')
            for child_node in eclass.nodes:
                cost = default_cost(child_node, egraph)
                if cost < min_child_cost:
                    min_child_cost = cost
            child_cost += min_child_cost
    
    return base_cost + child_cost


def print_egraph_contents(egraph: EGraph, eclass_map: Dict[str, int]):
    """
    Print e-graph contents for debugging.
    
    Args:
        egraph: E-graph to print
        eclass_map: Mapping of variable names to e-class IDs
    """
    print("\nE-Graph Contents:")
    print("=" * 60)
    print(f"Total e-classes: {len(egraph.eclasses)}")
    print(f"Variables tracked: {len(eclass_map)}")
    
    print("\nVariable -> E-Class Mapping:")
    for var, eclass_id in sorted(eclass_map.items()):
        eclass = egraph.eclasses[eclass_id]
        print(f"  {var} -> e-class {eclass_id} ({len(eclass.nodes)} nodes)")
        for node in eclass.nodes:
            print(f"    - {node}")
    
    print("=" * 60)
