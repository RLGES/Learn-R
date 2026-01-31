## SMT-Based Rule Verification

This document describes the SMT-based verification system for learned rewrite rules.

### Overview

The verification system uses **z3-solver** to formally verify that learned rewrite rules are semantically correct before they are applied. This prevents incorrect transformations from being added to the optimization pipeline.

### Architecture

The verification system consists of four main components:

1. **`symbolic_state.py`** - Models machine state symbolically
   - Registers represented as 64-bit bit-vectors
   - Flags represented as boolean variables
2. **`symbolic_executor.py`** - Executes instructions symbolically
   - Supports: MOV, ADD, SUB, CMP
   - Transforms symbolic state according to instruction semantics
3. **`equivalence_checker.py`** - Checks sequence equivalence
   - Uses SMT solver to prove equivalence
   - Returns UNSAT → sequences are equivalent
4. **`rule_verifier.py`** - Verifies ParsedRule objects
   - Converts rules to instruction sequences
   - Calls equivalence checker

### How It Works

```
┌─────────────────┐
│  Learned Rule   │
│  LHS → RHS      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Symbolic Execution     │
│  ┌────────┐  ┌────────┐ │
│  │ LHS    │  │ RHS    │ │
│  │ State  │  │ State  │ │
│  └────────┘  └────────┘ │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  SMT Solver (z3)        │
│  Assert: stateA ≠ stateB│
│  Check: SAT or UNSAT?   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Result                 │
│  UNSAT → ✓ Equivalent   │
│  SAT   → ✗ Not Equiv    │
└─────────────────────────┘
```

### Installation

The verification system requires z3-solver:

```bash
pip install z3-solver
```

If z3 is not installed, verification will be automatically disabled.

### Usage

#### Standalone Verification

```python
from verification import verify_rule
from learned_rules.rule_parser import ParsedRule

# Create a rule
rule = ParsedRule(
    lhs_seq=["MOV RAX, RBX", "MOV RCX, RAX"],
    rhs_seq=["MOV RCX, RBX"]
)

# Verify it
is_valid = verify_rule(rule)
print(f"Rule is {'valid' if is_valid else 'invalid'}")
```

#### Integrated Verification

Verification is automatically enabled in `LearnedRuleManager`:

```python
from learned_rules import LearnedRuleManager

# Create manager with verification enabled (default)
manager = LearnedRuleManager(enable_verification=True)

# When proposing rules, only verified rules are kept
rules = manager.propose_rules(instruction_window)
# ✓ Verified: MOV chain elimination
# ✗ Rejected: Invalid transformation
```

#### Checking Verification Stats

```python
stats = manager.get_verification_stats()
print(f"Total checked: {stats['total_checked']}")
print(f"Verified: {stats['verified']}")
print(f"Rejected: {stats['rejected']}")
print(f"Errors: {stats['errors']}")
```

### Supported Instructions

The current implementation supports a subset of x86-64 instructions:

| Instruction    | Semantics        | Flags  |
| -------------- | ---------------- | ------ |
| `MOV dst, src` | dst := src       | -      |
| `ADD dst, src` | dst := dst + src | -      |
| `SUB dst, src` | dst := dst - src | -      |
| `CMP r1, r2`   | (compare)        | ZF, SF |

### Examples

#### Example 1: Valid Transformation

```
LHS: MOV RAX, RBX
     MOV RCX, RAX
RHS: MOV RCX, RBX

Result: ✓ VERIFIED (equivalent)
```

The solver proves that both sequences result in the same final state.

#### Example 2: Invalid Transformation

```
LHS: ADD RAX, 5
RHS: SUB RAX, 5

Result: ✗ REJECTED (not equivalent)
```

The solver finds a counterexample where the states differ.

#### Example 3: Identity Transformation

```
LHS: ADD RAX, 5
     SUB RAX, 5
RHS: (empty)

Result: ✓ VERIFIED (equivalent)
```

The operations cancel out, leaving the state unchanged.

### Configuration

#### Timeout

Verification has a configurable timeout (default: 5000ms):

```python
from verification import verify_rule

# Shorter timeout for faster feedback
is_valid = verify_rule(rule, timeout_ms=2000)
```

#### Disabling Verification

```python
# Disable verification to speed up pipeline
manager = LearnedRuleManager(enable_verification=False)
```

### Limitations

1. **Instruction Coverage**: Only MOV, ADD, SUB, CMP are supported
   - Extend `symbolic_executor.py` to add more instructions
2. **Memory Operations**: Memory loads/stores not modeled
   - Only register and immediate operands supported
3. **Flags**: Limited flag modeling
   - Only ZF, SF modeled for CMP
   - ADD/SUB don't set flags currently
4. **Solver Timeout**: Complex rules may timeout
   - Increase timeout or simplify rules

### Performance

Verification adds overhead to rule generation:

- **Per-rule cost**: ~50-200ms (depends on complexity)
- **Typical overhead**: <5% for learned rule pipeline
- **Benefits**: Prevents incorrect optimizations that could:
  - Corrupt program semantics
  - Cause crashes or wrong output
  - Waste time debugging bad rules

### Testing

Run the verification demos:

```bash
# Without z3 (shows structure)
python examples/demo_verification.py

# With z3 (runs full verification)
python examples/test_verification_with_z3.py
```

### Extending the System

#### Adding New Instructions

1. Add semantics to `symbolic_executor.py`:

```python
def execute_xor(self, instr: Instruction, state: SymbolicState) -> None:
    dst = instr.dst
    src = instr.srcs[0]

    dst_value = state.get_register(dst)
    src_value = self._parse_operand(src, state)

    result = dst_value ^ src_value  # XOR
    state.set_register(dst, result)
```

2. Register in `supported_opcodes` set
3. Add case in `execute_instruction`

#### Adding Flag Support

Extend flag modeling in `symbolic_executor.py`:

```python
# For ADD with flags
result = dst_value + src_value
state.set_register(dst, result)

# Set flags
state.set_flag('zf', result == 0)
state.set_flag('sf', result < 0)
state.set_flag('cf', result > BitVecVal(2**64 - 1, 64))  # Carry
```

### Troubleshooting

#### z3-solver Installation Issues

```bash
# Try upgrading pip first
python -m pip install --upgrade pip
pip install z3-solver

# On Windows, may need Visual C++ build tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

#### Verification Timeouts

If rules consistently timeout:

1. Increase timeout: `verify_rule(rule, timeout_ms=10000)`
2. Simplify rule conditions
3. Check for complex register dependencies

#### False Negatives

If a valid rule is rejected:

1. Check instruction parsing in `rule_verifier.py`
2. Verify operand order matches convention
3. Ensure all instructions are supported

### Future Work

- [ ] Add memory modeling for load/store operations
- [ ] Support more x86-64 instructions (MUL, DIV, shifts, etc.)
- [ ] Model all FLAGS register bits
- [ ] Add support for conditional jumps
- [ ] Parallel verification for multiple rules
- [ ] Cache verification results
- [ ] Generate counterexamples for debugging

### References

- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [SMT-LIB Standard](http://smtlib.cs.uiowa.edu/)
- [Alive2: Bounded Translation Validation for LLVM](https://github.com/AliveToolkit/alive2)
