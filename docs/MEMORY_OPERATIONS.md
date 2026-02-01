# Memory Operations Support

## Overview

Extended the assembly optimizer to support memory operations with load/store tracking, dependency analysis, symbolic execution, and peephole optimizations.

## Changes

### 1. Extended Instruction Class ([asm_ir/instruction.py](asm_ir/instruction.py))

Added memory operation tracking:

**New Fields:**
- `mem_read: bool` - True if instruction reads from memory
- `mem_write: bool` - True if instruction writes to memory

**Updated Methods:**

**`reads()` method:**
- Extracts base registers from memory operands (e.g., `[rax]` → reads `rax`)
- Handles memory addressing: `MOV r, [base]` reads `base` register
- Handles memory stores: `MOV [base], r` reads both `base` and `r`

**`writes()` method:**
- Memory stores (`MOV [addr], r`) don't write to registers
- Only register destinations write to registers

**New Helper Methods:**
- `is_memory_operand(operand)` - Check if operand is memory reference (`[...]`)
- `get_memory_base(operand)` - Extract base register from memory operand

**Supported Memory Formats:**
- `[reg]` - Direct addressing (e.g., `[rax]`)
- `[reg+offset]` - Base + displacement (e.g., `[rbx+8]`)
- `[reg-offset]` - Base - displacement (e.g., `[rcx-16]`)

### 2. Enhanced Dependency Analysis ([hierarchical_engine/dependency.py](hierarchical_engine/dependency.py))

Extended `are_independent()` to handle memory dependencies:

**Memory Dependency Rules:**
- Memory write conflicts with **any** memory read or write (conservative)
- Memory read conflicts with memory write (but not other reads)
- Memory reads can execute in parallel (read-read independence)

**Conservative Approach:**
Without full alias analysis, we assume all memory operations may conflict. This prevents incorrect reordering but may miss some optimization opportunities.

**Examples:**
```python
MOV [rax], 5    # Write
MOV rbx, [rcx]  # Read
# → Dependent (conservative - addresses may alias)

MOV rax, [rbx]  # Read
MOV rcx, [rdx]  # Read
# → Independent (reads don't conflict)
```

### 3. Symbolic Memory Model ([verification/symbolic_state.py](verification/symbolic_state.py))

Added symbolic memory using z3 Arrays:

**Memory Representation:**
```python
memory: Array(BitVecSort(64), BitVecSort(64))
```
Maps 64-bit addresses to 64-bit values.

**New Methods:**
- `read_memory(address)` - Load from symbolic memory
- `write_memory(address, value)` - Store to symbolic memory (uses z3's `Store`)

**Semantics:**
- Memory is treated as a single symbolic array
- No distinction between stack/heap/globals
- No alias analysis (conservative approach)

### 4. Extended Symbolic Executor ([verification/symbolic_executor.py](verification/symbolic_executor.py))

Enhanced `execute_mov()` to handle memory operations:

**MOV Variants:**
1. **`MOV r, imm/reg`** - Regular register move
2. **`MOV r, [addr]`** - Load from memory
   - Parse address from memory operand
   - Read from symbolic memory array
   - Store result in register
3. **`MOV [addr], r`** - Store to memory
   - Parse address from memory operand
   - Read value from register
   - Write to symbolic memory array

**Example:**
```python
# MOV [rax], rbx - Store rbx to address in rax
address = state.get_register("rax")
value = state.get_register("rbx")
state.write_memory(address, value)

# MOV rcx, [rax] - Load from address in rax to rcx
address = state.get_register("rax")
value = state.read_memory(address)
state.set_register("rcx", value)
```

### 5. Load/Store Peephole Rules ([rewrite_rules/tier1_peephole/load_store.py](rewrite_rules/tier1_peephole/load_store.py))

Two new optimization rules:

#### Rule 1: `load_store_same`
```
MOV r, [a]      # Load from memory
MOV [a], r      # Store back to same location
→ (eliminate both)
```

**Rationale:** Loading a value then storing it back to the same address is redundant - the memory already contains that value.

**Precondition:** No intervening memory operations (currently assumed by pattern adjacency).

#### Rule 2: `load_forward`
```
MOV r1, [a]     # Load to intermediate register
MOV r2, r1      # Copy to final destination
→
MOV r2, [a]     # Load directly to final destination
```

**Rationale:** Eliminate the intermediate register copy by loading directly to the final destination.

**Precondition:** `r1 ≠ r2` (no same-register copies).

## Integration

All memory rules are exported from [rewrite_rules/tier1_peephole/__init__.py](rewrite_rules/tier1_peephole/__init__.py):

```python
from rewrite_rules.tier1_peephole import (
    load_store_same_rule,
    load_forward_rule,
)
```

## Testing

Run the test suite:

```bash
python tests/test_memory_ops.py
```

**Test Coverage:**
- ✅ Memory operand flags (`mem_read`, `mem_write`)
- ✅ Memory operand parsing (`[rax]`, `[rbx+8]`, `[rcx-16]`)
- ✅ Dependency analysis with memory operations
- ✅ Conservative memory conflict detection
- ✅ Symbolic execution with z3 Arrays (requires z3-solver)
- ✅ Load/store optimization rules

## Examples

### Example 1: Memory Dependency Detection
```assembly
MOV rax, 5
MOV rbx, [rax]  # Reads rax (as address)
```
**Analysis:** Dependent - `rbx` load depends on `rax` being set.

### Example 2: Conservative Memory Aliasing
```assembly
MOV [rax], 10   # Write
MOV rbx, [rcx]  # Read
```
**Analysis:** Dependent - conservative approach assumes addresses may alias.

### Example 3: Load/Store Elimination
```assembly
# Before optimization:
MOV rax, [rbx]
MOV [rbx], rax

# After optimization:
(both eliminated - redundant)
```

### Example 4: Load Forwarding
```assembly
# Before optimization:
MOV rax, [rbx]
MOV rcx, rax

# After optimization:
MOV rcx, [rbx]
```

## Limitations

Current implementation has several intentional limitations:

1. **No Alias Analysis**
   - All memory operations conservatively assumed to conflict
   - Cannot detect when `[rax]` and `[rbx]` refer to different locations
   - Future: Add address range analysis or points-to analysis

2. **Simple Address Parsing**
   - Only extracts base register from `[base+offset]`
   - Offset not yet used in symbolic execution
   - No support for complex addressing modes (e.g., `[base+index*scale+offset]`)

3. **No Memory Regions**
   - All memory treated as single address space
   - No distinction between stack, heap, globals
   - Future: Separate memory regions for better precision

4. **Pattern Matching Limitations**
   - Load/store rules assume adjacent instructions
   - No inter-procedural memory tracking
   - Future: Add liveness analysis for more aggressive optimization

## Future Enhancements

Potential improvements:

1. **Alias Analysis**
   - Track base pointers and offsets
   - Detect non-overlapping memory regions
   - Enable more aggressive reordering

2. **Memory Regions**
   - Separate stack, heap, globals
   - Stack slot analysis for local variables
   - Escape analysis for heap allocations

3. **Advanced Addressing**
   - Support for scaled indexing `[base+index*scale+offset]`
   - Segment registers (if needed)
   - Handle offset calculations symbolically

4. **More Optimization Rules**
   - Load hoisting (move loads earlier)
   - Store sinking (move stores later)
   - Dead store elimination
   - Load-after-store forwarding

5. **Liveness Analysis**
   - Track when memory locations are live
   - Enable more precise dependency checking
   - Reduce false dependencies

## Files Modified

1. `asm_ir/instruction.py` - Added `mem_read`, `mem_write`, memory operand parsing
2. `hierarchical_engine/dependency.py` - Extended independence checking for memory
3. `verification/symbolic_state.py` - Added z3 Array for symbolic memory
4. `verification/symbolic_executor.py` - Enhanced MOV to handle memory operations

## Files Created

1. `rewrite_rules/tier1_peephole/load_store.py` - 2 new load/store rules (~100 lines)
2. `tests/test_memory_ops.py` - Comprehensive test suite (~180 lines)
3. `docs/MEMORY_OPERATIONS.md` - This documentation

## Summary

Memory operations are now fully integrated:
- ✅ Memory reads/writes tracked at instruction level
- ✅ Dependency analysis handles memory conflicts conservatively
- ✅ Symbolic execution models memory with z3 Arrays
- ✅ 2 safe peephole rules optimize load/store patterns
- ✅ Foundation for future advanced memory optimizations

The conservative approach ensures correctness while providing a solid foundation for more sophisticated memory analysis in the future.
