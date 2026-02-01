# Bitwise Operations Extension

## Overview

Extended the assembly optimizer to support bitwise operations and shifts, including instruction-level support, symbolic execution, and peephole optimization rules.

## Changes

### 1. Extended Instruction Class ([asm_ir/instruction.py](asm_ir/instruction.py))

Added support for additional opcodes:

- **Arithmetic**: `ADD`, `SUB`, `MUL`, `IMUL`
- **Bitwise**: `AND`, `OR`, `XOR`, `NOT`
- **Shift**: `SHL`, `SHR`
- **Load Effective Address**: `LEA`

#### Updated Methods:

**`reads()` method:**

- Read-modify-write operations now properly track that they read the destination register
- Includes: `ADD`, `SUB`, `MUL`, `IMUL`, `AND`, `OR`, `XOR`, `SHL`, `SHR`
- `LEA` only reads sources (address calculation)

**`get_flags_written()` method** (NEW):

- **Arithmetic operations** (`ADD`, `SUB`, `MUL`, `IMUL`, `CMP`): Write `{zf, sf, cf, of}`
- **Bitwise operations** (`AND`, `OR`, `XOR`, `NOT`): Write `{zf, sf, pf}`
- **Shift operations** (`SHL`, `SHR`): Write `{zf, sf, cf, of}`
- **LEA and MOV**: Don't affect flags

### 2. Extended Symbolic Executor ([verification/symbolic_executor.py](verification/symbolic_executor.py))

Added symbolic execution support for all new operations using z3 bitvector primitives:

| Opcode | z3 Operation | Python Operator | Description           |
| ------ | ------------ | --------------- | --------------------- |
| `AND`  | `bvand`      | `&`             | Bitwise AND           |
| `OR`   | `bvor`       | `\|`            | Bitwise OR            |
| `XOR`  | `bvxor`      | `^`             | Bitwise XOR           |
| `NOT`  | `bvnot`      | `~`             | Bitwise NOT           |
| `SHL`  | `bvshl`      | `<<`            | Left shift            |
| `SHR`  | `LShR`       | `>>`            | Logical right shift   |
| `IMUL` | `bvmul`      | `*`             | Signed multiplication |

**Example symbolic execution:**

```python
# AND rax(0xFF), rbx(0x0F) → rax = 0x0F
state.set_register("rax", BitVecVal(0xFF, 64))
state.set_register("rbx", BitVecVal(0x0F, 64))
executor.execute_instruction(Instruction("AND", "rax", ["rbx"]), state)
# Result: rax = 0x0F (15)
```

### 3. New Bitwise Identity Rules ([rewrite_rules/tier1_peephole/bitwise_identities.py](rewrite_rules/tier1_peephole/bitwise_identities.py))

Six new peephole optimization rules:

#### Rule 1: `and_with_zero`

```
AND r, 0  →  MOV r, 0
```

Bitwise AND with 0 always produces 0.

#### Rule 2: `or_with_zero`

```
OR r, 0  →  (eliminate)
```

Bitwise OR with 0 is the identity operation (no-op).

#### Rule 3: `xor_with_zero`

```
XOR r, 0  →  (eliminate)
```

Bitwise XOR with 0 is the identity operation (no-op).

#### Rule 4: `xor_self`

```
XOR r, r  →  MOV r, 0
```

XOR of a value with itself always produces 0. Includes precondition to verify source and destination are the same register.

#### Rule 5: `shl_by_zero`

```
SHL r, 0  →  (eliminate)
```

Left shift by 0 is a no-op.

#### Rule 6: `shr_by_zero`

```
SHR r, 0  →  (eliminate)
```

Right shift by 0 is a no-op.

## Integration

All new rules are exported from [rewrite_rules/tier1_peephole/**init**.py](rewrite_rules/tier1_peephole/__init__.py) and can be used with the hierarchical rewrite engine:

```python
from rewrite_rules.tier1_peephole import (
    and_with_zero_rule,
    or_with_zero_rule,
    xor_with_zero_rule,
    xor_self_rule,
    shl_by_zero_rule,
    shr_by_zero_rule,
)

# Add to engine tier 1 rules
tier1_rules = [
    mov_elimination_rule,
    and_with_zero_rule,
    xor_self_rule,
    # ... etc
]
```

## Testing

Run the test suite to verify all functionality:

```bash
python tests/test_bitwise_opcodes.py
```

**Test results:**

- ✅ Instruction `reads()` and `writes()` correctly handle all new opcodes
- ✅ Flags tracking via `get_flags_written()` works for arithmetic, bitwise, and shift operations
- ✅ Symbolic executor handles all bitwise operations (requires z3-solver)
- ✅ All 6 bitwise identity rules defined and validated
- ✅ XOR self precondition correctly distinguishes `XOR r, r` from `XOR r, s`

## Example Optimizations

### Before:

```assembly
XOR rax, rax      ; Clear register
SHL rbx, 0        ; No-op shift
AND rcx, 0        ; Clear register
OR rdx, 0         ; No-op OR
```

### After (optimized):

```assembly
MOV rax, 0        ; Explicit zero (from XOR self)
                  ; SHL eliminated
MOV rcx, 0        ; Explicit zero (from AND)
                  ; OR eliminated
```

## Files Modified

1. `asm_ir/instruction.py` - Extended reads(), writes(), added get_flags_written()
2. `verification/symbolic_executor.py` - Added 7 new execution methods (AND, OR, XOR, NOT, SHL, SHR, IMUL)
3. `hierarchical_engine/engine.py` - Fixed method call from apply_rule → apply_rewrite

## Files Created

1. `rewrite_rules/tier1_peephole/bitwise_identities.py` - 6 new optimization rules (~120 lines)
2. `tests/test_bitwise_opcodes.py` - Comprehensive test suite (~180 lines)

## Capabilities Added

- **11 new opcodes**: ADD, SUB, MUL, IMUL, AND, OR, XOR, NOT, SHL, SHR, LEA
- **7 new symbolic execution handlers**: Full z3-based verification support
- **6 new optimization rules**: Identity elimination for bitwise operations
- **Flag tracking**: Proper modeling of x86 flag behavior

## Future Enhancements

Potential next steps:

1. **More bitwise rules**: AND with -1 (all 1's), strength reduction (MUL by power of 2 → SHL)
2. **Algebraic identities**: Distributive laws, De Morgan's laws
3. **Constant folding**: Evaluate operations on constants at compile time
4. **Strength reduction**: Replace expensive operations with cheaper equivalents
5. **Conditional execution**: Support for CMOV, conditional flags

## Notes

- Shift operations assume logical shifts (unsigned)
- IMUL implements signed multiplication semantics
- LEA is useful for address arithmetic without affecting flags
- All rules respect x86-64 semantics and flag behavior
