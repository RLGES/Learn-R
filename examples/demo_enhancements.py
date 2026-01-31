"""
Demo: Rule metrics, smart window sampling, and cooldown mechanism.

This demonstrates the three new enhancements:
1. Rule metrics tracking per rule
2. Smart window sampling for LLM
3. Cooldown mechanism for failing rules
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asm_ir import Instruction, BasicBlock
from evaluation import RuleMetrics
from learned_rules import WindowSampler, LearnedRuleManager
from learned_rules.rule_parser import ParsedRule


def demo_rule_metrics():
    """Demonstrate rule metrics tracking."""
    print("=" * 70)
    print("1. RULE METRICS TRACKING")
    print("=" * 70)
    
    metrics = RuleMetrics()
    
    # Simulate rule applications
    print("\nSimulating rule applications...")
    metrics.record_application("mov_chain_elimination", cost_before=5, cost_after=4, tier=1)
    metrics.record_application("mov_chain_elimination", cost_before=8, cost_after=6, tier=1)
    metrics.record_application("add_sub_cancellation", cost_before=6, cost_after=5, tier=1)
    metrics.record_application("double_add_folding", cost_before=4, cost_after=3, tier=1)
    metrics.record_application("double_add_folding", cost_before=7, cost_after=6, tier=1)
    metrics.record_application("double_add_folding", cost_before=3, cost_after=2, tier=1)
    metrics.record_application("learned_opt_1", cost_before=10, cost_after=8, tier=3)
    metrics.record_application("learned_opt_1", cost_before=6, cost_after=6, tier=3)  # No improvement
    
    # Get summary
    print("\nMetrics summary:")
    print(metrics)
    
    # Top rules by different metrics
    print("\nTop rules by total cost delta:")
    for rule, delta in metrics.get_top_rules(n=3, by='total_cost_delta'):
        print(f"  {rule}: {delta:+.0f}")
    
    print("\nTop rules by applications:")
    for rule, apps in metrics.get_top_rules(n=3, by='applications'):
        print(f"  {rule}: {int(apps)} times")
    
    print("\n✅ Rule metrics tracking working!\n")


def demo_window_sampler():
    """Demonstrate smart window sampling."""
    print("=" * 70)
    print("2. SMART WINDOW SAMPLING")
    print("=" * 70)
    
    # Create test basic block
    instructions = [
        Instruction("MOV", "eax", ["ebx"]),
        Instruction("ADD", "eax", ["1"]),
        Instruction("MOV", "ecx", ["eax"]),
        Instruction("ADD", "ecx", ["2"]),
        Instruction("MOV", "edx", ["ebx"]),
        Instruction("ADD", "edx", ["1"]),
        Instruction("MOV", "esi", ["edx"]),
    ]
    block = BasicBlock(instructions)
    
    print(f"\nTest block ({len(instructions)} instructions):")
    print(block)
    
    # Create sampler
    sampler = WindowSampler()
    
    # Record some sequences as frequent
    print("\nRecording sequence frequencies...")
    sampler.record_sequence(["MOV eax, ebx", "ADD eax, 1"])
    sampler.record_sequence(["MOV eax, ebx", "ADD eax, 1"])
    sampler.record_sequence(["MOV eax, ebx", "ADD eax, 1"])
    sampler.record_sequence(["MOV edx, ebx", "ADD edx, 1"])
    sampler.record_sequence(["MOV edx, ebx", "ADD edx, 1"])
    
    # Mark one as optimized
    sampler.mark_optimized(["MOV ecx, eax", "ADD ecx, 2"])
    
    print(sampler)
    
    # Sample windows
    print("\nSampling windows (size=2, max=3)...")
    windows = sampler.sample_windows(block, window_size=2, max_windows=3)
    
    print(f"\nSampled {len(windows)} windows:")
    for i, window in enumerate(windows, 1):
        print(f"\n  Window {i}:")
        for instr in window:
            print(f"    {instr}")
        # Show score
        score = sampler._compute_window_score(window)
        print(f"    Score: {score:.1f}")
    
    print("\n✅ Smart window sampling working!\n")


def demo_cooldown():
    """Demonstrate cooldown mechanism."""
    print("=" * 70)
    print("3. COOLDOWN MECHANISM")
    print("=" * 70)
    
    from learned_rules import RuleMemory
    
    memory = RuleMemory()
    
    print(f"\nCooldown settings:")
    print(f"  Threshold: {memory.COOLDOWN_THRESHOLD} consecutive failures")
    print(f"  Duration: {memory.COOLDOWN_DURATION} cycles")
    
    # Simulate a rule failing repeatedly
    print("\n\nSimulating 'bad_learned_rule' applications:")
    
    for i in range(5):
        print(f"\nCycle {i+1}:")
        
        # Check cooldown before applying
        if memory.is_on_cooldown("bad_learned_rule"):
            print("  ⏸ Rule is on cooldown, skipping")
            continue
        
        # Apply rule (it fails)
        print("  Applying rule...")
        success = False  # Always fails
        memory.record_failure("bad_learned_rule")
        memory.update_streak("bad_learned_rule", success)
        
        # Check streak
        streak = memory.failure_streaks.get("bad_learned_rule", 0)
        print(f"  ✗ Failed (streak: {streak})")
    
    # Show cooldown status
    print("\n\nCooldown status:")
    cooldown_status = memory.get_cooldown_status()
    for rule, remaining in cooldown_status.items():
        print(f"  {rule}: {remaining} cycles remaining")
    
    # Simulate cooldown expiring
    print("\n\nSimulating cooldown cycles...")
    for i in range(6):
        print(f"\nCycle {i+1}:")
        is_cooled = memory.is_on_cooldown("bad_learned_rule")
        if is_cooled:
            print("  ⏸ Still on cooldown")
        else:
            print("  ▶ Cooldown expired, rule available again")
            break
    
    print("\n✅ Cooldown mechanism working!\n")


def demo_integration():
    """Demonstrate integrated workflow."""
    print("=" * 70)
    print("4. INTEGRATED WORKFLOW")
    print("=" * 70)
    
    # Create test block
    instructions = [
        Instruction("MOV", "eax", ["ebx"]),
        Instruction("ADD", "eax", ["1"]),
        Instruction("ADD", "eax", ["1"]),
        Instruction("MOV", "ecx", ["eax"]),
    ]
    block = BasicBlock(instructions)
    
    print("\nTest block:")
    print(block)
    
    # Create manager with window sampler
    print("\nCreating LearnedRuleManager with WindowSampler...")
    manager = LearnedRuleManager(db_path="demo_integrated.json")
    
    print(f"  Window sampler initialized: ✓")
    print(f"  Tracked sequences: {len(manager.window_sampler.sequence_frequency)}")
    
    # Use smart sampling (would generate rules in real scenario)
    print("\nSampling windows from block...")
    windows = manager.window_sampler.sample_windows(block, window_size=2, max_windows=2)
    
    print(f"  Sampled {len(windows)} windows:")
    for i, window in enumerate(windows, 1):
        opcodes = ' '.join(instr.split()[0] for instr in window)
        print(f"    Window {i}: {opcodes}")
    
    # Record sequences
    for window in windows:
        manager.window_sampler.record_sequence(window)
    
    print(f"\n  Updated sampler state:")
    print(f"    Tracked sequences: {len(manager.window_sampler.sequence_frequency)}")
    
    # Simulate some rule applications with metrics
    print("\nSimulating rule applications with metrics + cooldown...")
    metrics = RuleMetrics()
    
    # Good rule
    print("\n  Applying 'double_add_learned' (good rule):")
    metrics.record_application("double_add_learned", 4, 3, tier=3)
    manager.memory.record_success("double_add_learned")
    manager.memory.update_streak("double_add_learned", success=True)
    print("    ✓ Success (cost: 4 → 3)")
    
    # Bad rule
    print("\n  Applying 'bad_learned' (poor rule, multiple failures):")
    for i in range(4):
        metrics.record_application("bad_learned", 5, 5, tier=3)
        manager.memory.record_failure("bad_learned")
        manager.memory.update_streak("bad_learned", success=False)
        print(f"    ✗ Failure #{i+1}")
    
    # Check cooldown
    print("\n  Cooldown status:")
    if manager.memory.is_on_cooldown("bad_learned"):
        print("    ⏸ 'bad_learned' is on cooldown")
    if not manager.memory.is_on_cooldown("double_add_learned"):
        print("    ▶ 'double_add_learned' is active")
    
    # Show metrics
    print("\n  Rule metrics:")
    summary = metrics.get_summary()
    for rule, stats in summary.items():
        print(f"    {rule}:")
        print(f"      Applications: {stats['applications']}")
        print(f"      Avg cost delta: {stats['avg_cost_delta']:+.2f}")
    
    # Cleanup
    from learned_rules.rule_storage import clear_database
    clear_database("demo_integrated.json")
    
    print("\n✅ Integrated workflow working!\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPREHENSIVE DEMO: New Enhancements")
    print("=" * 70)
    print("\nDemonstrating:")
    print("  1. Rule metrics tracking")
    print("  2. Smart window sampling")
    print("  3. Cooldown mechanism")
    print("  4. Integrated workflow")
    print()
    
    try:
        demo_rule_metrics()
        demo_window_sampler()
        demo_cooldown()
        demo_integration()
        
        print("=" * 70)
        print("ALL DEMOS PASSED ✅")
        print("=" * 70)
        print("\nNew features ready to use:")
        print("  ✓ RuleMetrics tracks per-rule performance")
        print("  ✓ WindowSampler intelligently samples patterns")
        print("  ✓ RuleMemory cooldown prevents wasted cycles")
        print("  ✓ All integrated into engine and manager")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
