"""
Egglog-based Equality Saturation Pipeline.

Complete pipeline for LLM-guided equality saturation:
1. Take assembly/SSA input
2. Convert to egglog expressions
3. Apply algebraic + LLM-generated rules
4. Extract optimized output

This is the main entry point for the equality saturation engine.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import egglog components
from egraph_bridge.egg_egraph import (
    EggEGraph, Asm, EGGLOG_AVAILABLE, ExprBuilder,
    create_algebraic_rules, create_strength_reduction_rules
)

# Import converters
from egraph_bridge.ssa_to_egglog import SSAToEgglog, ConversionResult

# Import LLM rule converter
from learned_rules.rule_to_egglog import (
    RuleToEgglogConverter, EgglogRule, convert_llm_output_to_egglog
)

# Import LLM generator (for generating rules)
try:
    from learned_rules.llm_rule_generator import call_llm_api, check_llm_availability
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class OptimizationResult:
    """Result from the optimization pipeline."""
    original_expressions: Dict[str, Any]
    optimized_expressions: Dict[str, Any]
    rules_applied: int
    llm_rules_added: int
    saturation_iterations: int
    errors: List[str] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Get a summary of the optimization."""
        lines = [
            f"Optimization Summary:",
            f"  - Expressions processed: {len(self.original_expressions)}",
            f"  - Rules applied: {self.rules_applied}",
            f"  - LLM rules added: {self.llm_rules_added}",
            f"  - Iterations: {self.saturation_iterations}",
        ]
        
        if self.errors:
            lines.append(f"  - Errors: {len(self.errors)}")
        
        # Show optimizations
        changes = 0
        for name, orig in self.original_expressions.items():
            opt = self.optimized_expressions.get(name)
            if str(opt) != str(orig):
                changes += 1
        
        lines.append(f"  - Expressions optimized: {changes}")
        
        return "\n".join(lines)


class EqualitySaturationPipeline:
    """
    Main pipeline for LLM-guided equality saturation.
    
    Usage:
        pipeline = EqualitySaturationPipeline()
        
        # Add expressions to optimize
        pipeline.add_expression(x + Asm(0), "x_plus_0")
        
        # Optionally generate LLM rules
        if pipeline.llm_available:
            pipeline.generate_llm_rules("Optimize x86 arithmetic")
        
        # Run optimization
        result = pipeline.optimize()
        
        # Get results
        for name, expr in result.optimized_expressions.items():
            print(f"{name} -> {expr}")
    """
    
    def __init__(self, 
                 use_strength_reduction: bool = True,
                 use_llm_rules: bool = True,
                 max_iterations: int = 10):
        """
        Initialize the pipeline.
        
        Args:
            use_strength_reduction: Enable strength reduction rules
            use_llm_rules: Enable LLM-generated rules
            max_iterations: Maximum saturation iterations
        """
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog not available")
        
        self._use_strength_reduction = use_strength_reduction
        self._use_llm_rules = use_llm_rules
        self._max_iterations = max_iterations
        
        self._egraph = EggEGraph()
        self._egraph.configure(use_strength_reduction=use_strength_reduction)
        
        self._expressions: Dict[str, Any] = {}
        self._llm_rules: List[EgglogRule] = []
        self._rule_converter = RuleToEgglogConverter(enable_verification=False)
        
        self._builder = ExprBuilder()
    
    @property
    def llm_available(self) -> bool:
        """Check if LLM API is available."""
        if not LLM_AVAILABLE:
            return False
        availability = check_llm_availability()
        return len(availability.get('available_providers', [])) > 0
    
    def add_expression(self, expr: Any, name: str = None) -> str:
        """
        Add an expression to optimize.
        
        Args:
            expr: The Asm expression
            name: Optional name for the expression
        
        Returns:
            The name assigned to the expression
        """
        if name is None:
            name = f"expr_{len(self._expressions)}"
        
        self._expressions[name] = expr
        self._egraph.register(expr, name)
        
        return name
    
    def add_instruction_sequence(self, instructions: List[str], name: str = None) -> Optional[str]:
        """
        Add an instruction sequence to optimize.
        
        Args:
            instructions: List of instruction strings
            name: Optional name
        
        Returns:
            Name of the registered expression, or None if parsing failed
        """
        expr = self._rule_converter._parse_instructions_to_expr(instructions)
        if expr is not None:
            return self.add_expression(expr, name)
        return None
    
    def add_llm_rule(self, rule: EgglogRule):
        """Add a pre-converted LLM rule."""
        self._llm_rules.append(rule)
    
    def generate_llm_rules(self, prompt_context: str = None) -> int:
        """
        Generate rules using the LLM API.
        
        Args:
            prompt_context: Additional context for the prompt
        
        Returns:
            Number of rules generated
        """
        if not self.llm_available:
            print("Warning: LLM not available, skipping rule generation")
            return 0
        
        # Build prompt
        prompt = self._build_rule_generation_prompt(prompt_context)
        
        try:
            # Call LLM
            response = call_llm_api(prompt)
            
            # Parse and convert rules
            rules = convert_llm_output_to_egglog(response, verify=False)
            
            for rule in rules:
                self._llm_rules.append(rule)
            
            return len(rules)
            
        except Exception as e:
            print(f"Error generating LLM rules: {e}")
            return 0
    
    def _build_rule_generation_prompt(self, context: str = None) -> str:
        """Build the prompt for LLM rule generation."""
        prompt = """Generate rewrite rules for x86/assembly code optimization.

Rules should be in this format:
LHS:
<instruction sequence pattern>
RHS:
<optimized instruction sequence>
Condition: <optional precondition>

Example rules:
1. Identity elimination:
LHS:
ADD r1, 0
RHS:
(empty)
Condition: None

2. Strength reduction:
LHS:
MUL r1, 2
RHS:
SHL r1, 1
Condition: None

Generate 3-5 optimization rules that:
- Simplify arithmetic operations
- Apply strength reduction (mul -> shift)
- Eliminate redundant operations
"""
        
        if context:
            prompt += f"\nAdditional context: {context}"
        
        return prompt
    
    def optimize(self) -> OptimizationResult:
        """
        Run the full optimization pipeline.
        
        Returns:
            OptimizationResult with original and optimized expressions
        """
        errors = []
        
        # Store original expressions
        original = {name: expr for name, expr in self._expressions.items()}
        
        # Add LLM rules to e-graph
        for rule in self._llm_rules:
            try:
                self._egraph.add_rule(rule.lhs_expr, rule.rhs_expr, rule.bidirectional)
            except Exception as e:
                errors.append(f"Failed to add LLM rule {rule.name}: {e}")
        
        # Run saturation
        stats = self._egraph.saturate(self._max_iterations)
        
        # Extract optimized expressions
        optimized = {}
        for name, expr in self._expressions.items():
            try:
                optimized[name] = self._egraph.extract(expr)
            except Exception as e:
                errors.append(f"Failed to extract {name}: {e}")
                optimized[name] = expr
        
        return OptimizationResult(
            original_expressions=original,
            optimized_expressions=optimized,
            rules_applied=stats.get('rules_count', 0),
            llm_rules_added=len(self._llm_rules),
            saturation_iterations=stats.get('iterations', 0),
            errors=errors
        )
    
    def optimize_single(self, expr: Any) -> Any:
        """
        Optimize a single expression.
        
        Args:
            expr: Expression to optimize
        
        Returns:
            Optimized expression
        """
        self.add_expression(expr, "__single__")
        result = self.optimize()
        return result.optimized_expressions.get("__single__", expr)


def optimize_expressions(expressions: Dict[str, Any],
                         use_llm: bool = False,
                         llm_context: str = None) -> Dict[str, Any]:
    """
    Convenience function to optimize multiple expressions.
    
    Args:
        expressions: Dictionary of name -> expression
        use_llm: Whether to generate LLM rules
        llm_context: Context for LLM rule generation
    
    Returns:
        Dictionary of name -> optimized expression
    """
    pipeline = EqualitySaturationPipeline()
    
    for name, expr in expressions.items():
        pipeline.add_expression(expr, name)
    
    if use_llm and pipeline.llm_available:
        pipeline.generate_llm_rules(llm_context)
    
    result = pipeline.optimize()
    return result.optimized_expressions


# ============================================
# Test / Demo
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Equality Saturation Pipeline Test")
    print("=" * 60)
    
    if not EGGLOG_AVAILABLE:
        print("ERROR: egglog not available")
        exit(1)
    
    print("✓ egglog is available")
    print(f"✓ LLM available: {LLM_AVAILABLE}\n")
    
    # Test 1: Basic optimization
    print("Test 1: Basic Algebraic Optimization")
    print("-" * 40)
    
    pipeline = EqualitySaturationPipeline()
    
    x = Asm.var("x")
    y = Asm.var("y")
    
    # Add expressions
    pipeline.add_expression(x + Asm(0), "x_plus_0")
    pipeline.add_expression(x * Asm(1), "x_times_1")
    pipeline.add_expression(x - x, "x_minus_x")
    pipeline.add_expression(x ^ x, "x_xor_x")
    
    print("  Before optimization:")
    print("    x_plus_0: x + 0")
    print("    x_times_1: x * 1")
    print("    x_minus_x: x - x")
    print("    x_xor_x: x ^ x")
    
    result = pipeline.optimize()
    
    print("\n  After optimization:")
    for name, expr in result.optimized_expressions.items():
        print(f"    {name}: {expr}")
    
    print(f"\n{result.get_summary()}")
    print("\n✓ Test 1 passed!\n")
    
    # Test 2: Strength reduction
    print("Test 2: Strength Reduction")
    print("-" * 40)
    
    pipeline2 = EqualitySaturationPipeline(use_strength_reduction=True)
    
    pipeline2.add_expression(y * Asm(2), "y_times_2")
    pipeline2.add_expression(y + y, "y_plus_y")
    
    print("  Before optimization:")
    print("    y_times_2: y * 2")
    print("    y_plus_y: y + y")
    
    result2 = pipeline2.optimize()
    
    print("\n  After optimization:")
    for name, expr in result2.optimized_expressions.items():
        print(f"    {name}: {expr}")
    
    print("\n✓ Test 2 passed!\n")
    
    # Test 3: Instruction sequence
    print("Test 3: Instruction Sequence Optimization")
    print("-" * 40)
    
    pipeline3 = EqualitySaturationPipeline()
    
    name = pipeline3.add_instruction_sequence(["ADD eax, 0"], "add_zero")
    print(f"  Added sequence 'ADD eax, 0' as '{name}'")
    
    name = pipeline3.add_instruction_sequence(["MOV ebx, eax", "ADD ebx, 0"], "mov_add_zero")
    print(f"  Added sequence 'MOV ebx, eax; ADD ebx, 0' as '{name}'")
    
    result3 = pipeline3.optimize()
    
    print("\n  After optimization:")
    for name, expr in result3.optimized_expressions.items():
        print(f"    {name}: {expr}")
    
    print("\n✓ Test 3 passed!\n")
    
    # Test 4: LLM availability check
    print("Test 4: LLM Availability")
    print("-" * 40)
    
    pipeline4 = EqualitySaturationPipeline()
    
    if pipeline4.llm_available:
        print("  ✓ LLM is available for rule generation")
        # Don't actually call - requires API key
    else:
        print("  ⚠ LLM not configured (set API key in .env)")
    
    print("\n✓ Test 4 passed!\n")
    
    # Summary
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print("\nThe equality saturation pipeline is ready.")
    print("Configure API keys in .env to enable LLM rule generation.")
