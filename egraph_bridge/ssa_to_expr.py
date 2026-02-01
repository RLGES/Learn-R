"""
Convert SSA-form instructions to expression DAG nodes.

Each SSA variable version becomes a node, and operations become expression
nodes that can be inserted into an e-graph for optimization.
"""
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from asm_ir import BasicBlock, Instruction


@dataclass
class ExprNode:
    """
    Represents an expression in DAG form.
    
    Can be:
    - Constant: op="const", children=[], value=<int>
    - Variable: op="var", children=[], name=<str>
    - Operation: op=<opcode>, children=[ExprNode, ...]
    """
    op: str
    children: List['ExprNode'] = field(default_factory=list)
    value: Optional[Union[int, str]] = None
    
    def __str__(self) -> str:
        """String representation of expression."""
        if self.op == "const":
            return f"Const({self.value})"
        elif self.op == "var":
            return f"Var({self.value})"
        elif not self.children:
            return self.op
        else:
            child_strs = ", ".join(str(c) for c in self.children)
            return f"{self.op}({child_strs})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __hash__(self) -> int:
        """Hash for use in dictionaries."""
        if self.op in ["const", "var"]:
            return hash((self.op, self.value))
        return hash((self.op, tuple(self.children)))
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, ExprNode):
            return False
        if self.op != other.op:
            return False
        if self.op in ["const", "var"]:
            return self.value == other.value
        return self.children == other.children
    
    def is_constant(self) -> bool:
        """Check if this is a constant expression."""
        return self.op == "const"
    
    def is_variable(self) -> bool:
        """Check if this is a variable reference."""
        return self.op == "var"
    
    def is_operation(self) -> bool:
        """Check if this is an operation."""
        return not self.is_constant() and not self.is_variable()


def parse_operand(operand: str) -> ExprNode:
    """
    Parse an operand into an ExprNode.
    
    Args:
        operand: Operand string (e.g., "123", "x_0", "rax")
    
    Returns:
        ExprNode representing the operand
    """
    # Check if it's a numeric constant
    if operand.isdigit() or (operand.startswith('-') and operand[1:].isdigit()):
        return ExprNode(op="const", value=int(operand))
    
    # Check if it's a hex constant
    if operand.startswith('0x') or operand.startswith('0X'):
        try:
            return ExprNode(op="const", value=int(operand, 16))
        except ValueError:
            pass
    
    # Otherwise it's a variable
    return ExprNode(op="var", value=operand)


def parse_memory_address(addr_str: str, expr_map: Dict[str, ExprNode]) -> ExprNode:
    """
    Parse memory address into an address expression.
    
    Handles:
    - [base]          → Var(base)
    - [base+offset]   → add(Var(base), Const(offset))
    - [base-offset]   → sub(Var(base), Const(offset))
    
    Args:
        addr_str: Memory address string (e.g., "[rax]", "[rbx+8]")
        expr_map: Map of variable names to their expression nodes
    
    Returns:
        ExprNode representing the address computation
    """
    # Remove brackets
    if addr_str.startswith('[') and addr_str.endswith(']'):
        inner = addr_str[1:-1]
    else:
        # Not a memory operand, treat as regular operand
        return expr_map.get(addr_str, parse_operand(addr_str))
    
    # Handle [base+offset] or [base-offset]
    if '+' in inner:
        parts = inner.split('+')
        base = parts[0].strip()
        offset = parts[1].strip()
        
        base_expr = expr_map.get(base, parse_operand(base))
        offset_expr = parse_operand(offset)
        return ExprNode(op="add", children=[base_expr, offset_expr])
    
    elif '-' in inner:
        parts = inner.split('-')
        base = parts[0].strip()
        offset = parts[1].strip()
        
        base_expr = expr_map.get(base, parse_operand(base))
        offset_expr = parse_operand(offset)
        return ExprNode(op="sub", children=[base_expr, offset_expr])
    
    else:
        # Just [base]
        base = inner.strip()
        return expr_map.get(base, parse_operand(base))


def instruction_to_expr(instr: Instruction, expr_map: Dict[str, ExprNode]) -> Optional[ExprNode]:
    """
    Convert a single SSA instruction to an expression node.
    
    Args:
        instr: SSA instruction to convert
        expr_map: Map of variable names to their expression nodes
    
    Returns:
        ExprNode representing the instruction, or None if not convertible
    """
    # Skip instructions without destinations (control flow, etc.)
    if not instr.dst:
        return None
    
    # Map instruction opcodes to expression operations
    # Arithmetic operations
    if instr.opcode in ['ADD', 'SUB', 'MUL', 'DIV', 'MOD']:
        if len(instr.srcs) != 2:
            return None
        
        # Get child expressions
        left = expr_map.get(instr.srcs[0], parse_operand(instr.srcs[0]))
        right = expr_map.get(instr.srcs[1], parse_operand(instr.srcs[1]))
        
        return ExprNode(op=instr.opcode.lower(), children=[left, right])
    
    # Bitwise operations
    elif instr.opcode in ['AND', 'OR', 'XOR', 'NOT']:
        if instr.opcode == 'NOT':
            if len(instr.srcs) != 1:
                return None
            operand = expr_map.get(instr.srcs[0], parse_operand(instr.srcs[0]))
            return ExprNode(op="not", children=[operand])
        else:
            if len(instr.srcs) != 2:
                return None
            left = expr_map.get(instr.srcs[0], parse_operand(instr.srcs[0]))
            right = expr_map.get(instr.srcs[1], parse_operand(instr.srcs[1]))
            return ExprNode(op=instr.opcode.lower(), children=[left, right])
    
    # Shift operations
    elif instr.opcode in ['SHL', 'SHR', 'SAR']:
        if len(instr.srcs) != 2:
            return None
        left = expr_map.get(instr.srcs[0], parse_operand(instr.srcs[0]))
        right = expr_map.get(instr.srcs[1], parse_operand(instr.srcs[1]))
        return ExprNode(op=instr.opcode.lower(), children=[left, right])
    
    # Move operations - just copy the source
    elif instr.opcode == 'MOV':
        if len(instr.srcs) != 1:
            return None
        # Return the expression for the source
        return expr_map.get(instr.srcs[0], parse_operand(instr.srcs[0]))
    
    # Phi nodes - merge values from multiple predecessors
    elif instr.opcode == 'PHI':
        # PHI node has multiple sources from different predecessors
        # Format: PHI dst, [src1, src2, ...]
        if len(instr.srcs) == 0:
            return None
        
        # Get expressions for all phi inputs
        phi_children = []
        for src in instr.srcs:
            phi_children.append(expr_map.get(src, parse_operand(src)))
        
        return ExprNode(op="phi", children=phi_children)
    
    # Comparison operations
    elif instr.opcode == 'CMP':
        # CMP doesn't produce a value we can track, skip it
        return None
    
    # Memory operations
    elif instr.opcode == 'LOAD':
        # LOAD: MOV dst, [address]
        # Treat as pure expression: load(address)
        if len(instr.srcs) != 1:
            return None
        
        addr_str = instr.srcs[0]
        # Parse address expression
        addr_expr = parse_memory_address(addr_str, expr_map)
        return ExprNode(op="load", children=[addr_expr])
    
    elif instr.opcode == 'STORE':
        # STORE: MOV [address], src
        # Stores have side effects, don't convert to expression
        return None
    
    # Default: unsupported operation
    return None


def ssa_block_to_exprs(block: BasicBlock) -> Dict[str, ExprNode]:
    """
    Convert SSA basic block to expression DAG.
    
    Each SSA variable is mapped to the expression that computes it.
    
    Args:
        block: BasicBlock in SSA form
    
    Returns:
        Dictionary mapping SSA variable names to their expression nodes
    
    Example:
        >>> block.instructions = [
        ...     Instruction("MOV", "x_0", ["1"]),
        ...     Instruction("ADD", "x_1", ["x_0", "2"]),
        ... ]
        >>> exprs = ssa_block_to_exprs(block)
        >>> exprs["x_0"]  # Const(1)
        >>> exprs["x_1"]  # add(Var(x_0), Const(2))
    """
    expr_map: Dict[str, ExprNode] = {}
    
    for instr in block.instructions:
        # Convert instruction to expression
        expr = instruction_to_expr(instr, expr_map)
        
        # Store expression for destination variable
        if expr and instr.dst:
            expr_map[instr.dst] = expr
    
    return expr_map


def print_expression_dag(expr_map: Dict[str, ExprNode]):
    """
    Print expression DAG in human-readable form.
    
    Args:
        expr_map: Dictionary of variable -> expression mappings
    """
    print("\nExpression DAG:")
    print("=" * 60)
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    print("=" * 60)


def get_expression_dependencies(expr: ExprNode) -> List[str]:
    """
    Get list of all variable dependencies for an expression.
    
    Args:
        expr: Expression node
    
    Returns:
        List of variable names that this expression depends on
    """
    deps = []
    
    def visit(node: ExprNode):
        if node.is_variable():
            deps.append(node.value)
        for child in node.children:
            visit(child)
    
    visit(expr)
    return deps


def topological_sort_exprs(expr_map: Dict[str, ExprNode]) -> List[str]:
    """
    Sort expressions in dependency order (topological sort).
    
    Args:
        expr_map: Dictionary of variable -> expression mappings
    
    Returns:
        List of variable names in dependency order
    """
    # Build dependency graph
    deps = {var: get_expression_dependencies(expr) 
            for var, expr in expr_map.items()}
    
    # Topological sort using DFS
    visited = set()
    result = []
    
    def visit(var: str):
        if var in visited:
            return
        visited.add(var)
        
        # Visit dependencies first
        if var in deps:
            for dep in deps[var]:
                if dep in expr_map:  # Only visit if it's in our expr_map
                    visit(dep)
        
        result.append(var)
    
    for var in expr_map:
        visit(var)
    
    return result


def simplify_expression(expr: ExprNode) -> ExprNode:
    """
    Perform basic constant folding on expression.
    
    Args:
        expr: Expression to simplify
    
    Returns:
        Simplified expression
    """
    # Recursively simplify children first
    if expr.children:
        simplified_children = [simplify_expression(child) for child in expr.children]
        expr = ExprNode(op=expr.op, children=simplified_children, value=expr.value)
    
    # Constant folding for binary operations
    if len(expr.children) == 2:
        left, right = expr.children
        if left.is_constant() and right.is_constant():
            left_val = left.value
            right_val = right.value
            
            result = None
            if expr.op == "add":
                result = left_val + right_val
            elif expr.op == "sub":
                result = left_val - right_val
            elif expr.op == "mul":
                result = left_val * right_val
            elif expr.op == "and":
                result = left_val & right_val
            elif expr.op == "or":
                result = left_val | right_val
            elif expr.op == "xor":
                result = left_val ^ right_val
            elif expr.op == "shl":
                result = left_val << right_val
            elif expr.op == "shr":
                result = left_val >> right_val
            
            if result is not None:
                return ExprNode(op="const", value=result)
    
    # Phi simplification: if all inputs are identical, replace with that input
    # This works for all expression types including load expressions
    if expr.op == "phi" and len(expr.children) > 0:
        # Check if all children are structurally equal
        first_child = expr.children[0]
        if all(child == first_child for child in expr.children):
            # All inputs identical: PHI(x, x, x) → x
            # This includes: PHI(load(a), load(a)) → load(a)
            return first_child
    
    # Identity operations
    if expr.op == "add" and len(expr.children) == 2:
        left, right = expr.children
        if right.is_constant() and right.value == 0:
            return left
        if left.is_constant() and left.value == 0:
            return right
    
    if expr.op == "mul" and len(expr.children) == 2:
        left, right = expr.children
        if right.is_constant() and right.value == 1:
            return left
        if left.is_constant() and left.value == 1:
            return right
        if right.is_constant() and right.value == 0:
            return ExprNode(op="const", value=0)
        if left.is_constant() and left.value == 0:
            return ExprNode(op="const", value=0)
    
    return expr
