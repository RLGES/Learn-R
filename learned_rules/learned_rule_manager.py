"""
Learned rule manager that orchestrates rule generation, parsing, filtering, and memory.

This module ties together all components of the learned rules system.
"""
from typing import List, Set
from .llm_rule_generator import generate_candidate_rules
from .rule_parser import ParsedRule, parse_llm_output
from .rule_filter import filter_candidate_rules, prioritize_by_reduction
from .rule_memory import RuleMemory


class LearnedRuleManager:
    """
    Manager for the learned rules system.
    
    Coordinates rule generation via LLM, parsing, filtering, and
    memory-based prioritization.
    """
    
    def __init__(self, existing_rule_names: Set[str] = None):
        """
        Initialize the learned rule manager.
        
        Args:
            existing_rule_names: Set of existing rule names to avoid duplicates
        """
        self.existing_rule_names = existing_rule_names or set()
        self.memory = RuleMemory()
        self.proposed_rules: List[ParsedRule] = []
    
    def propose_rules(self, instruction_window: List[str]) -> List[ParsedRule]:
        """
        Propose new rewrite rules for an instruction sequence.
        
        Pipeline:
        1. Generate candidates using LLM
        2. Parse LLM output into structured rules
        3. Filter invalid/duplicate rules
        
        Args:
            instruction_window: List of assembly instructions
        
        Returns:
            List of valid, filtered ParsedRule objects
        """
        # Step 1: Generate candidate rules via LLM
        llm_output = generate_candidate_rules(instruction_window)
        
        # Step 2: Parse LLM output
        parsed_rules = parse_llm_output(llm_output)
        
        # Step 3: Filter rules
        filtered_rules = filter_candidate_rules(
            parsed_rules,
            self.existing_rule_names
        )
        
        # Store for later reference
        self.proposed_rules = filtered_rules
        
        return filtered_rules
    
    def update_memory(self, rule_name: str, success: bool) -> None:
        """
        Update rule memory based on application outcome.
        
        Args:
            rule_name: Name of the rule that was applied
            success: True if application succeeded, False if failed
        """
        if success:
            self.memory.record_success(rule_name)
        else:
            self.memory.record_failure(rule_name)
    
    def prioritize_rules(self, rules: List[ParsedRule]) -> List[ParsedRule]:
        """
        Sort rules by priority using memory scores.
        
        Rules with higher success rates are prioritized first.
        New rules (not in memory) get a neutral priority.
        
        Args:
            rules: List of parsed rules to prioritize
        
        Returns:
            Sorted list of rules (highest priority first)
        """
        def get_priority(rule: ParsedRule) -> float:
            # Generate rule name (simple approach)
            from .rule_filter import extract_opcode
            rule_opcodes = [extract_opcode(instr) for instr in rule.lhs_seq]
            rule_name = '_'.join(rule_opcodes).lower() + '_learned'
            
            # Get priority score from memory
            return self.memory.priority_score(rule_name)
        
        # Sort by priority score (highest first)
        sorted_rules = sorted(rules, key=get_priority, reverse=True)
        return sorted_rules
    
    def get_memory_stats(self) -> dict:
        """
        Get current rule memory statistics.
        
        Returns:
            Dictionary of all tracked rules and their stats
        """
        return self.memory.get_all_stats()
    
    def get_top_rules(self, n: int = 5) -> list:
        """
        Get top N performing rules.
        
        Args:
            n: Number of top rules to return
        
        Returns:
            List of (rule_name, score) tuples
        """
        return self.memory.get_top_rules(n)
    
    def add_existing_rule(self, rule_name: str) -> None:
        """
        Add a rule name to the existing rules set.
        
        Args:
            rule_name: Name of an existing rule
        """
        self.existing_rule_names.add(rule_name)
    
    def reset_memory(self) -> None:
        """Clear all rule memory (for testing or retraining)."""
        self.memory.reset()
    
    def __str__(self) -> str:
        """String representation of manager state."""
        result = "LearnedRuleManager:\n"
        result += f"  Existing rules: {len(self.existing_rule_names)}\n"
        result += f"  Proposed rules: {len(self.proposed_rules)}\n"
        result += f"  Memory state:\n"
        
        stats = self.memory.get_all_stats()
        if stats:
            for rule, data in sorted(stats.items(), key=lambda x: x[1]['score'], reverse=True):
                result += f"    {rule}: {data['score']:.3f}\n"
        else:
            result += "    (empty)\n"
        
        return result
