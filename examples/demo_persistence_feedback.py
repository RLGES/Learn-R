"""
Demo: Rule persistence, extraction feedback, and pruning.

This demonstrates the complete learned rules lifecycle:
1. Load rules from disk (if available)
2. Apply rules during optimization
3. Extract best sequence
4. Give feedback based on optimization outcome
5. Prune low-performing rules
6. Save updated rules and memory to disk
"""
from asm_ir import Instruction, BasicBlock
from learned_rules import LearnedRuleManager
from learned_rules.rule_parser import ParsedRule
from learned_rules.rule_storage import clear_database, get_database_stats
import os


def demo_persistence():
    """Demonstrate rule persistence and feedback loop."""
    
    print("=" * 70)
    print("DEMO: Rule Persistence, Extraction Feedback, and Pruning")
    print("=" * 70)
    
    # Clean slate for demo
    db_path = "demo_learned_rules.json"
    if os.path.exists(db_path):
        clear_database(db_path)
        print("\nCleared previous demo database")
    
    # Create manager (will load empty database)
    print("\n1. Initializing LearnedRuleManager...")
    manager = LearnedRuleManager(db_path=db_path)
    print(f"   Loaded {len(manager.proposed_rules)} rules from disk")
    print(manager)
    
    # Simulate adding some learned rules
    print("\n2. Adding sample learned rules...")
    sample_rules = [
        ParsedRule(
            lhs_seq=["MOV EAX, EBX", "MOV ECX, EAX"],
            rhs_seq=["MOV ECX, EBX"],
            conditions=[]
        ),
        ParsedRule(
            lhs_seq=["ADD EAX, 1", "ADD EAX, 1"],
            rhs_seq=["ADD EAX, 2"],
            conditions=[]
        ),
        ParsedRule(
            lhs_seq=["SUB EAX, 5", "ADD EAX, 5"],
            rhs_seq=["NOP"],
            conditions=[]
        ),
    ]
    
    manager.proposed_rules = sample_rules
    print(f"   Added {len(sample_rules)} sample rules")
    
    # Simulate feedback from multiple optimization runs
    print("\n3. Simulating extraction feedback...")
    
    # Run 1: mov_mov_learned rule succeeds
    print("\n   Run 1: MOV chain optimization")
    manager.update_memory("mov_mov_learned", success=True)
    print(f"      ✓ Success recorded for 'mov_mov_learned'")
    
    # Run 2: add_add_learned rule succeeds
    print("\n   Run 2: ADD combination optimization")
    manager.update_memory("add_add_learned", success=True)
    print(f"      ✓ Success recorded for 'add_add_learned'")
    
    # Run 3: sub_add_learned rule fails (made code worse)
    print("\n   Run 3: SUB/ADD cancellation attempt")
    manager.update_memory("sub_add_learned", success=False)
    print(f"      ✗ Failure recorded for 'sub_add_learned'")
    
    # Run 4: add_add_learned succeeds again
    print("\n   Run 4: Another ADD combination")
    manager.update_memory("add_add_learned", success=True)
    print(f"      ✓ Success recorded for 'add_add_learned'")
    
    # Run 5: sub_add_learned fails again
    print("\n   Run 5: Another SUB/ADD attempt")
    manager.update_memory("sub_add_learned", success=False)
    print(f"      ✗ Failure recorded for 'sub_add_learned'")
    
    # Show current state
    print("\n4. Current rule memory statistics:")
    print(manager)
    
    # Check database file
    print("\n5. Database file status:")
    stats = get_database_stats(db_path)
    print(f"   File: {db_path}")
    print(f"   Exists: {stats['exists']}")
    if stats['exists']:
        print(f"   Size: {stats['file_size']} bytes")
        print(f"   Version: {stats['version']}")
        print(f"   Rules: {stats['rule_count']}")
        print(f"   Tracked rules: {stats['memory_entries']}")
    
    # Create a new manager to test loading
    print("\n6. Creating new manager to test persistence...")
    manager2 = LearnedRuleManager(db_path=db_path)
    print(f"   Loaded {len(manager2.proposed_rules)} rules")
    print("\n   Memory state restored:")
    print(manager2)
    
    # Verify memory matches
    print("\n7. Verifying memory integrity...")
    for rule_name in ["mov_mov_learned", "add_add_learned", "sub_add_learned"]:
        score1 = manager.memory.priority_score(rule_name)
        score2 = manager2.memory.priority_score(rule_name)
        match = "✓" if abs(score1 - score2) < 0.001 else "✗"
        print(f"   {match} {rule_name}: {score1:.3f} == {score2:.3f}")
    
    # Demonstrate pruning
    print("\n8. Demonstrating rule pruning...")
    print(f"   Current rules: {len(manager2.proposed_rules)}")
    
    # Add more failures to sub_add_learned to push it below threshold
    for i in range(10):
        manager2.update_memory("sub_add_learned", success=False)
    
    print(f"\n   After additional failures:")
    stats = manager2.memory.get_stats("sub_add_learned")
    print(f"      sub_add_learned: score={stats['score']:.3f} "
          f"(✓{stats['successes']} ✗{stats['failures']})")
    
    # Pruning happens automatically in update_memory if rules exceed threshold
    # Let's manually trigger it for demo
    print("\n   Manual pruning with threshold=0.1...")
    pruned = manager2.memory.prune_rules(manager2.proposed_rules, threshold=0.1)
    print(f"   Rules after pruning: {len(pruned)}")
    
    # Show which rules survived
    print("\n   Surviving rules:")
    for rule in pruned:
        opcodes = [instr.split()[0] for instr in rule.lhs_seq]
        rule_name = '_'.join(opcodes).lower() + '_learned'
        score = manager2.memory.priority_score(rule_name)
        print(f"      - {rule_name}: score={score:.3f}")
    
    # Cleanup
    print("\n9. Cleanup...")
    clear_database(db_path)
    print(f"   Removed {db_path}")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE: Persistence and feedback system working!")
    print("=" * 70)
    print("\nKey features demonstrated:")
    print("  ✓ Rules persist to disk in JSON format")
    print("  ✓ Memory (successes/failures) persists across sessions")
    print("  ✓ Extraction feedback updates rule effectiveness")
    print("  ✓ Low-performing rules are automatically pruned")
    print("  ✓ System creates closed-loop learning")


if __name__ == "__main__":
    demo_persistence()
