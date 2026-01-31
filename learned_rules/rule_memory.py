"""
Rule memory system for tracking rule effectiveness.

Tracks success and failure rates of learned rules to prioritize them.
"""
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .rule_parser import ParsedRule


class RuleMemory:
    """
    Tracks the effectiveness of learned rewrite rules.
    
    Maintains success and failure counts for each rule and computes
    a priority score based on historical performance.
    """
    
    def __init__(self):
        """Initialize empty rule memory."""
        self.successes: Dict[str, int] = {}
        self.failures: Dict[str, int] = {}
        
        # Cooldown system
        self.failure_streaks: Dict[str, int] = {}
        self.cooldown_rules: Dict[str, int] = {}
        
        # Cooldown configuration
        self.COOLDOWN_THRESHOLD = 3  # Failures in a row to trigger cooldown
        self.COOLDOWN_DURATION = 5   # Number of cycles to skip
    
    def record_success(self, rule_name: str) -> None:
        """
        Record a successful application of a rule.
        
        Args:
            rule_name: Name of the rule that succeeded
        """
        if rule_name not in self.successes:
            self.successes[rule_name] = 0
        self.successes[rule_name] += 1
    
    def record_failure(self, rule_name: str) -> None:
        """
        Record a failed application of a rule.
        
        Args:
            rule_name: Name of the rule that failed
        """
        if rule_name not in self.failures:
            self.failures[rule_name] = 0
        self.failures[rule_name] += 1
    
    def priority_score(self, rule_name: str) -> float:
        """
        Calculate priority score for a rule.
        
        Score formula: successes / (successes + failures + 1)
        
        - Higher score = more reliable rule
        - +1 in denominator prevents division by zero
        - New rules start with score ~0.5 (1/(0+0+1))
        
        Args:
            rule_name: Name of the rule
        
        Returns:
            Priority score between 0 and 1
        """
        successes = self.successes.get(rule_name, 0)
        failures = self.failures.get(rule_name, 0)
        
        score = successes / (successes + failures + 1)
        return score
    
    def get_stats(self, rule_name: str) -> Dict[str, int]:
        """
        Get statistics for a specific rule.
        
        Args:
            rule_name: Name of the rule
        
        Returns:
            Dictionary with 'successes' and 'failures' counts
        """
        return {
            'successes': self.successes.get(rule_name, 0),
            'failures': self.failures.get(rule_name, 0),
            'score': self.priority_score(rule_name)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for all tracked rules.
        
        Returns:
            Dictionary mapping rule names to their stats
        """
        all_rules = set(self.successes.keys()) | set(self.failures.keys())
        return {rule: self.get_stats(rule) for rule in all_rules}
    
    def get_top_rules(self, n: int = 10) -> list[tuple[str, float]]:
        """
        Get top N rules by priority score.
        
        Args:
            n: Number of top rules to return
        
        Returns:
            List of (rule_name, score) tuples, sorted by score descending
        """
        all_rules = set(self.successes.keys()) | set(self.failures.keys())
        scored_rules = [(rule, self.priority_score(rule)) for rule in all_rules]
        scored_rules.sort(key=lambda x: x[1], reverse=True)
        return scored_rules[:n]
    
    def reset(self) -> None:
        """Clear all memory (useful for testing or retraining)."""
        self.successes.clear()
        self.failures.clear()
        self.failure_streaks.clear()
        self.cooldown_rules.clear()
    
    def update_streak(self, rule_name: str, success: bool) -> None:
        """
        Update failure streak for cooldown tracking.
        
        Args:
            rule_name: Name of the rule
            success: Whether the rule succeeded or failed
        """
        if success:
            # Reset streak on success
            self.failure_streaks[rule_name] = 0
        else:
            # Increment failure streak
            if rule_name not in self.failure_streaks:
                self.failure_streaks[rule_name] = 0
            self.failure_streaks[rule_name] += 1
            
            # Check if we should put rule on cooldown
            if self.failure_streaks[rule_name] >= self.COOLDOWN_THRESHOLD:
                self.cooldown_rules[rule_name] = self.COOLDOWN_DURATION
                print(f"    ⏸ '{rule_name}' on cooldown for {self.COOLDOWN_DURATION} cycles")
    
    def is_on_cooldown(self, rule_name: str) -> bool:
        """
        Check if a rule is currently on cooldown.
        
        Args:
            rule_name: Name of the rule
        
        Returns:
            True if rule is on cooldown, False otherwise
        """
        if rule_name not in self.cooldown_rules:
            return False
        
        cooldown_remaining = self.cooldown_rules[rule_name]
        
        if cooldown_remaining <= 0:
            # Cooldown expired, remove from dict
            del self.cooldown_rules[rule_name]
            print(f"    ▶ '{rule_name}' cooldown expired")
            return False
        
        # Decrement cooldown counter
        self.cooldown_rules[rule_name] -= 1
        return True
    
    def get_cooldown_status(self) -> Dict[str, int]:
        """
        Get cooldown status for all rules.
        
        Returns:
            Dictionary mapping rule names to remaining cooldown cycles
        """
        return dict(self.cooldown_rules)
    
    def prune_rules(self, rules: 'List[ParsedRule]', threshold: float = 0.1) -> 'List[ParsedRule]':
        """
        Prune low-performing rules based on priority score.
        
        Filters out rules whose priority score falls below the threshold.
        This prevents accumulation of ineffective rules.
        
        Args:
            rules: List of ParsedRule objects to filter
            threshold: Minimum priority score (default: 0.1)
        
        Returns:
            Filtered list of rules above the threshold
        """
        from .rule_filter import extract_opcode
        
        pruned = []
        for rule in rules:
            # Generate rule name
            rule_opcodes = [extract_opcode(instr) for instr in rule.lhs_seq]
            rule_name = '_'.join(rule_opcodes).lower() + '_learned'
            
            # Check if rule meets threshold
            score = self.priority_score(rule_name)
            
            # Keep rules that are above threshold OR haven't been tried yet
            # (New rules get a chance to prove themselves)
            has_history = (rule_name in self.successes) or (rule_name in self.failures)
            if not has_history or score >= threshold:
                pruned.append(rule)
        
        return pruned
    
    def __str__(self) -> str:
        """String representation of rule memory state."""
        stats = self.get_all_stats()
        if not stats:
            return "RuleMemory: (empty)"
        
        result = "RuleMemory:\n"
        for rule, data in sorted(stats.items(), key=lambda x: x[1]['score'], reverse=True):
            result += f"  {rule}: score={data['score']:.3f} "
            result += f"(✓{data['successes']} ✗{data['failures']})\n"
        return result
