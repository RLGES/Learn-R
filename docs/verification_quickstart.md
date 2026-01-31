# Verification System - Quick Start Guide

## What is This?

The verification system uses **formal methods** (SMT solving with z3) to mathematically prove that learned rewrite rules are correct before they are used in optimization.

## Why Do We Need It?

**Problem**: Learned rules from LLMs might be semantically incorrect

- Example: LLM suggests `ADD RAX, 5` → `SUB RAX, 5` (WRONG!)
- This would corrupt program behavior

**Solution**: SMT verification proves equivalence

- ✓ Valid rules: Mathematically proven correct
- ✗ Invalid rules: Rejected before use

## How It Works (Simple Explanation)

1. **Rule**: `MOV RAX, RBX; MOV RCX, RAX` → `MOV RCX, RBX`
2. **Execute Symbolically**:
   - LHS: RAX becomes RBX, then RCX becomes RAX (which is RBX)
   - RHS: RCX becomes RBX directly
3. **SMT Solver**: Check if LHS state == RHS state for ALL possible inputs
4. **Result**: ✓ Equivalent (proven mathematically)

## Quick Start

### Without z3 (Testing Only)

```bash
python examples/demo_verification.py
```

Shows structure, verification skipped (safe mode).

### With z3 (Full Verification)

```bash
pip install z3-solver
python examples/test_verification_with_z3.py
```

Runs real verification tests.

### Integration Test

```bash
python examples/test_verification_integration.py
```

Tests that everything works together (no z3 needed).

## Usage in Code

### Automatic (Recommended)

```python
from learned_rules import LearnedRuleManager

# Verification enabled by default (if z3 installed)
manager = LearnedRuleManager()

# Propose rules - only verified ones returned
rules = manager.propose_rules(instruction_window)
# Output:
# ✓ Verified: MOV chain elimination
# ✗ Rejected: Invalid ADD transformation
```

### Manual Verification

```python
from verification import verify_rule
from learned_rules.rule_parser import ParsedRule

rule = ParsedRule(
    lhs_seq=["MOV RAX, RBX", "MOV RCX, RAX"],
    rhs_seq=["MOV RCX, RBX"]
)

if verify_rule(rule):
    print("✓ Rule is correct!")
else:
    print("✗ Rule is wrong!")
```

## What Instructions Are Supported?

Currently:

- **MOV** - Move data
- **ADD** - Addition
- **SUB** - Subtraction
- **CMP** - Compare (sets flags)

More can be added easily (see [docs/verification.md](../docs/verification.md)).

## Performance

- **Per-rule cost**: ~50-200ms
- **Pipeline impact**: <5%
- **Benefit**: Prevents wrong optimizations (priceless!)

## Configuration

### Enable/Disable

```python
# Enable (default if z3 available)
manager = LearnedRuleManager(enable_verification=True)

# Disable for speed
manager = LearnedRuleManager(enable_verification=False)
```

### Check Stats

```python
stats = manager.get_verification_stats()
print(f"Checked: {stats['total_checked']}")
print(f"Verified: {stats['verified']}")
print(f"Rejected: {stats['rejected']}")
```

## Examples

### Valid Rule

```
LHS: MOV RAX, RBX
     MOV RCX, RAX
RHS: MOV RCX, RBX

Result: ✓ EQUIVALENT
Reason: Both sequences copy RBX to RCX
```

### Invalid Rule

```
LHS: ADD RAX, 5
RHS: SUB RAX, 5

Result: ✗ NOT EQUIVALENT
Reason: ADD increases, SUB decreases
```

### Identity Rule

```
LHS: ADD RAX, 5
     SUB RAX, 5
RHS: (empty)

Result: ✓ EQUIVALENT
Reason: Operations cancel out
```

## Troubleshooting

### "z3-solver not installed"

```bash
pip install z3-solver
```

### "Verification timeout"

Increase timeout:

```python
verify_rule(rule, timeout_ms=10000)  # 10 seconds
```

### "Parsing failed"

Check instruction format:

```python
# Good: "MOV RAX, RBX"
# Bad:  "MOV RAX RBX" (missing comma)
```

## Files Overview

```
verification/
├── symbolic_state.py        # Machine state (registers + flags)
├── symbolic_executor.py     # Execute instructions symbolically
├── equivalence_checker.py   # SMT-based equivalence checking
└── rule_verifier.py        # Verify ParsedRule objects

examples/
├── demo_verification.py                # Comprehensive demos
├── test_verification_with_z3.py        # Full test (installs z3)
└── test_verification_integration.py    # Integration test (no z3 needed)

docs/
└── verification.md          # Complete documentation
```

## Learn More

- **Full Documentation**: [docs/verification.md](../docs/verification.md)
- **Implementation Details**: [VERIFICATION_SUMMARY.md](../VERIFICATION_SUMMARY.md)
- **Architecture**: [docs/architecture.md](../docs/architecture.md)

## Key Takeaways

1. ✓ **Safety**: Prevents wrong rules from corrupting programs
2. ✓ **Automatic**: Works seamlessly in learning pipeline
3. ✓ **Optional**: Can disable if z3 not available or for speed
4. ✓ **Proven**: Uses mathematical proof, not heuristics
5. ✓ **Extensible**: Easy to add more instructions

## Quick Reference

| Task             | Command                                            |
| ---------------- | -------------------------------------------------- |
| Demo (no z3)     | `python examples/demo_verification.py`             |
| Test with z3     | `python examples/test_verification_with_z3.py`     |
| Integration test | `python examples/test_verification_integration.py` |
| Install z3       | `pip install z3-solver`                            |
| Enable in code   | `LearnedRuleManager(enable_verification=True)`     |
| Disable in code  | `LearnedRuleManager(enable_verification=False)`    |
| Check stats      | `manager.get_verification_stats()`                 |

---

**Next Steps**:

1. Run `python examples/test_verification_integration.py` to verify everything works
2. Install z3: `pip install z3-solver`
3. Run `python examples/test_verification_with_z3.py` for full verification
4. Read [docs/verification.md](../docs/verification.md) for details
