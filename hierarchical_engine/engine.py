"""
Hierarchical rewrite engine.
"""
from typing import Any
from asm_ir import BasicBlock
from rewrite_rules import RewriteRule
from .matcher import Matcher


class HierarchicalEngine:
    """
    Hierarchical rewrite engine that applies rules in tiers.
    Delegates e-graph operations to an external API.
    """
    
    def __init__(self, egraph_api: Any, rules_by_tier: dict[int, list[RewriteRule]]):
        """
        Initialize the engine.
        
        Args:
            egraph_api: External e-graph API object (duck-typed)
            rules_by_tier: Dictionary mapping tier number to list of rules
        """
        self.egraph_api = egraph_api
        self.rules_by_tier = rules_by_tier
        self.matcher = Matcher()
        self.stats = {
            'matches_per_tier': {},
            'rewrites_per_tier': {},
            'iterations_per_tier': {}
        }
    
    def run(self, block: BasicBlock, max_iterations_per_tier: int = 10) -> None:
        """
        Run the hierarchical rewrite engine.
        
        Args:
            block: The basic block to optimize
            max_iterations_per_tier: Maximum iterations per tier
        """
        # Sort tiers
        sorted_tiers = sorted(self.rules_by_tier.keys())
        
        print(f"Running hierarchical rewrite engine with {len(sorted_tiers)} tiers")
        
        for tier in sorted_tiers:
            print(f"\n=== Processing Tier {tier} ===")
            rules = self.rules_by_tier[tier]
            
            # Initialize stats for this tier
            tier_matches = 0
            tier_rewrites = 0
            
            for iteration in range(max_iterations_per_tier):
                matches_found = False
                
                for rule in rules:
                    # Find all matches for this rule
                    matches = self.matcher.find_matches(rule.lhs, block)
                    tier_matches += len(matches)
                    
                    for match in matches:
                        # Check precondition
                        if not rule.precondition(match.bindings):
                            continue
                        
                        matches_found = True
                        tier_rewrites += 1
                        print(f"  [Tier {tier}, Iter {iteration}] Applying rule '{rule.name}' at index {match.start_index}")
                        print(f"    Bindings: {match.bindings}")
                        
                        # Apply the rule via e-graph API
                        # The e-graph should track equivalences non-destructively
                        self.egraph_api.apply_rule(rule, match)
                
                # If no matches found in this iteration, move to next tier
                if not matches_found:
                    print(f"  No more matches found in iteration {iteration}, moving to next tier")
                    self.stats['iterations_per_tier'][tier] = iteration + 1
                    break
            else:
                print(f"  Reached maximum iterations ({max_iterations_per_tier}) for tier {tier}")
                self.stats['iterations_per_tier'][tier] = max_iterations_per_tier
            
            # Store tier statistics
            self.stats['matches_per_tier'][tier] = tier_matches
            self.stats['rewrites_per_tier'][tier] = tier_rewrites
        
        print("\n=== Rewrite engine completed ===")
        self._print_stats()
    
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
