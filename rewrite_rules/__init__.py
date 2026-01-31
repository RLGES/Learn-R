"""
Rewrite rules package initialization.
"""
from .rule_base import InstructionPattern, RewriteRule
from .tier1_peephole import mov_elimination_rule

__all__ = ['InstructionPattern', 'RewriteRule', 'mov_elimination_rule']
