# Egglog Equality Saturation Engine

LLM-guided equality saturation for assembly code optimization using [egglog](https://github.com/egraphs-good/egglog).

## Quick Start

```bash
# Run all tests
python test_egglog_integration.py

# Run quick tests only
python test_egglog_integration.py --quick
```

## Components

### 1. E-Graph Engine (`egraph_bridge/egg_egraph.py`)

Egglog-based e-graph with built-in algebraic rewrite rules.

```bash
# Test e-graph directly
python egraph_bridge/egg_egraph.py
```

**Features:**
- Algebraic simplification (x+0→x, x*1→x, x-x→0, x^x→0)
- Strength reduction (x*2→x<<1)
- PHI node simplification
- Cost-based extraction

### 2. SSA to Egglog Converter (`egraph_bridge/ssa_to_egglog.py`)

Converts SSA-form instructions to egglog expressions.

```bash
# Test SSA conversion
python egraph_bridge/ssa_to_egglog.py
```

### 3. LLM Rule Generator (`learned_rules/llm_rule_generator.py`)

Generates optimization rules using LLM APIs.

**Supported Providers:**
- **OpenAI** (GPT-4, GPT-4o) - Cloud API
- **Anthropic** (Claude) - Cloud API
- **Google** (Gemini) - Cloud API
- **LM Studio** - Local inference (no API key needed)
- **Hugging Face** - Serverless inference API

```bash
# Check LLM availability
python -c "from learned_rules.llm_rule_generator import check_llm_availability; import json; print(json.dumps(check_llm_availability(), indent=2))"
```

**Setup:**
1. Copy `.env.example` to `.env`
2. Add your API key for any provider:
   - `OPENAI_API_KEY=sk-...`
   - `ANTHROPIC_API_KEY=sk-ant-...`
   - `GOOGLE_API_KEY=...`
   - `HUGGINGFACE_API_KEY=hf_...` or `HF_TOKEN=...`
   - For LM Studio: just start LM Studio and load a model

### 4. Rule Parser (`learned_rules/rule_parser.py`)

Parses LLM output into structured rules.

```bash
# Test rule parser
python learned_rules/rule_parser.py
```

### 5. Rule to Egglog Converter (`learned_rules/rule_to_egglog.py`)

Converts parsed rules to egglog format with Z3 verification.

```bash
# Test rule converter
python learned_rules/rule_to_egglog.py
```

### 6. Z3 Verification (`verification/`)

SMT-based verification of rewrite rule correctness.

```bash
# Test Z3 verification
python -c "
from learned_rules.rule_to_egglog import RuleToEgglogConverter, VERIFICATION_AVAILABLE
from learned_rules.rule_parser import ParsedRule

print(f'Z3 Verification: {VERIFICATION_AVAILABLE}')

# Test: XOR eax, eax -> MOV eax, 0
rule = ParsedRule(lhs_seq=['XOR eax, eax'], rhs_seq=['MOV eax, 0'], conditions=[])
converter = RuleToEgglogConverter(enable_verification=True)
result = converter.convert_rule(rule)
print(f'Rule verified: {result.verified if result else False}')
"
```

### 7. Full Pipeline (`egraph_bridge/egglog_pipeline.py`)

Complete equality saturation pipeline.

```bash
# Test full pipeline
python egraph_bridge/egglog_pipeline.py
```

## Test Commands

### Run All Tests
```bash
python test_egglog_integration.py
```

### Test Individual Components

```bash
# Z3 availability
python -c "from z3 import *; print('Z3 version:', get_version_string())"

# Egglog availability
python -c "from egglog import EGraph; print('Egglog OK')"

# E-Graph algebraic simplification
python egraph_bridge/egg_egraph.py

# SSA conversion
python egraph_bridge/ssa_to_egglog.py

# LLM rule generator
python learned_rules/llm_rule_generator.py

# Rule to egglog converter
python learned_rules/rule_to_egglog.py

# Full pipeline
python egraph_bridge/egglog_pipeline.py

# Comprehensive test suite
python test_egglog_integration.py
```

### Z3 Verification Examples

```bash
# Verify XOR eax, eax == MOV eax, 0
python -c "
from verification.rule_verifier import verify_rule_with_details
from learned_rules.rule_parser import ParsedRule

rule = ParsedRule(lhs_seq=['XOR eax, eax'], rhs_seq=['MOV eax, 0'], conditions=[])
result = verify_rule_with_details(rule)
print(f'Verified: {result[\"verified\"]}')
"

# Verify MUL eax, 2 == SHL eax, 1 (strength reduction)
python -c "
from verification.rule_verifier import verify_rule_with_details
from learned_rules.rule_parser import ParsedRule

rule = ParsedRule(lhs_seq=['MUL eax, 2'], rhs_seq=['SHL eax, 1'], conditions=[])
result = verify_rule_with_details(rule)
print(f'Verified: {result[\"verified\"]}')
"
```

### Pipeline Usage Example

```python
from egraph_bridge.egglog_pipeline import EqualitySaturationPipeline, Asm

# Create pipeline
pipeline = EqualitySaturationPipeline()

# Add expressions to optimize
x = Asm.var("x")
pipeline.add_expression(x + Asm(0), "x_plus_0")
pipeline.add_expression(x * Asm(1), "x_times_1")

# Add instruction sequence
pipeline.add_instruction_sequence(["ADD eax, 0"], "add_zero")

# Run optimization
result = pipeline.optimize()

# Print results
for name, expr in result.optimized_expressions.items():
    print(f"{name}: {expr}")
```

## File Structure

```
Learn-R/
├── .env.example              # API key template
├── config.py                 # Environment configuration
├── test_egglog_integration.py # Comprehensive test suite
├── requirements.txt          # Dependencies
│
├── egraph_bridge/
│   ├── egg_egraph.py         # Egglog e-graph implementation
│   ├── ssa_to_egglog.py      # SSA to egglog converter
│   ├── egglog_pipeline.py    # Full optimization pipeline
│   └── simple_egraph.py      # (Legacy) Simple e-graph
│
├── learned_rules/
│   ├── llm_rule_generator.py # LLM API integration
│   ├── rule_parser.py        # Parse LLM output
│   └── rule_to_egglog.py     # Convert to egglog rules
│
└── verification/
    ├── equivalence_checker.py # Z3 equivalence checking
    ├── symbolic_executor.py   # Symbolic execution
    ├── symbolic_state.py      # Symbolic state model
    └── rule_verifier.py       # Rule verification API
```

## Requirements

```bash
pip install egglog z3-solver openai anthropic google-generativeai python-dotenv requests
```

## LLM Provider Setup

### Cloud Providers

| Provider | API Key Variable | Get Key From |
|----------|-----------------|--------------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| Google | `GOOGLE_API_KEY` | https://aistudio.google.com/app/apikey |
| Hugging Face | `HF_TOKEN` | https://huggingface.co/settings/tokens |

### LM Studio (Local Models)

Run AI models locally without API keys:

1. Download [LM Studio](https://lmstudio.ai/)
2. Load any model (Mistral, Llama, Qwen, etc.)
3. Start the local server (menu: Local Server → Start)
4. Configure in `.env`:
   ```
   LLM_PROVIDER=lmstudio
   LMSTUDIO_BASE_URL=http://localhost:1234/v1
   ```

### Hugging Face (Serverless)

Use open-source models via HF Inference API:

1. Get token from https://huggingface.co/settings/tokens
2. Configure in `.env`:
   ```
   LLM_PROVIDER=huggingface
   HF_TOKEN=hf_xxxxxxxxxxxx
   HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.3
   ```

## Supported Opcodes

The symbolic executor supports:
- **Arithmetic**: ADD, SUB, MUL, IMUL
- **Bitwise**: AND, OR, XOR, NOT
- **Shift**: SHL, SHR
- **Move**: MOV
- **Compare**: CMP

## Built-in Rewrite Rules

| Pattern | Replacement |
|---------|-------------|
| `x + 0` | `x` |
| `x - 0` | `x` |
| `x * 1` | `x` |
| `x * 0` | `0` |
| `x - x` | `0` |
| `x ^ x` | `0` |
| `x & 0` | `0` |
| `x \| 0` | `x` |
| `x << 0` | `x` |
| `x >> 0` | `x` |
| `phi(x, x)` | `x` |
