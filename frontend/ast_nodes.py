"""
AST nodes for a minimal high-level expression language.

Supports:
- Integer literals
- Variables
- Binary operations (+, -, *)
- Assignment statements
- Statement sequences (blocks)
"""
from dataclasses import dataclass
from typing import List


@dataclass
class Expr:
    """Base class for expressions."""
    pass


@dataclass
class IntLiteral(Expr):
    """
    Integer literal expression.
    
    Example: 42, 0, -5
    """
    value: int
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Variable(Expr):
    """
    Variable reference.
    
    Example: x, count, temp
    """
    name: str
    
    def __str__(self) -> str:
        return self.name


@dataclass
class BinOp(Expr):
    """
    Binary operation expression.
    
    Supported operators: +, -, *
    
    Example: a + b, x * 2, y - 1
    """
    op: str  # '+', '-', '*'
    left: Expr
    right: Expr
    
    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"


@dataclass
class Assign:
    """
    Assignment statement.
    
    Example: x = 5, y = a + b
    """
    name: str
    expr: Expr
    
    def __str__(self) -> str:
        return f"{self.name} = {self.expr}"


@dataclass
class Block:
    """
    Sequence of statements (program block).
    
    Example:
        a = 5
        b = a + 3
        c = b * 2
    """
    statements: List[Assign]
    
    def __str__(self) -> str:
        return '\n'.join(str(stmt) for stmt in self.statements)
    
    def __repr__(self) -> str:
        stmts = ',\n  '.join(repr(stmt) for stmt in self.statements)
        return f"Block([\n  {stmts}\n])"
