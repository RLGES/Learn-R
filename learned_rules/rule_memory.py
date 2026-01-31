"""
Rule memory system for tracking rule effectiveness.

Tracks success and failure rates of learned rules to prioritize them.
"""
from typing import Dict


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
