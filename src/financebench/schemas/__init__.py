"""Pydantic v2 schemas: canonical samples, model I/O, predictions, metrics, runs, leaderboard,
and dataset manifests.

Dependency direction is strictly ``common/tooling -> sample/model_io -> prediction -> {metric,
run, leaderboard, manifest}``, so importing any single module never triggers a cycle.
"""

from __future__ import annotations

from financebench.schemas.common import (
    SCHEMA_VERSION,
    AnswerType,
    Language,
    Scale,
    SplitOrigin,
    TranslationProvenance,
)
from financebench.schemas.gates import GateResult, GatesReport
from financebench.schemas.leaderboard import LeaderboardRecord
from financebench.schemas.manifest import AdapterStatus, DatasetManifest
from financebench.schemas.metric import MetricAggregate, MetricResult
from financebench.schemas.model_io import (
    ChatMessage,
    Citation,
    FinancialAnswer,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    Role,
    TokenUsage,
)
from financebench.schemas.prediction import ParsedAnswer, Prediction
from financebench.schemas.run import CacheMode, RunConfig, RunMetadata
from financebench.schemas.sample import (
    CanonicalSample,
    ConversationTurn,
    DocumentRef,
    EvaluationSpec,
    Evidence,
    GoldAnswer,
    ImageRef,
    SampleContext,
    SourceInfo,
    Table,
)
from financebench.schemas.tooling import ToolCall, ToolResult, ToolSpec

__all__ = [
    "SCHEMA_VERSION",
    "AdapterStatus",
    "AnswerType",
    "CacheMode",
    "CanonicalSample",
    "ChatMessage",
    "Citation",
    "ConversationTurn",
    "DatasetManifest",
    "DocumentRef",
    "EvaluationSpec",
    "Evidence",
    "FinancialAnswer",
    "GateResult",
    "GatesReport",
    "GoldAnswer",
    "ImageRef",
    "Language",
    "LeaderboardRecord",
    "MetricAggregate",
    "MetricResult",
    "ModelRequest",
    "ModelResponse",
    "ModelSpec",
    "ParsedAnswer",
    "Prediction",
    "Role",
    "RunConfig",
    "RunMetadata",
    "SampleContext",
    "Scale",
    "SourceInfo",
    "SplitOrigin",
    "Table",
    "TokenUsage",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "TranslationProvenance",
]
