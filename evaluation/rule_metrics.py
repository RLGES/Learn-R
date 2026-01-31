"""
Rule metrics tracking for evaluation.

Tracks per-rule statistics including applications, cost deltas, and tier distribution.
"""
from typing import Dict


class RuleMetrics:
    """
    Track evaluation metrics per rewrite rule.
    
    Maintains statistics for each rule including:
    - Total applications
    - Cost deltas (before - after)
    - Tier distribution
    """
    
    def __init__(self):
        """Initialize empty metrics."""
        # Track applications per rule
        self.total_applications: Dict[str, int] = {}
        
        # Track cumulative cost delta per rule (before - after)
        # Positive = reduction, negative = increase
        self.total_cost_delta: Dict[str, int] = {}
        
        # Track tier distribution per rule
        self.tier_counts: Dict[str, Dict[int, int]] = {}
    
    def record_application(self, rule_name: str, cost_before: int, 
                          cost_after: int, tier: int) -> None:
        """
        Record a rule application.
        
        Args:
            rule_name: Name of the rule that was applied
            cost_before: Cost before applying the rule
            cost_after: Cost after applying the rule
            tier: Tier the rule belongs to
        """
        # Initialize if first time seeing this rule
        if rule_name not in self.total_applications:
            self.total_applications[rule_name] = 0
            self.total_cost_delta[rule_name] = 0
            self.tier_counts[rule_name] = {}
        
        # Update counts
        self.total_applications[rule_name] += 1
        
        # Update cost delta (positive = improvement)
        cost_delta = cost_before - cost_after
        self.total_cost_delta[rule_name] += cost_delta
        
        # Update tier counts
        if tier not in self.tier_counts[rule_name]:
            self.tier_counts[rule_name][tier] = 0
        self.tier_counts[rule_name][tier] += 1
    
    def get_summary(self) -> Dict[str, Dict]:
        """
        Get summary statistics for all rules.
        
        Returns:
            Dictionary mapping rule names to their statistics:
            {
                'rule_name': {
                    'applications': int,
                    'total_cost_delta': int,
                    'avg_cost_delta': float,
                    'tier_counts': dict[tier -> count]
                }
            }
        """
        summary = {}
        
        for rule_name in self.total_applications:
            apps = self.total_applications[rule_name]
            total_delta = self.total_cost_delta[rule_name]
            avg_delta = total_delta / apps if apps > 0 else 0.0
            
            summary[rule_name] = {
                'applications': apps,
                'total_cost_delta': total_delta,
                'avg_cost_delta': avg_delta,
                'tier_counts': dict(self.tier_counts[rule_name])
            }
        
        return summary
    
    def get_rule_stats(self, rule_name: str) -> Dict:
        """
        Get statistics for a specific rule.
        
        Args:
            rule_name: Name of the rule
        
        Returns:
            Dictionary with rule statistics, or empty dict if rule not found
        """
        if rule_name not in self.total_applications:
            return {}
        
        apps = self.total_applications[rule_name]
        total_delta = self.total_cost_delta[rule_name]
        avg_delta = total_delta / apps if apps > 0 else 0.0
        
        return {
            'applications': apps,
            'total_cost_delta': total_delta,
            'avg_cost_delta': avg_delta,
            'tier_counts': dict(self.tier_counts[rule_name])
        }
    
    def get_top_rules(self, n: int = 10, by: str = 'applications') -> list[tuple[str, float]]:
        """
        Get top N rules by a specific metric.
        
        Args:
            n: Number of top rules to return
            by: Metric to sort by ('applications', 'total_cost_delta', 'avg_cost_delta')
        
        Returns:
            List of (rule_name, metric_value) tuples, sorted descending
        """
        if by == 'applications':
            items = [(name, self.total_applications[name]) 
                    for name in self.total_applications]
        elif by == 'total_cost_delta':
            items = [(name, self.total_cost_delta[name]) 
                    for name in self.total_cost_delta]
        elif by == 'avg_cost_delta':
            items = [(name, self.total_cost_delta[name] / self.total_applications[name]) 
                    for name in self.total_applications]
        else:
            raise ValueError(f"Unknown metric: {by}")
        
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:n]
    
    def reset(self) -> None:
        """Clear all metrics."""
        self.total_applications.clear()
        self.total_cost_delta.clear()
        self.tier_counts.clear()
    
    def __str__(self) -> str:
        """String representation of metrics."""
        if not self.total_applications:
            return "RuleMetrics: (no data)"
        
        result = "RuleMetrics:\n"
        summary = self.get_summary()
        
        # Sort by total cost delta (most improvement first)
        sorted_rules = sorted(summary.items(), 
                            key=lambda x: x[1]['total_cost_delta'], 
                            reverse=True)
        
        for rule_name, stats in sorted_rules:
            result += f"  {rule_name}:\n"
            result += f"    Applications: {stats['applications']}\n"
            result += f"    Total cost delta: {stats['total_cost_delta']:+d}\n"
            result += f"    Avg cost delta: {stats['avg_cost_delta']:+.2f}\n"
            result += f"    Tiers: {stats['tier_counts']}\n"
        
        return result
