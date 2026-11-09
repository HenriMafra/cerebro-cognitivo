"""Pacote Core do Cérebro Cognitivo Fractal Multi-Agente."""

from .cortex import (
    ConvergenceSynthesisNeuron,
    CortexExecutionResult,
    DAGTaskNode,
    ExecutionDAG,
    FractalCognitiveCortex,
    SensoryInputNeuron,
)
from .event_store import EpistemicEventStore
from .llm_bridge import CognitiveSynthesisBridge, DeterministicSynthesisEngine
from .neuron import CognitiveNeuron, InMemoryEventStore
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
