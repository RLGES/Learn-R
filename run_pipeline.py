#!/usr/bin/env python3
"""
LLM-Guided Equality Saturation Pipeline

Run the full pipeline:
1. Generate rewrite rules from LLM (local or cloud)
2. Verify rules with Z3 SMT solver
3. Apply verified rules to input expressions
4. Show optimization results

Usage:
    python run_pipeline.py                    # Basic run
    python run_pipeline.py --verify           # Enable Z3 verification
    python run_pipeline.py --verbose          # Verbose output
    python run_pipeline.py --expr "x + 0"     # Custom expression
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str):
    """Print a section header."""
    print(f"\n--- {title} ---")


def run_pipeline(verify: bool = True, verbose: bool = False, custom_expr: str = None):
    """Run the full LLM-guided equality saturation pipeline."""
    
    print_header("LLM-GUIDED EQUALITY SATURATION PIPELINE")
    
    # Step 1: Check dependencies
    print_section("Step 1: Checking Dependencies")
    
    try:
        from egraph_bridge.egglog_pipeline import EqualitySaturationPipeline, Asm
        print("  ✓ Egglog pipeline loaded")
    except Exception as e:
        print(f"  ✗ Failed to load pipeline: {e}")
        return False
    
    try:
        from learned_rules.llm_rule_generator import check_llm_availability
        availability = check_llm_availability()
        available = availability.get('available_providers', [])
        if available:
            print(f"  ✓ LLM available via: {', '.join(available)}")
        else:
            print("  ⚠ No LLM configured (will use built-in rules only)")
    except Exception as e:
        print(f"  ⚠ LLM check failed: {e}")
        available = []
    
    if verify:
        try:
            from z3 import get_version_string
            print(f"  ✓ Z3 verification available (v{get_version_string()})")
        except ImportError:
            print("  ⚠ Z3 not available, verification disabled")
            verify = False
    
    # Step 2: Create pipeline
    print_section("Step 2: Creating Pipeline")
    
    pipeline = EqualitySaturationPipeline(
        use_strength_reduction=True,
        use_llm_rules=True
    )
    print(f"  ✓ Pipeline created")
    print(f"  ✓ Strength reduction: enabled")
    print(f"  ✓ LLM rules: enabled" if available else "  ⚠ LLM rules: disabled (no provider)")
    
    # Step 3: Generate LLM rules
    print_section("Step 3: Generating LLM Rules")
    
    llm_rules_generated = 0
    verified_rules = []
    rejected_rules = []
    
    if available:
        try:
            from learned_rules.llm_rule_generator import call_llm_api
            from learned_rules.rule_parser import parse_llm_output
            from learned_rules.rule_to_egglog import RuleToEgglogConverter
            
            print("  Calling LLM for rewrite rules...")
            
            prompt = """Generate 5 rewrite rules for x86/assembly code optimization.

Rules should be in this format:
LHS:
<instruction sequence>
RHS:
<optimized instruction sequence>
Condition: <optional>

Generate rules for:
1. Identity elimination (e.g., ADD r, 0)
2. Strength reduction (e.g., MUL r, 2 → SHL r, 1)
3. Redundant operation removal
"""
            
            response = call_llm_api(prompt)
            
            if verbose:
                print(f"\n  LLM Response:\n{'-'*40}")
                print(response[:500] + "..." if len(response) > 500 else response)
                print(f"{'-'*40}\n")
            
            # Parse rules
            from learned_rules.rule_parser import parse_llm_output
            parsed_rules = parse_llm_output(response)
            print(f"  ✓ Parsed {len(parsed_rules)} rules from LLM output")
            
            # Convert and optionally verify
            converter = RuleToEgglogConverter(enable_verification=verify)
            
            for i, rule in enumerate(parsed_rules, 1):
                try:
                    converted = converter.convert_rule(rule)
                    if converted:
                        verified_rules.append(converted)
                        pipeline.add_llm_rule(converted)
                        status = "✓ VERIFIED" if verify else "✓ ADDED"
                        print(f"    Rule {i}: {status}")
                        if verbose:
                            print(f"      LHS: {rule.lhs_seq}")
                            print(f"      RHS: {rule.rhs_seq}")
                    else:
                        rejected_rules.append(rule)
                        print(f"    Rule {i}: ✗ REJECTED (failed verification)")
                        if verbose:
                            print(f"      LHS: {rule.lhs_seq}")
                            print(f"      RHS: {rule.rhs_seq}")
                except Exception as e:
                    rejected_rules.append(rule)
                    print(f"    Rule {i}: ✗ ERROR ({str(e)[:40]})")
            
            llm_rules_generated = len(verified_rules)
            
        except Exception as e:
            print(f"  ⚠ LLM rule generation failed: {e}")
    else:
        print("  ⚠ Skipping LLM rules (no provider configured)")
    
    # Step 4: Add test expressions
    print_section("Step 4: Adding Expressions to Optimize")
    
    x = Asm.var("x")
    y = Asm.var("y")
    
    expressions = [
        ("x + 0", x + Asm(0)),
        ("x * 1", x * Asm(1)),
        ("x - x", x - x),
        ("x ^ x", x ^ x),
        ("x * 2", x * Asm(2)),
        ("y + y", y + y),
    ]
    
    if custom_expr:
        print(f"  Custom expression: {custom_expr} (not implemented yet)")
    
    for name, expr in expressions:
        pipeline.add_expression(expr, name.replace(" ", "_"))
        print(f"  ✓ Added: {name}")
    
    # Step 5: Run optimization
    print_section("Step 5: Running Equality Saturation")
    
    result = pipeline.optimize()
    
    print(f"  ✓ Saturation complete")
    print(f"    - Rules applied: {result.rules_applied}")
    print(f"    - LLM rules: {result.llm_rules_added}")
    print(f"    - Iterations: {result.saturation_iterations}")
    
    # Step 6: Show results
    print_section("Step 6: Optimization Results")
    
    optimized_count = 0
    for name, orig in result.original_expressions.items():
        opt = result.optimized_expressions.get(name)
        if str(opt) != str(orig):
            status = "✓ OPTIMIZED"
            optimized_count += 1
        else:
            status = "- unchanged"
        print(f"  {name}: {orig} → {opt}  [{status}]")
    
    # Summary
    print_header("SUMMARY")
    print(f"  Expressions processed: {len(result.original_expressions)}")
    print(f"  Expressions optimized: {optimized_count}")
    print(f"  Built-in rules applied: {result.rules_applied - result.llm_rules_added}")
    print(f"  LLM rules generated: {len(verified_rules) + len(rejected_rules)}")
    if verify:
        print(f"  LLM rules verified: {len(verified_rules)}")
        print(f"  LLM rules rejected: {len(rejected_rules)}")
    print("=" * 60)
    
    # Show rewrite trees for RL
    if verbose:
        print_section("Rewrite Trees (for RL Agent)")
        print(result.get_rewrite_summary())
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LLM-Guided Equality Saturation Pipeline"
    )
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        default=True,
        help="Enable Z3 verification of LLM rules (default: enabled)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable Z3 verification"
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--expr", "-e",
        type=str,
        help="Custom expression to optimize"
    )
    
    args = parser.parse_args()
    
    verify = not args.no_verify
    
    success = run_pipeline(
        verify=verify,
        verbose=args.verbose,
        custom_expr=args.expr
    )
    
    sys.exit(0 if success else 1)
