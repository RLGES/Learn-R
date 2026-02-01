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
from .ast_nodes import Expr, IntLiteral, Variable, BinOp, Assign, Block, If, While


class IRGenerator:
    """Generates three-address code IR from AST."""
    
    def __init__(self):
        self.temp_counter = 0
        self.label_counter = 0
        self.instructions: List[str] = []
    
    def new_temp(self) -> str:
        """Generate a new temporary variable name."""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def new_label(self) -> str:
        """Generate a new label name."""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label
    
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
            
            # For comparison operators, emit a CMP instruction
            if expr.op in ['<', '>', '<=', '>=', '==', '!=']:
                # Emit comparison (sets flags)
                self.instructions.append(f"CMP {left_result}, {right_result}")
                # Return a placeholder for the comparison result
                # (actual branching happens in if/while lowering)
                return f"_cmp_{expr.op}"
            else:
                # Arithmetic operation
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
        if result_var != assign.name and not result_var.startswith('_cmp_'):
            self.instructions.append(f"{assign.name} = {result_var}")
    
    def lower_if(self, if_stmt: If):
        """
        Lower an if statement to IR with labels and conditional jumps.
        
        Pattern:
            if (a < b) { then_body } else { else_body }
        
        Lowers to:
            CMP a, b
            JGE else_label     ; Jump if NOT(a < b)
            <then_body>
            JMP end_label
            else_label:
            <else_body>
            end_label:
        """
        # Lower condition (emits CMP instruction)
        cmp_result = self.lower_expr(if_stmt.condition)
        
        # Extract comparison operator
        if cmp_result.startswith('_cmp_'):
            op = cmp_result[5:]  # Remove '_cmp_' prefix
        else:
            raise ValueError("If condition must be a comparison")
        
        # Generate labels
        else_label = self.new_label()
        end_label = self.new_label()
        
        # Emit conditional jump (inverted logic - jump if condition is FALSE)
        jump_map = {
            '<': 'JGE',   # Jump if NOT less than (greater or equal)
            '>': 'JLE',   # Jump if NOT greater than (less or equal)
            '<=': 'JG',   # Jump if NOT less or equal (greater)
            '>=': 'JL',   # Jump if NOT greater or equal (less)
            '==': 'JNE',  # Jump if NOT equal
            '!=': 'JE'    # Jump if NOT not-equal (i.e., equal)
        }
        
        jump_instr = jump_map.get(op, 'JMP')
        
        if if_stmt.else_block:
            # With else: jump to else_label if condition false
            self.instructions.append(f"{jump_instr} {else_label}")
            
            # Then block
            self.lower_statements(if_stmt.then_block.statements)
            self.instructions.append(f"JMP {end_label}")
            
            # Else block
            self.instructions.append(f"{else_label}:")
            self.lower_statements(if_stmt.else_block.statements)
            
            # End label
            self.instructions.append(f"{end_label}:")
        else:
            # No else: jump to end_label if condition false
            self.instructions.append(f"{jump_instr} {end_label}")
            
            # Then block
            self.lower_statements(if_stmt.then_block.statements)
            
            # End label
            self.instructions.append(f"{end_label}:")
    
    def lower_while(self, while_stmt: While):
        """
        Lower a while loop to IR with labels and conditional jumps.
        
        Pattern:
            while (a < b) { body }
        
        Lowers to:
            loop_start:
            CMP a, b
            JGE loop_end       ; Jump if NOT(a < b)
            <body>
            JMP loop_start
            loop_end:
        """
        # Generate labels
        loop_start = self.new_label()
        loop_end = self.new_label()
        
        # Loop start label
        self.instructions.append(f"{loop_start}:")
        
        # Lower condition (emits CMP instruction)
        cmp_result = self.lower_expr(while_stmt.condition)
        
        # Extract comparison operator
        if cmp_result.startswith('_cmp_'):
            op = cmp_result[5:]  # Remove '_cmp_' prefix
        else:
            raise ValueError("While condition must be a comparison")
        
        # Emit conditional jump (inverted logic - jump if condition is FALSE)
        jump_map = {
            '<': 'JGE',
            '>': 'JLE',
            '<=': 'JG',
            '>=': 'JL',
            '==': 'JNE',
            '!=': 'JE'
        }
        
        jump_instr = jump_map.get(op, 'JMP')
        self.instructions.append(f"{jump_instr} {loop_end}")
        
        # Loop body
        self.lower_statements(while_stmt.body.statements)
        
        # Jump back to start
        self.instructions.append(f"JMP {loop_start}")
        
        # Loop end label
        self.instructions.append(f"{loop_end}:")
    
    def lower_statements(self, statements: List):
        """Lower a list of statements (handles mixed types)."""
        for stmt in statements:
            if isinstance(stmt, Assign):
                self.lower_assign(stmt)
            elif isinstance(stmt, If):
                self.lower_if(stmt)
            elif isinstance(stmt, While):
                self.lower_while(stmt)
            else:
                raise ValueError(f"Unknown statement type: {type(stmt)}")
    
    def lower_block(self, block: Block) -> List[str]:
        """
        Lower a block of statements to IR.
        
        Args:
            block: Block of statements
        
        Returns:
            List of three-address IR instructions
        """
        self.instructions = []
        self.lower_statements(block.statements)
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
