"""
Learned rule manager that orchestrates rule generation, parsing, filtering, and memory.

This module ties together all components of the learned rules system.
"""
from typing import List, Set
from .llm_rule_generator import generate_candidate_rules
from .rule_parser import ParsedRule, parse_llm_output
from .rule_filter import filter_candidate_rules, prioritize_by_reduction
from .rule_memory import RuleMemory

# Import verification (optional - gracefully handle if z3 not installed)
try:
    from verification import verify_rule
    VERIFICATION_AVAILABLE = True
except ImportError:
    VERIFICATION_AVAILABLE = False
    verify_rule = None


class LearnedRuleManager:
    """
    Manager for the learned rules system.
    
    Coordinates rule generation via LLM, parsing, filtering, and
    memory-based prioritization.
    """
    
    def __init__(self, existing_rule_names: Set[str] = None, enable_verification: bool = True):
        """
        Initialize the learned rule manager.
        
        Args:
            existing_rule_names: Set of existing rule names to avoid duplicates
            enable_verification: If True, verify rules using SMT (requires z3-solver)
        """
        self.existing_rule_names = existing_rule_names or set()
        self.memory = RuleMemory()
        self.proposed_rules: List[ParsedRule] = []
        self.enable_verification = enable_verification and VERIFICATION_AVAILABLE
        
        # Track verification stats
        self.verification_stats = {
            'total_checked': 0,
            'verified': 0,
            'rejected': 0,
            'errors': 0
        }
        
        if self.enable_verification:
            print("✓ SMT verification enabled")
        elif enable_verification:
            print("⚠ SMT verification requested but z3-solver not available")
    
    def propose_rules(self, instruction_window: List[str]) -> List[ParsedRule]:
        """
        Propose new rewrite rules for an instruction sequence.
        
        Pipeline:
        1. Generate candidates using LLM
        2. Parse LLM output into structured rules
        3. Filter invalid/duplicate rules
        4. Verify rules using SMT (if enabled)
        
        Args:
            instruction_window: List of assembly instructions
        
        Returns:
            List of valid, filtered, and verified ParsedRule objects
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
        
        # Step 4: Verify rules using SMT (if enabled)
        if self.enable_verification:
            verified_rules = self._verify_rules(filtered_rules)
        else:
            verified_rules = filtered_rules
        
        # Store for later reference
        self.proposed_rules = verified_rules
        
        return verified_rules
    
    def _verify_rules(self, rules: List[ParsedRule]) -> List[ParsedRule]:
        """
        Verify rules using SMT-based equivalence checking.
        
        Only rules that pass verification are kept.
        
        Args:
            rules: List of parsed rules to verify
        
        Returns:
            List of verified rules
        """
        verified = []
        
        for rule in rules:
            self.verification_stats['total_checked'] += 1
            
            try:
                is_verified = verify_rule(rule, timeout_ms=5000)
                
                if is_verified:
                    verified.append(rule)
                    self.verification_stats['verified'] += 1
                    print(f"✓ Verified: {rule.lhs_seq[0] if rule.lhs_seq else 'rule'}")
                else:
                    self.verification_stats['rejected'] += 1
                    print(f"✗ Rejected (not equivalent): {rule.lhs_seq[0] if rule.lhs_seq else 'rule'}")
            
            except Exception as e:
                self.verification_stats['errors'] += 1
                print(f"⚠ Verification error: {e}")
                # Don't include rules that errored during verification
        
        return verified
    
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
    
    def get_verification_stats(self) -> dict:
        """
        Get verification statistics.
        
        Returns:
            Dictionary with verification counts
        """
        return self.verification_stats.copy()
    
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
