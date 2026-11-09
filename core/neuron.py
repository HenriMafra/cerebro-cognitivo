"""
Neurônio Cognitivo Composto (Microcircuito Fechado de 8 Estágios).
Implementação canônica do processador de raciocínio fractal com auto-correção,
verificação tripla ortogonal (V1 Lógica, V2 Grounding, V3 Red Team) e
registro estrito de cada transição no Event Sourcing Epistêmico.
"""

from __future__ import annotations
import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from .llm_bridge import CognitiveSynthesisBridge
from .schemas import (
    Claim,
    EpistemicEvent,
    HypothesisPayload,
    NeuronCertificate,
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


class InMemoryEventStore:
    """
    Implementação em memória canônica do Repositório de Eventos Epistêmicos.
    Garante encadeamento de hashes criptográficos SHA-256 (blockchain local),
    rastreabilidade de branches e suporte a rollback causal.
    Compatível com chamadas tanto de objeto EpistemicEvent quanto por argumentos avulsos.
    """

    def __init__(self) -> None:
        self.events: Dict[str, EpistemicEvent] = {}
        self.branch_heads: Dict[str, str] = {}
        self.branch_lineage: Dict[str, List[str]] = {}

    def record_event(
        self,
        event_or_neuron_id: Any,
        subagent_role: Optional[str] = None,
        event_type: Optional[str] = None,
        epistemic_state: Optional[Dict[str, Any]] = None,
        delta_changes: Optional[Dict[str, Any]] = None,
        verdict: Optional[str] = None,
        confidence_score: float = 1.0,
        cycle_iteration: int = 1,
        parent_event_id: Optional[str] = None,
        branch_id: str = "main",
        timestamp_utc: Optional[str] = None,
    ) -> EpistemicEvent:
        """Registra um evento encadeando hash e atualizando a cabeça do branch."""
        if isinstance(event_or_neuron_id, EpistemicEvent):
            event = event_or_neuron_id
        else:
            event = EpistemicEvent(
                neuron_id=str(event_or_neuron_id),
                subagent_role=subagent_role or "system",
                event_type=event_type or "GENERIC_EVENT",
                epistemic_state=epistemic_state or {},
                delta_changes=delta_changes or {},
                verdict=str(verdict or "RECORDED"),
                confidence_score=float(confidence_score),
                cycle_iteration=int(cycle_iteration),
                parent_event_id=parent_event_id,
                branch_id=branch_id,
                timestamp_utc=timestamp_utc or utc_now_iso(),
            )

        head_id = self.branch_heads.get(event.branch_id)
        if head_id and head_id in self.events:
            prev_event = self.events[head_id]
            event.previous_event_hash = prev_event.content_hash
            if not event.parent_event_id:
                event.parent_event_id = head_id

        # Recalcular hash canônico
        event.content_hash = event.compute_canonical_hash()

        self.events[event.event_id] = event
        self.branch_heads[event.branch_id] = event.event_id

        if event.branch_id not in self.branch_lineage:
            self.branch_lineage[event.branch_id] = []
        self.branch_lineage[event.branch_id].append(event.event_id)

        return event

    def branch_from(
        self,
        target_event_id: str,
        new_branch_id: str,
        reason: str = "Rollback Causal",
        neuron_id: str = "neuron",
    ) -> str:
        """Cria um novo branch apontando para target_event_id como vértice raiz."""
        self.branch_heads[new_branch_id] = target_event_id
        self.branch_lineage[new_branch_id] = []
        return new_branch_id

    def get_head_event_id(self, branch_id: str = "main") -> Optional[str]:
        """Retorna o identificador do evento no topo do branch especificado."""
        return self.branch_heads.get(branch_id)

    def get_event(self, event_id: str) -> Optional[EpistemicEvent]:
        """Recupera um evento pelo ID."""
        return self.events.get(event_id)

    def get_all_events(self) -> List[EpistemicEvent]:
        """Retorna todos os eventos em ordem cronológica de inserção."""
        return list(self.events.values())


class CognitiveNeuron:
    """
    Neurônio Cognitivo Composto.
    Executa o microcircuito fechado de 8 estágios:
    1. Dendrito Receptor: Sanitização e validação de esquema estrito.
    2. Expansor de Premissas: Mapeamento de axiomas e restrições.
    3. Núcleo Pensador: Formulação de hipóteses com ProvenancePointers.
    4. Camada V1: Auditor Lógico Silogístico.
    5. Camada V2: Árbitro de Máquina Determinístico em Sandbox.
    6. Camada V3: Inquisidor Adversário Red Team e Casos de Borda.
    7. Lapidador de Saída: Consolidação formal de pureza semântica.
    8. Axônio Emissor: Emissão do Certificado do Neurônio ou Aborto Epistêmico.
    """

    def __init__(
        self,
        neuron_id: str,
        specialty: str,
        event_store: Optional[Any] = None,
        max_iterations: int = 3,
        synthesis_bridge: Optional[CognitiveSynthesisBridge] = None,
        custom_thinker_fn: Optional[Callable[..., Any]] = None,
        v1_logic: Optional[LogicalVerifier] = None,
        v2_grounding: Optional[DeterministicMachineVerifier] = None,
        v3_red_team: Optional[AdversarialRedTeamVerifier] = None,
    ) -> None:
        self.neuron_id = neuron_id
        self.specialty = specialty
        self.event_store = event_store if event_store is not None else InMemoryEventStore()
        self.max_iterations = max_iterations
        self.synthesis_bridge = synthesis_bridge or CognitiveSynthesisBridge()
        self.custom_thinker_fn = custom_thinker_fn

        # As 3 Camadas Ortogonais Canônicas
        self.v1_logic = v1_logic or LogicalVerifier()
        self.v2_grounding = v2_grounding or DeterministicMachineVerifier()
        self.v3_red_team = v3_red_team or AdversarialRedTeamVerifier()

    def process_signal(
        self,
        signal: SynapticSignal,
        branch_id: str = "main",
    ) -> NeuronCertificate:
        """
        Processa um sinal sináptico executando o ciclo fechado de 8 estágios.
        Se qualquer verificador reprovar, efetua Rollback Causal, injeta as
        restrições negativas e tenta novamente até max_iterations.
        Se esgotar as iterações, efetua Aborto Epistêmico Formal (zero alucinação).
        """
        start_time = time.perf_counter()
        current_branch = branch_id

        # -------------------------------------------------------------
        # ESTÁGIO 1: Dendrito Receptor
        # -------------------------------------------------------------
        if not signal.signal_hash:
            signal.__post_init__()

        evt_signal = EpistemicEvent(
            neuron_id=self.neuron_id,
            subagent_role="DENDRITO_RECEPTOR",
            event_type="SIGNAL_RECEIVED",
            epistemic_state={
                "status": "SIGNAL_ACCEPTED",
                "signal_id": signal.signal_id,
                "source_neuron": signal.source_neuron,
                "target_neuron": signal.target_neuron,
                "task_intent": signal.task_intent,
            },
            delta_changes={
                "axioms_count": len(signal.axioms),
                "constraints_count": len(signal.constraints),
                "signal_hash": signal.signal_hash,
            },
            verdict="ACCEPTED",
            confidence_score=1.0,
            cycle_iteration=0,
            parent_event_id=signal.parent_event_id,
            branch_id=current_branch,
        )
        head_event_id = self._record_event(evt_signal)

        # -------------------------------------------------------------
        # ESTÁGIO 2: Expansor de Premissas
        # -------------------------------------------------------------
        expanded_axioms = list(signal.axioms) + [
            f"Especialidade do neurônio '{self.specialty}' ativada",
            "Axioma da Não-Contradição Formal",
        ]
        expanded_constraints = list(signal.constraints) + [
            "Toda afirmação requer ProvenancePointer verificável",
            "Integridade de tipos e ausência de efeitos colaterais destrutivos",
        ]

        evt_premises = EpistemicEvent(
            neuron_id=self.neuron_id,
            subagent_role="EXPANSOR_PREMISSAS",
            event_type="PREMISES_EXPANDED",
            epistemic_state={
                "expanded_axioms": expanded_axioms,
                "expanded_constraints": expanded_constraints,
            },
            delta_changes={
                "total_axioms": len(expanded_axioms),
                "total_constraints": len(expanded_constraints),
            },
            verdict="PREMISES_EXPANDED",
            confidence_score=1.0,
            cycle_iteration=0,
            parent_event_id=head_event_id,
            branch_id=current_branch,
        )
        head_event_id = self._record_event(evt_premises)

        # -------------------------------------------------------------
        # ESTÁGIO 3 ao 6: Loop de Síntese e Tripla Verificação (até max_iterations)
        # -------------------------------------------------------------
        accumulated_negative_constraints: List[str] = list(signal.constraints)
        last_hypothesis: Optional[HypothesisPayload] = None
        last_verifier_reports: List[VerifierReport] = []

        for iteration in range(1, self.max_iterations + 1):
            checkpoint_head = head_event_id

            # --- ESTÁGIO 3: Núcleo Pensador (Geração de Hipótese) ---
            hypothesis = self.synthesis_bridge.synthesize(
                signal=signal,
                iteration=iteration,
                negative_constraints=accumulated_negative_constraints,
                custom_thinker_fn=self.custom_thinker_fn,
            )
            last_hypothesis = hypothesis

            evt_hyp = EpistemicEvent(
                neuron_id=self.neuron_id,
                subagent_role="NUCLEO_PENSADOR",
                event_type="HYPOTHESIS_GENERATED",
                epistemic_state={
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "description": hypothesis.description,
                    "claims_count": len(hypothesis.claims),
                    "code_present": bool(hypothesis.code_artifact),
                    "entrypoint": hypothesis.entrypoint_function,
                },
                delta_changes={
                    "iteration": iteration,
                    "negative_constraints_applied": hypothesis.negative_constraints_applied,
                },
                verdict="HYPOTHESIS_FORMULATED",
                confidence_score=0.5,
                cycle_iteration=iteration,
                parent_event_id=head_event_id,
                branch_id=current_branch,
            )
            head_event_id = self._record_event(evt_hyp)

            # --- ESTÁGIO 4: Camada V1 - Verificador Lógico Silogístico ---
            report_v1 = self.v1_logic.verify(hypothesis, signal)
            evt_v1 = EpistemicEvent(
                neuron_id=self.neuron_id,
                subagent_role="VERIFICADOR_V1_LOGICA",
                event_type="VERIFICATION_V1",
                epistemic_state={
                    "status": report_v1.status.value,
                    "score": report_v1.score,
                },
                delta_changes={
                    "reasons": report_v1.reasons,
                    "negative_constraints_added": report_v1.negative_constraints_added,
                },
                verdict=report_v1.status.value,
                confidence_score=report_v1.score,
                cycle_iteration=iteration,
                parent_event_id=head_event_id,
                branch_id=current_branch,
            )
            head_event_id = self._record_event(evt_v1)

            if report_v1.status != VerdictStatus.APPROVED:
                # Rollback Causal
                rollback_branch = f"rollback_v1_iter_{iteration}_{new_id('br')}"
                current_branch = self._branch_from(
                    checkpoint_head,
                    rollback_branch,
                    reason=f"Reprovação V1 Lógica na iteração {iteration}",
                )
                head_event_id = checkpoint_head

                for nc in report_v1.negative_constraints_added:
                    if nc not in accumulated_negative_constraints:
                        accumulated_negative_constraints.append(nc)
                last_verifier_reports = [report_v1]
                continue

            # --- ESTÁGIO 5: Camada V2 - Árbitro Determinístico em Sandbox ---
            report_v2 = self.v2_grounding.verify(hypothesis, signal)
            evt_v2 = EpistemicEvent(
                neuron_id=self.neuron_id,
                subagent_role="VERIFICADOR_V2_GROUNDING",
                event_type="VERIFICATION_V2",
                epistemic_state={
                    "status": report_v2.status.value,
                    "score": report_v2.score,
                    "machine_executed": report_v2.machine_feedback.executed if report_v2.machine_feedback else False,
                    "exit_code": report_v2.machine_feedback.exit_code if report_v2.machine_feedback else None,
                },
                delta_changes={
                    "reasons": report_v2.reasons,
                    "negative_constraints_added": report_v2.negative_constraints_added,
                    "stderr": report_v2.machine_feedback.stderr if report_v2.machine_feedback else "",
                },
                verdict=report_v2.status.value,
                confidence_score=report_v2.score,
                cycle_iteration=iteration,
                parent_event_id=head_event_id,
                branch_id=current_branch,
            )
            head_event_id = self._record_event(evt_v2)

            if report_v2.status != VerdictStatus.APPROVED:
                # Rollback Causal
                rollback_branch = f"rollback_v2_iter_{iteration}_{new_id('br')}"
                current_branch = self._branch_from(
                    checkpoint_head,
                    rollback_branch,
                    reason=f"Reprovação V2 Grounding na iteração {iteration}",
                )
                head_event_id = checkpoint_head

                for nc in report_v2.negative_constraints_added:
                    if nc not in accumulated_negative_constraints:
                        accumulated_negative_constraints.append(nc)
                if report_v2.machine_feedback and report_v2.machine_feedback.stderr:
                    stderr_msg = f"stderr da máquina: {report_v2.machine_feedback.stderr.strip()}"
                    if stderr_msg not in accumulated_negative_constraints:
                        accumulated_negative_constraints.append(stderr_msg)

                last_verifier_reports = [report_v1, report_v2]
                continue

            # --- ESTÁGIO 6: Camada V3 - Inquisidor Adversário Red Team ---
            report_v3 = self.v3_red_team.verify(hypothesis, signal)
            evt_v3 = EpistemicEvent(
                neuron_id=self.neuron_id,
                subagent_role="VERIFICADOR_V3_RED_TEAM",
                event_type="VERIFICATION_V3",
                epistemic_state={
                    "status": report_v3.status.value,
                    "score": report_v3.score,
                    "counterexamples_count": len(report_v3.counterexamples),
                },
                delta_changes={
                    "reasons": report_v3.reasons,
                    "counterexamples": report_v3.counterexamples,
                    "negative_constraints_added": report_v3.negative_constraints_added,
                },
                verdict=report_v3.status.value,
                confidence_score=report_v3.score,
                cycle_iteration=iteration,
                parent_event_id=head_event_id,
                branch_id=current_branch,
            )
            head_event_id = self._record_event(evt_v3)

            if report_v3.status != VerdictStatus.APPROVED:
                # Rollback Causal
                rollback_branch = f"rollback_v3_iter_{iteration}_{new_id('br')}"
                current_branch = self._branch_from(
                    checkpoint_head,
                    rollback_branch,
                    reason=f"Reprovação V3 Red Team na iteração {iteration}",
                )
                head_event_id = checkpoint_head

                for nc in report_v3.negative_constraints_added:
                    if nc not in accumulated_negative_constraints:
                        accumulated_negative_constraints.append(nc)
                for ce in report_v3.counterexamples:
                    ce_msg = f"Contraexemplo Red Team: {ce}"
                    if ce_msg not in accumulated_negative_constraints:
                        accumulated_negative_constraints.append(ce_msg)

                last_verifier_reports = [report_v1, report_v2, report_v3]
                continue

            # -------------------------------------------------------------
            # ESTÁGIOS 7 & 8: Lapidador de Saída & Axônio Emissor (Aprovação Total)
            # -------------------------------------------------------------
            duration_ms = (time.perf_counter() - start_time) * 1000
            overall_confidence = min(report_v1.score, report_v2.score, report_v3.score)

            evt_axon = EpistemicEvent(
                neuron_id=self.neuron_id,
                subagent_role="AXONIO_EMISSOR",
                event_type="AXON_EMITTED",
                epistemic_state={
                    "status": VerdictStatus.APPROVED.value,
                    "confidence_score": overall_confidence,
                    "iterations": iteration,
                },
                delta_changes={
                    "certificate_issued": True,
                    "execution_time_ms": round(duration_ms, 2),
                },
                verdict="APPROVED",
                confidence_score=overall_confidence,
                cycle_iteration=iteration,
                parent_event_id=head_event_id,
                branch_id=current_branch,
            )
            head_event_id = self._record_event(evt_axon)

            return NeuronCertificate(
                neuron_id=self.neuron_id,
                signal_id=signal.signal_id,
                status=VerdictStatus.APPROVED,
                total_iterations=iteration,
                final_hypothesis=hypothesis,
                verifier_reports=[report_v1, report_v2, report_v3],
                head_event_id=head_event_id,
                confidence_score=overall_confidence,
                execution_time_ms=round(duration_ms, 2),
            )

        # -------------------------------------------------------------
        # ABORTO EPISTÊMICO FORMAL (Esgotamento das Iterações)
        # -------------------------------------------------------------
        duration_ms = (time.perf_counter() - start_time) * 1000

        evt_abort = EpistemicEvent(
            neuron_id=self.neuron_id,
            subagent_role="AXONIO_EMISSOR",
            event_type="EPISTEMIC_ABORT",
            epistemic_state={
                "status": VerdictStatus.EPISTEMIC_FAILURE.value,
                "max_iterations_exhausted": self.max_iterations,
                "reason": "Solução não convergiu nas 3 camadas após esgotamento das iterações permitidas.",
            },
            delta_changes={
                "last_reports_count": len(last_verifier_reports),
                "accumulated_negative_constraints": accumulated_negative_constraints,
            },
            verdict="EPISTEMIC_FAILURE",
            confidence_score=0.0,
            cycle_iteration=self.max_iterations,
            parent_event_id=head_event_id,
            branch_id=current_branch,
        )
        head_event_id = self._record_event(evt_abort)

        return NeuronCertificate(
            neuron_id=self.neuron_id,
            signal_id=signal.signal_id,
            status=VerdictStatus.EPISTEMIC_FAILURE,
            total_iterations=self.max_iterations,
            final_hypothesis=last_hypothesis,
            verifier_reports=last_verifier_reports,
            head_event_id=head_event_id,
            confidence_score=0.0,
            execution_time_ms=round(duration_ms, 2),
        )

    def _record_event(self, event: EpistemicEvent) -> str:
        """
        Encaminha a gravação do evento para o event_store fornecido,
        adaptando dinamicamente a assinatura se for EpistemicEventStore ou InMemoryEventStore.
        """
        if not hasattr(self.event_store, "record_event"):
            raise AttributeError("O event_store deve implementar o método 'record_event'.")

        sig = inspect.signature(self.event_store.record_event)
        params = list(sig.parameters.keys())

        if len(params) > 0 and params[0] in ("event", "evt", "event_or_neuron_id"):
            res = self.event_store.record_event(event)
        elif "neuron_id" in params:
            res = self.event_store.record_event(
                neuron_id=event.neuron_id,
                subagent_role=event.subagent_role,
                event_type=event.event_type,
                epistemic_state=event.epistemic_state,
                delta_changes=event.delta_changes,
                verdict=event.verdict,
                confidence_score=event.confidence_score,
                cycle_iteration=event.cycle_iteration,
                parent_event_id=event.parent_event_id,
                branch_id=event.branch_id,
                timestamp_utc=event.timestamp_utc,
            )
        else:
            try:
                res = self.event_store.record_event(event)
            except TypeError:
                res = self.event_store.record_event(
                    neuron_id=event.neuron_id,
                    subagent_role=event.subagent_role,
                    event_type=event.event_type,
                    epistemic_state=event.epistemic_state,
                    delta_changes=event.delta_changes,
                    verdict=event.verdict,
                    confidence_score=event.confidence_score,
                    cycle_iteration=event.cycle_iteration,
                    parent_event_id=event.parent_event_id,
                    branch_id=event.branch_id,
                    timestamp_utc=event.timestamp_utc,
                )

        if hasattr(res, "event_id"):
            return res.event_id
        return str(res)

    def _branch_from(
        self,
        parent_event_id: str,
        new_branch_id: str,
        reason: str = "Rollback Causal",
    ) -> str:
        """
        Solicita a criação de um novo branch causal no event_store,
        adaptando argumentos conforme a assinatura do backend.
        """
        if hasattr(self.event_store, "branch_from"):
            sig = inspect.signature(self.event_store.branch_from)
            params = list(sig.parameters.keys())
            if "reason" in params:
                res = self.event_store.branch_from(
                    target_event_id=parent_event_id,
                    new_branch_id=new_branch_id,
                    reason=reason,
                    neuron_id=self.neuron_id,
                )
            else:
                res = self.event_store.branch_from(parent_event_id, new_branch_id)

            if hasattr(res, "branch_id"):
                return res.branch_id
            elif isinstance(res, str):
                return res

        return new_branch_id
