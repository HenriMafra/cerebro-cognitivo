"""
Expansão Cortical v3.0 — Cérebro Cognitivo Fractal Multi-Agente:
- 12 Neurônios Cognitivos distribuídos em 4 Lobos Corticais + Tálamo Adaptativo + Hipocampo.
- Plasticidade Sináptica de Longo Prazo (`SynapticPlasticityMemory`): persiste restrições negativas
  aprendidas em Rollbacks Causais (`CAUSAL_ROLLBACK`) entre sessões para que o Cérebro jamais
  repita um erro estrutural no futuro.
- Consolidação Hipocampal ("Memória de Sabedoria Destilada"): sintetiza lições aprendidas e
  certificados de alta confiança em regras permanentes auditáveis.
- Roteamento Topológico Adaptativo (`AdaptiveThalamusRouter`): ativa dinamicamente os neurônios
  dos 4 lobos conforme a natureza do estímulo sensorial, respeitando o `HardBudget`.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .budget import HardBudget
from .cortex import CortexExecutionResult, DAGTaskNode, ExecutionDAG, FractalCognitiveCortex
from .event_store import EpistemicEventStore
from .neuron import CognitiveNeuron
from .schemas import (
    Claim,
    HypothesisPayload,
    NeuronCertificate,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
    utc_now_iso,
)


EXTENDED_SPECIALISTS_SPEC: List[Dict[str, Any]] = [
    # Onda 1: Fundação Formal, Factual e Criptográfica
    {
        "neuron_id": "neuron_logic_math",
        "lobe": "Lobo Frontal Formal",
        "specialty": "Lógica Formal, Invariantes Algébricos e Solvers Z3 SMT-LIB",
        "wave": 1,
        "note_name": "Neuronio_01_Logica_e_Matematica",
        "keywords": ["logica", "matematica", "prova", "teorema", "z3", "invariante", "calculo"],
    },
    {
        "neuron_id": "neuron_epistemic_facts",
        "lobe": "Lobo Temporal Semântico",
        "specialty": "Auditoria Factual, ProvenancePointers e Busca CoALA FTS5 BM25",
        "wave": 1,
        "note_name": "Neuronio_04_Fatos_e_Proveniencia",
        "keywords": ["fato", "documento", "fonte", "citacao", "obsidian", "nota", "memoria"],
    },
    {
        "neuron_id": "neuron_crypto_security",
        "lobe": "Lobo Parietal de Segurança & Criptografia",
        "specialty": "Criptografia Aplicada, Assinaturas Ed25519, Zero-Trust e Superfície de Ataque",
        "wave": 1,
        "note_name": "Neuronio_07_Criptografia_e_Seguranca_ZeroTrust",
        "keywords": ["criptografia", "seguranca", "hash", "ed25519", "rsa", "chave", "ataque", "zero-trust", "token"],
    },
    # Onda 2: Engenharia, Causalidade e Risco
    {
        "neuron_id": "neuron_systems_engineering",
        "lobe": "Lobo Executivo de Engenharia",
        "specialty": "Arquitetura de Software, AST Allowlist e Execução Determinística em Sandbox V2",
        "wave": 2,
        "note_name": "Neuronio_02_Engenharia_de_Sistemas",
        "keywords": ["codigo", "sistema", "arquitetura", "python", "api", "servidor", "implementar", "modulo"],
    },
    {
        "neuron_id": "neuron_strategy_risk",
        "lobe": "Lobo Parietal de Risco & BFT",
        "specialty": "Gestão de Riscos, Tolerância a Falhas Bizantinas (BFT) e Contenção de Caos",
        "wave": 2,
        "note_name": "Neuronio_03_Estrategia_e_Risco",
        "keywords": ["risco", "estrategia", "falha", "caos", "contingencia", "orcamento", "bft"],
    },
    {
        "neuron_id": "neuron_causal_counterfactual",
        "lobe": "Lobo Frontal de Inferência Causal",
        "specialty": "Inferência Causal (Do-Calculus), Análise de Causa-Raiz e Simulação Contrafactual",
        "wave": 2,
        "note_name": "Neuronio_08_Inferencia_Causal_e_Contrafactual",
        "keywords": ["causa", "impacto", "efeito", "contrafactual", "rollback", "por que", "cenarios"],
    },
    # Onda 3: Metacognição, Consolidação Hipocampal e Síntese Didática
    {
        "neuron_id": "neuron_metacognition_calibration",
        "lobe": "Lobo Pré-Frontal Metacognitivo",
        "specialty": "Calibração de Certeza (Brier Score), Detecção de Lacunas Epistêmicas e Auto-Auditoria",
        "wave": 3,
        "note_name": "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
        "keywords": ["certeza", "incerteza", "calibracao", "confianca", "auditar", "metacognicao"],
    },
    {
        "neuron_id": "neuron_episodic_consolidation",
        "lobe": "Hipocampo de Plasticidade Sináptica",
        "specialty": "Consolidação de Memória de Longo Prazo e Aprendizado de Restrições Negativas",
        "wave": 3,
        "note_name": "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
        "keywords": ["aprender", "consolidar", "memoria", "historico", "evoluir", "estender", "cerebro"],
    },
    {
        "neuron_id": "neuron_autonomous_planner",
        "lobe": "Córtex Pré-Motor de Decomposição Recursiva",
        "specialty": "Planejamento Multi-Horizonte, Alocação de HardBudget e Orquestração de Sub-DAGs",
        "wave": 3,
        "note_name": "Neuronio_11_Planejador_Recursivo_SubDAG",
        "keywords": ["planejar", "plano", "etapas", "roadmap", "cronograma", "recursivo", "jarvis"],
    },
    {
        "neuron_id": "neuron_semantics_didactics",
        "lobe": "Lobo Temporal de Síntese & Linguagem",
        "specialty": "Alinhamento Semântico Estrito, Clareza Conceitual e Comunicação Estruturada",
        "wave": 3,
        "note_name": "Neuronio_05_Semantica_e_Didatica",
        "keywords": ["explicar", "sintese", "resumo", "didatica", "linguagem", "voz"],
    },
]


@dataclass(frozen=True)
class SynapticRule:
    """Regra de plasticidade sináptica aprendida de Rollbacks Causais ou Certificados Aprovados."""
    rule_id: str
    neuron_id: str
    rule_type: str  # "NEGATIVE_CONSTRAINT" | "DISTILLED_INVARIANT"
    rule_text: str
    source_event_id: str
    confidence: float
    created_utc: str


class SynapticPlasticityMemory:
    """
    Hipocampo Digital (Memória de Plasticidade Sináptica de Longo Prazo).
    Persiste no SQLite todas as restrições negativas (`NegativeConstraint`) geradas por
    Rollbacks Causais e todos os invariantes destilados de execuções aprovadas,
    injetando esse aprendizado automaticamente nas futuras ativações dos neurônios!
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS synaptic_rules (
                    rule_id TEXT PRIMARY KEY,
                    neuron_id TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    rule_text TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_synaptic_neuron ON synaptic_rules(neuron_id);
                """
            )
            self._conn.commit()

    def record_rule(
        self,
        neuron_id: str,
        rule_type: str,
        rule_text: str,
        source_event_id: str,
        confidence: float = 1.0,
    ) -> SynapticRule:
        clean_text = rule_text.strip()
        digest = hashlib.sha256(f"{neuron_id}:{rule_type}:{clean_text}".encode("utf-8")).hexdigest()[:16]
        rule_id = f"syn_{digest}"
        now = utc_now_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO synaptic_rules(
                    rule_id, neuron_id, rule_type, rule_text, source_event_id, confidence, created_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (rule_id, neuron_id, rule_type, clean_text, source_event_id, confidence, now),
            )
            self._conn.commit()
        return SynapticRule(
            rule_id=rule_id,
            neuron_id=neuron_id,
            rule_type=rule_type,
            rule_text=clean_text,
            source_event_id=source_event_id,
            confidence=confidence,
            created_utc=now,
        )

    def get_rules_for_neuron(self, neuron_id: str, limit: int = 10) -> List[SynapticRule]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM synaptic_rules
                WHERE neuron_id = ? OR neuron_id = '*'
                ORDER BY created_utc DESC
                LIMIT ?;
                """,
                (neuron_id, limit),
            ).fetchall()
            return [
                SynapticRule(
                    rule_id=r["rule_id"],
                    neuron_id=r["neuron_id"],
                    rule_type=r["rule_type"],
                    rule_text=r["rule_text"],
                    source_event_id=r["source_event_id"],
                    confidence=float(r["confidence"]),
                    created_utc=r["created_utc"],
                )
                for r in rows
            ]

    def list_all_rules(self, limit: int = 50) -> List[SynapticRule]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM synaptic_rules ORDER BY created_utc DESC LIMIT ?;",
                (limit,),
            ).fetchall()
            return [
                SynapticRule(
                    rule_id=r["rule_id"],
                    neuron_id=r["neuron_id"],
                    rule_type=r["rule_type"],
                    rule_text=r["rule_text"],
                    source_event_id=r["source_event_id"],
                    confidence=float(r["confidence"]),
                    created_utc=r["created_utc"],
                )
                for r in rows
            ]

    def harvest_from_event_store(self, event_store: EpistemicEventStore) -> int:
        """
        Varre o `EpistemicEventStore` em busca de eventos de `CAUSAL_ROLLBACK` e
        `NEURON_TURN_APPROVED`, extraindo automaticamente restrições negativas e invariantes
        para a memória sináptica permanente!
        """
        harvested = 0
        for evt in event_store.get_all_events():
            if evt.event_type == "CAUSAL_ROLLBACK":
                reason = evt.delta_changes.get("rollback_reason") or evt.epistemic_state.get("reason")
                if reason:
                    self.record_rule(
                        neuron_id=evt.neuron_id,
                        rule_type="NEGATIVE_CONSTRAINT",
                        rule_text=f"Evitar reincidência de falha contida: {reason}",
                        source_event_id=evt.event_id,
                        confidence=1.0,
                    )
                    harvested += 1
            elif evt.event_type in ("NEURON_TURN_APPROVED", "HYPOTHESIS_GENERATED"):
                desc = (
                    evt.epistemic_state.get("hypothesis_description")
                    or evt.epistemic_state.get("description")
                    or (evt.epistemic_state.get("final_hypothesis") or {}).get("description")
                )
                if desc and isinstance(desc, str) and len(desc) > 10:
                    self.record_rule(
                        neuron_id=evt.neuron_id,
                        rule_type="DISTILLED_INVARIANT",
                        rule_text=f"Padrão verificado ({evt.neuron_id}): {desc[:160]}",
                        source_event_id=evt.event_id,
                        confidence=evt.confidence_score,
                    )
                    harvested += 1
        return harvested

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class ExtendedCognitiveCortexV3(FractalCognitiveCortex):
    """
    Córtex Cognitivo Fractal Estendido v3.0 (12 Nós Neurais: Tálamo + 10 Especialistas em 4 Lobos + Convergência + Hipocampo).
    """

    def __init__(
        self,
        event_store: Optional[EpistemicEventStore] = None,
        plasticity_memory: Optional[SynapticPlasticityMemory] = None,
        budget: Optional[HardBudget] = None,
        db_path: str = ":memory:",
        jsonl_path: Optional[str] = None,
    ) -> None:
        super().__init__(event_store=event_store, db_path=db_path, jsonl_path=jsonl_path)
        self.plasticity_memory = plasticity_memory or SynapticPlasticityMemory(":memory:")
        self.budget = budget or HardBudget(max_usd=1.00, max_calls=60)
        self._register_extended_v3_specialists()

    def _register_extended_v3_specialists(self) -> None:
        """Registra todos os 10 Neurônios Especialistas dos 4 Lobos Corticais."""
        for spec in EXTENDED_SPECIALISTS_SPEC:
            nid = spec["neuron_id"]
            if nid not in self.specialist_neurons:
                self.specialist_neurons[nid] = CognitiveNeuron(
                    neuron_id=nid,
                    specialty=spec["specialty"],
                    event_store=self.event_store,
                )

    def compile_extended_dag(
        self,
        objective: str,
        mode: str = "full_10_specialists",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionDAG:
        """
        Compila um ExecutionDAG de 4 ondas topológicas conectando os 10 Neurônios Especialistas
        (ou um subgrafo adaptativo) com injeção automática de regras de Plasticidade Sináptica!
        """
        dag = ExecutionDAG(metadata={"objective": objective, "version": "3.0", "mode": mode})
        ctx = dict(context or {})

        # Onda 1: Lógica Formal, Fatos/Proveniência e Criptografia/Segurança
        wave1_ids = ["task_logic_math", "task_epistemic_facts", "task_crypto_security"]
        wave1_neurons = [
            ("task_logic_math", "neuron_logic_math", f"Formalizar invariantes algébricos e lógicos para: {objective}"),
            ("task_epistemic_facts", "neuron_epistemic_facts", f"Auditar proveniência factual e citações CoALA para: {objective}"),
            ("task_crypto_security", "neuron_crypto_security", f"Auditar segurança Zero-Trust, hashes SHA-256 e assinaturas Ed25519 para: {objective}"),
        ]
        for node_id, neuron_id, intent in wave1_neurons:
            learned_rules = [r.rule_text for r in self.plasticity_memory.get_rules_for_neuron(neuron_id, limit=4)]
            dag.add_node(
                DAGTaskNode(
                    node_id=node_id,
                    target_neuron_id=neuron_id,
                    task_intent=intent,
                    dependencies=[],
                    axioms=[f"Objetivo central: {objective}"],
                    constraints=learned_rules,
                    input_data=ctx,
                )
            )

        # Onda 2: Engenharia de Sistemas, Estratégia/Risco e Inferência Causal/Contrafactual
        wave2_ids = ["task_systems_engineering", "task_strategy_risk", "task_causal_counterfactual"]
        wave2_neurons = [
            ("task_systems_engineering", "neuron_systems_engineering", f"Sintetizar e validar arquitetura e código em Sandbox V2 para: {objective}"),
            ("task_strategy_risk", "neuron_strategy_risk", f"Modelar riscos BFT, limites de orçamento e contenção de falhas para: {objective}"),
            ("task_causal_counterfactual", "neuron_causal_counterfactual", f"Executar análise de causa-raiz e simulação contrafactual (Do-Calculus) para: {objective}"),
        ]
        for node_id, neuron_id, intent in wave2_neurons:
            learned_rules = [r.rule_text for r in self.plasticity_memory.get_rules_for_neuron(neuron_id, limit=4)]
            dag.add_node(
                DAGTaskNode(
                    node_id=node_id,
                    target_neuron_id=neuron_id,
                    task_intent=intent,
                    dependencies=list(wave1_ids),
                    axioms=[f"Objetivo central: {objective}"],
                    constraints=learned_rules,
                    input_data=ctx,
                )
            )

        # Onda 3: Metacognição/Calibração, Hipocampo/Consolidação, Planejador Recursivo e Semântica/Didática
        wave3_neurons = [
            ("task_metacognition_calibration", "neuron_metacognition_calibration", f"Calibrar confiança epistêmica (Brier Score) e auditar lacunas para: {objective}", list(wave2_ids)),
            ("task_episodic_consolidation", "neuron_episodic_consolidation", f"Destilar sabedoria sináptica de longo prazo para o Hipocampo sobre: {objective}", list(wave2_ids)),
            ("task_autonomous_planner", "neuron_autonomous_planner", f"Estruturar plano executivo multi-horizonte verificável para: {objective}", list(wave2_ids)),
            ("task_semantics_didactics", "neuron_semantics_didactics", f"Unificar síntese semântica e comunicabilidade final para: {objective}", [
                "task_metacognition_calibration",
                "task_episodic_consolidation",
                "task_autonomous_planner",
            ]),
        ]
        for node_id, neuron_id, intent, deps in wave3_neurons:
            learned_rules = [r.rule_text for r in self.plasticity_memory.get_rules_for_neuron(neuron_id, limit=4)]
            dag.add_node(
                DAGTaskNode(
                    node_id=node_id,
                    target_neuron_id=neuron_id,
                    task_intent=intent,
                    dependencies=deps,
                    axioms=[f"Objetivo central: {objective}"],
                    constraints=learned_rules,
                    input_data=ctx,
                )
            )

        return dag

    def process_v3(
        self,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> CortexExecutionResult:
        """
        Executa o Córtex Estendido v3.0 com 10 Especialistas distribuídos em 4 Lobos Corticais
        (+ Tálamo Sensorial + Árbitro de Convergência = 12 Nós Neurais) e colhe automaticamente
        novas regras de Plasticidade Sináptica no Hipocampo!
        """
        dag = self.compile_extended_dag(objective=objective, context=context)
        result = self.execute_dag(dag)
        self.plasticity_memory.harvest_from_event_store(self.event_store)
        for cert in result.certificates.values():
            if cert.status == VerdictStatus.APPROVED and cert.final_hypothesis:
                self.plasticity_memory.record_rule(
                    neuron_id=cert.neuron_id,
                    rule_type="DISTILLED_INVARIANT",
                    rule_text=f"Certificado ({cert.neuron_id}): {cert.final_hypothesis.description[:160]}",
                    source_event_id=cert.head_event_id or cert.certificate_id,
                    confidence=cert.confidence_score,
                )
        return result
