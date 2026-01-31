"""
Learned rules package for LLM-based assembly optimization.

This package provides infrastructure for generating, parsing, filtering,
and managing assembly rewrite rules learned from LLMs.
"""
from .llm_rule_generator import generate_candidate_rules, call_llm_api
from .rule_parser import ParsedRule, parse_llm_output, rule_to_string
from .rule_filter import filter_candidate_rules, validate_rule_safety, prioritize_by_reduction
from .rule_memory import RuleMemory
from .learned_rule_manager import LearnedRuleManager
from .window_sampler import WindowSampler, sample_windows

__all__ = [
    'generate_candidate_rules',
    'call_llm_api',
    'ParsedRule',
    'parse_llm_output',
    'rule_to_string',
    'filter_candidate_rules',
    'validate_rule_safety',
    'prioritize_by_reduction',
    'RuleMemory',
    'LearnedRuleManager',
    'WindowSampler',
    'sample_windows',
]

