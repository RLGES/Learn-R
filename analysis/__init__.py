"""
Analysis package for compiler optimizations.

Contains:
- SSA transformation (ssa.py)
- Dataflow analysis (dataflow.py) - reaching definitions, liveness
- Dead code elimination (dce.py)
"""
from .ssa import (
    SSAVariable,
    SSATransformer,
    convert_cfg_to_ssa,
    get_ssa_version,
    get_base_name
)
from .dataflow import (
    Definition,
    ReachingDefinitions,
    LivenessAnalysis,
    compute_reaching_definitions,
    compute_liveness
)
from .dce import (
    DeadCodeEliminator,
    AggressiveDeadCodeEliminator,
    eliminate_dead_code,
    iterative_dce
)

__all__ = [
    # SSA
    'SSAVariable',
    'SSATransformer',
    'convert_cfg_to_ssa',
    'get_ssa_version',
    'get_base_name',
    # Dataflow
    'Definition',
    'ReachingDefinitions',
    'LivenessAnalysis',
    'compute_reaching_definitions',
    'compute_liveness',
    # DCE
    'DeadCodeEliminator',
    'AggressiveDeadCodeEliminator',
    'eliminate_dead_code',
    'iterative_dce',
]
