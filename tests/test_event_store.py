"""
Suíte de Testes Formais do EpistemicEventStore.
Valida:
1. Imutabilidade absoluta via triggers SQLite (Append-Only).
2. Encadeamento criptográfico (Hash Chain e Merkle-DAG).
3. Persistência híbrida SQLite (WAL) e JSON Lines.
4. Auditoria forense anti-adulteração e detecção de corrupção via Chaos Test.
5. Time-Travel Debugging (fold/reduce de estado) e Rollback Causal com branching.
6. Exportação de topologia do DAG.
"""

import json
import os
import shutil
import sqlite3
import tempfile
import unittest

from cerebro_cognitivo.core import EpistemicEventStore, VerdictStatus


class TestEpistemicEventStore(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_epistemic_store_")
        self.db_path = os.path.join(self.temp_dir, "events.db")
        self.jsonl_path = os.path.join(self.temp_dir, "events.jsonl")
        self.store = EpistemicEventStore(db_path=self.db_path, jsonl_path=self.jsonl_path)

    def tearDown(self) -> None:
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_genesis_and_hash_chain(self) -> None:
        """Testa o bloco gênese e o encadeamento estrito de SHA-256 entre eventos."""
        e1 = self.store.record_event(
            neuron_id="neuron_architect",
            subagent_role="genesis_planner",
            event_type="TASK_INITIALIZED",
            epistemic_state={"axioms": ["zero_hallucination", "pure_causality"]},
            delta_changes={"system_status": "BOOTED"},
            verdict="APPROVED",
            confidence_score=1.0,
            cycle_iteration=1,
            branch_id="main",
        )

        self.assertEqual(e1.previous_event_hash, "GENESIS_BLOCK")
        self.assertTrue(e1.content_hash.startswith("sha256:"))
        self.assertIsNone(e1.parent_event_id)
        self.assertTrue(e1.verify_integrity())

        # Segundo evento encadeado
        e2 = self.store.record_event(
            neuron_id="neuron_code_engineer",
            subagent_role="hypothesis_generator",
            event_type="HYPOTHESIS_FORMULATED",
            epistemic_state={"hypothesis": "Implement SHA-256 DAG"},
            delta_changes={"code_written": True, "state_mutations": {"phase": "coding"}},
            verdict="APPROVED",
            confidence_score=0.98,
            cycle_iteration=1,
            branch_id="main",
        )

        self.assertEqual(e2.previous_event_hash, e1.content_hash)
        self.assertEqual(e2.parent_event_id, e1.event_id)
        self.assertTrue(e2.verify_integrity())

        # Terceiro evento
        e3 = self.store.record_event(
            neuron_id="neuron_verifier",
            subagent_role="level_2_grounding",
            event_type="SANDBOX_VERIFICATION",
            epistemic_state={"sandbox_exit_code": 0},
            delta_changes={"tests_passed": 15, "state_mutations": {"status": "verified"}},
            verdict=VerdictStatus.APPROVED.value,
            confidence_score=0.999,
            cycle_iteration=1,
            branch_id="main",
        )

        self.assertEqual(e3.previous_event_hash, e2.content_hash)
        self.assertEqual(e3.parent_event_id, e2.event_id)
        self.assertTrue(e3.verify_integrity())

        # Integridade global da cadeia
        is_valid, violations = self.store.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertEqual(violations, [])

    def test_02_database_immutability_triggers(self) -> None:
        """Garante que instruções UPDATE ou DELETE são bloqueadas violentamente pelo SQLite."""
        e1 = self.store.record_event(
            neuron_id="neuron_alpha",
            subagent_role="worker",
            event_type="STEP_1",
            epistemic_state={"data": 123},
            delta_changes={},
            verdict="APPROVED",
            confidence_score=1.0,
        )

        # Tentativa criminosa de UPDATE
        with self.assertRaises(sqlite3.DatabaseError) as cm_upd:
            cur = self.store._conn.cursor()
            cur.execute(
                "UPDATE epistemic_events SET verdict = 'HACKED' WHERE event_id = ?;",
                (e1.event_id,),
            )
        self.assertIn("Epistemic Immutability Violation", str(cm_upd.exception))

        # Tentativa criminosa de DELETE
        with self.assertRaises(sqlite3.DatabaseError) as cm_del:
            cur = self.store._conn.cursor()
            cur.execute(
                "DELETE FROM epistemic_events WHERE event_id = ?;",
                (e1.event_id,),
            )
        self.assertIn("Epistemic Immutability Violation", str(cm_del.exception))

    def test_03_jsonl_streaming_persistence(self) -> None:
        """Testa se o arquivo .jsonl reflete com fidelidade todos os eventos inseridos."""
        self.store.record_event(
            neuron_id="neuron_streamer",
            subagent_role="logger",
            event_type="STREAM_TEST",
            epistemic_state={"stream": True},
            delta_changes={"seq": 1},
            verdict="APPROVED",
            confidence_score=0.95,
        )

        self.assertTrue(os.path.exists(self.jsonl_path))
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["neuron_id"], "neuron_streamer")
        self.assertTrue(data["content_hash"].startswith("sha256:"))

    def test_04_chaos_engineering_tamper_detection(self) -> None:
        """
        Executa teste destrutivo de Engenharia de Caos:
        Adultera uma linha com _unsafe_tamper_for_chaos_test e valida se verify_chain_integrity()
        detecta imediatamente a quebra do hash canônico.
        """
        e1 = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="E1",
            epistemic_state={"secret": "original_payload"}, delta_changes={},
            verdict="APPROVED", confidence_score=1.0,
        )
        e2 = self.store.record_event(
            neuron_id="n2", subagent_role="r2", event_type="E2",
            epistemic_state={"status": "all_good"}, delta_changes={},
            verdict="APPROVED", confidence_score=1.0,
        )

        # Antes do ataque: 100% íntegro
        valid, violations = self.store.verify_chain_integrity()
        self.assertTrue(valid)
        self.assertEqual(len(violations), 0)

        # Injeção Maliciosa via método de Caos
        corrupted_state = json.dumps({"secret": "TAMPERED_BY_ATTACKER_OR_BIT_FLIP"})
        self.store._unsafe_tamper_for_chaos_test(e1.event_id, corrupted_state)

        # Auditoria pós-ataque
        valid, violations = self.store.verify_chain_integrity()
        self.assertFalse(valid)
        self.assertGreaterEqual(len(violations), 1)
        # Deve ter detectado que o content_hash recalculado divergiu do registrado
        self.assertTrue(any("Adulteração de dados detectada" in v for v in violations))

    def test_05_time_travel_checkout_state(self) -> None:
        """Valida a reconstrução temporal exata do cérebro via fold/reduce causal."""
        # T0: Estado Inicial
        e0 = self.store.record_event(
            neuron_id="arbiter", subagent_role="genesis", event_type="INIT",
            epistemic_state={"config": {"timeout": 30, "env": "prod"}, "axioms": ["A1"]},
            delta_changes={"boot": True},
            verdict="APPROVED", confidence_score=1.0,
        )

        # T1: Primeira mutação
        e1 = self.store.record_event(
            neuron_id="worker", subagent_role="mutator", event_type="STEP_1",
            epistemic_state={},
            delta_changes={
                "files_written": ["/app/config.yaml"],
                "state_mutations": {"config": {"timeout": 60}, "system_load": 0.42},
            },
            verdict="APPROVED", confidence_score=0.9,
        )

        # T2: Segunda mutação
        e2 = self.store.record_event(
            neuron_id="worker", subagent_role="mutator", event_type="STEP_2",
            epistemic_state={},
            delta_changes={
                "state_mutations": {"system_load": 0.88, "status": "processing"},
            },
            verdict="APPROVED", confidence_score=0.85,
        )

        # Checkout em T0
        state_t0 = self.store.checkout_state(e0.event_id)
        self.assertEqual(state_t0["config"]["timeout"], 30)
        self.assertEqual(state_t0["boot"], True)
        self.assertNotIn("files_written", state_t0)
        self.assertNotIn("system_load", state_t0)

        # Checkout em T1
        state_t1 = self.store.checkout_state(e1.event_id)
        self.assertEqual(state_t1["config"]["timeout"], 60)
        self.assertEqual(state_t1["config"]["env"], "prod")
        self.assertEqual(state_t1["system_load"], 0.42)
        self.assertEqual(state_t1["files_written"], ["/app/config.yaml"])
        self.assertNotIn("status", state_t1)

        # Checkout em T2
        state_t2 = self.store.checkout_state(e2.event_id)
        self.assertEqual(state_t2["system_load"], 0.88)
        self.assertEqual(state_t2["status"], "processing")
        self.assertEqual(state_t2["config"]["timeout"], 60)

    def test_06_causal_rollback_and_branching(self) -> None:
        """Testa o rollback causal em um DAG bifurcado com time-travel branching."""
        # Cria trajetória principal: E1 -> E2 -> E3_FAIL
        e1 = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="PLAN",
            epistemic_state={"step": 1}, delta_changes={"data": "base"},
            verdict="APPROVED", confidence_score=1.0, branch_id="main",
        )
        e2 = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="EXEC_V1",
            epistemic_state={"step": 2}, delta_changes={"data": "good_progress"},
            verdict="APPROVED", confidence_score=0.95, branch_id="main",
        )
        e3_fail = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="EXEC_FAIL",
            epistemic_state={"step": 3, "error": "NullPointerException"},
            delta_changes={"data": "corrupted"},
            verdict="REJECTED_LOGIC", confidence_score=0.1, branch_id="main",
        )

        # Rollback Causal para E2 gerando a branch 'recovery_branch'
        rollback_event = self.store.branch_from(
            target_event_id=e2.event_id,
            new_branch_id="recovery_branch",
            reason="Erro lógico em E3: Rollback para E2 para nova estratégia",
            neuron_id="arbiter_supreme",
        )

        self.assertEqual(rollback_event.branch_id, "recovery_branch")
        self.assertEqual(rollback_event.event_type, "CAUSAL_ROLLBACK")
        self.assertEqual(rollback_event.parent_event_id, e2.event_id)
        self.assertEqual(rollback_event.epistemic_state["data"], "good_progress")

        # Continua execução na nova branch
        e4_repaired = self.store.record_event(
            neuron_id="n2", subagent_role="fixer", event_type="EXEC_CORRECTED",
            epistemic_state={"step": 4, "fix_applied": True},
            delta_changes={"data": "perfect_fix"},
            verdict="APPROVED", confidence_score=1.0, branch_id="recovery_branch",
        )

        self.assertEqual(e4_repaired.parent_event_id, rollback_event.event_id)

        # Testa linhagem causal da recovery_branch: [E1, E2, Rollback, E4]
        lineage_recovery = self.store.get_causal_lineage(e4_repaired.event_id)
        lineage_ids = [evt.event_id for evt in lineage_recovery]
        self.assertEqual(lineage_ids, [e1.event_id, e2.event_id, rollback_event.event_id, e4_repaired.event_id])
        self.assertNotIn(e3_fail.event_id, lineage_ids)

        # Testa linhagem da main antiga: [E1, E2, E3_FAIL]
        lineage_main = self.store.get_causal_lineage(e3_fail.event_id)
        self.assertEqual([evt.event_id for evt in lineage_main], [e1.event_id, e2.event_id, e3_fail.event_id])

    def test_07_export_dag_summary(self) -> None:
        """Testa o resumo consolidado do grafo DAG."""
        e1 = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="GENESIS",
            epistemic_state={}, delta_changes={}, verdict="APPROVED", confidence_score=1.0,
        )
        e2 = self.store.record_event(
            neuron_id="n1", subagent_role="r1", event_type="STEP",
            epistemic_state={}, delta_changes={}, verdict="APPROVED", confidence_score=1.0,
        )
        self.store.branch_from(
            target_event_id=e1.event_id,
            new_branch_id="alt_branch",
            reason="Explorar caminho alternativo",
        )

        summary = self.store.export_dag_summary()
        self.assertEqual(summary["total_events"], 3)
        self.assertEqual(summary["total_rollbacks"], 1)
        self.assertEqual(summary["chain_integrity_valid"], True)
        self.assertIn("main", summary["active_branches"])
        self.assertIn("alt_branch", summary["active_branches"])
        self.assertEqual(len(summary["dag_nodes"]), 3)
        # E1 é raiz (parent is None). E2 e Rollback têm parent. Logo, 2 edges.
        self.assertEqual(len(summary["dag_edges"]), 2)

    def test_08_reopen_from_disk_persistence(self) -> None:
        """Testa reabertura do arquivo SQLite em uma nova instância do repositório."""
        e1 = self.store.record_event(
            neuron_id="persister", subagent_role="writer", event_type="INIT",
            epistemic_state={"key": "saved_to_disk"}, delta_changes={},
            verdict="APPROVED", confidence_score=1.0,
        )
        self.store.close()

        # Reabre em uma nova instância conectada ao mesmo arquivo
        store2 = EpistemicEventStore(db_path=self.db_path, jsonl_path=self.jsonl_path)
        try:
            e1_reloaded = store2.get_event(e1.event_id)
            self.assertIsNotNone(e1_reloaded)
            self.assertEqual(e1_reloaded.content_hash, e1.content_hash)
            self.assertEqual(e1_reloaded.epistemic_state["key"], "saved_to_disk")

            # Grava novo evento na instância reaberta
            e2 = store2.record_event(
                neuron_id="persister", subagent_role="writer", event_type="STEP_2",
                epistemic_state={"key": "step2"}, delta_changes={},
                verdict="APPROVED", confidence_score=1.0,
            )
            self.assertEqual(e2.previous_event_hash, e1.content_hash)

            valid, violations = store2.verify_chain_integrity()
            self.assertTrue(valid)
            self.assertEqual(len(violations), 0)
        finally:
            store2.close()

    def test_09_deep_lineage_and_context_manager(self) -> None:
        """Testa linhagem profunda de 50 eventos sequenciais e uso com Context Manager."""
        mem_db = os.path.join(self.temp_dir, "deep_lineage.db")
        with EpistemicEventStore(db_path=mem_db) as deep_store:
            prev_id = None
            for i in range(50):
                evt = deep_store.record_event(
                    neuron_id=f"neuron_{i % 5}",
                    subagent_role="deep_chainer",
                    event_type="RECURSIVE_STEP",
                    epistemic_state={"counter": i},
                    delta_changes={"accumulated": i * 10},
                    verdict="APPROVED",
                    confidence_score=0.99,
                    cycle_iteration=i + 1,
                )
                if prev_id is not None:
                    self.assertEqual(evt.parent_event_id, prev_id)
                prev_id = evt.event_id

            self.assertEqual(deep_store.count_events(), 50)
            lineage = deep_store.get_causal_lineage(prev_id)
            self.assertEqual(len(lineage), 50)

            valid, violations = deep_store.verify_chain_integrity()
            self.assertTrue(valid)
            self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
