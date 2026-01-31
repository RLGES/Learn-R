"""
Abstract E-Graph API interface for the rewrite engine.
"""
from abc import ABC, abstractmethod
from typing import Any, Iterable
from asm_ir import Instruction
from rewrite_rules import RewriteRule


class EGraphAPI(ABC):
    """
    Abstract interface for e-graph operations.
    
    The rewrite engine uses this interface to interact with the e-graph
    without knowing its internal implementation details.
    """
    
    @abstractmethod
    def add_sequence(self, instructions: list[Instruction]) -> Any:
        """
        Add a sequence of instructions to the e-graph.
        
        Args:
            instructions: List of instructions to add
        
        Returns:
            Reference or ID for the added sequence (implementation-specific)
        """
        pass
    
    @abstractmethod
    def apply_rewrite(self, rule: RewriteRule, match: Any) -> None:
        """
        Apply a rewrite rule at a specific match location.
        
        This adds an equivalence edge in the e-graph between the LHS and RHS
        of the rule. Does not delete the original instructions.
        
        Args:
            rule: The rewrite rule to apply
            match: Match object containing bindings and location information
        """
        pass
    
    @abstractmethod
    def get_recent_eclasses(self) -> Iterable[Any]:
        """
        Get e-classes that were recently modified.
        
        This enables incremental rewriting - the engine can focus on
        e-classes that changed in the previous iteration rather than
        scanning the entire graph.
        
        Returns:
            Iterable of e-class references or IDs that were recently updated
        """
        pass
    
    @abstractmethod
    def extract_best(self) -> list[Instruction]:
        """
        Extract the best (optimal) instruction sequence from the e-graph.
        
        Uses a cost function to select the lowest-cost equivalent expression
        from all the equivalences stored in the e-graph.
        
        Returns:
            Optimized list of instructions
        """
        pass
    
    @abstractmethod
    def get_applied_rules(self) -> list[str]:
        """
        Get names of rules that were successfully applied during e-graph expansion.
        
        This enables extraction feedback - the engine can determine which rules
        contributed to the final optimized sequence.
        
        Returns:
            List of rule names that were applied
        """
        pass
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about the e-graph state.
        
        Returns:
            Dictionary with statistics (optional, not required by all implementations)
        """
        return {
            'eclasses': 0,
            'enodes': 0,
            'equivalences': 0
        }
