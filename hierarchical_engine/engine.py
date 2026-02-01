"""
Hierarchical rewrite engine.
"""
from typing import Any, Optional
from asm_ir import BasicBlock
from rewrite_rules import RewriteRule
from .matcher import Matcher
from .tier_scheduler import get_max_iterations
from evaluation import RuleMetrics


class HierarchicalEngine:
    """
    Hierarchical rewrite engine that applies rules in tiers.
    Delegates e-graph operations to an external API.
    """
    
    def __init__(self, egraph_api: Any, rules_by_tier: dict[int, list[RewriteRule]], 
                 learned_rule_manager: Optional[Any] = None):
        """
        Initialize the engine.
        
        Args:
            egraph_api: External e-graph API object (duck-typed)
            rules_by_tier: Dictionary mapping tier number to list of rules
            learned_rule_manager: Optional LearnedRuleManager for Tier 3 prioritization
        """
        self.egraph_api = egraph_api
        self.rules_by_tier = rules_by_tier
        self.matcher = Matcher()
        self.learned_rule_manager = learned_rule_manager
        self.rule_metrics = RuleMetrics()
        self.stats = {
            'matches_per_tier': {},
            'rewrites_per_tier': {},
            'iterations_per_tier': {},
            'sequences_added': 0,
            'preconditions_failed': 0
        }
    
    def run(self, block: BasicBlock, max_iterations_per_tier: int = None) -> BasicBlock:
        """
        Run the hierarchical rewrite engine.
        
        Args:
            block: The basic block to optimize
            max_iterations_per_tier: Default maximum iterations per tier (if tier not configured)
                                    If None, uses 10 as default
        
        Returns:
            Optimized basic block (extracted from e-graph)
        """
        if max_iterations_per_tier is None:
            max_iterations_per_tier = 10
        
        # Add original sequence to e-graph
        self.egraph_api.add_sequence(block.instructions)
        
        # Calculate original cost
        original_cost = len(block.instructions)
        
        # Sort tiers
        sorted_tiers = sorted(self.rules_by_tier.keys())
        
        print(f"Running hierarchical rewrite engine with {len(sorted_tiers)} tiers")
        
        for tier in sorted_tiers:
            print(f"\n=== Processing Tier {tier} ===")
            rules = self.rules_by_tier[tier]
            
            # Prioritize Tier 3 rules using learned rule manager
            if tier == 3 and self.learned_rule_manager and rules:
                print("  Prioritizing Tier 3 rules using RuleMemory...")
                # Note: This assumes rules can be prioritized
                # In a full implementation, we'd need a way to convert
                # RewriteRule objects or track them by name
                # For now, this is a hook point for future integration
            
            # Get tier-specific iteration limit
            tier_max_iter = get_max_iterations(tier, max_iterations_per_tier)
            print(f"  Max iterations for tier {tier}: {tier_max_iter}")
            
            # Initialize stats for this tier
            tier_matches = 0
            tier_rewrites = 0
            
            for iteration in range(tier_max_iter):
                matches_found = False
                
                for rule in rules:
                    # Check cooldown for Tier 3 (learned) rules
                    if tier == 3 and self.learned_rule_manager:
                        if self.learned_rule_manager.memory.is_on_cooldown(rule.name):
                            print(f"  [Tier {tier}] Skipping '{rule.name}' (on cooldown)")
                            continue
                    
                    # Find all matches for this rule
                    matches = self.matcher.find_matches(rule.lhs, block)
                    tier_matches += len(matches)
                    
                    for match in matches:
                        # Check precondition
                        if not rule.precondition(match.bindings):
                            self.stats['preconditions_failed'] += 1
                            continue
                        
                        matches_found = True
                        tier_rewrites += 1
                        self.stats['sequences_added'] += 1
                        
                        # Record metrics (before applying)
                        cost_before = len(block.instructions)
                        
                        print(f"  [Tier {tier}, Iter {iteration}] Applying rule '{rule.name}' at index {match.start_index}")
                        print(f"    Bindings: {match.bindings}")
                        
                        # Apply the rule via e-graph API
                        # The e-graph should track equivalences non-destructively
                        self.egraph_api.apply_rewrite(rule, match)
                        
                        # Record metrics (after applying)
                        # Note: In a real e-graph, cost calculation would be more sophisticated
                        cost_after = len(block.instructions)  # Simplified
                        self.rule_metrics.record_application(rule.name, cost_before, cost_after, tier)
                
                # If no matches found in this iteration, move to next tier
                if not matches_found:
                    print(f"  No more matches found in iteration {iteration}, moving to next tier")
                    self.stats['iterations_per_tier'][tier] = iteration + 1
                    break
            else:
                print(f"  Reached maximum iterations ({tier_max_iter}) for tier {tier}")
                self.stats['iterations_per_tier'][tier] = tier_max_iter
            
            # Store tier statistics
            self.stats['matches_per_tier'][tier] = tier_matches
            self.stats['rewrites_per_tier'][tier] = tier_rewrites
        
        print("\n=== Rewrite engine completed ===")
        self._print_stats()
        
        # Extract best sequence from e-graph
        print("\n=== Extracting optimized sequence ===")
        optimized_instructions = self.egraph_api.extract_best()
        optimized_cost = len(optimized_instructions)
        
        print(f"Original cost: {original_cost} instructions")
        print(f"Optimized cost: {optimized_cost} instructions")
        
        # Provide feedback to learned rule manager
        if self.learned_rule_manager:
            applied_rules = self.egraph_api.get_applied_rules()
            improvement = original_cost - optimized_cost
            
            print(f"\n=== Extraction Feedback ===")
            print(f"Applied rules: {applied_rules}")
            print(f"Improvement: {improvement} instructions")
            
            # Give feedback based on whether optimization improved the code
            success = improvement > 0
            
            for rule_name in applied_rules:
                # Only track Tier 3 (learned) rules
                if '_learned' in rule_name:
                    print(f"  Recording {'success' if success else 'failure'} for rule: {rule_name}")
                    self.learned_rule_manager.update_memory(rule_name, success)
                    # Update cooldown streak
                    self.learned_rule_manager.memory.update_streak(rule_name, success)
        
        # Print rule metrics summary
        print("\n=== Rule Metrics Summary ===")
        self._print_rule_metrics()
        
        # Return optimized basic block
        return BasicBlock(optimized_instructions)
    
    def _print_stats(self) -> None:
        """Print statistics about the rewrite process."""
        print("\n" + "=" * 60)
        print("REWRITE ENGINE STATISTICS")
        print("=" * 60)
        
        total_matches = sum(self.stats['matches_per_tier'].values())
        total_rewrites = sum(self.stats['rewrites_per_tier'].values())
        
        print(f"\nOverall:")
        print(f"  Total matches found: {total_matches}")
        print(f"  Total rewrites applied: {total_rewrites}")
        print(f"  Instruction sequences added: {self.stats['sequences_added']}")
        print(f"  Preconditions failed: {self.stats['preconditions_failed']}")
        
        print(f"\nPer-tier breakdown:")
        for tier in sorted(self.stats['matches_per_tier'].keys()):
            matches = self.stats['matches_per_tier'].get(tier, 0)
            rewrites = self.stats['rewrites_per_tier'].get(tier, 0)
            iterations = self.stats['iterations_per_tier'].get(tier, 0)
            print(f"  Tier {tier}:")
            print(f"    Matches: {matches}")
            print(f"    Rewrites: {rewrites}")
            print(f"    Iterations: {iterations}")
        
        print("=" * 60)
    
    def _print_rule_metrics(self) -> None:
        """Print rule metrics summary."""
        if not self.rule_metrics.total_applications:
            print("  No rule applications recorded")
            return
        
        print("\nTop rules by cost reduction:")
        top_by_delta = self.rule_metrics.get_top_rules(n=5, by='total_cost_delta')
        for rule_name, delta in top_by_delta:
            stats = self.rule_metrics.get_rule_stats(rule_name)
            print(f"  {rule_name}: {delta:+d} total (avg: {stats['avg_cost_delta']:+.2f})")
        
        print("\nTop rules by applications:")
        top_by_apps = self.rule_metrics.get_top_rules(n=5, by='applications')
        for rule_name, apps in top_by_apps:
            print(f"  {rule_name}: {int(apps)} applications")
