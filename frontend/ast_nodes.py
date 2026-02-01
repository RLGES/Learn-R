"""
AST nodes for a minimal high-level expression language.

Supports:
- Integer literals
- Variables
- Binary operations (+, -, *, <, >, <=, >=, ==, !=)
- Assignment statements
- If statements with optional else
- While loops
- Statement sequences (blocks)
"""
from __future__ import annotations
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
    
    Supported operators: +, -, *, <, >, <=, >=, ==, !=
    
    Example: a + b, x * 2, y - 1, a < b
    """
    op: str  # '+', '-', '*', '<', '>', '<=', '>=', '==', '!='
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
class If:
    """
    If statement with optional else clause.
    
    Example:
        if (a < b) {
            c = a
        } else {
            c = b
        }
    """
    condition: Expr
    then_block: Block
    else_block: Block = None
    
    def __str__(self) -> str:
        result = f"if {self.condition} {{\n"
        for stmt in self.then_block.statements:
            result += f"  {stmt}\n"
        result += "}"
        if self.else_block:
            result += " else {\n"
            for stmt in self.else_block.statements:
                result += f"  {stmt}\n"
            result += "}"
        return result


@dataclass
class While:
    """
    While loop statement.
    
    Example:
        while (a < 10) {
            a = a + 1
        }
    """
    condition: Expr
    body: Block
    
    def __str__(self) -> str:
        result = f"while {self.condition} {{\n"
        for stmt in self.body.statements:
            result += f"  {stmt}\n"
        result += "}"
        return result


@dataclass
class Block:
    """
    Sequence of statements (program block).
    
    Example:
        a = 5
        b = a + 3
        c = b * 2
    """
    statements: List  # Can be Assign, If, While, etc.
    
    def __str__(self) -> str:
        return '\n'.join(str(stmt) for stmt in self.statements)
    
    def __repr__(self) -> str:
        stmts = ',\n  '.join(repr(stmt) for stmt in self.statements)
        return f"Block([\n  {stmts}\n])"
