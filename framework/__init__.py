"""AEGIS modular framework (roadmap Phase 9): typed, interchangeable detection / open-set / adaptation /
explanation / decision modules over the existing components. See ``framework/interfaces.py``."""
from framework.interfaces import (  # noqa: F401
    AdaptationReport, Adapter, Decision, DecisionPolicy, DetectionOutput, Detector, Explainer, OpenSetModule,
    OpenSetOutput,
)
from framework.pipeline import AegisPipeline, PipelineResult  # noqa: F401
from framework.registry import UnknownModuleError, registry  # noqa: F401
