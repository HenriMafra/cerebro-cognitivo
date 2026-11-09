"""Pacote Core do Cérebro Cognitivo Fractal Multi-Agente (v2.0)."""

from .budget import (
    BudgetExceededError,
    GroundingLevel,
    HardBudget,
    MODEL_PRICING_TABLE,
    ModelPricing,
    VerificationProfile,
)
from .cortex import (
    ConvergenceSynthesisNeuron,
    CortexExecutionResult,
    DAGTaskNode,
    ExecutionDAG,
    FractalCognitiveCortex,
    SensoryInputNeuron,
)
from .crypto_signing import EventSigner, ExternalAnchor, HAS_ED25519
from .event_store import EpistemicEventStore
from .formal_z3 import (
    ALLOWED_STDLIB_MODULES,
    ASTPolicyViolation,
    check_ast_allowlist,
    detect_trivial_tests,
    run_smtlib_formal_check,
)
from .llm_bridge import CognitiveSynthesisBridge, DeterministicSynthesisEngine
from .neuron import CognitiveNeuron, InMemoryEventStore
from .rag_memory import CoALAMemoryStore, KnowledgeChunk, normalize_for_literal_match
from .schemas import (
    Claim,
    EpistemicEvent,
    HypothesisPayload,
    MachineFeedback,
    NeuronCertificate,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
    VerifierReport,
    compute_sha256,
    new_id,
    utc_now_iso,
)
from .verifiers import (
    AdversarialRedTeamVerifier,
    DeterministicMachineVerifier,
    LogicalVerifier,
)

__all__ = [
    # Schemas & Cryptography
    "Claim",
    "EpistemicEvent",
    "HypothesisPayload",
    "MachineFeedback",
    "NeuronCertificate",
    "ProvenancePointer",
    "ProvenanceType",
    "SynapticSignal",
    "VerdictStatus",
    "VerifierReport",
    "compute_sha256",
    "new_id",
    "utc_now_iso",
    # Crypto Signing & External Anchors
    "EventSigner",
    "ExternalAnchor",
    "HAS_ED25519",
    # Budget & Grounding Levels
    "HardBudget",
    "BudgetExceededError",
    "VerificationProfile",
    "GroundingLevel",
    "ModelPricing",
    "MODEL_PRICING_TABLE",
    # AST Allowlist, Trivial Tests & Formal Z3
    "ALLOWED_STDLIB_MODULES",
    "ASTPolicyViolation",
    "check_ast_allowlist",
    "detect_trivial_tests",
    "run_smtlib_formal_check",
    # CoALA Memory & Literal Quote RAG
    "CoALAMemoryStore",
    "KnowledgeChunk",
    "normalize_for_literal_match",
    # Event Store
    "EpistemicEventStore",
    "InMemoryEventStore",
    # Verifiers
    "LogicalVerifier",
    "DeterministicMachineVerifier",
    "AdversarialRedTeamVerifier",
    # LLM Bridge & Synthesis
    "CognitiveSynthesisBridge",
    "DeterministicSynthesisEngine",
    # Neuron
    "CognitiveNeuron",
    # Cortex & DAG
    "DAGTaskNode",
    "ExecutionDAG",
    "SensoryInputNeuron",
    "ConvergenceSynthesisNeuron",
    "FractalCognitiveCortex",
    "CortexExecutionResult",
]
