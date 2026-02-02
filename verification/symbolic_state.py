"""
Symbolic machine state for SMT verification.

Models registers, flags, and memory symbolically using z3.
"""
try:
    from z3 import BitVec, Bool, BitVecRef, BoolRef, Array, BitVecSort
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    # Provide stub types for when z3 is not available
    BitVecRef = object
    BoolRef = object


class SymbolicState:
    """
    Symbolic machine state for verification.
    
    Represents registers as 64-bit bit-vectors and flags as boolean
    variables for SMT-based reasoning.
    """
    
    # Common x86-64 registers
    REGISTER_NAMES = [
        'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rsp', 'rbp',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
        # 32-bit aliases
        'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'esp', 'ebp',
    ]
    
    # Common flags
    FLAG_NAMES = ['zf', 'sf', 'cf', 'of']
    
    def __init__(self, prefix: str = ""):
        """
        Initialize symbolic state with fresh variables.
        
        Args:
            prefix: Optional prefix for variable names (useful for distinguishing states)
        """
        if not Z3_AVAILABLE:
            raise RuntimeError("z3-solver is not installed. Install with: pip install z3-solver")
        
        self.prefix = prefix
        
        # Initialize registers as 64-bit bit-vectors
        self.registers = {}
        for reg in self.REGISTER_NAMES:
            var_name = f"{prefix}{reg}" if prefix else reg
            self.registers[reg] = BitVec(var_name, 64)
        
        # Initialize flags as boolean variables
        self.flags = {}
        for flag in self.FLAG_NAMES:
            var_name = f"{prefix}{flag}" if prefix else flag
            self.flags[flag] = Bool(var_name)
        
        # Initialize symbolic memory as a z3 Array
        # Array maps 64-bit addresses to 64-bit values
        mem_name = f"{prefix}mem" if prefix else "mem"
        self.memory = Array(mem_name, BitVecSort(64), BitVecSort(64))
    
    def copy(self, new_prefix: str = "") -> 'SymbolicState':
        """
        Create a copy of the state with optional new prefix.
        
        Args:
            new_prefix: Prefix for variables in copied state
        
        Returns:
            New SymbolicState with same variable names (or new prefix)
        """
        new_state = SymbolicState(new_prefix if new_prefix else self.prefix)
        
        # Copy register bindings
        for reg in self.registers:
            new_state.registers[reg] = self.registers[reg]
        
        # Copy flag bindings
        for flag in self.flags:
            new_state.flags[flag] = self.flags[flag]
        
        # Copy memory
        new_state.memory = self.memory
        
        return new_state
    
    def get_register(self, name: str):
        """
        Get register by name (case-insensitive).
        
        If the register doesn't exist, creates it dynamically.
        This allows handling of normalized memory addresses like 'mem_rbp_4'.
        
        Args:
            name: Register name or normalized variable name
        
        Returns:
            BitVecRef for the register
        """
        name_lower = name.lower()
        if name_lower in self.registers:
            return self.registers[name_lower]
        
        # Auto-create symbolic variable for unknown names (e.g., mem_rbp_4)
        var_name = f"{self.prefix}{name_lower}" if self.prefix else name_lower
        self.registers[name_lower] = BitVec(var_name, 64)
        return self.registers[name_lower]
    
    def set_register(self, name: str, value) -> None:
        """
        Set register value.
        
        Args:
            name: Register name
            value: BitVecRef value
        """
        name_lower = name.lower()
        if name_lower in self.registers:
            self.registers[name_lower] = value
        else:
            # Allow setting new registers dynamically
            self.registers[name_lower] = value
    
    def get_flag(self, name: str):
        """
        Get flag by name (case-insensitive).
        
        Args:
            name: Flag name
        
        Returns:
            BoolRef for the flag
        
        Raises:
            KeyError: If flag not found
        """
        name_lower = name.lower()
        if name_lower in self.flags:
            return self.flags[name_lower]
        raise KeyError(f"Unknown flag: {name}")
    
    def set_flag(self, name: str, value) -> None:
        """
        Set flag value.
        
        Args:
            name: Flag name
            value: BoolRef value
        """
        name_lower = name.lower()
        self.flags[name_lower] = value
    
    def read_memory(self, address):
        """
        Read from symbolic memory.
        
        Args:
            address: 64-bit address (BitVecRef)
        
        Returns:
            64-bit value at that address (BitVecRef)
        """
        return self.memory[address]
    
    def write_memory(self, address, value) -> None:
        """
        Write to symbolic memory.
        
        Args:
            address: 64-bit address (BitVecRef)
            value: 64-bit value to write (BitVecRef)
        """
        from z3 import Store
        self.memory = Store(self.memory, address, value)
    
    def __str__(self) -> str:
        """String representation of state."""
        result = f"SymbolicState(prefix='{self.prefix}'):\n"
        result += "  Registers:\n"
        for reg, val in sorted(self.registers.items()):
            result += f"    {reg}: {val}\n"
        result += "  Flags:\n"
        for flag, val in sorted(self.flags.items()):
            result += f"    {flag}: {val}\n"
        return result


def is_z3_available() -> bool:
    """Check if z3-solver is available."""
    return Z3_AVAILABLE
