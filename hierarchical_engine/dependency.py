"""
Dependency analysis utilities for assembly instructions.
"""
from asm_ir import Instruction


def has_register_dependency(inst1: Instruction, inst2: Instruction) -> bool:
    """
    Check if two instructions have a register dependency.
    
    A register dependency exists if:
    - inst1 writes a register that inst2 reads or writes
    - inst2 writes a register that inst1 reads or writes
    
    Args:
        inst1: First instruction
        inst2: Second instruction
    
    Returns:
        True if a register dependency exists, False otherwise
    """
    writes1 = inst1.writes()
    reads1 = inst1.reads()
    writes2 = inst2.writes()
    reads2 = inst2.reads()
    
    # Check if inst1 writes something inst2 reads or writes
    if writes1 & (reads2 | writes2):
        return True
    
    # Check if inst2 writes something inst1 reads or writes
    if writes2 & (reads1 | writes1):
        return True
    
    return False


def has_flag_dependency(inst1: Instruction, inst2: Instruction) -> bool:
    """
    Check if two instructions have a flag dependency.
    
    A flag dependency exists if:
    - inst1 writes flags that inst2 reads
    - inst2 writes flags that inst1 reads
    
    Args:
        inst1: First instruction
        inst2: Second instruction
    
    Returns:
        True if a flag dependency exists, False otherwise
    """
    # Check if inst1 writes flags that inst2 reads
    if inst1.flags_written & inst2.flags_read:
        return True
    
    # Check if inst2 writes flags that inst1 reads
    if inst2.flags_written & inst1.flags_read:
        return True
    
    return False


def are_independent(inst1: Instruction, inst2: Instruction) -> bool:
    """
    Check if two instructions are independent (can be reordered).
    
    Instructions are independent if they have no register dependencies,
    no flag dependencies, and no memory dependencies.
    
    Args:
        inst1: First instruction
        inst2: Second instruction
    
    Returns:
        True if instructions are independent, False otherwise
    """
    # Check register and flag dependencies
    if has_register_dependency(inst1, inst2) or has_flag_dependency(inst1, inst2):
        return False
    
    # Check memory dependencies
    # Conservative approach: any memory operation conflicts with any other memory operation
    # This avoids incorrect reordering without full alias analysis
    
    # Memory write conflicts with any memory read or write
    if inst1.mem_write and (inst2.mem_read or inst2.mem_write):
        return False
    
    if inst2.mem_write and (inst1.mem_read or inst1.mem_write):
        return False
    
    # Memory read conflicts with memory write (but not with other reads)
    if inst1.mem_read and inst2.mem_write:
        return False
    
    if inst2.mem_read and inst1.mem_write:
        return False
    
    return True
