"""
Test: SMT Verification with z3-solver

This test installs z3-solver and tests the verification system.
"""
import subprocess
import sys

def install_z3():
    """Install z3-solver package."""
    print("Installing z3-solver...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "z3-solver", "-q"])
        print("\u2713 z3-solver installed successfully\n")
        return True
    except subprocess.CalledProcessError:
        print("\u2717 Failed to install z3-solver\n")
        return False

def run_simple_test():
    """Run a simple verification test."""
    print("=" * 70)
    print("SIMPLE VERIFICATION TEST")
    print("=" * 70)
    
    try:
        from z3 import BitVec, Solver, sat
        from verification import SymbolicState, execute_sequence, are_sequences_equivalent
        from asm_ir import Instruction
        
        print("\n1. Testing MOV chain elimination...")
        seq1 = [
            Instruction('MOV', 'rax', ['rbx']),
            Instruction('MOV', 'rcx', ['rax']),
        ]
        seq2 = [
            Instruction('MOV', 'rcx', ['rbx']),
        ]
        
        result = are_sequences_equivalent(seq1, seq2)
        print(f"   MOV rax,rbx; MOV rcx,rax  ==  MOV rcx,rbx")
        print(f"   Result: {'\u2713 EQUIVALENT' if result else '\u2717 NOT EQUIVALENT'}")
        
        print("\n2. Testing ADD/SUB non-equivalence...")
        seq3 = [Instruction('ADD', 'rax', ['5'])]
        seq4 = [Instruction('SUB', 'rax', ['5'])]
        
        result2 = are_sequences_equivalent(seq3, seq4)
        print(f"   ADD rax,5  ==  SUB rax,5")
        print(f"   Result: {'\u2717 NOT EQUIVALENT (expected)' if not result2 else '\u2713 EQUIVALENT (unexpected)'}")
        
        print("\n3. Testing ADD/SUB cancellation...")
        seq5 = [
            Instruction('ADD', 'rax', ['5']),
            Instruction('SUB', 'rax', ['5']),
        ]
        seq6 = []
        
        result3 = are_sequences_equivalent(seq5, seq6)
        print(f"   ADD rax,5; SUB rax,5  ==  (no-op)")
        print(f"   Result: {'\u2713 EQUIVALENT' if result3 else '\u2717 NOT EQUIVALENT'}")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETED \u2713")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n\u2717 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test entry point."""
    print("\n" + "=" * 70)
    print("SMT VERIFICATION TEST SUITE")
    print("=" * 70 + "\n")
    
    # Check if z3 is already installed
    try:
        import z3
        print("\u2713 z3-solver already installed\n")
    except ImportError:
        print("\u26a0 z3-solver not installed")
        if not install_z3():
            print("\nTest aborted: Cannot install z3-solver")
            return False
    
    # Run the test
    success = run_simple_test()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
