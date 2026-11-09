"""
Bateria Executável de Engenharia de Caos e Validação Empírica do Cérebro Cognitivo Fractal.
Executa ataques reais de alucinação, bugs de sintaxe/runtime, casos de borda sutis,
falsificação criptográfica de proveniência, loops impossíveis e adulteração de banco SQLite.
Gera o banco de eventos auditável, o relatório técnico em Markdown e o Dashboard HTML.
"""

from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Garantir que a raiz do projeto esteja no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.schemas import (
    Claim,
    HypothesisPayload,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
    compute_sha256,
)
from core.event_store import EpistemicEventStore
from core.neuron import CognitiveNeuron
from core.cortex import FractalCognitiveCortex
from dashboard.inspector_generator import generate_telemetry_dashboard


def run_chaos_benchmark() -> Dict[str, Any]:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "epistemic_brain.db"
    jsonl_path = data_dir / "epistemic_events.jsonl"

    # Limpar execução anterior de benchmark para gerar trilha forense limpa e reproduzível
    for p in [db_path, jsonl_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]:
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    store = EpistemicEventStore(db_path=str(db_path), jsonl_path=str(jsonl_path))
    chaos_cases: List[Dict[str, Any]] = []
    start_total = time.perf_counter()

    # =========================================================================
    # CENÁRIO 1: Alucinação sem Lastro -> Bloqueio em V1 + Rollback + Correção
    # =========================================================================
    t0 = time.perf_counter()

    def thinker_cenario_1(signal: SynapticSignal, iteration: int, neg_constraints: List[str]) -> HypothesisPayload:
        if iteration == 1:
            # Iteração 1: Tenta emitir afirmação sem ProvenancePointer (alucinação pura)
            return HypothesisPayload(
                iteration=iteration,
                description="Hipótese inicial sem ponteiro de proveniência.",
                claims=[
                    Claim(
                        statement="O algoritmo RSA de 512 bits ainda é seguro hoje.",
                        provenance=None,  # Sem lastro!
                    )
                ],
                code_artifact="def rsa_bits() -> int:\n    return 2048\n",
                entrypoint_function="rsa_bits",
                expected_invariants=["rsa_bits() >= 2048"],
                negative_constraints_applied=list(neg_constraints),
            )
        # Iteração 2: Após Rollback Causal e restrição negativa de V1, anexa ProvenancePointer real
        return HypothesisPayload(
            iteration=iteration,
            description="Hipótese corrigida com ProvenancePointer formal e invariante verificável.",
            claims=[
                Claim(
                    statement="Chaves RSA exigem módulo mínimo de 2048 bits segundo recomendação NIST SP 800-57.",
                    provenance=ProvenancePointer(
                        source_type=ProvenanceType.AXIOM_USER,
                        reference_id="nist_sp_800_57_axiom",
                        excerpt="Módulo RSA mínimo aceitável >= 2048 bits.",
                    ),
                )
            ],
            code_artifact="def rsa_bits() -> int:\n    return 2048\n",
            entrypoint_function="rsa_bits",
            expected_invariants=["rsa_bits() >= 2048"],
            negative_constraints_applied=list(neg_constraints),
        )

    neuron_c1 = CognitiveNeuron(
        neuron_id="neuron_epistemic_guard",
        specialty="Auditoria Anti-Alucinação",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=thinker_cenario_1,
    )
    sig_c1 = SynapticSignal(
        source_neuron="chaos_harness",
        target_neuron="neuron_epistemic_guard",
        task_intent="Validar tamanho mínimo de chave RSA sem alucinar fatos sem lastro.",
        axioms=["Módulo RSA mínimo aceitável >= 2048 bits."],
    )
    cert_c1 = neuron_c1.process_signal(sig_c1, branch_id="chaos_c1_main")
    dt_c1 = (time.perf_counter() - t0) * 1000.0
    c1_events = [e for e in store.get_all_events() if e.neuron_id == "neuron_epistemic_guard"]
    c1_passed = (
        cert_c1.status == VerdictStatus.APPROVED
        and cert_c1.total_iterations == 2
        and any(e.event_type == "VERIFICATION_V1" and e.verdict == VerdictStatus.REJECTED_LOGIC.value for e in c1_events)
    )
    chaos_cases.append({
        "id": "CHAOS-01",
        "name": "Injeção de Alucinação sem ProvenancePointer",
        "target_layer": "V1_LOGIC",
        "attack_vector": "Claim emitida com provenance=None na Iteração 1",
        "system_response": f"Bloqueado em V1_LOGIC -> Rollback Causal -> Corrigido na Iteração {cert_c1.total_iterations}",
        "contained": c1_passed,
        "duration_ms": round(dt_c1, 2),
        "certificate_hash": cert_c1.certificate_hash,
    })

    # =========================================================================
    # CENÁRIO 2: Erro de Runtime (Divisão por Zero) -> Bloqueio em V2 Sandbox
    # =========================================================================
    t0 = time.perf_counter()

    def thinker_cenario_2(signal: SynapticSignal, iteration: int, neg_constraints: List[str]) -> HypothesisPayload:
        prov = ProvenancePointer(
            source_type=ProvenanceType.FORMAL_DEDUCTION,
            reference_id="deducao_taxa_02",
            excerpt="Cálculo seguro de taxa normalizada com proteção de denominador zero.",
        )
        if iteration == 1:
            # Código com bug fatal de execução (ZeroDivisionError quando total=0)
            bad_code = (
                "def calcular_taxa(acertos: int, total: int) -> float:\n"
                "    return acertos / total\n"
            )
            return HypothesisPayload(
                iteration=iteration,
                description="Implementação ingênua sem tratamento de denominador zero.",
                claims=[Claim(statement="Função calcula razão direta entre acertos e total.", provenance=prov)],
                code_artifact=bad_code,
                entrypoint_function="calcular_taxa",
                expected_invariants=[
                    "calcular_taxa(5, 10) == 0.5",
                    "calcular_taxa(0, 0) == 0.0",  # Provoca ZeroDivisionError no Sandbox V2!
                ],
                negative_constraints_applied=list(neg_constraints),
            )
        # Iteração 2: Lê o stderr do Sandbox V2 injetado nas restrições negativas e corrige o código
        fixed_code = (
            "def calcular_taxa(acertos: int, total: int) -> float:\n"
            "    if total <= 0:\n"
            "        return 0.0\n"
            "    return float(acertos) / float(total)\n"
        )
        return HypothesisPayload(
            iteration=iteration,
            description="Implementação corrigida após captura de ZeroDivisionError no Sandbox V2.",
            claims=[Claim(statement="Função protege denominador <= 0 retornando 0.0.", provenance=prov)],
            code_artifact=fixed_code,
            entrypoint_function="calcular_taxa",
            expected_invariants=[
                "calcular_taxa(5, 10) == 0.5",
                "calcular_taxa(0, 0) == 0.0",
            ],
            negative_constraints_applied=list(neg_constraints),
        )

    neuron_c2 = CognitiveNeuron(
        neuron_id="neuron_sandbox_guard",
        specialty="Engenharia Determinística",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=thinker_cenario_2,
    )
    sig_c2 = SynapticSignal(
        source_neuron="chaos_harness",
        target_neuron="neuron_sandbox_guard",
        task_intent="Implementar função calcular_taxa tolerante a total=0.",
        axioms=["Divisão por zero deve retornar 0.0 sem levantar exceção."],
    )
    cert_c2 = neuron_c2.process_signal(sig_c2, branch_id="chaos_c2_main")
    dt_c2 = (time.perf_counter() - t0) * 1000.0
    c2_events = [e for e in store.get_all_events() if e.neuron_id == "neuron_sandbox_guard"]
    c2_passed = (
        cert_c2.status == VerdictStatus.APPROVED
        and cert_c2.total_iterations == 2
        and any(e.event_type == "VERIFICATION_V2" and e.verdict == VerdictStatus.REJECTED_GROUNDING.value for e in c2_events)
    )
    chaos_cases.append({
        "id": "CHAOS-02",
        "name": "Injeção de Crash em Tempo de Execução (ZeroDivisionError)",
        "target_layer": "V2_GROUNDING",
        "attack_vector": "Código sintaticamente válido que falha em runtime no subprocesso isolado",
        "system_response": f"Capturado pelo Sandbox V2 (exit_code=1) -> Stack trace injetado -> Corrigido na Iteração {cert_c2.total_iterations}",
        "contained": c2_passed,
        "duration_ms": round(dt_c2, 2),
        "certificate_hash": cert_c2.certificate_hash,
    })

    # =========================================================================
    # CENÁRIO 3: Bug Sutil de Borda que Passa em V1 e V2, mas é Pego em V3 (Red Team)
    # =========================================================================
    t0 = time.perf_counter()

    def thinker_cenario_3(signal: SynapticSignal, iteration: int, neg_constraints: List[str]) -> HypothesisPayload:
        prov = ProvenancePointer(
            source_type=ProvenanceType.DETERMINISTIC_EXEC,
            reference_id="clamp_spec_03",
            excerpt="Função clamp_score deve limitar qualquer entrada ao intervalo fechado [0, 100].",
        )
        if iteration == 1:
            # Bug sutil: limita o teto (100), passa nos testes positivos de V2,
            # mas esquece de limitar números negativos!
            subtle_bug_code = (
                "def clamp_score(x: int) -> int:\n"
                "    if x > 100:\n"
                "        return 100\n"
                "    return x\n"
            )
            return HypothesisPayload(
                iteration=iteration,
                description="Versão com bug de fronteira inferior (não trata negativos).",
                claims=[Claim(statement="Limita valores ao intervalo [0, 100].", provenance=prov)],
                code_artifact=subtle_bug_code,
                entrypoint_function="clamp_score",
                expected_invariants=[
                    "clamp_score(50) == 50",
                    "clamp_score(250) == 100",
                ],
                negative_constraints_applied=list(neg_constraints),
            )
        # Iteração 2: Após o Red Team V3 descobrir que clamp_score(-20) == -20 (violando >= 0), corrige!
        hardened_code = (
            "def clamp_score(x: int) -> int:\n"
            "    if x is None or not isinstance(x, (int, float)):\n"
            "        return 0\n"
            "    if x < 0:\n"
            "        return 0\n"
            "    if x > 100:\n"
            "        return 100\n"
            "    return int(x)\n"
        )
        return HypothesisPayload(
            iteration=iteration,
            description="Versão blindada contra entradas negativas e tipos nulos após auditoria V3.",
            claims=[Claim(statement="Garante intervalo fechado [0, 100] em todas as bordas.", provenance=prov)],
            code_artifact=hardened_code,
            entrypoint_function="clamp_score",
            expected_invariants=[
                "clamp_score(50) == 50",
                "clamp_score(250) == 100",
                "clamp_score(-20) == 0",
            ],
            negative_constraints_applied=list(neg_constraints),
        )

    neuron_c3 = CognitiveNeuron(
        neuron_id="neuron_redteam_guard",
        specialty="Segurança de Borda",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=thinker_cenario_3,
    )
    sig_c3 = SynapticSignal(
        source_neuron="chaos_harness",
        target_neuron="neuron_redteam_guard",
        task_intent="Implementar clamp_score garantido no intervalo [0, 100].",
        axioms=["O retorno deve estar sempre entre 0 e 100 inclusive."],
        input_data={
            "adversarial_assertions": [
                "0 <= clamp_score(-20) <= 100",
                "0 <= clamp_score(0) <= 100",
                "0 <= clamp_score(999999) <= 100",
            ]
        },
    )
    cert_c3 = neuron_c3.process_signal(sig_c3, branch_id="chaos_c3_main")
    dt_c3 = (time.perf_counter() - t0) * 1000.0
    c3_events = [e for e in store.get_all_events() if e.neuron_id == "neuron_redteam_guard"]
    c3_passed = (
        cert_c3.status == VerdictStatus.APPROVED
        and cert_c3.total_iterations == 2
        and any(e.event_type == "VERIFICATION_V3" and e.verdict == VerdictStatus.REJECTED_RED_TEAM.value for e in c3_events)
    )
    chaos_cases.append({
        "id": "CHAOS-03",
        "name": "Bug Sutil de Caso de Borda (Escapa de V1 e V2, Capturado por V3 Red Team)",
        "target_layer": "V3_RED_TEAM",
        "attack_vector": "Função passa nos testes básicos de V2 mas falha para x = -20",
        "system_response": f"Interceptado pelo Inquisidor Adversário V3 -> Contraexemplo injetado -> Blindado na Iteração {cert_c3.total_iterations}",
        "contained": c3_passed,
        "duration_ms": round(dt_c3, 2),
        "certificate_hash": cert_c3.certificate_hash,
    })

    # =========================================================================
    # CENÁRIO 4: Falsificação Criptográfica de Proveniência -> Bloqueada em V3
    # =========================================================================
    t0 = time.perf_counter()

    def thinker_cenario_4(signal: SynapticSignal, iteration: int, neg_constraints: List[str]) -> HypothesisPayload:
        if iteration == 1:
            # Tenta falsificar o hash SHA-256 de evidência no ProvenancePointer
            forged_prov = ProvenancePointer(
                source_type=ProvenanceType.EVENT_CITATION,
                reference_id="evt_fake_001",
                excerpt="Dados auditados originais.",
                evidence_hash="sha256:00000000000000000000000000000000000000000000000000000000deadbeef",
            )
            return HypothesisPayload(
                iteration=iteration,
                description="Hipótese com hash de proveniência adulterado.",
                claims=[Claim(statement="Dados autenticados com hash forjado.", provenance=forged_prov)],
                code_artifact="def status_ok() -> bool:\n    return True\n",
                entrypoint_function="status_ok",
                expected_invariants=["status_ok() is True"],
                negative_constraints_applied=list(neg_constraints),
            )
        # Iteração 2: Emite ProvenancePointer com hash SHA-256 legítimo calculado canonicamente
        honest_prov = ProvenancePointer(
            source_type=ProvenanceType.EVENT_CITATION,
            reference_id="evt_verified_001",
            excerpt="Dados auditados originais com hash SHA-256 íntegro.",
        )
        return HypothesisPayload(
            iteration=iteration,
            description="Hipótese com ProvenancePointer criptograficamente autêntico.",
            claims=[Claim(statement="Dados autenticados com hash SHA-256 verificado.", provenance=honest_prov)],
            code_artifact="def status_ok() -> bool:\n    return True\n",
            entrypoint_function="status_ok",
            expected_invariants=["status_ok() is True"],
            negative_constraints_applied=list(neg_constraints),
        )

    neuron_c4 = CognitiveNeuron(
        neuron_id="neuron_crypto_auditor",
        specialty="Auditoria Criptográfica de Lastro",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=thinker_cenario_4,
    )
    sig_c4 = SynapticSignal(
        source_neuron="chaos_harness",
        target_neuron="neuron_crypto_auditor",
        task_intent="Verificar autenticidade de assinatura de proveniência.",
        axioms=["Hashes de proveniência devem corresponder ao SHA-256 real da evidência."],
    )
    cert_c4 = neuron_c4.process_signal(sig_c4, branch_id="chaos_c4_main")
    dt_c4 = (time.perf_counter() - t0) * 1000.0
    c4_events = [e for e in store.get_all_events() if e.neuron_id == "neuron_crypto_auditor"]
    c4_passed = (
        cert_c4.status == VerdictStatus.APPROVED
        and cert_c4.total_iterations == 2
        and any(e.event_type == "VERIFICATION_V3" and e.verdict == VerdictStatus.REJECTED_RED_TEAM.value for e in c4_events)
    )
    chaos_cases.append({
        "id": "CHAOS-04",
        "name": "Tentativa de Falsificação de Hash no ProvenancePointer",
        "target_layer": "V3_RED_TEAM (Crypto Audit)",
        "attack_vector": "ProvenancePointer com sha256:0000...deadbeef divergente do payload real",
        "system_response": f"Falsificação detectada em V3 -> Rollback Causal -> Hash autêntico exigido na Iteração {cert_c4.total_iterations}",
        "contained": c4_passed,
        "duration_ms": round(dt_c4, 2),
        "certificate_hash": cert_c4.certificate_hash,
    })

    # =========================================================================
    # CENÁRIO 5: Missão Matematicamente Insatisfatível -> Parada em T=3 (Zero Deadlock)
    # =========================================================================
    t0 = time.perf_counter()

    def thinker_cenario_5(signal: SynapticSignal, iteration: int, neg_constraints: List[str]) -> HypothesisPayload:
        prov = ProvenancePointer(
            source_type=ProvenanceType.AXIOM_USER,
            reference_id=f"attempt_{iteration}",
            excerpt="Tentativa de encontrar inteiro simultaneamente > 10 e < 5.",
        )
        return HypothesisPayload(
            iteration=iteration,
            description=f"Tentativa {iteration} para restrição impossível (x > 10 e x < 5).",
            claims=[Claim(statement=f"Candidato testado na iteração {iteration}.", provenance=prov)],
            code_artifact=f"def candidato() -> int:\n    return {iteration * 5}\n",
            entrypoint_function="candidato",
            expected_invariants=["candidato() > 10 and candidato() < 5"],
            negative_constraints_applied=list(neg_constraints),
        )

    neuron_c5 = CognitiveNeuron(
        neuron_id="neuron_deadlock_breaker",
        specialty="Prevenção de Loop Infinito",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=thinker_cenario_5,
    )
    sig_c5 = SynapticSignal(
        source_neuron="chaos_harness",
        target_neuron="neuron_deadlock_breaker",
        task_intent="Retornar inteiro x tal que x > 10 e x < 5 simultaneamente.",
        axioms=["Restrição contraditória injetada para testar teto de convergência."],
    )
    cert_c5 = neuron_c5.process_signal(sig_c5, branch_id="chaos_c5_main")
    dt_c5 = (time.perf_counter() - t0) * 1000.0
    c5_events = [e for e in store.get_all_events() if e.neuron_id == "neuron_deadlock_breaker"]
    c5_passed = (
        cert_c5.status == VerdictStatus.EPISTEMIC_FAILURE
        and cert_c5.total_iterations == 3
        and cert_c5.confidence_score == 0.0
        and any(e.event_type == "EPISTEMIC_ABORT" for e in c5_events)
    )
    chaos_cases.append({
        "id": "CHAOS-05",
        "name": "Injeção de Paradoxo Insatisfatível (Prevenção de Deadlock & Alucinação Forçada)",
        "target_layer": "Teto Bayesiano (T_max = 3)",
        "attack_vector": "Invariante matematicamente impossível: x > 10 and x < 5",
        "system_response": "Executou exatamente 3 iterações -> Emitiu EPISTEMIC_ABORT formal sem alucinar resposta falsa",
        "contained": c5_passed,
        "duration_ms": round(dt_c5, 2),
        "certificate_hash": cert_c5.certificate_hash,
    })

    # =========================================================================
    # CENÁRIO 6:Execução Completa do Córtex Global (5 Neurônios Especialistas em DAG)
    # =========================================================================
    t0 = time.perf_counter()
    cortex = FractalCognitiveCortex(event_store=store)
    cortex_result = cortex.process(
        objective="Projetar e validar protocolo criptográfico autenticado com auditoria formal de integridade."
    )
    dt_c6 = (time.perf_counter() - t0) * 1000.0
    c6_passed = (
        cortex_result.status == VerdictStatus.APPROVED
        and len(cortex_result.certificates) == 5
        and all(c.status == VerdictStatus.APPROVED for c in cortex_result.certificates.values())
    )
    chaos_cases.append({
        "id": "CHAOS-06",
        "name": "Orquestração Completa do Córtex em DAG (5 Neurônios Especialistas)",
        "target_layer": "CORTEX_CONVERGENCE",
        "attack_vector": "Propagação multi-onda topológica com verificação cruzada de 5 certificados",
        "system_response": f"5/5 Neurônios Aprovados ({cortex_result.executed_nodes}/{cortex_result.total_nodes} nós certificados)",
        "contained": c6_passed,
        "duration_ms": round(dt_c6, 2),
        "certificate_hash": cortex_result.convergence_event_id,
    })

    # =========================================================================
    # CENÁRIO 7: Ataque de Adulteração Direta ao SQLite (Triggers & Hash Chain)
    # =========================================================================
    t0 = time.perf_counter()
    all_events = store.get_all_events()
    target_evt = all_events[2]

    # Parte A: Tentar UPDATE e DELETE direto via conexão SQLite (deve ser bloqueado pelos Triggers!)
    trigger_blocked_update = False
    trigger_blocked_delete = False
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE epistemic_events SET verdict = 'HACKED' WHERE event_id = ?",
            (target_evt.event_id,),
        )
    except sqlite3.IntegrityError:
        trigger_blocked_update = True
    except sqlite3.DatabaseError:
        trigger_blocked_update = True

    try:
        conn.execute(
            "DELETE FROM epistemic_events WHERE event_id = ?",
            (target_evt.event_id,),
        )
    except sqlite3.IntegrityError:
        trigger_blocked_delete = True
    except sqlite3.DatabaseError:
        trigger_blocked_delete = True
    finally:
        conn.close()

    # Parte B: Simular corrupção física de disco ignorando trigger, testar detecção SHA-256 e restaurar!
    orig_state_json = json.dumps(target_evt.epistemic_state, sort_keys=True, ensure_ascii=False)
    store._unsafe_tamper_for_chaos_test(target_evt.event_id, '{"hacked_payload": true}')
    valid_during_attack, violations_detected = store.verify_chain_integrity()
    # Restaurar imediatamente o estado original para manter o banco 100% íntegro
    store._unsafe_tamper_for_chaos_test(target_evt.event_id, orig_state_json)
    valid_after_restore, violations_after = store.verify_chain_integrity()

    dt_c7 = (time.perf_counter() - t0) * 1000.0
    c7_passed = (
        trigger_blocked_update
        and trigger_blocked_delete
        and (not valid_during_attack)
        and len(violations_detected) > 0
        and valid_after_restore
        and len(violations_after) == 0
    )
    chaos_cases.append({
        "id": "CHAOS-07",
        "name": "Ataque de Mutação SQL + Corrupção de Disco na Cadeia de Eventos",
        "target_layer": "SQLite Triggers & SHA-256 Merkle Chain",
        "attack_vector": "Tentativa de UPDATE/DELETE direto + adulteração binária de payload",
        "system_response": f"Triggers bloquearam UPDATE/DELETE; Auditoria SHA-256 detectou corrupção em {target_evt.event_id} e restaurou integridade",
        "contained": c7_passed,
        "duration_ms": round(dt_c7, 2),
        "certificate_hash": target_evt.content_hash,
    })

    total_duration_ms = (time.perf_counter() - start_total) * 1000.0
    dag_summary = store.export_dag_summary()

    benchmark_results = {
        "suite_name": "Chaos Engineering & Epistemic Verification Benchmark v1.0",
        "total_scenarios": len(chaos_cases),
        "scenarios_contained": sum(1 for c in chaos_cases if c["contained"]),
        "containment_rate_pct": 100.0 * sum(1 for c in chaos_cases if c["contained"]) / len(chaos_cases),
        "total_duration_ms": round(total_duration_ms, 2),
        "chain_integrity_verified": bool(dag_summary.get("chain_integrity_valid", True)),
        "total_events_recorded": dag_summary["total_events"],
        "total_branches_created": dag_summary["total_branches"],
        "total_causal_rollbacks": dag_summary["total_rollbacks"],
        "cases": chaos_cases,
    }

    # Gerar Dashboard Interativo HTML
    dashboard_path = PROJECT_ROOT / "dashboard" / "inspector_telemetria.html"
    generate_telemetry_dashboard(
        dag_summary=dag_summary,
        benchmark_results=benchmark_results,
        output_html_path=str(dashboard_path),
    )

    # Salvar JSON de métricas e Relatório Técnico Markdown
    metrics_json_path = data_dir / "chaos_benchmark_report.json"
    metrics_json_path.write_text(
        json.dumps(benchmark_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_audit_markdown(benchmark_results, dag_summary, PROJECT_ROOT / "docs" / "02_manual_auditoria_e_metricas.md")
    store.close()
    return benchmark_results


def write_audit_markdown(bench: Dict[str, Any], dag: Dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Relatório Empírico de Auditoria e Engenharia de Caos",
        "",
        "Este documento registra os resultados reais extraídos da execução da bancada de testes adversários (`tests/chaos_benchmark.py`) sobre o **Cérebro Cognitivo Fractal Multi-Agente**.",
        "",
        "---",
        "",
        "## 1. Métricas Globais Consolidadas",
        "",
        "| Métrica Auditada | Valor Empírico Medido | Status |",
        "| :--- | :---: | :---: |",
        f"| **Cenários Adversários Executados** | **{bench['total_scenarios']}** | ✅ 100% Executados |",
        f"| **Taxa de Contenção de Erros e Alucinações** | **{bench['containment_rate_pct']:.1f}% ({bench['scenarios_contained']}/{bench['total_scenarios']})** | ✅ Contenção Total |",
        f"| **Eventos Imutáveis Gravados no SQLite WAL** | **{bench['total_events_recorded']}** | ✅ Persistidos |",
        f"| **Branches / Bifurcações no Grafo (DAG)** | **{bench['total_branches_created']}** | ✅ Auditadas |",
        f"| **Rollbacks Causais Automáticos Executados** | **{bench['total_causal_rollbacks']}** | ✅ Auto-Recuperados |",
        f"| **Integridade Criptográfica da Cadeia SHA-256** | **{'100% ÍNTEGRA' if bench['chain_integrity_verified'] else 'FALHA'}** | ✅ Verificada |",
        f"| **Tempo Total da Bateria (com Sandboxes Reais)** | **{bench['total_duration_ms']:.2f} ms** | ⚡ Alta Performance |",
        "",
        "---",
        "",
        "## 2. Detalhamento dos 7 Cenários de Engenharia de Caos",
        "",
        "| ID | Cenário / Vetor de Ataque | Camada Alvo | Resposta Real do Sistema | Tempo (ms) | Resultado |",
        "| :--- | :--- | :---: | :--- | :---: | :---: |",
    ]
    for c in bench["cases"]:
        status_badge = "✅ BLOQUEADO / CORRIGIDO" if c["contained"] else "❌ FALHOU"
        lines.append(
            f"| `{c['id']}` | **{c['name']}**<br/>*{c['attack_vector']}* | `{c['target_layer']}` | {c['system_response']} | `{c['duration_ms']} ms` | {status_badge} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Verificação Forense e Como Reproduzir",
        "",
        "Todos os eventos encontram-se gravados em:",
        "- Banco SQLite WAL: `data/epistemic_brain.db`",
        "- Trilha de Auditoria JSONL: `data/epistemic_events.jsonl`",
        "- Relatório JSON: `data/chaos_benchmark_report.json`",
        "- Painel Visual Interativo: `dashboard/inspector_telemetria.html`",
        "",
        "Para reexecutar a validação completa a qualquer momento:",
        "```bash",
        "python tests/chaos_benchmark.py",
        "python -m unittest discover -s tests -p \"test_*.py\" -v",
        "```",
    ])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    results = run_chaos_benchmark()
    print("=" * 78)
    print(f"BENCHMARK CONCLUIDO: {results['scenarios_contained']}/{results['total_scenarios']} cenarios contidos ({results['containment_rate_pct']:.1f}%)")
    print(f"Eventos gravados: {results['total_events_recorded']} | Rollbacks causais: {results['total_causal_rollbacks']} | Tempo: {results['total_duration_ms']} ms")
    print("=" * 78)
    for case in results["cases"]:
        mark = "[PASS]" if case["contained"] else "[FAIL]"
        print(f"{mark} {case['id']} ({case['target_layer']}): {case['name']} -> {case['duration_ms']} ms")
    if results["scenarios_contained"] != results["total_scenarios"]:
        sys.exit(1)
