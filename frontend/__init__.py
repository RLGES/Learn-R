"""
Frontend package for high-level language compilation.

Provides AST, parsing, IR lowering, and code generation.
"""
from .ast_nodes import Expr, IntLiteral, Variable, BinOp, Assign, Block, If, While
from .parser import parse
from .ir_lowering import lower_to_ir
from .asm_codegen import ir_to_assembly

__all__ = [
    'Expr',
    'IntLiteral',
    'Variable',
    'BinOp',
    'Assign',
    'Block',
    'If',
    'While',
    'parse',
    'lower_to_ir',
    'ir_to_assembly',
]
