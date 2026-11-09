"""
Suíte de Testes Formais do Córtex Global em Grafo (DAG) e do Painel Telemétrico.
Valida:
1. DAGTaskNode e ExecutionDAG: Ordenação topológica de Kahn determinística em ondas paralelas.
2. Detecção estrita de ciclos no ExecutionDAG (ValueError: Cycle detected in ExecutionDAG).
3. SensoryInputNeuron: Compilação de plano e persistência do evento DAG_COMPILED.
4. ConvergenceSynthesisNeuron: Invariantes globais, verificação criptográfica de certificados e aborto.
5. FractalCognitiveCortex: Execução end-to-end com os 5 especialistas e passagem causal de contexto.
6. generate_telemetry_dashboard: Geração do dashboard HTML autônomo com métricas, grafo e caos.
"""

from __future__ import annotations
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cerebro_cognitivo.core.cortex import (
    ConvergenceSynthesisNeuron,
    CortexExecutionResult,
    DAGTaskNode,
    ExecutionDAG,
    FractalCognitiveCortex,
    SensoryInputNeuron,
)
from cerebro_cognitivo.core.event_store import EpistemicEventStore
from cerebro_cognitivo.core.schemas import (
    HypothesisPayload,
    NeuronCertificate,
    VerdictStatus,
    VerifierReport,
    compute_sha256,
)
from cerebro_cognitivo.dashboard.inspector_generator import generate_telemetry_dashboard


class TestExecutionDAGAndKahn(unittest.TestCase):
    """Testes formais do Algoritmo de Kahn e estrutura do DAG."""

    def test_01_linear_topological_generations(self) -> None:
        """Valida ordenação linear de tarefas dependentes sequenciais."""
        dag = ExecutionDAG()
        dag.add_node(DAGTaskNode("n1", "target_1", "Step 1"))
        dag.add_node(DAGTaskNode("n2", "target_2", "Step 2", dependencies=["n1"]))
        dag.add_node(DAGTaskNode("n3", "target_3", "Step 3", dependencies=["n2"]))

        generations = dag.topological_generations()
        self.assertEqual(len(generations), 3)
        self.assertEqual([n.node_id for n in generations[0]], ["n1"])
        self.assertEqual([n.node_id for n in generations[1]], ["n2"])
        self.assertEqual([n.node_id for n in generations[2]], ["n3"])

    def test_02_parallel_wave_generations_deterministic(self) -> None:
        """Valida agrupamento de nós independentes na mesma onda com ordenação determinística."""
        dag = ExecutionDAG()
        # n_root inicia
        dag.add_node(DAGTaskNode("n_root", "target", "Start"))
        # n_b e n_a dependem de n_root e podem rodar em paralelo
        dag.add_node(DAGTaskNode("n_b", "target", "Branch B", dependencies=["n_root"]))
        dag.add_node(DAGTaskNode("n_a", "target", "Branch A", dependencies=["n_root"]))
        # n_join depende de ambos
        dag.add_node(DAGTaskNode("n_join", "target", "Join", dependencies=["n_a", "n_b"]))

        generations = dag.topological_generations()
        self.assertEqual(len(generations), 3)
        self.assertEqual([n.node_id for n in generations[0]], ["n_root"])
        # Determinismo lexicográfico: n_a vem antes de n_b
        self.assertEqual([n.node_id for n in generations[1]], ["n_a", "n_b"])
        self.assertEqual([n.node_id for n in generations[2]], ["n_join"])

    def test_03_cycle_detection_raises_value_error(self) -> None:
        """Valida que qualquer ciclo causal levanta ValueError('Cycle detected in ExecutionDAG')."""
        # Ciclo simples A <-> B
        dag = ExecutionDAG()
        dag.add_node(DAGTaskNode("A", "target", "Intent A", dependencies=["B"]))
        dag.add_node(DAGTaskNode("B", "target", "Intent B", dependencies=["A"]))

        with self.assertRaises(ValueError) as ctx:
            dag.topological_generations()
        self.assertIn("Cycle detected in ExecutionDAG", str(ctx.exception))

        # Ciclo triangular com precursor válido
        dag_tri = ExecutionDAG()
        dag_tri.add_node(DAGTaskNode("root", "target", "Root"))
        dag_tri.add_node(DAGTaskNode("X", "target", "X", dependencies=["root", "Z"]))
        dag_tri.add_node(DAGTaskNode("Y", "target", "Y", dependencies=["X"]))
        dag_tri.add_node(DAGTaskNode("Z", "target", "Z", dependencies=["Y"]))

        with self.assertRaises(ValueError) as ctx2:
            dag_tri.topological_generations()
        self.assertIn("Cycle detected in ExecutionDAG", str(ctx2.exception))

    def test_04_missing_dependency_raises_value_error(self) -> None:
        """Valida que dependências inexistentes são identificadas imediatamente."""
        dag = ExecutionDAG()
        dag.add_node(DAGTaskNode("A", "target", "Task A", dependencies=["phantom_node"]))

        with self.assertRaises(ValueError) as ctx:
            dag.topological_generations()
        self.assertIn("phantom_node", str(ctx.exception))


class TestSensoryAndConvergenceNeurons(unittest.TestCase):
    """Testes dos Neurônios Tálamo e Convergência."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_cortex_")
        self.db_path = os.path.join(self.temp_dir, "test_events.db")
        self.store = EpistemicEventStore(db_path=self.db_path)

    def tearDown(self) -> None:
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_05_sensory_input_neuron_compilation(self) -> None:
        """Valida compilação do plano pelo SensoryInputNeuron e gravação de DAG_COMPILED."""
        sensory = SensoryInputNeuron(event_store=self.store)
        dag = sensory.compile_plan(objective="Auditar e otimizar motor criptográfico")

        self.assertEqual(len(dag.nodes), 5)
        # Verifica se o evento foi gravado no banco de eventos
        events = self.store.get_all_events()
        dag_events = [e for e in events if e.event_type == "DAG_COMPILED"]
        self.assertEqual(len(dag_events), 1)
        self.assertEqual(dag_events[0].neuron_id, "neuron_sensory_input")
        self.assertEqual(dag_events[0].verdict, "APPROVED")

    def test_06_convergence_neuron_approved_and_tamper_detection(self) -> None:
        """Valida aprovação de síntese e detecção imediata de certificados adulterados."""
        convergence = ConvergenceSynthesisNeuron(event_store=self.store)
        dag = ExecutionDAG()
        dag.add_node(DAGTaskNode("task_1", "neuron_logic_math", "Calculo"))

        hyp = HypothesisPayload(description="Solucao formal provada")
        cert = NeuronCertificate(
            neuron_id="neuron_logic_math",
            signal_id="sig_test_1",
            status=VerdictStatus.APPROVED,
            total_iterations=1,
            final_hypothesis=hyp,
            verifier_reports=[],
            head_event_id="evt_head_1",
            confidence_score=0.99,
            execution_time_ms=5.0,
        )

        # 1. Execução normal e íntegra
        res = convergence.synthesize(dag, {"task_1": cert})
        self.assertEqual(res.status, VerdictStatus.APPROVED)
        self.assertTrue(res.integrity_verified)

        # 2. Adulteração do hash do certificado
        forged_cert = NeuronCertificate(
            neuron_id=cert.neuron_id,
            signal_id=cert.signal_id,
            status=cert.status,
            total_iterations=cert.total_iterations,
            final_hypothesis=cert.final_hypothesis,
            verifier_reports=cert.verifier_reports,
            head_event_id=cert.head_event_id,
            confidence_score=cert.confidence_score,
            execution_time_ms=cert.execution_time_ms,
            certificate_id=cert.certificate_id,
            timestamp_utc=cert.timestamp_utc,
            certificate_hash="sha256:corrupted_forged_signature_attack",
        )
        res_tampered = convergence.synthesize(dag, {"task_1": forged_cert})
        self.assertEqual(res_tampered.status, VerdictStatus.EPISTEMIC_FAILURE)
        self.assertFalse(res_tampered.integrity_verified)
        self.assertTrue(any("integridade criptográfica" in err for err in res_tampered.errors))


class TestFractalCognitiveCortexAndDashboard(unittest.TestCase):
    """Testes de ponta a ponta do Córtex Global e do Gerador de Telemetria."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_cortex_e2e_")
        self.db_path = os.path.join(self.temp_dir, "cortex_events.db")
        self.dashboard_path = os.path.join(self.temp_dir, "inspector.html")
        self.cortex = FractalCognitiveCortex(db_path=self.db_path)

    def tearDown(self) -> None:
        self.cortex.event_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_07_end_to_end_cortex_execution(self) -> None:
        """Executa fluxo completo pelos 5 neurônios especialistas e valida invariantes."""
        # Todos os 5 especialistas devem estar registrados
        self.assertIn("neuron_logic_math", self.cortex.specialist_neurons)
        self.assertIn("neuron_systems_engineering", self.cortex.specialist_neurons)
        self.assertIn("neuron_strategy_risk", self.cortex.specialist_neurons)
        self.assertIn("neuron_epistemic_facts", self.cortex.specialist_neurons)
        self.assertIn("neuron_semantics_didactics", self.cortex.specialist_neurons)

        result = self.cortex.process("Implementar e auditar algoritmo criptográfico de chave pública")
        self.assertEqual(result.status, VerdictStatus.APPROVED)
        self.assertEqual(result.total_nodes, 5)
        self.assertEqual(result.executed_nodes, 5)
        self.assertTrue(result.integrity_verified)

        # Valida integridade absoluta da cadeia de eventos no banco
        is_valid, violations = self.cortex.event_store.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertEqual(violations, [])

    def test_08_generate_telemetry_dashboard_html(self) -> None:
        """Valida que o dashboard HTML executivo autônomo é gerado com todas as seções."""
        self.cortex.process("Auditoria de segurança e resiliência a caos")
        dag_summary = self.cortex.event_store.export_dag_summary()

        bench_results = {
            "containment_rate": 1.0,
            "total_chaos_tests": 5,
            "passed_chaos_tests": 5,
        }

        generated_file = generate_telemetry_dashboard(
            dag_summary=dag_summary,
            benchmark_results=bench_results,
            output_html_path=self.dashboard_path,
        )

        self.assertTrue(os.path.exists(generated_file))
        self.assertGreater(os.path.getsize(generated_file), 10000)

        with open(generated_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Valida seções obrigatórias
        self.assertIn("SHA-256 100% VERIFIED", content)
        self.assertIn("Total de Eventos no Event Store", content)
        self.assertIn("Taxa de Contenção de Alucinações / Caos", content)
        self.assertIn("Grafo Causal da Linha do Tempo", content)
        self.assertIn("Tabela de Auditoria Forense", content)
        self.assertIn("Relatório de Engenharia de Caos", content)
        self.assertIn("Alucinação sem Lastro Epistêmico", content)
        self.assertIn("Bug de Sintaxe e Exceção de Runtime", content)
        self.assertIn("Bug Sutil de Caso de Borda", content)
        self.assertIn("Tentativa de Loop Infinito e Exaustão", content)
        self.assertIn("Ataque de Adulteração Direta no SQLite", content)
        self.assertIn("mermaid", content)


if __name__ == "__main__":
    unittest.main()
