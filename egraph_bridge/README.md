# E-Graph Bridge for SSA Optimization

Connects SSA-form intermediate representation with equality saturation via e-graphs for powerful algebraic optimizations.

## Overview

The e-graph bridge enables optimization of SSA code by:

1. Converting SSA instructions to expression DAGs
2. Inserting expressions into an e-graph for equality saturation
3. Extracting optimized expressions with algebraic simplifications
4. Reconstructing SSA instructions from optimized expressions

## Architecture

```
SSA Instructions → Expression DAG → E-Graph → Optimized Expressions → SSA Instructions
```

### Components

**`ssa_to_expr.py`**: SSA → Expression DAG

- `ExprNode`: Expression tree representation (operations, constants, variables)
- `ssa_block_to_exprs()`: Convert SSA basic block to expression map
- `simplify_expression()`: Algebraic simplification (constant folding, identities, **phi nodes**)

**`expr_to_egraph.py`**: Expression DAG → E-Graph

- `insert_expr_into_egraph()`: Recursively insert expression tree
- `insert_exprs_into_egraph()`: Batch insert multiple expressions
- `extract_expr_from_egraph()`: Extract best representation from e-class

**`egraph_to_ssa.py`**: E-Graph → SSA Instructions

- `extract_optimized_exprs()`: Get optimized expressions from e-graph
- `exprs_to_ssa_instructions()`: Convert expressions back to SSA
- `linearize_expression()`: Handle complex expressions with temporaries

**`simple_egraph.py`**: E-Graph Data Structures

- `ENode`: Operation with child e-classes (supports binary, unary, and **n-ary phi** nodes)
- `EClass`: Equivalence class of expressions
- `EGraph`: Graph maintaining equivalences with union-find

## Usage

### Basic Usage

```python
from asm_ir import BasicBlock, Instruction
from pipeline.ssa_egraph_pipeline import optimize_ssa_block

# Create SSA block
block = BasicBlock("example")
block.instructions.append(Instruction("MOV", "x_0", ["5"]))
block.instructions.append(Instruction("ADD", "y_0", ["x_0", "0"]))  # x + 0
block.instructions.append(Instruction("MUL", "z_0", ["y_0", "1"]))  # y * 1

# Optimize
optimized = optimize_ssa_block(block)

# Result: x=5, y=5, z=5 (all simplified to constants)
```

### Expression Conversion

```python
from egraph_bridge import ssa_block_to_exprs, print_expression_dag

# Convert SSA to expressions
expr_map = ssa_block_to_exprs(block)

# Print expression DAG
print_expression_dag(expr_map)
# Output:
#   x_0 = Const(5)
#   y_0 = add(Const(5), Const(0))
#   z_0 = mul(add(Const(5), Const(0)), Const(1))
```

### E-Graph Insertion

```python
from egraph_bridge import insert_exprs_into_egraph, EGraph

# Create e-graph
egraph = EGraph()

# Insert expressions
eclass_map = insert_exprs_into_egraph(expr_map, egraph)

# E-graph now contains equivalence classes for all expressions
print(f"Created {len(egraph.eclasses)} e-classes")
```

### Optimization Pipeline

```python
from pipeline.ssa_egraph_pipeline import optimize_ssa_block

# Complete pipeline with all stages
optimized = optimize_ssa_block(
    block,
    max_iterations=10,  # Equality saturation iterations
    verbose=True        # Print detailed progress
)
```

## Optimizations Performed

### 1. Algebraic Identities

**Addition Identity:**

```
x + 0 → x
0 + x → x
```

**Multiplication Identity:**

```
x * 1 → x
1 * x → x
x * 0 → 0
0 * x → 0
```

**Subtraction:**

```
x - x → 0
```

**Bitwise:**

```
x & x → x
x | x → x
x ^ x → 0
```

### 2. Constant Folding

```
MOV a, 10
MOV b, 5
ADD c, a, b    # 10 + 5

→

MOV a, 10
MOV b, 5
MOV c, 15      # Folded!
```

### 3. Common Subexpression Elimination

```
ADD x, a, b
ADD y, a, b    # Same expression

→ E-graph recognizes equivalence
```

### 4. Strength Reduction (Future)

```
MUL x, y, 2 → SHL x, y, 1    # Cheaper operation
```

### 5. PHI Node Simplification ⭐ NEW

**Identical Inputs:**

```
PHI x, [a, a, a] → a    # All inputs same
```

**Constant Propagation Through PHI:**

```
# Control flow:
if (...) x = 5
else     x = 5
# After merge:
PHI x, [5, 5] → 5       # Simplified to constant
```

**Nested PHI Nodes:**

```
PHI x, [y, y]        → y
PHI z, [x, w]        → PHI z, [y, w]    # Propagate simplification
```

**Example: Loop Invariant PHI:**

```python
# Original:
MOV x_0, 10
MOV x_1, 10
PHI x_2, [x_0, x_1]    # Both branches assign 10
ADD y_0, x_2, 5

# Optimized:
MOV x_0, 10
MOV x_1, 10
MOV x_2, 10            # PHI simplified
MOV y_0, 15            # Constant folded
```

### 6. Memory Load Optimization ⭐ NEW

**Load as Pure Expression:**

```
LOAD x, [addr]  →  load(address)    # Treat as expression
```

**Common Subexpression Elimination:**

```
LOAD x, [ptr]
LOAD y, [ptr]    # Same address
# E-graph recognizes as identical: load(ptr) = load(ptr)
```

**PHI with Identical Loads:**

```
# Control flow:
if (...) x = load(addr)
else     x = load(addr)
# After merge:
PHI x, [load(addr), load(addr)] → load(addr)
```

**Address Computation:**

```
[base]          → load(Var(base))
[base+8]        → load(add(Var(base), Const(8)))
[base-16]       → load(sub(Var(base), Const(16)))
```

**Example: Array Access:**

```python
# Original:
MOV base, 0x1000
LOAD x0, [base+0]     # arr[0]
LOAD x1, [base+8]     # arr[1]
LOAD x2, [base+16]    # arr[2]

# Expressions:
x0 = load(add(base, 0))
x1 = load(add(base, 8))
x2 = load(add(base, 16))

# Each distinct address = distinct load
```

## Example: Complete Optimization

**Original SSA:**

```
MOV x_0, 1
ADD y_0, x_0, 0    # x + 0
MUL z_0, y_0, 1    # y * 1
SUB w_0, z_0, z_0  # z - z
MUL a_0, w_0, 5    # 0 * 5
```

**Expression DAG:**

```
x_0 = Const(1)
y_0 = add(Const(1), Const(0))
z_0 = mul(add(Const(1), Const(0)), Const(1))
w_0 = sub(mul(...), mul(...))
a_0 = mul(sub(...), Const(5))
```

**After Simplification:**

```
x_0 = Const(1)
y_0 = Const(1)    # 1 + 0 → 1
z_0 = Const(1)    # 1 * 1 → 1
w_0 = Const(0)    # 1 - 1 → 0
a_0 = Const(0)    # 0 * 5 → 0
```

**Optimized SSA:**

```
MOV x_0, 1
MOV y_0, 1
MOV z_0, 1
MOV w_0, 0
MOV a_0, 0
```

**Result:** All unnecessary operations eliminated!

## Example: PHI Node Optimization ⭐ NEW

**Original SSA (Control Flow Merge):**

```
# if (condition):
#     x = 42
# else:
#     x = 42
# y = x * 2

MOV x_0, 42        # then branch
MOV x_1, 42        # else branch
PHI x_2, x_0, x_1  # merge point
MUL y_0, x_2, 2    # use merged value
```

**Expression DAG:**

```
x_0 = Const(42)
x_1 = Const(42)
x_2 = phi(Const(42), Const(42))
y_0 = mul(phi(Const(42), Const(42)), Const(2))
```

**After Simplification:**

```
x_0 = Const(42)
x_1 = Const(42)
x_2 = Const(42)    # PHI(42, 42) → 42
y_0 = Const(84)    # 42 * 2 → 84 (constant folding)
```

**Optimized SSA:**

```
MOV x_0, 42
MOV x_1, 42
MOV x_2, 42
MOV y_0, 84
```

**Complex Example: Nested Control Flow**

```
# Nested if:
#   if (outer):
#       if (inner):
#           x = 1
#       else:
#           x = 1
#       # x = 1 here
#   else:
#       x = 2
#   y = x * 10

MOV x_0, 1                  # inner then
MOV x_1, 1                  # inner else
PHI x_2, x_0, x_1          # inner merge → simplifies to 1
MOV x_3, 2                  # outer else
PHI x_4, x_2, x_3          # outer merge → PHI(1, 2)
MUL y_0, x_4, 10

# After optimization:
MOV x_0, 1
MOV x_1, 1
MOV x_2, 1                  # Inner PHI(1, 1) simplified
MOV x_3, 2
PHI x_4, 1, 2              # Outer PHI preserved (different values)
PHI _t0, 1, 2
MUL y_0, _t0, 10
```

**Result:** Inner PHI simplified, outer PHI correctly preserved!

## Integration with Analysis Framework

The e-graph bridge works seamlessly with SSA analysis:

```python
from analysis import convert_cfg_to_ssa
from pipeline.ssa_egraph_pipeline import optimize_cfg

# Convert CFG to SSA
cfg = build_my_cfg()
convert_cfg_to_ssa(cfg)

# Optimize with e-graph
optimized_cfg = optimize_cfg(
    cfg,
    convert_to_ssa=False,  # Already in SSA
    max_iterations=10,
    verbose=True
)
```

## Performance

**Optimization Time Complexity:**

- SSA → Expression: O(n) where n = instructions
- E-graph insertion: O(n) with hash-consing
- Equality saturation: O(iterations × rules × e-classes)
- Extraction: O(e-classes × nodes)
- Expression → SSA: O(n)

**Space Complexity:**

- Expression DAG: O(n)
- E-graph: O(n) to O(n²) depending on equivalences discovered
- Optimized SSA: O(n)

## Testing

Run comprehensive tests:

```bash
# Core e-graph bridge tests
python examples/test_egraph_bridge.py

# PHI node support tests ⭐
python examples/test_phi_nodes.py

# Memory load support tests ⭐ NEW
python examples/test_memory_loads.py
```

Run demonstrations:

```bash
# Basic pipeline demo
python pipeline/ssa_egraph_pipeline.py

# PHI optimization demo ⭐
python examples/demo_phi_optimization.py

# Memory load optimization demo ⭐ NEW
python examples/demo_memory_loads.py
```

Tests cover:

- ✅ SSA to expression conversion
- ✅ Expression to e-graph insertion
- ✅ Algebraic simplification
- ✅ Constant folding
- ✅ Common subexpression detection
- ✅ Complete pipeline
- ✅ **PHI node conversion and simplification** ⭐
- ✅ **PHI constant propagation** ⭐
- ✅ **Nested PHI nodes** ⭐
- ✅ **Memory load expressions** ⭐ NEW
- ✅ **Load address computation ([base+offset])** ⭐ NEW
- ✅ **PHI with identical loads simplification** ⭐ NEW
- ✅ **Load deduplication via hash-consing** ⭐ NEW

## API Reference

### Expression Nodes

```python
class ExprNode:
    """Expression tree node."""
    op: str                    # Operation or "const"/"var"
    children: List[ExprNode]   # Child expressions
    value: Optional[Any]       # For constants/variables

    def is_constant() -> bool
    def is_variable() -> bool
    def is_operation() -> bool
```

### Functions

```python
# SSA → Expression
ssa_block_to_exprs(block: BasicBlock) -> Dict[str, ExprNode]
simplify_expression(expr: ExprNode) -> ExprNode
parse_operand(operand: str) -> ExprNode

# Expression → E-Graph
insert_expr_into_egraph(expr: ExprNode, egraph: EGraph) -> int
insert_exprs_into_egraph(expr_map: Dict, egraph: EGraph) -> Dict[str, int]
extract_expr_from_egraph(eclass_id: int, egraph: EGraph) -> ExprNode

# E-Graph → SSA
extract_optimized_exprs(eclass_map: Dict, egraph: EGraph) -> Dict[str, ExprNode]
exprs_to_ssa_instructions(expr_map: Dict) -> List[Instruction]

# Pipeline
optimize_ssa_block(block: BasicBlock, max_iterations: int = 10,
                   verbose: bool = True) -> BasicBlock
optimize_cfg(cfg: CFG, convert_to_ssa: bool = True,
            max_iterations: int = 10, verbose: bool = True) -> CFG
```

## Limitations & Future Work

**Current Limitations:**

- Simple pattern matching (not full e-matching)
- Limited rewrite rules (mostly algebraic identities)
- No loop-aware optimizations
- Basic cost model for extraction

**Future Enhancements:**

- [ ] Full e-matching with pattern variables
- [ ] More rewrite rules (distributivity, factorization, etc.)
- [ ] Conditional constant propagation
- [ ] Strength reduction (mul → shl, div → shr)
- [ ] Loop invariant code motion integration
- [ ] Better cost models (instruction latency, register pressure)
- [ ] Parallel equality saturation
- [ ] Learned rewrite rules from execution traces

## References

- **Equality Saturation**: Tate et al. "Equality Saturation: A New Approach to Optimization" (POPL 2009)
- **E-Graphs**: Willsey et al. "egg: Fast and Extensible Equality Saturation" (POPL 2021)
- **SSA Form**: Cytron et al. "Efficiently Computing SSA Form" (TOPLAS 1991)

## Examples

See [examples/test_egraph_bridge.py](../examples/test_egraph_bridge.py) for comprehensive examples and [pipeline/ssa_egraph_pipeline.py](../pipeline/ssa_egraph_pipeline.py) for the complete pipeline implementation.
