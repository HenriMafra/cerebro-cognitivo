"""
Módulo de Orquestração do Córtex Global em Grafo Acíclico Dirigido (DAG).
Orquestra o Tálamo Sensorial, Especialistas Cognitivos e Neurônio de Convergência.
"""

from __future__ import annotations
import dataclasses
from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .event_store import EpistemicEventStore
from .neuron import CognitiveNeuron
from .schemas import (
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


@dataclass
class DAGTaskNode:
    """Vértice de tarefa no Grafo Acíclico Dirigido de Execução Cognitiva."""
    node_id: str
    target_neuron_id: str
    task_intent: str
    dependencies: List[str] = field(default_factory=list)
    axioms: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class ExecutionDAG:
    """
    Grafo Acíclico Dirigido (DAG) de Execução Neural.
    Implementa ordenação topológica determinística pelo Algoritmo de Kahn,
    agrupando nós em gerações de ondas paralelas e detectando ciclos causais.
    """
    dag_id: str = field(default_factory=lambda: new_id("dag"))
    nodes: Dict[str, DAGTaskNode] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: DAGTaskNode) -> None:
        """Adiciona um nó ao grafo. Levanta ValueError se node_id duplicado."""
        if node.node_id in self.nodes:
            raise ValueError(f"Nó com identificador '{node.node_id}' já existe no ExecutionDAG.")
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[DAGTaskNode]:
        """Recupera um nó pelo identificador."""
        return self.nodes.get(node_id)

    def topological_generations(self) -> List[List[DAGTaskNode]]:
        """
        Calcula a ordenação topológica determinística pelo Algoritmo de Kahn,
        agrupando nós independentes em ondas (gerações) paralelas de execução.

        Detecta ciclos e levanta ValueError("Cycle detected in ExecutionDAG").
        Detecta dependências inexistentes e levanta ValueError("Dependency not found").
        """
        if not self.nodes:
            return []

        # 1. Validação de existência de todas as dependências declaradas
        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(
                        f"Dependência '{dep}' exigida pelo nó '{nid}' não foi encontrada no ExecutionDAG."
                    )

        # 2. Cálculo dos graus de entrada (in-degree) e lista de dependentes (adjacência)
        in_degree: Dict[str, int] = {nid: len(node.dependencies) for nid, node in self.nodes.items()}
        dependents: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                dependents[dep].append(nid)

        # 3. Onda inicial: nós com grau de entrada zero (ordenados deterministicamente por node_id)
        current_wave = sorted([nid for nid, deg in in_degree.items() if deg == 0])

        if not current_wave:
            raise ValueError("Cycle detected in ExecutionDAG")

        generations: List[List[DAGTaskNode]] = []
        visited_count = 0

        # 4. Iteração por ondas topológicas
        while current_wave:
            generations.append([self.nodes[nid] for nid in current_wave])
            visited_count += len(current_wave)

            next_candidates: List[str] = []
            for nid in current_wave:
                for child_id in dependents[nid]:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        next_candidates.append(child_id)

            # Ordenação determinística lexicográfica da próxima onda
            current_wave = sorted(next_candidates)

        # 5. Detecção estrita de ciclos (Algoritmo de Kahn)
        if visited_count < len(self.nodes):
            raise ValueError("Cycle detected in ExecutionDAG")

        return generations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "metadata": self.metadata,
        }


class SensoryInputNeuron:
    """
    Neurônio de Entrada Sensorial / Tálamo Central.
    Recebe estímulos e objetivos em linguagem de alto nível, compila um plano
    estruturado em ExecutionDAG estritamente validado e grava o evento DAG_COMPILED.
    """

    def __init__(
        self,
        neuron_id: str = "neuron_sensory_input",
        event_store: Optional[EpistemicEventStore] = None,
    ) -> None:
        self.neuron_id = neuron_id
        self.event_store = event_store

    def compile_plan(
        self,
        objective: str,
        nodes: Optional[List[DAGTaskNode]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionDAG:
        """
        Compila o estímulo sensorial em um ExecutionDAG formal.
        Garante ordenação causal válida e ausência de ciclos.
        Persiste o evento DAG_COMPILED no EpistemicEventStore.
        """
        dag = ExecutionDAG()

        if nodes is not None and len(nodes) > 0:
            for n in nodes:
                dag.add_node(n)
        else:
            # Compilação canônica padrão ativando a rede de 5 especialistas
            n_facts = DAGTaskNode(
                node_id="task_epistemic_facts",
                target_neuron_id="neuron_epistemic_facts",
                task_intent=f"Auditoria de proveniência factual e ancoragem para: {objective}",
                dependencies=[],
                axioms=["Axioma do Lastro Empírico Obrigatório"],
                constraints=["Toda afirmação deve ter ProvenancePointer verificável"],
                input_data={"objective": objective, "context": context or {}},
            )
            n_logic = DAGTaskNode(
                node_id="task_logic_math",
                target_neuron_id="neuron_logic_math",
                task_intent=f"Formalização de teoremas, invariantes lógicos e matemáticos para: {objective}",
                dependencies=["task_epistemic_facts"],
                axioms=["Axioma da Não-Contradição Formal"],
                constraints=["Pureza matemática e consistência axiomática"],
                input_data={"objective": objective},
            )
            n_eng = DAGTaskNode(
                node_id="task_systems_engineering",
                target_neuron_id="neuron_systems_engineering",
                task_intent=f"Engenharia de software e implementação determinística para: {objective}",
                dependencies=["task_logic_math"],
                axioms=["Axioma do Grounding em Sandbox"],
                constraints=["Código determinístico, sem efeitos colaterais"],
                input_data={"objective": objective},
            )
            n_risk = DAGTaskNode(
                node_id="task_strategy_risk",
                target_neuron_id="neuron_strategy_risk",
                task_intent=f"Auditoria adversarial de riscos, casos de borda e contingências para: {objective}",
                dependencies=["task_systems_engineering"],
                axioms=["Axioma da Análise Adversarial"],
                constraints=["Identificação exaustiva de riscos e falhas"],
                input_data={"objective": objective},
            )
            n_sem = DAGTaskNode(
                node_id="task_semantics_didactics",
                target_neuron_id="neuron_semantics_didactics",
                task_intent=f"Síntese conceitual, semântica e didática executiva para: {objective}",
                dependencies=["task_strategy_risk"],
                axioms=["Axioma da Precisão Conceitual"],
                constraints=["Clareza didática sem perda de rigor formal"],
                input_data={"objective": objective},
            )
            for n in [n_facts, n_logic, n_eng, n_risk, n_sem]:
                dag.add_node(n)

        # Validação estrita do DAG antes de gravar o evento
        generations = dag.topological_generations()

        if self.event_store is not None:
            head = self.event_store.get_branch_head("main")
            parent_id = head.event_id if head else None
            self.event_store.record_event(
                neuron_id=self.neuron_id,
                subagent_role="sensory_thalamus_compiler",
                event_type="DAG_COMPILED",
                epistemic_state={
                    "objective": objective,
                    "total_nodes": len(dag.nodes),
                    "total_generations": len(generations),
                    "context": context or {},
                    "waves": [[n.node_id for n in gen] for gen in generations],
                },
                delta_changes={
                    "dag_id": dag.dag_id,
                    "node_ids": list(dag.nodes.keys()),
                },
                verdict="APPROVED",
                confidence_score=1.0,
                cycle_iteration=1,
                parent_event_id=parent_id,
                branch_id="main",
            )

        return dag


@dataclass
class CortexExecutionResult:
    """Resultado consolidado da execução do Grafo Cognitivo no Córtex."""
    dag_id: str
    status: VerdictStatus
    total_nodes: int
    executed_nodes: int
    certificates: Dict[str, NeuronCertificate]
    synthesis: Dict[str, Any]
    convergence_event_id: str
    execution_time_ms: float
    integrity_verified: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "status": self.status.value,
            "total_nodes": self.total_nodes,
            "executed_nodes": self.executed_nodes,
            "certificates": {nid: cert.to_dict() for nid, cert in self.certificates.items()},
            "synthesis": self.synthesis,
            "convergence_event_id": self.convergence_event_id,
            "execution_time_ms": self.execution_time_ms,
            "integrity_verified": self.integrity_verified,
            "errors": self.errors,
        }


class ConvergenceSynthesisNeuron:
    """
    Neurônio de Convergência e Síntese.
    Recebe os certificados emitidos por todos os neurônios especialistas do DAG,
    valida invariantes globais, verifica integridade criptográfica dos certificados,
    grava o evento CORTEX_CONVERGENCE (ou CORTEX_ABORT) e consolida a entrega final.
    """

    def __init__(
        self,
        neuron_id: str = "neuron_convergence_synthesis",
        event_store: Optional[EpistemicEventStore] = None,
    ) -> None:
        self.neuron_id = neuron_id
        self.event_store = event_store

    def synthesize(
        self,
        dag: ExecutionDAG,
        certificates: Dict[str, NeuronCertificate],
        start_time: Optional[float] = None,
    ) -> CortexExecutionResult:
        """
        Consolida todos os certificados dos nós do DAG, verificando integridade e aprovação global.
        """
        duration_ms = (time.perf_counter() - start_time) * 1000.0 if start_time else 0.0
        errors: List[str] = []
        is_approved = True

        # 1. Verifica se todos os nós do DAG foram executados
        for node_id, node in dag.nodes.items():
            if node_id not in certificates:
                errors.append(f"Certificado ausente para o nó obrigatório '{node_id}' ({node.target_neuron_id}).")
                is_approved = False

        # 2. Verifica invariantes globais em cada certificado
        for node_id, cert in certificates.items():
            if cert.status != VerdictStatus.APPROVED:
                errors.append(
                    f"Nó '{node_id}' ({cert.neuron_id}) não foi aprovado (status: {cert.status.value})."
                )
                is_approved = False

            # Validação criptográfica estrita do hash do certificado
            expected_hash = compute_sha256({
                "certificate_id": cert.certificate_id,
                "neuron_id": cert.neuron_id,
                "signal_id": cert.signal_id,
                "status": cert.status.value,
                "total_iterations": cert.total_iterations,
                "final_hypothesis": cert.final_hypothesis.to_dict() if cert.final_hypothesis else None,
                "head_event_id": cert.head_event_id,
                "confidence_score": cert.confidence_score,
            })
            if cert.certificate_hash != expected_hash:
                errors.append(
                    f"Violação de integridade criptográfica detectada no certificado do nó '{node_id}'. "
                    f"Hash registrado: {cert.certificate_hash}, esperado: {expected_hash}."
                )
                is_approved = False

        # 3. Consolidação de síntese
        approved_count = sum(1 for c in certificates.values() if c.status == VerdictStatus.APPROVED)
        avg_confidence = (
            sum(c.confidence_score for c in certificates.values()) / max(len(certificates), 1)
            if certificates else 0.0
        )

        synthesis_payload = {
            "dag_id": dag.dag_id,
            "total_nodes": len(dag.nodes),
            "executed_nodes": len(certificates),
            "approved_nodes": approved_count,
            "average_confidence": round(avg_confidence, 4),
            "node_summaries": {
                nid: {
                    "neuron_id": c.neuron_id,
                    "status": c.status.value,
                    "confidence": c.confidence_score,
                    "hypothesis_summary": (
                        c.final_hypothesis.description
                        if c.final_hypothesis else "Sem hipótese"
                    ),
                    "code_present": bool(c.final_hypothesis and c.final_hypothesis.code_artifact),
                }
                for nid, c in certificates.items()
            },
        }

        verdict_status = VerdictStatus.APPROVED if is_approved else VerdictStatus.EPISTEMIC_FAILURE
        event_type = "CORTEX_CONVERGENCE" if is_approved else "CORTEX_ABORT"
        verdict_str = "APPROVED" if is_approved else "EPISTEMIC_FAILURE"

        convergence_event_id = "evt_unpersisted"
        if self.event_store is not None:
            head = self.event_store.get_branch_head("main")
            parent_id = head.event_id if head else None
            evt = self.event_store.record_event(
                neuron_id=self.neuron_id,
                subagent_role="convergence_synthesis_arbiter",
                event_type=event_type,
                epistemic_state={
                    "dag_id": dag.dag_id,
                    "is_converged": is_approved,
                    "errors": errors,
                    "synthesis_summary": synthesis_payload,
                },
                delta_changes={
                    "dag_status": verdict_status.value,
                    "total_certificates": len(certificates),
                },
                verdict=verdict_str,
                confidence_score=avg_confidence if is_approved else 0.0,
                cycle_iteration=1,
                parent_event_id=parent_id,
                branch_id="main",
            )
            convergence_event_id = evt.event_id

        return CortexExecutionResult(
            dag_id=dag.dag_id,
            status=verdict_status,
            total_nodes=len(dag.nodes),
            executed_nodes=len(certificates),
            certificates=certificates,
            synthesis=synthesis_payload,
            convergence_event_id=convergence_event_id,
            execution_time_ms=round(duration_ms, 2),
            integrity_verified=is_approved,
            errors=errors,
        )


class FractalCognitiveCortex:
    """
    O Cérebro Cognitivo Global.
    Coordena o fluxo de ativação sináptica de ponta a ponta sobre grafos acíclicos dirigidos.
    Inicializa o EpistemicEventStore, o Tálamo Sensorial, os 5 Especialistas e o Árbitro de Convergência.
    """

    def __init__(
        self,
        event_store: Optional[EpistemicEventStore] = None,
        db_path: str = ":memory:",
        jsonl_path: Optional[str] = None,
    ) -> None:
        self.event_store = (
            event_store
            if event_store is not None
            else EpistemicEventStore(db_path=db_path, jsonl_path=jsonl_path)
        )
        self.sensory_neuron = SensoryInputNeuron(event_store=self.event_store)
        self.convergence_neuron = ConvergenceSynthesisNeuron(event_store=self.event_store)

        self.specialist_neurons: Dict[str, CognitiveNeuron] = {}
        self._register_default_specialists()

    def _register_default_specialists(self) -> None:
        """Registra os 5 Neurônios Especialistas Compostos Canônicos."""
        specialists = [
            ("neuron_logic_math", "Lógica Formal & Matemática"),
            ("neuron_systems_engineering", "Engenharia de Software & Sistemas"),
            ("neuron_strategy_risk", "Planejamento & Gestão de Riscos"),
            ("neuron_epistemic_facts", "Auditoria Factual & Proveniência"),
            ("neuron_semantics_didactics", "Semântica & Síntese Conceitual"),
        ]
        for nid, spec in specialists:
            self.specialist_neurons[nid] = CognitiveNeuron(
                neuron_id=nid,
                specialty=spec,
                event_store=self.event_store,
            )

    def register_neuron(self, neuron_id: str, neuron: Any) -> None:
        """Registra ou substitui um neurônio especialista no córtex."""
        self.specialist_neurons[neuron_id] = neuron

    def get_neuron(self, neuron_id: str) -> Optional[Any]:
        """Recupera um neurônio especialista pelo ID."""
        return self.specialist_neurons.get(neuron_id)

    def execute_dag(self, dag: ExecutionDAG) -> CortexExecutionResult:
        """
        Executa onda por onda topológica do DAG compilado.
        Passa resultados verificados dos nós pais para os nós filhos através dos sinais sinápticos.
        Coleta certificados e consolida a execução no ConvergenceSynthesisNeuron.
        """
        start_time = time.perf_counter()
        generations = dag.topological_generations()

        collected_certificates: Dict[str, NeuronCertificate] = {}
        node_outputs: Dict[str, Any] = {}

        abort_early = False

        for wave in generations:
            if abort_early:
                break

            for node in wave:
                # 1. Recupera o neurônio especialista correspondente
                neuron = self.specialist_neurons.get(node.target_neuron_id)
                if neuron is None:
                    # Registra falha de neurônio não registrado
                    cert = NeuronCertificate(
                        neuron_id=node.target_neuron_id,
                        signal_id=new_id("sig_err"),
                        status=VerdictStatus.EPISTEMIC_FAILURE,
                        total_iterations=0,
                        final_hypothesis=None,
                        verifier_reports=[],
                        head_event_id="",
                        confidence_score=0.0,
                        execution_time_ms=0.0,
                    )
                    collected_certificates[node.node_id] = cert
                    abort_early = True
                    break

                # 2. Consolida saídas dos nós pais (dependências)
                parent_context: Dict[str, Any] = {}
                for dep_id in node.dependencies:
                    if dep_id in node_outputs:
                        parent_context[dep_id] = node_outputs[dep_id]

                # 3. Constrói o sinal sináptico estritamente tipado
                signal_input = dict(node.input_data)
                if parent_context:
                    signal_input["parent_results"] = parent_context

                head = self.event_store.get_branch_head("main")
                parent_event_id = head.event_id if head else None

                signal = SynapticSignal(
                    source_neuron="cortex_orchestrator",
                    target_neuron=node.target_neuron_id,
                    task_intent=node.task_intent,
                    axioms=list(node.axioms),
                    constraints=list(node.constraints),
                    input_data=signal_input,
                    parent_event_id=parent_event_id,
                )

                # 4. Despacha o sinal para o neurônio especialista
                if hasattr(neuron, "process_signal"):
                    cert = neuron.process_signal(signal)
                elif hasattr(neuron, "receive_signal"):
                    cert = neuron.receive_signal(signal)
                elif callable(neuron):
                    cert = neuron(signal)
                else:
                    raise TypeError(f"Neurônio '{node.target_neuron_id}' não possui método de despacho suportado.")

                collected_certificates[node.node_id] = cert

                # Guarda a saída estruturada do nó para os nós filhos
                if cert.final_hypothesis:
                    node_outputs[node.node_id] = {
                        "hypothesis_id": cert.final_hypothesis.hypothesis_id,
                        "description": cert.final_hypothesis.description,
                        "claims": [c.to_dict() for c in cert.final_hypothesis.claims],
                        "code_artifact": cert.final_hypothesis.code_artifact,
                        "metadata": cert.final_hypothesis.metadata,
                    }
                else:
                    node_outputs[node.node_id] = {"status": cert.status.value}

                # Se falha epistêmica grave ocorrer, pode abortar o DAG
                if cert.status == VerdictStatus.EPISTEMIC_FAILURE:
                    abort_early = True
                    break

        # 5. Consolidação de Convergência Global
        return self.convergence_neuron.synthesize(
            dag=dag,
            certificates=collected_certificates,
            start_time=start_time,
        )

    def process(
        self,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
        custom_nodes: Optional[List[DAGTaskNode]] = None,
    ) -> CortexExecutionResult:
        """
        Ponto de entrada de alto nível:
        1. Compila o DAG sensorial via SensoryInputNeuron.
        2. Executa a orquestração causal completa.
        3. Retorna o CortexExecutionResult consolidado e certificado.
        """
        dag = self.sensory_neuron.compile_plan(objective=objective, nodes=custom_nodes, context=context)
        return self.execute_dag(dag)
