"""
Tier scheduler configuration for the rewrite engine.

Defines maximum iteration limits per tier to control e-graph explosion.
"""

# Maximum iterations allowed per tier
MAX_ITERATIONS = {
    0: 1,   # Tier 0: Normalization - run once
    1: 5,   # Tier 1: Peephole optimizations - limited exploration
    2: 2,   # Tier 2: Structural rewrites - controlled explosion
    3: 1,   # Tier 3: Advanced optimizations - minimal exploration
}


def get_max_iterations(tier: int, default: int = 10) -> int:
    """
    Get the maximum iterations for a given tier.
    
    Args:
        tier: The tier number
        default: Default value if tier is not in configuration
    
    Returns:
        Maximum iterations for the tier
    """
    return MAX_ITERATIONS.get(tier, default)


# Tier descriptions for documentation
TIER_DESCRIPTIONS = {
    0: "Normalization - cleanup and canonicalization",
    1: "Peephole optimizations - local pattern matching",
    2: "Structural rewrites - instruction reordering and grouping",
    3: "Advanced optimizations - algebraic simplification and global analysis"
}


def get_tier_description(tier: int) -> str:
    """
    Get a human-readable description of what a tier does.
    
    Args:
        tier: The tier number
    
    Returns:
        Description string
    """
    return TIER_DESCRIPTIONS.get(tier, "Unknown tier")


def print_tier_config():
    """Print the tier scheduler configuration."""
    print("Tier Scheduler Configuration")
    print("=" * 60)
    for tier in sorted(MAX_ITERATIONS.keys()):
        print(f"  Tier {tier}: {get_max_iterations(tier)} iterations")
        print(f"           {get_tier_description(tier)}")
    print("=" * 60)
