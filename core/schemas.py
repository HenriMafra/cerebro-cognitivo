"""
Contratos de Dados Estritamente Tipados e Primitivas Criptográficas de Auditoria.
Módulo canônico do Cérebro Cognitivo Fractal Multi-Agente.
"""

from __future__ import annotations
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional


def compute_sha256(data: Any) -> str:
    """Calcula o hash SHA-256 canônico e determinístico de qualquer estrutura serializável."""
    if isinstance(data, (dict, list, tuple, str, int, float, bool)) or data is None:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    elif dataclasses.is_dataclass(data):
        raw = json.dumps(dataclasses.asdict(data), sort_keys=True, ensure_ascii=False, default=str)
    else:
        raw = str(data)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def utc_now_iso() -> str:
    """Retorna o timestamp UTC atual em formato ISO-8601 com precisão de microssegundos."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Gera um identificador único prefixado."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class VerdictStatus(str, Enum):
    """Status possíveis de veredito das camadas de verificação e emissão."""
    APPROVED = "APPROVED"
    REJECTED_LOGIC = "REJECTED_LOGIC"
    REJECTED_GROUNDING = "REJECTED_GROUNDING"
    REJECTED_RED_TEAM = "REJECTED_RED_TEAM"
    EPISTEMIC_FAILURE = "EPISTEMIC_FAILURE"


class ProvenanceType(str, Enum):
    """Tipos aceitos de lastro epistêmico para erradicação de alucinações."""
    AXIOM_USER = "AXIOM_USER"
    DETERMINISTIC_EXEC = "DETERMINISTIC_EXEC"
    FORMAL_DEDUCTION = "FORMAL_DEDUCTION"
    EVENT_CITATION = "EVENT_CITATION"


@dataclass(frozen=True)
class ProvenancePointer:
    """Ponteiro obrigatório de proveniência empírica ou formal para qualquer afirmação."""
    source_type: ProvenanceType
    reference_id: str
    excerpt: str
    evidence_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, ProvenanceType):
            object.__setattr__(self, "source_type", ProvenanceType(self.source_type))
        if not self.reference_id or not str(self.reference_id).strip():
            raise ValueError("ProvenancePointer exige um 'reference_id' não vazio.")
        if not self.excerpt or not str(self.excerpt).strip():
            raise ValueError("ProvenancePointer exige um 'excerpt' comprobatório não vazio.")
        if not self.evidence_hash:
            computed = compute_sha256({
                "source_type": self.source_type.value,
                "reference_id": self.reference_id,
                "excerpt": self.excerpt
            })
            object.__setattr__(self, "evidence_hash", computed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "reference_id": self.reference_id,
            "excerpt": self.excerpt,
            "evidence_hash": self.evidence_hash,
        }


@dataclass
class Claim:
    """Afirmação atômica produzida pelo Núcleo Pensador, sujeita a auditoria de lastro."""
    statement: str
    provenance: Optional[ProvenancePointer] = None

    def has_valid_provenance(self) -> bool:
        """Verifica se a afirmação possui ponteiro de proveniência íntegro."""
        if self.provenance is None:
            return False
        return (
            isinstance(self.provenance, ProvenancePointer)
            and bool(self.provenance.reference_id.strip())
            and bool(self.provenance.evidence_hash.startswith("sha256:"))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


@dataclass
class MachineFeedback:
    """Resultado bruto determinístico retornado pelo interpretador/sandbox na Camada V2/V3."""
    executed: bool
    tool_name: str
    command_or_code: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    ast_valid: bool = True
    invariants_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class VerifierReport:
    """Relatório formal emitido por um Verificador (V1 Lógico, V2 Grounding ou V3 Red Team)."""
    verifier_layer: str
    status: VerdictStatus
    score: float
    reasons: List[str] = field(default_factory=list)
    counterexamples: List[str] = field(default_factory=list)
    negative_constraints_added: List[str] = field(default_factory=list)
    machine_feedback: Optional[MachineFeedback] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, VerdictStatus):
            self.status = VerdictStatus(self.status)
        if not (0.0 <= float(self.score) <= 1.0):
            raise ValueError(f"Score do verificador deve estar entre 0.0 e 1.0 (recebido: {self.score}).")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verifier_layer": self.verifier_layer,
            "status": self.status.value,
            "score": self.score,
            "reasons": self.reasons,
            "counterexamples": self.counterexamples,
            "negative_constraints_added": self.negative_constraints_added,
            "machine_feedback": self.machine_feedback.to_dict() if self.machine_feedback else None,
        }


@dataclass
class HypothesisPayload:
    """Hipótese estruturada formulada pelo Núcleo Pensador de um Neurônio."""
    hypothesis_id: str = field(default_factory=lambda: new_id("hyp"))
    iteration: int = 1
    description: str = ""
    claims: List[Claim] = field(default_factory=list)
    code_artifact: Optional[str] = None
    entrypoint_function: Optional[str] = None
    expected_invariants: List[str] = field(default_factory=list)
    negative_constraints_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "iteration": self.iteration,
            "description": self.description,
            "claims": [c.to_dict() for c in self.claims],
            "code_artifact": self.code_artifact,
            "entrypoint_function": self.entrypoint_function,
            "expected_invariants": self.expected_invariants,
            "negative_constraints_applied": self.negative_constraints_applied,
            "metadata": self.metadata,
        }


@dataclass
class SynapticSignal:
    """Sinal sináptico estritamente tipado que trafega entre neurônios da rede."""
    source_neuron: str
    target_neuron: str
    task_intent: str
    axioms: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    signal_id: str = field(default_factory=lambda: new_id("sig"))
    timestamp_utc: str = field(default_factory=utc_now_iso)
    signal_hash: str = ""

    def __post_init__(self) -> None:
        if not self.source_neuron or not str(self.source_neuron).strip():
            raise ValueError("SynapticSignal exige 'source_neuron' válido.")
        if not self.target_neuron or not str(self.target_neuron).strip():
            raise ValueError("SynapticSignal exige 'target_neuron' válido.")
        if not self.task_intent or not str(self.task_intent).strip():
            raise ValueError("SynapticSignal exige 'task_intent' não vazio.")
        if not isinstance(self.input_data, dict):
            raise TypeError("SynapticSignal exige que 'input_data' seja um dicionário (dict).")
        if not self.signal_hash:
            self.signal_hash = compute_sha256({
                "signal_id": self.signal_id,
                "source_neuron": self.source_neuron,
                "target_neuron": self.target_neuron,
                "task_intent": self.task_intent,
                "axioms": self.axioms,
                "constraints": self.constraints,
                "input_data": self.input_data,
                "parent_event_id": self.parent_event_id,
            })

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class NeuronCertificate:
    """Certificado emitido pelo Axônio de um Neurônio após aprovação nas 3 camadas."""
    neuron_id: str
    signal_id: str
    status: VerdictStatus
    total_iterations: int
    final_hypothesis: Optional[HypothesisPayload]
    verifier_reports: List[VerifierReport]
    head_event_id: str
    confidence_score: float
    execution_time_ms: float
    certificate_id: str = field(default_factory=lambda: new_id("cert"))
    timestamp_utc: str = field(default_factory=utc_now_iso)
    certificate_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, VerdictStatus):
            self.status = VerdictStatus(self.status)
        if not self.certificate_hash:
            self.certificate_hash = compute_sha256({
                "certificate_id": self.certificate_id,
                "neuron_id": self.neuron_id,
                "signal_id": self.signal_id,
                "status": self.status.value,
                "total_iterations": self.total_iterations,
                "final_hypothesis": self.final_hypothesis.to_dict() if self.final_hypothesis else None,
                "head_event_id": self.head_event_id,
                "confidence_score": self.confidence_score,
            })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "neuron_id": self.neuron_id,
            "signal_id": self.signal_id,
            "status": self.status.value,
            "total_iterations": self.total_iterations,
            "final_hypothesis": self.final_hypothesis.to_dict() if self.final_hypothesis else None,
            "verifier_reports": [r.to_dict() for r in self.verifier_reports],
            "head_event_id": self.head_event_id,
            "confidence_score": self.confidence_score,
            "execution_time_ms": self.execution_time_ms,
            "timestamp_utc": self.timestamp_utc,
            "certificate_hash": self.certificate_hash,
        }


@dataclass
class EpistemicEvent:
    """
    Registro atômico e imutável do Event Sourcing Epistêmico.
    Representa um vértice na árvore de execução causal (DAG) do cérebro.
    """
    neuron_id: str
    subagent_role: str
    event_type: str
    epistemic_state: Dict[str, Any]
    delta_changes: Dict[str, Any]
    verdict: str
    confidence_score: float
    cycle_iteration: int = 1
    parent_event_id: Optional[str] = None
    branch_id: str = "main"
    previous_event_hash: str = "GENESIS_BLOCK"
    event_id: str = field(default_factory=lambda: new_id("evt"))
    timestamp_utc: str = field(default_factory=utc_now_iso)
    content_hash: str = ""

    def compute_canonical_hash(self) -> str:
        """Calcula o hash criptográfico encadeado deste evento."""
        payload = {
            "event_id": self.event_id,
            "parent_event_id": self.parent_event_id,
            "branch_id": self.branch_id,
            "timestamp_utc": self.timestamp_utc,
            "neuron_id": self.neuron_id,
            "subagent_role": self.subagent_role,
            "cycle_iteration": self.cycle_iteration,
            "event_type": self.event_type,
            "epistemic_state": self.epistemic_state,
            "delta_changes": self.delta_changes,
            "verdict": self.verdict,
            "confidence_score": round(float(self.confidence_score), 6),
            "previous_event_hash": self.previous_event_hash,
        }
        return compute_sha256(payload)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = self.compute_canonical_hash()

    def verify_integrity(self) -> bool:
        """Verifica se o conteúdo do evento não sofreu mutação ou adulteração."""
        return self.content_hash == self.compute_canonical_hash()

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
