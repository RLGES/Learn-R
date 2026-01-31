"""
Tier 1 peephole rules package.
"""
from .mov_elimination import mov_elimination_rule
from .cancel_add_sub import add_sub_cancel_rule
from .mov_overwrite import mov_overwrite_rule
from .double_add import double_add_rule

__all__ = [
    'mov_elimination_rule',
    'add_sub_cancel_rule',
    'mov_overwrite_rule',
    'double_add_rule'
]
