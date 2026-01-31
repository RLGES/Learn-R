"""
Hierarchical engine package initialization.
"""
from .matcher import Matcher, Match
from .engine import HierarchicalEngine
from .egraph_api import EGraphAPI
from .dependency import has_register_dependency, has_flag_dependency, are_independent
from .tier_scheduler import MAX_ITERATIONS, get_max_iterations, get_tier_description

__all__ = [
    'Matcher', 'Match', 'HierarchicalEngine', 'EGraphAPI',
    'has_register_dependency', 'has_flag_dependency', 'are_independent',
    'MAX_ITERATIONS', 'get_max_iterations', 'get_tier_description'
]
