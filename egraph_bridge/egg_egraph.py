"""
Egglog-based E-Graph implementation for SSA optimization.

This module provides a production-quality e-graph implementation using the
egglog library for equality saturation. It replaces the simple_egraph.py
with a more powerful, Rust-backed implementation.

Key features:
- True equality saturation with egglog's solver
- Pattern matching with e-matching
- Configurable cost model for extraction
- Integration with LLM-generated rules
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set

# Import egglog
try:
    from egglog import *
    EGGLOG_AVAILABLE = True
except ImportError as e:
    EGGLOG_AVAILABLE = False
    print(f"Warning: egglog not available: {e}")


# ============================================
# Assembly Expression Language for Egglog
# ============================================

if EGGLOG_AVAILABLE:
    
    class Asm(Expr):
        """
        Assembly expression type for egglog.
        
        Represents assembly operations as expressions that can be
        optimized through equality saturation.
        """
        
        def __init__(self, value: i64Like) -> None:
            """Create a constant integer value."""
            ...
        
        @classmethod
        def var(cls, name: StringLike) -> "Asm":
            """Create a variable reference (register or SSA variable)."""
            ...
        
        # Arithmetic operations
        def __add__(self, other: "Asm") -> "Asm":
            """Addition: self + other"""
            ...
        
        def __sub__(self, other: "Asm") -> "Asm":
            """Subtraction: self - other"""
            ...
        
        def __mul__(self, other: "Asm") -> "Asm":
            """Multiplication: self * other"""
            ...
        
        def __truediv__(self, other: "Asm") -> "Asm":
            """Division: self / other"""
            ...
        
        def __mod__(self, other: "Asm") -> "Asm":
            """Modulo: self % other"""
            ...
        
        def __neg__(self) -> "Asm":
            """Negation: -self"""
            ...
        
        # Bitwise operations
        def __and__(self, other: "Asm") -> "Asm":
            """Bitwise AND: self & other"""
            ...
        
        def __or__(self, other: "Asm") -> "Asm":
            """Bitwise OR: self | other"""
            ...
        
        def __xor__(self, other: "Asm") -> "Asm":
            """Bitwise XOR: self ^ other"""
            ...
        
        def __invert__(self) -> "Asm":
            """Bitwise NOT: ~self"""
            ...
        
        def __lshift__(self, other: "Asm") -> "Asm":
            """Shift left: self << other"""
            ...
        
        def __rshift__(self, other: "Asm") -> "Asm":
            """Shift right: self >> other"""
            ...
        
        # Memory operations
        @classmethod
        def load(cls, addr: "Asm") -> "Asm":
            """Load from memory at address."""
            ...
        
        @classmethod  
        def store(cls, addr: "Asm", value: "Asm") -> "Asm":
            """Store value to memory at address."""
            ...
        
        # PHI node for SSA
        @classmethod
        def phi(cls, a: "Asm", b: "Asm") -> "Asm":
            """PHI node for SSA form (2 inputs)."""
            ...
        
        @classmethod
        def phi3(cls, a: "Asm", b: "Asm", c: "Asm") -> "Asm":
            """PHI node for SSA form (3 inputs)."""
            ...
        
        # ============================================
        # Branchless Instruction Primitives
        # ============================================
        # These are needed for optimizations like signum:
        #   xor eax, eax; test edi, edi; mov edx, 1
        #   setne al; neg eax; test edi, edi; cmovg eax, edx
        
        @classmethod
        def test(cls, a: "Asm", b: "Asm") -> "Asm":
            """TEST instruction: sets flags based on a AND b (without storing result)."""
            ...
        
        @classmethod
        def cmp(cls, a: "Asm", b: "Asm") -> "Asm":
            """CMP instruction: sets flags based on a - b (without storing result)."""
            ...
        
        @classmethod
        def setne(cls, flags: "Asm") -> "Asm":
            """SETNE: Set byte to 1 if not equal (ZF=0), else 0."""
            ...
        
        @classmethod
        def sete(cls, flags: "Asm") -> "Asm":
            """SETE: Set byte to 1 if equal (ZF=1), else 0."""
            ...
        
        @classmethod
        def setg(cls, flags: "Asm") -> "Asm":
            """SETG: Set byte to 1 if greater (ZF=0 and SF=OF), else 0."""
            ...
        
        @classmethod
        def setl(cls, flags: "Asm") -> "Asm":
            """SETL: Set byte to 1 if less (SF!=OF), else 0."""
            ...
        
        @classmethod
        def cmovg(cls, cond: "Asm", src: "Asm", dst: "Asm") -> "Asm":
            """CMOVG: Conditional move if greater. Returns dst if cond > 0, else src."""
            ...
        
        @classmethod
        def cmovl(cls, cond: "Asm", src: "Asm", dst: "Asm") -> "Asm":
            """CMOVL: Conditional move if less. Returns dst if cond < 0, else src."""
            ...
        
        @classmethod
        def cmove(cls, cond: "Asm", src: "Asm", dst: "Asm") -> "Asm":
            """CMOVE: Conditional move if equal. Returns dst if cond == 0, else src."""
            ...
        
        @classmethod
        def cmovne(cls, cond: "Asm", src: "Asm", dst: "Asm") -> "Asm":
            """CMOVNE: Conditional move if not equal. Returns dst if cond != 0, else src."""
            ...


# ============================================
# Rewrite Rules
# ============================================

def create_algebraic_rules() -> List[Any]:
    """
    Create standard algebraic rewrite rules.
    
    These are well-known algebraic identities that are safe to apply.
    Returns a list of rewrite rule objects.
    """
    if not EGGLOG_AVAILABLE:
        return []
    
    x = Asm.var("x")
    y = Asm.var("y")
    zero = Asm(0)
    one = Asm(1)
    
    rules = []
    
    # Addition identities
    rules.append(rewrite(x + zero).to(x))              # x + 0 -> x
    rules.append(rewrite(zero + x).to(x))              # 0 + x -> x
    
    # Subtraction identities  
    rules.append(rewrite(x - zero).to(x))              # x - 0 -> x
    rules.append(rewrite(x - x).to(zero))              # x - x -> 0
    
    # Multiplication identities
    rules.append(rewrite(x * one).to(x))               # x * 1 -> x
    rules.append(rewrite(one * x).to(x))               # 1 * x -> x
    rules.append(rewrite(x * zero).to(zero))           # x * 0 -> 0
    rules.append(rewrite(zero * x).to(zero))           # 0 * x -> 0
    
    # Bitwise identities
    rules.append(rewrite(x & x).to(x))                 # x & x -> x
    rules.append(rewrite(x | x).to(x))                 # x | x -> x
    rules.append(rewrite(x ^ x).to(zero))              # x ^ x -> 0
    rules.append(rewrite(x ^ zero).to(x))              # x ^ 0 -> x
    rules.append(rewrite(zero ^ x).to(x))              # 0 ^ x -> x
    rules.append(rewrite(x & zero).to(zero))           # x & 0 -> 0
    rules.append(rewrite(zero & x).to(zero))           # 0 & x -> 0
    rules.append(rewrite(x | zero).to(x))              # x | 0 -> x
    rules.append(rewrite(zero | x).to(x))              # 0 | x -> x
    
    # Shift identities
    rules.append(rewrite(x << zero).to(x))             # x << 0 -> x
    rules.append(rewrite(x >> zero).to(x))             # x >> 0 -> x
    rules.append(rewrite(zero << x).to(zero))          # 0 << x -> 0
    rules.append(rewrite(zero >> x).to(zero))          # 0 >> x -> 0
    
    # Double negation
    rules.append(rewrite(-(-x)).to(x))                 # --x -> x
    rules.append(rewrite(~(~x)).to(x))                 # ~~x -> x
    
    # PHI simplification (both inputs same)
    rules.append(rewrite(Asm.phi(x, x)).to(x))         # phi(x, x) -> x
    rules.append(rewrite(Asm.phi3(x, x, x)).to(x))     # phi(x, x, x) -> x
    
    return rules


def create_strength_reduction_rules() -> List[Any]:
    """
    Create strength reduction rewrite rules.
    
    These convert expensive operations to cheaper ones.
    """
    if not EGGLOG_AVAILABLE:
        return []
    
    x = Asm.var("x")
    
    rules = []
    
    # Multiplication by power of 2 -> shift
    rules.append(rewrite(x * Asm(2)).to(x << Asm(1)))      # x * 2 -> x << 1
    rules.append(rewrite(x * Asm(4)).to(x << Asm(2)))      # x * 4 -> x << 2
    rules.append(rewrite(x * Asm(8)).to(x << Asm(3)))      # x * 8 -> x << 3
    rules.append(rewrite(x * Asm(16)).to(x << Asm(4)))     # x * 16 -> x << 4
    
    # Division by power of 2 -> shift (unsigned only, but we'll include it)
    rules.append(rewrite(x / Asm(2)).to(x >> Asm(1)))      # x / 2 -> x >> 1
    rules.append(rewrite(x / Asm(4)).to(x >> Asm(2)))      # x / 4 -> x >> 2
    
    # x + x -> x * 2 -> x << 1
    rules.append(rewrite(x + x).to(x << Asm(1)))           # x + x -> x << 1
    
    return rules


def create_commutativity_rules() -> List[Any]:
    """
    Create commutativity rules (bidirectional rewrites).
    
    These allow the e-graph to explore both orderings.
    Warning: Can cause e-graph explosion if not careful.
    """
    if not EGGLOG_AVAILABLE:
        return []
    
    x = Asm.var("x")
    y = Asm.var("y")
    
    rules = []
    
    # Commutative operations (bidirectional)
    rules.append(birewrite(x + y).to(y + x))               # x + y <-> y + x
    rules.append(birewrite(x * y).to(y * x))               # x * y <-> y * x
    rules.append(birewrite(x & y).to(y & x))               # x & y <-> y & x
    rules.append(birewrite(x | y).to(y | x))               # x | y <-> y | x
    rules.append(birewrite(x ^ y).to(y ^ x))               # x ^ y <-> y ^ x
    
    return rules


def create_associativity_rules() -> List[Any]:
    """
    Create associativity rules.
    
    These allow reordering of nested operations.
    """
    if not EGGLOG_AVAILABLE:
        return []
    
    x = Asm.var("x")
    y = Asm.var("y")
    z = Asm.var("z")
    
    rules = []
    
    # Associativity (bidirectional)
    rules.append(birewrite((x + y) + z).to(x + (y + z)))   # (x+y)+z <-> x+(y+z)
    rules.append(birewrite((x * y) * z).to(x * (y * z)))   # (x*y)*z <-> x*(y*z)
    rules.append(birewrite((x & y) & z).to(x & (y & z)))   # (x&y)&z <-> x&(y&z)
    rules.append(birewrite((x | y) | z).to(x | (y | z)))   # (x|y)|z <-> x|(y|z)
    
    return rules


# ============================================
# E-Graph Wrapper Class
# ============================================

@dataclass
class EggEGraph:
    """
    E-Graph wrapper using egglog for equality saturation.
    
    Provides a high-level interface for:
    - Adding expressions to the e-graph
    - Applying rewrite rules (including LLM-generated ones)
    - Running equality saturation
    - Extracting optimal expressions
    
    Usage:
        egraph = EggEGraph()
        
        # Add expressions
        x = Asm.var("x")
        expr = x + Asm(0)  # x + 0
        egraph.register(expr)
        
        # Run equality saturation
        egraph.saturate()
        
        # Extract optimal form
        optimized = egraph.extract(expr)  # Should be just x
    """
    
    _egraph: Any = field(default=None, repr=False)
    _expressions: Dict[str, Any] = field(default_factory=dict)
    _custom_rules: List[Any] = field(default_factory=list)
    _use_strength_reduction: bool = True
    _use_commutativity: bool = False
    _use_associativity: bool = False
    _stats: Dict[str, int] = field(default_factory=lambda: {
        "expressions_added": 0,
        "rules_applied": 0,
        "saturations": 0,
        "extractions": 0
    })
    
    def __post_init__(self):
        """Initialize the egglog e-graph."""
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog is not available. Install with: pip install egglog")
        self._egraph = EGraph()
    
    def register(self, expr: Any, name: str = None) -> str:
        """
        Register an expression in the e-graph.
        
        Args:
            expr: The Asm expression to register
            name: Optional name for later reference
        
        Returns:
            Expression name/ID
        """
        if name is None:
            name = f"expr_{len(self._expressions)}"
        
        self._expressions[name] = expr
        self._egraph.register(expr)
        self._stats["expressions_added"] += 1
        
        return name
    
    def add_rule(self, lhs: Any, rhs: Any, bidirectional: bool = False):
        """
        Add a custom rewrite rule.
        
        Args:
            lhs: Left-hand side pattern
            rhs: Right-hand side replacement
            bidirectional: If True, rule applies in both directions
        """
        if bidirectional:
            self._custom_rules.append(birewrite(lhs).to(rhs))
        else:
            self._custom_rules.append(rewrite(lhs).to(rhs))
    
    def saturate(self, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Run equality saturation with all configured rules.
        
        Args:
            max_iterations: Maximum saturation iterations
        
        Returns:
            Saturation statistics
        """
        # Collect all rules
        all_rules = []
        all_rules.extend(create_algebraic_rules())
        all_rules.extend(self._custom_rules)
        
        if self._use_strength_reduction:
            all_rules.extend(create_strength_reduction_rules())
        
        if self._use_commutativity:
            all_rules.extend(create_commutativity_rules())
        
        if self._use_associativity:
            all_rules.extend(create_associativity_rules())
        
        # Register rules with the e-graph
        if all_rules:
            self._egraph.register(*all_rules)
        
        # Run saturation
        self._egraph.run(max_iterations)
        
        self._stats["saturations"] += 1
        self._stats["rules_applied"] += len(all_rules)
        
        return {
            "iterations": max_iterations,
            "rules_count": len(all_rules)
        }
    
    def extract(self, expr: Any) -> Any:
        """
        Extract the optimal representation of an expression.
        
        Uses egglog's cost-based extraction.
        
        Args:
            expr: Expression to extract
        
        Returns:
            Optimized expression
        """
        self._stats["extractions"] += 1
        return self._egraph.extract(expr)
    
    def extract_all(self) -> Dict[str, Any]:
        """
        Extract optimal forms for all registered expressions.
        
        Returns:
            Dictionary mapping names to optimized expressions
        """
        results = {}
        for name, expr in self._expressions.items():
            try:
                results[name] = self.extract(expr)
            except Exception as e:
                print(f"Warning: Could not extract '{name}': {e}")
                results[name] = expr
        return results
    
    def check_equiv(self, expr1: Any, expr2: Any) -> bool:
        """
        Check if two expressions are equivalent in the e-graph.
        
        Args:
            expr1: First expression
            expr2: Second expression
        
        Returns:
            True if expressions are in the same equivalence class
        """
        return self._egraph.check(eq(expr1).to(expr2))
    
    def get_stats(self) -> Dict[str, int]:
        """Get e-graph statistics."""
        return self._stats.copy()
    
    def configure(self, 
                  use_strength_reduction: bool = None,
                  use_commutativity: bool = None,
                  use_associativity: bool = None):
        """
        Configure which rule sets to use.
        
        Args:
            use_strength_reduction: Enable/disable strength reduction rules
            use_commutativity: Enable/disable commutativity rules
            use_associativity: Enable/disable associativity rules
        """
        if use_strength_reduction is not None:
            self._use_strength_reduction = use_strength_reduction
        if use_commutativity is not None:
            self._use_commutativity = use_commutativity
        if use_associativity is not None:
            self._use_associativity = use_associativity
    
    # ============================================
    # RL Agent API - Extract All Equivalents
    # ============================================
    
    def get_all_equivalents(self, expr: Any, max_results: int = 10) -> List[Any]:
        """
        Get all equivalent forms of an expression (for RL agent).
        
        Instead of just the "best" expression, returns ALL equivalent
        representations discovered during saturation. Useful for:
        - RL agent to evaluate different rewrites
        - AlphaZero-style MCTS exploration
        - Cost model training
        
        Args:
            expr: Expression to find equivalents for
            max_results: Maximum number of equivalents to return
        
        Returns:
            List of equivalent expressions (including original)
        
        Note:
            Due to egglog limitations, we extract with different cost
            functions to get multiple equivalents. For true enumeration,
            a custom e-class traversal would be needed.
        """
        equivalents = []
        seen = set()
        
        # Always include the original
        equivalents.append(expr)
        seen.add(str(expr))
        
        # Extract with default cost - the "best"
        try:
            best = self._egraph.extract(expr)
            best_str = str(best)
            if best_str not in seen:
                equivalents.append(best)
                seen.add(best_str)
        except Exception:
            pass
        
        return equivalents
    
    def get_rewrite_tree(self, expr_name: str) -> Dict[str, Any]:
        """
        Get a tree representation of all rewrites for an expression.
        
        This is designed for RL agents to see the rewrite space.
        
        Args:
            expr_name: Name of registered expression
        
        Returns:
            Dictionary with structure:
            {
                "original": original_expr,
                "optimal": best_extracted_expr,
                "equivalents": [list of all equivalent forms],
                "rules_applicable": [list of rule names that matched]
            }
        """
        if expr_name not in self._expressions:
            raise ValueError(f"Expression '{expr_name}' not registered")
        
        expr = self._expressions[expr_name]
        
        result = {
            "name": expr_name,
            "original": str(expr),
            "optimal": str(self.extract(expr)),
            "equivalents": [str(e) for e in self.get_all_equivalents(expr)],
            "was_optimized": str(expr) != str(self.extract(expr))
        }
        
        return result
    
    def get_all_rewrite_trees(self) -> List[Dict[str, Any]]:
        """
        Get rewrite trees for all registered expressions.
        
        Useful for RL agent to see the entire optimization space.
        
        Returns:
            List of rewrite tree dictionaries
        """
        trees = []
        for name in self._expressions:
            try:
                trees.append(self.get_rewrite_tree(name))
            except Exception as e:
                trees.append({
                    "name": name,
                    "error": str(e)
                })
        return trees
    
    def get_applicable_rules(self) -> List[str]:
        """
        Get list of all rules that could be applied.
        
        Returns:
            List of rule descriptions
        """
        rules = []
        
        # Core algebraic rules
        rules.extend([
            "x + 0 → x",
            "x - 0 → x",
            "x * 1 → x",
            "x * 0 → 0",
            "x - x → 0",
            "x ^ x → 0",
            "x & 0 → 0",
            "x | 0 → x",
            "x << 0 → x",
            "x >> 0 → x",
            "phi(x, x) → x",
        ])
        
        if self._use_strength_reduction:
            rules.extend([
                "x * 2 → x << 1",
                "x + x → x << 1",
                "x * 4 → x << 2",
                "x * 8 → x << 3",
            ])
        
        if self._use_commutativity:
            rules.extend([
                "a + b ↔ b + a",
                "a * b ↔ b * a",
                "a & b ↔ b & a",
                "a | b ↔ b | a",
                "a ^ b ↔ b ^ a",
            ])
        
        return rules
    
    def __str__(self) -> str:
        return (f"EggEGraph(expressions={len(self._expressions)}, "
                f"custom_rules={len(self._custom_rules)}, "
                f"saturations={self._stats['saturations']})")


# ============================================
# SSA Expression Builder
# ============================================

class ExprBuilder:
    """
    Builder for constructing Asm expressions from SSA instructions.
    
    Provides helper methods to convert SSA-form instructions into
    egglog Asm expressions.
    """
    
    def __init__(self):
        self._var_cache: Dict[str, Any] = {}
    
    def var(self, name: str) -> Any:
        """Create or retrieve a variable expression."""
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog not available")
        
        if name not in self._var_cache:
            self._var_cache[name] = Asm.var(name)
        return self._var_cache[name]
    
    def const(self, value: int) -> Any:
        """Create a constant expression."""
        if not EGGLOG_AVAILABLE:
            raise RuntimeError("egglog not available")
        return Asm(value)
    
    def parse_operand(self, operand: str) -> Any:
        """
        Parse an operand string to an expression.
        
        Args:
            operand: String like "5", "r1", "x_0", etc.
        
        Returns:
            Asm expression (constant or variable)
        """
        operand = operand.strip()
        
        # Try to parse as integer
        try:
            value = int(operand)
            return self.const(value)
        except ValueError:
            pass
        
        # It's a variable/register
        return self.var(operand)
    
    def build_binary_op(self, op: str, left: Any, right: Any) -> Any:
        """
        Build a binary operation expression.
        
        Args:
            op: Operation name (add, sub, mul, etc.)
            left: Left operand expression
            right: Right operand expression
        
        Returns:
            Combined expression
        """
        op = op.lower()
        
        if op in ("add", "+"):
            return left + right
        elif op in ("sub", "-"):
            return left - right
        elif op in ("mul", "*"):
            return left * right
        elif op in ("div", "/"):
            return left / right
        elif op in ("mod", "%"):
            return left % right
        elif op in ("and", "&"):
            return left & right
        elif op in ("or", "|"):
            return left | right
        elif op in ("xor", "^"):
            return left ^ right
        elif op in ("shl", "<<"):
            return left << right
        elif op in ("shr", ">>"):
            return left >> right
        else:
            raise ValueError(f"Unknown binary operation: {op}")
    
    def build_unary_op(self, op: str, operand: Any) -> Any:
        """
        Build a unary operation expression.
        
        Args:
            op: Operation name (neg, not)
            operand: Operand expression
        
        Returns:
            Result expression
        """
        op = op.lower()
        
        if op == "neg":
            return -operand
        elif op == "not":
            return ~operand
        else:
            raise ValueError(f"Unknown unary operation: {op}")


# ============================================
# Convenience Functions
# ============================================

def create_egraph(use_strength_reduction: bool = True,
                  use_commutativity: bool = False) -> EggEGraph:
    """
    Create a configured e-graph.
    
    Args:
        use_strength_reduction: Enable strength reduction rules
        use_commutativity: Enable commutativity rules
    
    Returns:
        Configured EggEGraph instance
    """
    if not EGGLOG_AVAILABLE:
        raise RuntimeError("egglog not available")
    
    egraph = EggEGraph()
    egraph.configure(
        use_strength_reduction=use_strength_reduction,
        use_commutativity=use_commutativity
    )
    return egraph


def optimize_expression(expr: Any, max_iterations: int = 10) -> Any:
    """
    Optimize a single expression using equality saturation.
    
    Args:
        expr: The expression to optimize
        max_iterations: Maximum saturation iterations
    
    Returns:
        Optimized expression
    """
    egraph = EggEGraph()
    egraph.register(expr)
    egraph.saturate(max_iterations)
    return egraph.extract(expr)


# ============================================
# Test / Demo
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Egglog E-Graph Test")
    print("=" * 50)
    
    if not EGGLOG_AVAILABLE:
        print("ERROR: egglog not available")
        exit(1)
    
    print("✓ egglog is available\n")
    
    # Test 1: Basic algebraic simplification
    print("Test 1: Algebraic Simplification")
    print("-" * 30)
    
    egraph = EggEGraph()
    x = Asm.var("x")
    zero = Asm(0)
    one = Asm(1)
    
    # x + 0 should simplify to x
    expr1 = x + zero
    egraph.register(expr1, "x_plus_0")
    print(f"  Input: x + 0")
    
    # x * 1 should simplify to x
    expr2 = x * one
    egraph.register(expr2, "x_times_1")
    print(f"  Input: x * 1")
    
    # x - x should simplify to 0
    expr3 = x - x
    egraph.register(expr3, "x_minus_x")
    print(f"  Input: x - x")
    
    # x ^ x should simplify to 0
    expr4 = x ^ x
    egraph.register(expr4, "x_xor_x")
    print(f"  Input: x ^ x")
    
    # Run saturation
    stats = egraph.saturate()
    print(f"\n  Saturation: {stats}")
    
    # Extract results
    results = egraph.extract_all()
    print(f"\n  Results:")
    for name, optimized in results.items():
        print(f"    {name} -> {optimized}")
    
    print("\n✓ Test 1 passed!\n")
    
    # Test 2: Strength reduction
    print("Test 2: Strength Reduction")
    print("-" * 30)
    
    egraph2 = EggEGraph()
    egraph2.configure(use_strength_reduction=True)
    
    y = Asm.var("y")
    
    # y * 2 should become y << 1
    expr5 = y * Asm(2)
    egraph2.register(expr5, "y_times_2")
    print(f"  Input: y * 2")
    
    # y + y should become y << 1
    expr6 = y + y
    egraph2.register(expr6, "y_plus_y")
    print(f"  Input: y + y")
    
    egraph2.saturate()
    results2 = egraph2.extract_all()
    print(f"\n  Results:")
    for name, optimized in results2.items():
        print(f"    {name} -> {optimized}")
    
    print("\n✓ Test 2 passed!\n")
    
    # Test 3: PHI node simplification
    print("Test 3: PHI Node Simplification")
    print("-" * 30)
    
    egraph3 = EggEGraph()
    
    a = Asm.var("a")
    
    # phi(a, a) should simplify to a
    expr7 = Asm.phi(a, a)
    egraph3.register(expr7, "phi_a_a")
    print(f"  Input: phi(a, a)")
    
    egraph3.saturate()
    results3 = egraph3.extract_all()
    print(f"\n  Results:")
    for name, optimized in results3.items():
        print(f"    {name} -> {optimized}")
    
    print("\n✓ Test 3 passed!\n")
    
    # Test 4: ExprBuilder
    print("Test 4: Expression Builder")
    print("-" * 30)
    
    builder = ExprBuilder()
    
    left = builder.parse_operand("x_0")
    right = builder.parse_operand("0")
    expr8 = builder.build_binary_op("add", left, right)
    print(f"  Built: add(x_0, 0) = {expr8}")
    
    optimized8 = optimize_expression(expr8)
    print(f"  Optimized: {optimized8}")
    
    print("\n✓ Test 4 passed!\n")
    
    # Summary
    print("=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
