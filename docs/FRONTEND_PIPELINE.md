# Frontend Compilation Pipeline

## Overview

This document describes the complete frontend compilation pipeline that transforms high-level source code into optimized assembly instructions.

## Architecture

The pipeline consists of 4 main stages:

```
Source Code → AST → Three-Address IR → Assembly → Optimized Assembly
   (Parser)    (IR Lowering)  (Code Generator)  (Hierarchical Engine)
```

## Components

### 1. AST Nodes (`frontend/ast_nodes.py`)

Defines the abstract syntax tree structure for a minimal expression language:

- **`Expr`**: Base class for expressions
- **`IntLiteral`**: Integer constants (`5`, `42`)
- **`Variable`**: Variable references (`x`, `y`)
- **`BinOp`**: Binary operations (`+`, `-`, `*`)
- **`Assign`**: Assignment statements (`x = 5`)
- **`Block`**: Sequence of statements

### 2. Parser (`frontend/parser.py`)

Recursive-descent parser with two main classes:

- **`Lexer`**: Tokenizes input into `Token` objects (INT, IDENT, PLUS, MINUS, etc.)
- **`Parser`**: Builds AST from tokens using recursive descent

**Grammar:**

```
program    → statement*
statement  → IDENT '=' expr ';'?
expr       → term (('+' | '-') term)*
term       → factor (('*' | '/') factor)*
factor     → INT | IDENT | '(' expr ')'
```

**Example:**

```python
from frontend import parse

ast = parse("x = 5\ny = x + 3")
# Returns: Block([
#   Assign('x', IntLiteral(5)),
#   Assign('y', BinOp('+', Variable('x'), IntLiteral(3)))
# ])
```

### 3. IR Lowering (`frontend/ir_lowering.py`)

Converts AST to three-address code intermediate representation:

**Transformation:**

```
c = (a + b) * 2  →  t1 = a + b
                    t2 = t1 * 2
                    c = t2
```

Each operation is broken down into:

- At most one operator per instruction
- Maximum of three operands (dst, src1, src2)
- Temporary variables (`t0`, `t1`, ...) for intermediate results

**Example:**

```python
from frontend import lower_to_ir

ir = lower_to_ir(ast)
# Returns: ["t0 = 5", "x = t0", "t1 = 3", "t2 = x + t1", "y = t2"]
```

### 4. Code Generation (`frontend/asm_codegen.py`)

Converts three-address IR to assembly instructions:

**Mapping Rules:**

```
t = a + b  →  MOV t, a
              ADD t, b

t = a      →  MOV t, a
```

Generates `Instruction` objects from `asm_ir` module with opcode, destination, and sources.

**Example:**

```python
from frontend import ir_to_assembly

asm = ir_to_assembly(ir)
# Returns: [
#   Instruction("MOV", "t0", ["5"]),
#   Instruction("MOV", "x", ["t0"]),
#   ...
# ]
```

## Full Pipeline Integration

### `pipeline/full_pipeline.py`

Demonstrates end-to-end compilation with optimization:

```python
def run_full_pipeline(source_code: str):
    # Stage 1: Parse source to AST
    ast = parse(source_code)

    # Stage 2: Lower AST to IR
    ir = lower_to_ir(ast)

    # Stage 3: Generate assembly
    asm = ir_to_assembly(ir)

    # Stage 4: Optimize using hierarchical rewrite engine
    optimized_asm = optimize(asm)

    return optimized_asm
```

### StubEGraph Implementation

To integrate with the hierarchical rewrite engine, we implement `StubEGraph` - a concrete implementation of `EGraphAPI` that directly modifies instruction sequences:

```python
class StubEGraph(EGraphAPI):
    def apply_rewrite(self, rule, match):
        # Convert rule.rhs patterns to concrete instructions
        # Substitute pattern variables with match.bindings
        # Modify block.instructions in place
        ...
```

This bypasses the full e-graph abstraction for demonstration purposes, allowing direct rewriting of instruction sequences.

## Example Execution

### Input:

```
a = 5
b = a + 3
c = b + 1
```

### Stage 1 - Parsing:

```
AST with 3 statements:
  a = 5
  b = (a + 3)
  c = (b + 1)
```

### Stage 2 - IR Lowering:

```
8 IR instructions:
  t0 = 5
  a = t0
  t1 = 3
  t2 = a + t1
  b = t2
  t3 = 1
  t4 = b + t3
  c = t4
```

### Stage 3 - Assembly Generation:

```
10 assembly instructions:
  0. MOV t0, 5
  1. MOV a, t0
  2. MOV t1, 3
  3. MOV t2, a
  4. ADD t2, t1
  5. MOV b, t2
  6. MOV t3, 1
  7. MOV t4, b
  8. ADD t4, t3
  9. MOV c, t4
```

### Stage 4 - Optimization:

```
9 assembly instructions (1 instruction eliminated):
  0. MOV a, 5         ← MOV chain eliminated (t0 → a merged)
  1. MOV t1, 3
  2. MOV t2, a
  3. ADD t2, t1
  4. MOV b, t2
  5. MOV t3, 1
  6. MOV t4, b
  7. ADD t4, t3
  8. MOV c, t4

Reduction: 1 instruction (10%)
Applied rules: mov_chain_elimination
```

## Performance Results

| Example            | Original | Optimized | Reduction |
| ------------------ | -------- | --------- | --------- |
| Simple arithmetic  | 10       | 9         | 1 (10%)   |
| MOV chain          | 5        | 4         | 1 (20%)   |
| Complex expression | 15       | 13        | 2 (13%)   |

## Usage

Run the full pipeline demonstration:

```bash
python pipeline/full_pipeline.py
```

This executes three examples showing:

1. Simple arithmetic with peephole optimization
2. MOV chain elimination
3. Complex expressions with multiple optimizations

## Integration with Existing System

The frontend pipeline integrates with:

- **`asm_ir`**: Core instruction representation
- **`hierarchical_engine`**: Multi-tier rewrite engine
- **`rewrite_rules.tier1_peephole`**: Peephole optimization rules
  - `mov_elimination_rule`
  - `mov_chain_elimination_rule`
  - `cancel_add_sub_rule`
  - `double_add_rule`

## Future Enhancements

Potential improvements:

1. **More operators**: Bitwise operations, comparisons, control flow
2. **Type system**: Add type checking and inference
3. **Variables**: Register allocation and liveness analysis
4. **Control flow**: If statements, loops, function calls
5. **More optimizations**: Constant folding, dead code elimination, common subexpression elimination
6. **Better IR**: SSA form, phi nodes for control flow merging

## Files

- `frontend/__init__.py` - Package exports
- `frontend/ast_nodes.py` - AST node definitions (90 lines)
- `frontend/parser.py` - Lexer and Parser (240 lines)
- `frontend/ir_lowering.py` - AST to IR transformer (110 lines)
- `frontend/asm_codegen.py` - IR to assembly code generator (90 lines)
- `pipeline/full_pipeline.py` - End-to-end demo (260 lines)

Total: ~790 lines of code for complete frontend pipeline.
