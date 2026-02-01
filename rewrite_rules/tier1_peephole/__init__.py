"""
Tier 1 peephole rules package.
"""
from .mov_elimination import mov_elimination_rule
from .cancel_add_sub import add_sub_cancel_rule
from .mov_overwrite import mov_overwrite_rule
from .double_add import double_add_rule
from .bitwise_identities import (
    and_with_zero_rule,
    or_with_zero_rule,
    xor_with_zero_rule,
    xor_self_rule,
    shl_by_zero_rule,
    shr_by_zero_rule,
)
from .load_store import (
    load_store_same_rule,
    load_forward_rule,
)

__all__ = [
    'mov_elimination_rule',
    'add_sub_cancel_rule',
    'mov_overwrite_rule',
    'double_add_rule',
    'and_with_zero_rule',
    'or_with_zero_rule',
    'xor_with_zero_rule',
    'xor_self_rule',
    'shl_by_zero_rule',
    'shr_by_zero_rule',
    'load_store_same_rule',
    'load_forward_rule',
]
