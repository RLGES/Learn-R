"""
Comprehensive test for SMT verification integration.

Tests the complete verification system without requiring z3 installation.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_verification_module_import():
    """Test that verification module can be imported."""
    print("Test 1: Verification module import...")
    try:
        import verification
        print("  \u2713 verification package imported")
        
        from verification import SymbolicState, execute_sequence, are_sequences_equivalent, verify_rule
        print("  \u2713 All verification functions imported")
        
        return True
    except ImportError as e:
        print(f"  \u2717 Import failed: {e}")
        return False


def test_graceful_z3_handling():
    """Test that system handles missing z3 gracefully."""
    print("\nTest 2: Graceful z3 handling...")
    try:
        from verification.symbolic_state import is_z3_available
        
        z3_available = is_z3_available()
        if z3_available:
            print("  \u2713 z3-solver is installed")
        else:
            print("  \u2713 z3-solver not installed (expected)")
            print("  \u2713 System handles gracefully")
        
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        return False


def test_manager_integration():
    """Test LearnedRuleManager integration."""
    print("\nTest 3: LearnedRuleManager integration...")
    try:
        from learned_rules import LearnedRuleManager
        
        # Create manager with verification
        manager = LearnedRuleManager(enable_verification=True)
        print(f"  \u2713 Manager created with verification={manager.enable_verification}")
        
        # Check verification stats
        stats = manager.get_verification_stats()
        print(f"  \u2713 Verification stats accessible: {stats}")
        
        # Check that existing functionality still works
        from learned_rules.rule_parser import ParsedRule
        rule = ParsedRule(
            lhs_seq=["MOV EAX, EBX"],
            rhs_seq=["MOV EAX, EBX"]
        )
        print(f"  \u2713 ParsedRule creation works")
        
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_verification_api():
    """Test rule verification API."""
    print("\nTest 4: Rule verification API...")
    try:
        from verification import verify_rule
        from learned_rules.rule_parser import ParsedRule
        
        # Create a simple rule
        rule = ParsedRule(
            lhs_seq=["MOV EAX, EBX"],
            rhs_seq=["MOV EAX, EBX"]
        )
        
        # Try to verify (will fail gracefully if z3 not installed)
        result = verify_rule(rule)
        print(f"  \u2713 verify_rule() callable: returned {result}")
        
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        return False


def test_instruction_parsing():
    """Test instruction parsing in rule verifier."""
    print("\nTest 5: Instruction parsing...")
    try:
        from verification.rule_verifier import parse_instruction_string
        
        # Test various instruction formats
        test_cases = [
            ("MOV RAX, RBX", "MOV", "RAX", ["RBX"]),
            ("ADD EAX, 5", "ADD", "EAX", ["5"]),
            ("SUB RCX, RDX", "SUB", "RCX", ["RDX"]),
            ("CMP R1, R2", "CMP", "R1", ["R2"]),
        ]
        
        for instr_str, expected_op, expected_dst, expected_srcs in test_cases:
            instr = parse_instruction_string(instr_str)
            if instr is None:
                print(f"  \u2717 Failed to parse: {instr_str}")
                return False
            
            if instr.opcode != expected_op:
                print(f"  \u2717 Wrong opcode: {instr.opcode} != {expected_op}")
                return False
            
            if instr.dst != expected_dst:
                print(f"  \u2717 Wrong dst: {instr.dst} != {expected_dst}")
                return False
            
            if instr.srcs != expected_srcs:
                print(f"  \u2717 Wrong srcs: {instr.srcs} != {expected_srcs}")
                return False
        
        print(f"  \u2713 All {len(test_cases)} instruction formats parsed correctly")
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        return False


def test_verification_stats():
    """Test verification statistics tracking."""
    print("\nTest 6: Verification statistics...")
    try:
        from learned_rules import LearnedRuleManager
        
        manager = LearnedRuleManager(enable_verification=True)
        
        # Get stats
        stats = manager.get_verification_stats()
        
        # Check structure
        required_keys = ['total_checked', 'verified', 'rejected', 'errors']
        for key in required_keys:
            if key not in stats:
                print(f"  \u2717 Missing stat key: {key}")
                return False
        
        print(f"  \u2713 All stat keys present: {list(stats.keys())}")
        print(f"  \u2713 Initial values: {stats}")
        
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        return False


def test_backward_compatibility():
    """Test that existing code still works."""
    print("\nTest 7: Backward compatibility...")
    try:
        from learned_rules import LearnedRuleManager
        
        # Old usage (without verification parameter)
        manager1 = LearnedRuleManager()
        print("  \u2713 LearnedRuleManager() works without parameters")
        
        # With existing parameter
        manager2 = LearnedRuleManager(existing_rule_names={'rule1', 'rule2'})
        print("  \u2713 LearnedRuleManager(existing_rule_names=...) works")
        
        # Disable verification explicitly
        manager3 = LearnedRuleManager(enable_verification=False)
        print(f"  \u2713 Verification can be disabled: {manager3.enable_verification}")
        
        return True
    except Exception as e:
        print(f"  \u2717 Error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("VERIFICATION INTEGRATION TEST SUITE")
    print("=" * 70 + "\n")
    
    tests = [
        test_verification_module_import,
        test_graceful_z3_handling,
        test_manager_integration,
        test_rule_verification_api,
        test_instruction_parsing,
        test_verification_stats,
        test_backward_compatibility,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n\u2717 Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n\u2713 ALL TESTS PASSED")
        return True
    else:
        print(f"\n\u2717 {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
