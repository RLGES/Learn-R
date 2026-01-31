"""
End-to-end test: Complete persistence and feedback workflow.

Tests the full integration:
1. Create manager → empty state
2. Add rules → save to disk
3. Give feedback → update scores
4. Load in new manager → verify restoration
5. Prune low-scorers → verify removal
6. Cleanup
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from learned_rules import LearnedRuleManager
from learned_rules.rule_parser import ParsedRule
from learned_rules.rule_storage import clear_database, get_database_stats


def test_end_to_end():
    """Complete integration test."""
    
    print("=" * 70)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 70)
    
    db_path = "test_e2e.json"
    
    # Cleanup any previous test
    if os.path.exists(db_path):
        clear_database(db_path)
    
    # TEST 1: Create manager with empty state
    print("\n[TEST 1] Create manager with empty state")
    manager1 = LearnedRuleManager(db_path=db_path)
    assert len(manager1.proposed_rules) == 0, "Should start empty"
    assert len(manager1.memory.get_all_stats()) == 0, "Memory should be empty"
    print("  ✓ Empty state verified")
    
    # TEST 2: Add rules manually
    print("\n[TEST 2] Add rules")
    test_rules = [
        ParsedRule(["MOV EAX, EBX", "MOV ECX, EAX"], ["MOV ECX, EBX"], []),
        ParsedRule(["ADD EAX, 1", "ADD EAX, 1"], ["ADD EAX, 2"], []),
        ParsedRule(["SUB EAX, 5", "ADD EAX, 5"], ["NOP"], []),
    ]
    manager1.proposed_rules = test_rules
    assert len(manager1.proposed_rules) == 3, "Should have 3 rules"
    print("  ✓ 3 rules added")
    
    # TEST 3: Give feedback (triggers save)
    print("\n[TEST 3] Give feedback")
    manager1.update_memory("mov_mov_learned", success=True)
    manager1.update_memory("add_add_learned", success=True)
    manager1.update_memory("add_add_learned", success=True)  # Second success
    manager1.update_memory("sub_add_learned", success=False)
    manager1.update_memory("sub_add_learned", success=False)  # Second failure
    
    # Verify scores
    mov_score = manager1.memory.priority_score("mov_mov_learned")
    add_score = manager1.memory.priority_score("add_add_learned")
    sub_score = manager1.memory.priority_score("sub_add_learned")
    
    assert 0.4 < mov_score < 0.6, f"MOV score should be ~0.5, got {mov_score}"
    assert 0.6 < add_score < 0.8, f"ADD score should be ~0.67, got {add_score}"
    assert sub_score < 0.1, f"SUB score should be <0.1, got {sub_score}"
    
    print(f"  ✓ mov_mov_learned: {mov_score:.3f}")
    print(f"  ✓ add_add_learned: {add_score:.3f}")
    print(f"  ✓ sub_add_learned: {sub_score:.3f}")
    
    # TEST 4: Verify database file exists
    print("\n[TEST 4] Verify database file")
    assert os.path.exists(db_path), "Database file should exist"
    stats = get_database_stats(db_path)
    assert stats['exists'], "Database should exist"
    assert stats['rule_count'] == 3, f"Should have 3 rules, got {stats['rule_count']}"
    assert stats['memory_entries'] == 3, f"Should track 3 rules, got {stats['memory_entries']}"
    print(f"  ✓ Database exists: {db_path}")
    print(f"  ✓ Rules: {stats['rule_count']}")
    print(f"  ✓ Tracked: {stats['memory_entries']}")
    print(f"  ✓ Size: {stats['file_size']} bytes")
    
    # TEST 5: Load in new manager
    print("\n[TEST 5] Load in new manager")
    manager2 = LearnedRuleManager(db_path=db_path)
    assert len(manager2.proposed_rules) == 3, "Should load 3 rules"
    
    # Verify scores match
    mov_score2 = manager2.memory.priority_score("mov_mov_learned")
    add_score2 = manager2.memory.priority_score("add_add_learned")
    sub_score2 = manager2.memory.priority_score("sub_add_learned")
    
    assert abs(mov_score - mov_score2) < 0.001, "MOV scores should match"
    assert abs(add_score - add_score2) < 0.001, "ADD scores should match"
    assert abs(sub_score - sub_score2) < 0.001, "SUB scores should match"
    
    print("  ✓ Loaded 3 rules")
    print(f"  ✓ mov_mov_learned: {mov_score2:.3f} (matches)")
    print(f"  ✓ add_add_learned: {add_score2:.3f} (matches)")
    print(f"  ✓ sub_add_learned: {sub_score2:.3f} (matches)")
    
    # TEST 6: Pruning
    print("\n[TEST 6] Prune low-scorers")
    pruned = manager2.memory.prune_rules(manager2.proposed_rules, threshold=0.1)
    assert len(pruned) == 2, f"Should have 2 rules after pruning, got {len(pruned)}"
    
    # Verify sub_add rule was removed (score=0.0)
    remaining_opcodes = []
    for rule in pruned:
        opcodes = [instr.split()[0] for instr in rule.lhs_seq]
        remaining_opcodes.extend(opcodes)
    
    assert "MOV" in remaining_opcodes, "MOV rule should survive"
    assert "ADD" in remaining_opcodes, "ADD rule should survive"
    assert "SUB" not in remaining_opcodes, "SUB rule should be pruned"
    
    print("  ✓ Pruned 1 low-scorer")
    print("  ✓ 2 rules remaining")
    print("  ✓ MOV rule survived")
    print("  ✓ ADD rule survived")
    print("  ✓ SUB rule pruned")
    
    # TEST 7: Verify prioritization
    print("\n[TEST 7] Verify prioritization")
    prioritized = manager2.prioritize_rules(pruned)
    
    # ADD should be first (highest score ~0.67)
    # MOV should be second (score ~0.50)
    first_opcodes = [instr.split()[0] for instr in prioritized[0].lhs_seq]
    assert "ADD" in first_opcodes, "ADD rule should be prioritized first"
    
    print("  ✓ Rules prioritized by score")
    print(f"  ✓ First rule: {' '.join(first_opcodes)} (highest score)")
    
    # TEST 8: Cleanup
    print("\n[TEST 8] Cleanup")
    clear_database(db_path)
    assert not os.path.exists(db_path), "Database should be removed"
    print("  ✓ Database removed")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print("\nVerified:")
    print("  ✓ Rule persistence (save/load)")
    print("  ✓ Memory persistence (scores preserved)")
    print("  ✓ Feedback updates scores correctly")
    print("  ✓ Pruning removes low-performers")
    print("  ✓ Prioritization works correctly")
    print("  ✓ Round-trip integrity maintained")
    
    return True


if __name__ == "__main__":
    try:
        success = test_end_to_end()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
