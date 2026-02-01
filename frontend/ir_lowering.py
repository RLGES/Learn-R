"""
Lowering pass from AST to three-address code IR.

Converts high-level AST into simpler three-address instructions.

Example transformation:
    AST: c = (a + b) * 2
    IR:
        t1 = a + b
        t2 = t1 * 2
        c = t2
"""
from typing import List, Tuple
from .ast_nodes import Expr, IntLiteral, Variable, BinOp, Assign, Block


class IRGenerator:
    """Generates three-address code IR from AST."""
    
    def __init__(self):
        self.temp_counter = 0
        self.instructions: List[str] = []
    
    def new_temp(self) -> str:
        """Generate a new temporary variable name."""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def lower_expr(self, expr: Expr) -> str:
        """
        Lower an expression to IR, returning the name of the result.
        
        Args:
            expr: Expression to lower
        
        Returns:
            Name of variable/temp holding the result
        """
        if isinstance(expr, IntLiteral):
            # For literals, create a temp and assign
            temp = self.new_temp()
            self.instructions.append(f"{temp} = {expr.value}")
            return temp
        
        elif isinstance(expr, Variable):
            # Variables are already in the right form
            return expr.name
        
        elif isinstance(expr, BinOp):
            # Lower left and right operands first
            left_result = self.lower_expr(expr.left)
            right_result = self.lower_expr(expr.right)
            
            # Create temp for result and emit operation
            temp = self.new_temp()
            self.instructions.append(f"{temp} = {left_result} {expr.op} {right_result}")
            return temp
        
        else:
            raise ValueError(f"Unknown expression type: {type(expr)}")
    
    def lower_assign(self, assign: Assign):
        """
        Lower an assignment statement to IR.
        
        Args:
            assign: Assignment statement to lower
        """
        # Lower the RHS expression
        result_var = self.lower_expr(assign.expr)
        
        # If the result is not already the target variable, emit assignment
        if result_var != assign.name:
            self.instructions.append(f"{assign.name} = {result_var}")
    
    def lower_block(self, block: Block) -> List[str]:
        """
        Lower a block of statements to IR.
        
        Args:
            block: Block of statements
        
        Returns:
            List of three-address IR instructions
        """
        self.instructions = []
        
        for stmt in block.statements:
            self.lower_assign(stmt)
        
        return self.instructions


def lower_to_ir(ast_block: Block) -> List[str]:
    """
    Convert AST block to three-address code IR.
    
    Args:
        ast_block: Block AST node
    
    Returns:
        List of IR instruction strings
    
    Example:
        >>> from frontend import parse, lower_to_ir
        >>> ast = parse("a = 5\\nb = a + 3")
        >>> ir = lower_to_ir(ast)
        >>> for instr in ir:
        ...     print(instr)
        t0 = 5
        a = t0
        t1 = a + 3
        b = t1
    """
    generator = IRGenerator()
    return generator.lower_block(ast_block)
