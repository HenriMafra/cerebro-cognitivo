"""
Bateria de Testes Canônica para o Neurônio Cognitivo e as 3 Camadas de Verificação.
Valida rigorosamente:
1. LogicalVerifier (V1)
2. DeterministicMachineVerifier (V2)
3. AdversarialRedTeamVerifier (V3)
4. CognitiveSynthesisBridge & DeterministicSynthesisEngine
5. CognitiveNeuron (Microcircuito Fechado de 8 Estágios e Causal Rollback)
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cerebro_cognitivo.core import (
    Claim,
    CognitiveNeuron,
    CognitiveSynthesisBridge,
    DeterministicMachineVerifier,
    DeterministicSynthesisEngine,
    EpistemicEventStore,
    HypothesisPayload,
    InMemoryEventStore,
    LogicalVerifier,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
    compute_sha256,
)
from cerebro_cognitivo.core.verifiers import AdversarialRedTeamVerifier


# =============================================================================
# 1. TESTES DA CAMADA V1: LogicalVerifier
# =============================================================================

def test_v1_rejects_missing_or_invalid_claims():
    v1 = LogicalVerifier()
    signal = SynapticSignal(
        source_neuron="prefrontal_cortex",
        target_neuron="math_specialist",
        task_intent="Calcular determinante de matriz",
    )

    # Caso 1: Nenhuma claim
    hyp_empty = HypothesisPayload(claims=[])
    report = v1.verify(hyp_empty, signal)
    assert report.status == VerdictStatus.REJECTED_LOGIC
    assert "Toda afirmação exige ProvenancePointer válido" in report.negative_constraints_added

    # Caso 2: Claim sem ProvenancePointer
    hyp_no_prov = HypothesisPayload(claims=[Claim(statement="A resposta é 42", provenance=None)])
    report2 = v1.verify(hyp_no_prov, signal)
    assert report2.status == VerdictStatus.REJECTED_LOGIC


def test_v1_rejects_uncertainty_and_hallucination_markers():
    v1 = LogicalVerifier()
    signal = SynapticSignal(
        source_neuron="sensor",
        target_neuron="analyst",
        task_intent="Classificar risco de transação",
    )
    ptr = ProvenancePointer(
        source_type=ProvenanceType.AXIOM_USER,
        reference_id=signal.signal_id,
        excerpt="Risco transacional",
    )
    hyp = HypothesisPayload(
        claims=[
            Claim(statement="Eu acho que a transação é fraudulenta", provenance=ptr)
        ]
    )
    report = v1.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_LOGIC
    assert any("marcador de incerteza" in r.lower() for r in report.reasons)


def test_v1_rejects_violation_of_negative_constraints():
    v1 = LogicalVerifier()
    signal = SynapticSignal(
        source_neuron="security_officer",
        target_neuron="worker",
        task_intent="Criar arquivo temporário",
        constraints=["Proibido os.system", "Evitar recursão"],
    )
    ptr = ProvenancePointer(
        source_type=ProvenanceType.AXIOM_USER,
        reference_id=signal.signal_id,
        excerpt="Restrição de segurança",
    )
    hyp = HypothesisPayload(
        description="Executando comando via os.system('echo 1')",
        claims=[Claim(statement="Arquivo criado com sucesso", provenance=ptr)],
    )
    report = v1.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_LOGIC


def test_v1_approves_valid_rigorous_hypothesis():
    v1 = LogicalVerifier()
    signal = SynapticSignal(
        source_neuron="architect",
        target_neuron="logic_unit",
        task_intent="Validar congruência matemática",
    )
    ptr = ProvenancePointer(
        source_type=ProvenanceType.FORMAL_DEDUCTION,
        reference_id=signal.signal_id,
        excerpt="Dedução formal comprovada",
    )
    hyp = HypothesisPayload(
        claims=[
            Claim(statement="O número primo p é estritamente maior que 2.", provenance=ptr)
        ]
    )
    report = v1.verify(hyp, signal)
    assert report.status == VerdictStatus.APPROVED
    assert report.score == 1.0


# =============================================================================
# 2. TESTES DA CAMADA V2: DeterministicMachineVerifier
# =============================================================================

def test_v2_rejects_syntax_error():
    v2 = DeterministicMachineVerifier()
    signal = SynapticSignal(
        source_neuron="n1", target_neuron="n2", task_intent="Compilar código"
    )
    hyp = HypothesisPayload(
        code_artifact="def bad_syntax(x\n    return x + 1\n",
        entrypoint_function="bad_syntax",
    )
    report = v2.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_GROUNDING
    assert report.machine_feedback is not None
    assert report.machine_feedback.ast_valid is False
    assert "SyntaxError" in report.machine_feedback.stderr


def test_v2_blocks_dangerous_destructive_system_calls():
    v2 = DeterministicMachineVerifier()
    signal = SynapticSignal(
        source_neuron="n1", target_neuron="n2", task_intent="Executar tarefa"
    )
    hyp = HypothesisPayload(
        code_artifact="""
import os

def malicious_routine():
    os.system("echo format c:")
    return 0
""",
        entrypoint_function="malicious_routine",
    )
    report = v2.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_GROUNDING
    assert "os.system" in str(report.reasons)


def test_v2_rejects_missing_entrypoint():
    v2 = DeterministicMachineVerifier()
    signal = SynapticSignal(
        source_neuron="n1", target_neuron="n2", task_intent="Executar função"
    )
    hyp = HypothesisPayload(
        code_artifact="def other_func(): return 10\n",
        entrypoint_function="expected_function_name",
    )
    report = v2.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_GROUNDING
    assert "não encontrada na AST" in str(report.reasons)


def test_v2_detects_runtime_failure_and_injects_stderr():
    v2 = DeterministicMachineVerifier()
    signal = SynapticSignal(
        source_neuron="n1", target_neuron="n2", task_intent="Dividir valores"
    )
    hyp = HypothesisPayload(
        code_artifact="""
def divide(a, b):
    return a / b

result = divide(10, 0)
""",
        entrypoint_function="divide",
    )
    report = v2.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_GROUNDING
    assert report.machine_feedback is not None
    assert report.machine_feedback.exit_code != 0
    assert "ZeroDivisionError" in report.machine_feedback.stderr


def test_v2_approves_successful_execution_and_invariants():
    v2 = DeterministicMachineVerifier()
    signal = SynapticSignal(
        source_neuron="n1",
        target_neuron="n2",
        task_intent="Multiplicar inteiros",
        input_data={"validation_assertions": ["multiply(6, 7) == 42"]},
    )
    hyp = HypothesisPayload(
        code_artifact="""
def multiply(a, b):
    return a * b
""",
        entrypoint_function="multiply",
        expected_invariants=[
            "multiply(2, 3) == 6",
            "multiply(-2, 5) == -10",
        ],
    )
    report = v2.verify(hyp, signal)
    assert report.status == VerdictStatus.APPROVED
    assert report.score == 1.0
    assert report.machine_feedback.invariants_passed is True


# =============================================================================
# 3. TESTES DA CAMADA V3: AdversarialRedTeamVerifier
# =============================================================================

def test_v3_detects_tampered_provenance_hash():
    v3 = AdversarialRedTeamVerifier()
    signal = SynapticSignal(
        source_neuron="audit", target_neuron="crypto", task_intent="Auditoria"
    )
    legit_ptr = ProvenancePointer(
        source_type=ProvenanceType.AXIOM_USER,
        reference_id=signal.signal_id,
        excerpt="Evidência fidedigna",
    )
    # Adulterar o hash intencionalmente
    tampered_ptr = ProvenancePointer(
        source_type=legit_ptr.source_type,
        reference_id=legit_ptr.reference_id,
        excerpt=legit_ptr.excerpt,
        evidence_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
    )
    hyp = HypothesisPayload(
        claims=[Claim(statement="Dado legítimo", provenance=tampered_ptr)]
    )
    report = v3.verify(hyp, signal)
    assert report.status == VerdictStatus.REJECTED_RED_TEAM
    assert any("falsificação" in r.lower() for r in report.reasons)


def test_v3_finds_counterexample_in_unhandled_edge_case():
    v3 = AdversarialRedTeamVerifier()
    signal = SynapticSignal(
        source_neuron="tester",
        target_neuron="worker",
        task_intent="Fatorial seguro",
        input_data={
            "red_team_cases": [
                {"call": "factorial(-1)", "should_raise": "ValueError"},
                {"call": "factorial(0)", "expected": 1},
            ]
        },
    )
    # Código ingênuo que quebra com recursão infinita ou não trata negativos
    hyp = HypothesisPayload(
        code_artifact="""
def factorial(n):
    # Bug proposital: não trata negativos nem lança ValueError
    if n == 0:
        return 1
    return n * factorial(n - 1)
""",
        entrypoint_function="factorial",
    )
    report = v3.verify(hyp, signal, timeout_sec=1.5)
    assert report.status == VerdictStatus.REJECTED_RED_TEAM
    assert len(report.counterexamples) > 0


def test_v3_approves_robust_edge_resistant_code():
    v3 = AdversarialRedTeamVerifier()
    signal = SynapticSignal(
        source_neuron="tester",
        target_neuron="worker",
        task_intent="Fatorial robusto",
        input_data={
            "red_team_cases": [
                {"call": "factorial(-1)", "should_raise": "ValueError"},
                {"call": "factorial(0)", "expected": 1},
                {"call": "factorial(5)", "expected": 120},
            ]
        },
    )
    ptr = ProvenancePointer(
        source_type=ProvenanceType.AXIOM_USER,
        reference_id=signal.signal_id,
        excerpt="Fatorial robusto",
    )
    hyp = HypothesisPayload(
        description="Fatorial defensivo com tratamento estrito de borda",
        claims=[Claim(statement="Fatorial implementado com salvaguarda", provenance=ptr)],
        code_artifact="""
def factorial(n):
    if not isinstance(n, int):
        raise TypeError("Deve ser int")
    if n < 0:
        raise ValueError("n deve ser não-negativo")
    if n == 0 or n == 1:
        return 1
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res
""",
        entrypoint_function="factorial",
    )
    report = v3.verify(hyp, signal)
    assert report.status == VerdictStatus.APPROVED
    assert report.score == 1.0


# =============================================================================
# 4. TESTES DE LLM BRIDGE & SÍNTESE DETERMINÍSTICA
# =============================================================================

def test_deterministic_synthesis_engine_generates_valid_payload():
    engine = DeterministicSynthesisEngine()
    signal = SynapticSignal(
        source_neuron="cortex",
        target_neuron="math",
        task_intent="Calcular fatorial de n",
        input_data={"operation": "factorial", "function_name": "factorial", "code_task": True},
    )
    hyp = engine.synthesize(signal, iteration=1)
    assert hyp.iteration == 1
    assert hyp.entrypoint_function == "factorial"
    assert len(hyp.claims) >= 1
    assert all(c.has_valid_provenance() for c in hyp.claims)


def test_custom_thinker_fn_injection_in_bridge():
    bridge = CognitiveSynthesisBridge()
    signal = SynapticSignal(
        source_neuron="chaos",
        target_neuron="test",
        task_intent="Injeção de teste",
    )

    def chaos_thinker(sig, it, neg_constraints):
        return HypothesisPayload(
            description=f"Hipótese do Caos Iter {it}",
            claims=[
                Claim(
                    statement="Caos controlado",
                    provenance=ProvenancePointer(
                        source_type=ProvenanceType.AXIOM_USER,
                        reference_id=sig.signal_id,
                        excerpt="Caos",
                    ),
                )
            ],
            code_artifact="def chaos_func(): return True\n",
            entrypoint_function="chaos_func",
        )

    hyp = bridge.synthesize(signal, iteration=1, custom_thinker_fn=chaos_thinker)
    assert hyp.entrypoint_function == "chaos_func"
    assert "Caos Iter 1" in hyp.description


# =============================================================================
# 5. TESTES DO CIRCUITO INTEGRADO DO NEURÔNIO COGNITIVO COMPOSTO
# =============================================================================

def test_neuron_successful_convergence_with_in_memory_store():
    store = InMemoryEventStore()
    neuron = CognitiveNeuron(
        neuron_id="neuron_math_01",
        specialty="Aritmética e Teoria dos Números",
        event_store=store,
        max_iterations=3,
    )
    signal = SynapticSignal(
        source_neuron="prefrontal_cortex",
        target_neuron="neuron_math_01",
        task_intent="Implementar e verificar fatorial(n)",
        input_data={
            "operation": "factorial",
            "function_name": "factorial",
            "code_task": True,
            "invariants": ["factorial(0) == 1", "factorial(4) == 24"],
            "red_team_cases": [
                {"call": "factorial(-1)", "should_raise": "ValueError"},
                {"call": "factorial(5)", "expected": 120},
            ],
        },
    )

    cert = neuron.process_signal(signal)
    assert cert.status == VerdictStatus.APPROVED
    assert cert.total_iterations >= 1
    assert cert.final_hypothesis is not None
    assert len(cert.verifier_reports) == 3
    assert cert.confidence_score == 1.0

    # Validar integridade dos eventos registrados
    all_events = store.get_all_events()
    assert len(all_events) >= 5
    assert all_events[0].event_type == "SIGNAL_RECEIVED"
    assert all_events[1].event_type == "PREMISES_EXPANDED"
    assert all_events[-1].event_type == "AXON_EMITTED"


def test_neuron_epistemic_abort_on_hopeless_problem():
    """Valida o princípio de Zero Alucinação: esgotamento de iterações gera EPISTEMIC_FAILURE."""
    store = InMemoryEventStore()

    # Um pensador customizado que sempre comete um erro fatal de sintaxe
    def broken_thinker(sig, it, neg_constraints):
        ptr = ProvenancePointer(
            source_type=ProvenanceType.AXIOM_USER,
            reference_id=sig.signal_id,
            excerpt="Tentativa",
        )
        return HypothesisPayload(
            iteration=it,
            description="Hipótese quebrada intencionalmente",
            claims=[Claim(statement="Afirmação lastreada", provenance=ptr)],
            code_artifact="def syntaXXX_error(\n",
            entrypoint_function="syntaXXX_error",
        )

    neuron = CognitiveNeuron(
        neuron_id="neuron_broken_02",
        specialty="Teste de Aborto",
        event_store=store,
        max_iterations=2,
        custom_thinker_fn=broken_thinker,
    )

    signal = SynapticSignal(
        source_neuron="cortex",
        target_neuron="neuron_broken_02",
        task_intent="Tarefa Impossível",
    )

    cert = neuron.process_signal(signal)
    assert cert.status == VerdictStatus.EPISTEMIC_FAILURE
    assert cert.total_iterations == 2
    assert cert.confidence_score == 0.0

    # Evento final gravado no repositório DEVE ser EPISTEMIC_ABORT
    all_events = store.get_all_events()
    assert all_events[-1].event_type == "EPISTEMIC_ABORT"


def test_neuron_iterative_causal_rollback_and_self_correction():
    """
    Cenário crucial: a iteração 1 falha na Camada V2 (ZeroDivisionError).
    O neurônio executa Causal Rollback, injeta a restrição negativa
    e a iteração 2 gera o código corrigido, aprovando nas 3 camadas!
    """
    store = InMemoryEventStore()

    # Pensador adaptativo simulando aprendizado reflexivo
    def adaptive_thinker(sig, it, neg_constraints):
        ptr = ProvenancePointer(
            source_type=ProvenanceType.AXIOM_USER,
            reference_id=sig.signal_id,
            excerpt="Divisão segura",
        )
        if it == 1:
            # Iteração 1: código ingênuo que falha com ZeroDivisionError
            code = """
def safe_div(a, b):
    return a / b
"""
        else:
            # Iteração 2: corrigido com base nas restrições negativas acumuladas!
            code = """
def safe_div(a, b):
    if b == 0:
        return 0
    return a / b
"""
        return HypothesisPayload(
            iteration=it,
            description=f"Hipótese de divisão ciclo {it}",
            claims=[Claim(statement="Divisão computada deterministicamente", provenance=ptr)],
            code_artifact=code,
            entrypoint_function="safe_div",
            expected_invariants=["safe_div(10, 2) == 5.0", "safe_div(10, 0) == 0"],
        )

    neuron = CognitiveNeuron(
        neuron_id="neuron_reflexive_03",
        specialty="Divisão Segura Reflexiva",
        event_store=store,
        max_iterations=3,
        custom_thinker_fn=adaptive_thinker,
    )

    signal = SynapticSignal(
        source_neuron="math_dept",
        target_neuron="neuron_reflexive_03",
        task_intent="Computar divisão com segurança em zero",
        constraints=["Tratar divisão por zero"],
    )

    cert = neuron.process_signal(signal)
    assert cert.status == VerdictStatus.APPROVED
    assert cert.total_iterations == 2  # Converteu na 2ª tentativa!
    assert cert.confidence_score == 1.0


def test_neuron_with_sqlite_epistemic_event_store():
    """Valida interoperabilidade total do Neurônio com o EpistemicEventStore SQLite."""
    sqlite_store = EpistemicEventStore(db_path=":memory:")
    neuron = CognitiveNeuron(
        neuron_id="neuron_sqlite_04",
        specialty="Validação Forense",
        event_store=sqlite_store,
        max_iterations=2,
    )

    signal = SynapticSignal(
        source_neuron="director",
        target_neuron="neuron_sqlite_04",
        task_intent="Inverter string determinística",
        input_data={
            "operation": "reverse",
            "function_name": "reverse_str",
            "code_task": True,
            "invariants": ["reverse_str('abc') == 'cba'"],
        },
    )

    cert = neuron.process_signal(signal)
    assert cert.status == VerdictStatus.APPROVED
    assert cert.total_iterations == 1

    # Verificar integridade criptográfica da cadeia no SQLite
    is_valid, violations = sqlite_store.verify_chain_integrity()
    assert is_valid is True
    assert len(violations) == 0


import unittest


class TestNeuronAndVerifiersSuite(unittest.TestCase):
    """Wrapper unittest para integração com 'python -m unittest discover'."""
    pass


for _name, _fn in list(globals().items()):
    if _name.startswith("test_") and callable(_fn):
        setattr(TestNeuronAndVerifiersSuite, _name, staticmethod(_fn))


if __name__ == "__main__":
    test_funcs = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    print(f"\n=======================================================")
    print(f" Executando Bateria de Testes: {len(test_funcs)} testes encontrados")
    print(f"=======================================================\n")
    
    passed = 0
    failed = 0
    t0_all = time.perf_counter()
    
    for fn in test_funcs:
        fn_name = fn.__name__
        t0 = time.perf_counter()
        try:
            fn()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f" [PASS] {fn_name:<60} ({elapsed_ms:6.1f} ms)")
            passed += 1
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f" [FAIL] {fn_name:<60} ({elapsed_ms:6.1f} ms) -> {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            
    total_elapsed = (time.perf_counter() - t0_all) * 1000
    print(f"\n=======================================================")
    print(f" Resultado: {passed} PASSADOS | {failed} FALHAS | Total: {total_elapsed:.1f} ms")
    print(f"=======================================================\n")
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

