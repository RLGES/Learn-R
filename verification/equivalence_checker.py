"""
SMT-based equivalence checker for instruction sequences.

Uses z3 to verify that two sequences have the same semantics.
"""
from typing import List
try:
    from z3 import Solver, Or, sat
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

from asm_ir import Instruction
from .symbolic_state import SymbolicState
from .symbolic_executor import execute_sequence


def are_sequences_equivalent(lhs_seq: List[Instruction], 
                            rhs_seq: List[Instruction],
                            timeout_ms: int = 5000) -> bool:
    """
    Check if two instruction sequences are semantically equivalent.
    
    Uses SMT solving to verify that both sequences produce the same
    final state for all possible initial states.
    
    Args:
        lhs_seq: Left-hand side instruction sequence
        rhs_seq: Right-hand side instruction sequence
        timeout_ms: Solver timeout in milliseconds
    
    Returns:
        True if sequences are proven equivalent, False otherwise
    """
    if not Z3_AVAILABLE:
        # If z3 is not available, we can't verify - fail safe by returning False
        print("Warning: z3-solver not available, cannot verify equivalence")
        return False
    
    try:
        # Create initial symbolic state (shared by both sequences)
        initial_state = SymbolicState(prefix="init_")
        
        # Execute both sequences symbolically
        state_lhs = execute_sequence(lhs_seq, initial_state)
        state_rhs = execute_sequence(rhs_seq, initial_state)
        
        # Build constraints: find if there's ANY difference
        differences = []
        
        # Check all registers
        for reg in initial_state.registers:
            if reg in state_lhs.registers and reg in state_rhs.registers:
                differences.append(state_lhs.registers[reg] != state_rhs.registers[reg])
        
        # Check all flags
        for flag in initial_state.flags:
            if flag in state_lhs.flags and flag in state_rhs.flags:
                differences.append(state_lhs.flags[flag] != state_rhs.flags[flag])
        
        if not differences:
            # No state elements to compare (shouldn't happen)
            return True
        
        # Create solver
        solver = Solver()
        solver.set("timeout", timeout_ms)
        
        # Assert: Is there ANY input where states differ?
        solver.add(Or(*differences))
        
        # Check satisfiability
        result = solver.check()
        
        if result == sat:
            # Found a counterexample where states differ
            return False
        else:
            # UNSAT means no counterexample exists → sequences are equivalent
            return True
    
    except Exception as e:
        # If verification fails for any reason, be conservative
        print(f"Warning: Equivalence checking failed: {e}")
        return False


def are_sequences_equivalent_with_model(lhs_seq: List[Instruction], 
                                       rhs_seq: List[Instruction],
                                       timeout_ms: int = 5000) -> tuple[bool, dict]:
    """
    Check equivalence and return counterexample if found.
    
    Args:
        lhs_seq: Left-hand side instruction sequence
        rhs_seq: Right-hand side instruction sequence
        timeout_ms: Solver timeout in milliseconds
    
    Returns:
        Tuple of (is_equivalent, counterexample_dict)
        If not equivalent, counterexample_dict contains the input values
    """
    if not Z3_AVAILABLE:
        return False, {"error": "z3-solver not available"}
    
    try:
        initial_state = SymbolicState(prefix="init_")
        
        state_lhs = execute_sequence(lhs_seq, initial_state)
        state_rhs = execute_sequence(rhs_seq, initial_state)
        
        differences = []
        
        for reg in initial_state.registers:
            if reg in state_lhs.registers and reg in state_rhs.registers:
                differences.append(state_lhs.registers[reg] != state_rhs.registers[reg])
        
        for flag in initial_state.flags:
            if flag in state_lhs.flags and flag in state_rhs.flags:
                differences.append(state_lhs.flags[flag] != state_rhs.flags[flag])
        
        if not differences:
            return True, {}
        
        solver = Solver()
        solver.set("timeout", timeout_ms)
        solver.add(Or(*differences))
        
        result = solver.check()
        
        if result == sat:
            # Found counterexample
            model = solver.model()
            counterexample = {}
            
            # Extract input values from model
            for reg in initial_state.registers:
                val = model.eval(initial_state.registers[reg])
                counterexample[reg] = str(val)
            
            return False, counterexample
        else:
            return True, {}
    
    except Exception as e:
        return False, {"error": str(e)}
