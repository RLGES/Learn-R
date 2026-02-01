"""
Extract optimized expressions from e-graph and convert back to SSA instructions.

After equality saturation, extracts the best representation and rebuilds
SSA instructions in dependency order.
"""
from typing import Dict, List, Set
from .ssa_to_expr import ExprNode, topological_sort_exprs
from .expr_to_egraph import extract_expr_from_egraph, default_cost
from asm_ir import Instruction
from .simple_egraph import EGraph


def extract_optimized_exprs(eclass_map: Dict[str, int], egraph: EGraph,
                            cost_fn=None) -> Dict[str, ExprNode]:
    """
    Extract optimized expressions from e-graph.
    
    For each variable, extracts the best (lowest cost) representation
    from its e-class.
    
    Args:
        eclass_map: Mapping of variable names to e-class IDs
        egraph: E-graph after optimization
        cost_fn: Optional cost function for extraction
    
    Returns:
        Dictionary mapping variable names to optimized expressions
    """
    if cost_fn is None:
        cost_fn = default_cost
    
    optimized_exprs: Dict[str, ExprNode] = {}
    
    from .ssa_to_expr import simplify_expression
    
    for var_name, eclass_id in eclass_map.items():
        try:
            expr = extract_expr_from_egraph(eclass_id, egraph, cost_fn)
            # Apply algebraic simplifications
            expr = simplify_expression(expr)
            optimized_exprs[var_name] = expr
        except Exception as e:
            print(f"Warning: Could not extract expression for {var_name}: {e}")
            # Keep the variable as-is
            optimized_exprs[var_name] = ExprNode(op="var", value=var_name)
    
    return optimized_exprs


def expr_to_instruction(var_name: str, expr: ExprNode) -> Instruction:
    """
    Convert an expression to an SSA instruction.
    
    Args:
        var_name: Destination variable name
        expr: Expression to convert
    
    Returns:
        Instruction representing the expression
    """
    # Constants: MOV var, const
    if expr.is_constant():
        return Instruction("MOV", var_name, [str(expr.value)])
    
    # Variables: MOV var, src_var
    if expr.is_variable():
        return Instruction("MOV", var_name, [expr.value])
    
    # Binary operations
    if len(expr.children) == 2:
        left, right = expr.children
        
        # Get operand strings
        left_op = get_operand_string(left)
        right_op = get_operand_string(right)
        
        # Map expression op to instruction opcode
        opcode = expr.op.upper()
        return Instruction(opcode, var_name, [left_op, right_op])
    
    # Unary operations
    if len(expr.children) == 1:
        operand = expr.children[0]
        operand_str = get_operand_string(operand)
        
        opcode = expr.op.upper()
        return Instruction(opcode, var_name, [operand_str])
    
    # Phi operations - n-ary merge
    if expr.op == "phi" and len(expr.children) > 0:
        # PHI instruction with multiple sources
        phi_srcs = [get_operand_string(child) for child in expr.children]
        return Instruction("PHI", var_name, phi_srcs)
    
    # Default: MOV
    return Instruction("MOV", var_name, ["0"])


def get_operand_string(expr: ExprNode) -> str:
    """
    Get operand string from expression.
    
    Args:
        expr: Expression node
    
    Returns:
        String representation suitable for instruction operand
    """
    if expr.is_constant():
        return str(expr.value)
    if expr.is_variable():
        return expr.value
    # For complex expressions, would need temporary variable
    # For now, return a placeholder
    return f"({expr})"


def needs_temporary(expr: ExprNode) -> bool:
    """
    Check if expression needs a temporary variable.
    
    Args:
        expr: Expression to check
    
    Returns:
        True if expression is complex and needs a temporary
    """
    # Constants and variables don't need temporaries
    if expr.is_constant() or expr.is_variable():
        return False
    
    # Operations need temporaries
    return True


def linearize_expression(expr: ExprNode, var_name: str, temp_counter: List[int]) -> List[Instruction]:
    """
    Convert complex expression to sequence of SSA instructions.
    
    Introduces temporary variables as needed for nested expressions.
    
    Args:
        expr: Expression to linearize
        var_name: Destination variable
        temp_counter: Counter for generating unique temporary names
    
    Returns:
        List of instructions computing the expression
    """
    instructions = []
    
    # Simple cases: constant or variable
    if expr.is_constant() or expr.is_variable():
        instructions.append(expr_to_instruction(var_name, expr))
        return instructions
    
    # Phi nodes are special - convert directly without linearizing children
    # Phi children must remain as simple operands (vars/constants)
    if expr.op == "phi":
        instructions.append(expr_to_instruction(var_name, expr))
        return instructions
    
    # Complex expression: linearize children first
    operands = []
    for child in expr.children:
        if needs_temporary(child):
            # Generate temporary variable
            temp_name = f"_t{temp_counter[0]}"
            temp_counter[0] += 1
            
            # Recursively linearize child
            child_instrs = linearize_expression(child, temp_name, temp_counter)
            instructions.extend(child_instrs)
            operands.append(temp_name)
        else:
            # Simple operand
            operands.append(get_operand_string(child))
    
    # Create instruction for this operation
    opcode = expr.op.upper()
    instructions.append(Instruction(opcode, var_name, operands))
    
    return instructions


def exprs_to_ssa_instructions(expr_map: Dict[str, ExprNode]) -> List[Instruction]:
    """
    Convert expression map back to SSA instructions.
    
    Generates instructions in dependency order, introducing temporary
    variables as needed for complex expressions.
    
    Args:
        expr_map: Dictionary mapping variable names to expressions
    
    Returns:
        List of SSA instructions in dependency order
    
    Example:
        >>> expr_map = {
        ...     "x_0": ExprNode("const", value=1),
        ...     "x_1": ExprNode("add", [ExprNode("var", value="x_0"), ...])
        ... }
        >>> instrs = exprs_to_ssa_instructions(expr_map)
    """
    instructions = []
    temp_counter = [0]  # Use list to allow mutation in nested function
    
    # Sort variables in dependency order
    sorted_vars = topological_sort_exprs(expr_map)
    
    # Generate instructions for each variable
    for var_name in sorted_vars:
        expr = expr_map[var_name]
        
        # Linearize expression
        var_instrs = linearize_expression(expr, var_name, temp_counter)
        instructions.extend(var_instrs)
    
    return instructions


def compare_instruction_counts(original_instrs: List[Instruction],
                               optimized_instrs: List[Instruction]):
    """
    Compare original and optimized instruction counts.
    
    Args:
        original_instrs: Original instruction list
        optimized_instrs: Optimized instruction list
    """
    print("\nInstruction Count Comparison:")
    print("=" * 60)
    print(f"Original:  {len(original_instrs)} instructions")
    print(f"Optimized: {len(optimized_instrs)} instructions")
    
    reduction = len(original_instrs) - len(optimized_instrs)
    if len(original_instrs) > 0:
        percent = (reduction / len(original_instrs)) * 100
        print(f"Reduction: {reduction} instructions ({percent:.1f}%)")
    
    print("=" * 60)


def print_ssa_comparison(original_block, optimized_instrs: List[Instruction]):
    """
    Print side-by-side comparison of SSA code.
    
    Args:
        original_block: Original BasicBlock
        optimized_instrs: Optimized instruction list
    """
    print("\nSSA Code Comparison:")
    print("=" * 60)
    
    print("\nOriginal SSA:")
    print("-" * 30)
    for instr in original_block.instructions:
        print(f"  {instr}")
    
    print("\nOptimized SSA:")
    print("-" * 30)
    for instr in optimized_instrs:
        print(f"  {instr}")
    
    print("=" * 60)
