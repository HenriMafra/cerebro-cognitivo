"""
Suíte de Testes das Evoluções v2.0 (Absorção Cruzada e Melhorias Arquiteturais):
1. Assinatura Criptográfica (Ed25519 / Determinística) e Âncoras Externas Anti-Reescrita.
2. Política AST com Allowlist Estrita e Bloqueio de Introspecção (__subclasses__, __globals__).
3. Detector de Testes Triviais/Tautológicos ('assert True' ou não invocação da função).
4. Memória CoALA (FTS5 BM25 Versionado, Conferência Literal de Citação e Bloqueio Episódico).
5. Orçamento Rígido com Reserva de Pior Caso (HardBudget) e Prevenção de Estouro.
6. Verificador Formal SMT-LIB (Bloqueio de diretivas inseguras).
"""

from __future__ import annotations
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cerebro_cognitivo.core import (
    BudgetExceededError,
    CoALAMemoryStore,
    EventSigner,
    HardBudget,
    VerdictStatus,
    check_ast_allowlist,
    detect_trivial_tests,
    run_smtlib_formal_check,
)


class TestV2ArchitecturalUpgrades(unittest.TestCase):

    def test_01_event_signer_and_external_anchor(self) -> None:
        signer = EventSigner()
        h = "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        sig = signer.sign(h)
        self.assertTrue(signer.verify(h, sig))
        self.assertFalse(signer.verify(h + "_tampered", sig))

        anchor = signer.create_external_anchor(
            head_event_id="evt_99",
            head_content_hash=h,
            total_events=99,
        )
        self.assertTrue(signer.verify_external_anchor(anchor, current_event_hash_at_seq=h))
        self.assertFalse(signer.verify_external_anchor(anchor, current_event_hash_at_seq="sha256:rewritten"))

    def test_02_ast_allowlist_and_sandbox_escape_prevention(self) -> None:
        safe_code = "import math\nimport hashlib\ndef calc(x: int) -> float:\n    return math.sqrt(x)\n"
        self.assertEqual(len(check_ast_allowlist(safe_code)), 0)

        # Tentativa de importar subprocess/socket ou usar __subclasses__
        escape_code = (
            "import subprocess\n"
            "def exploit():\n"
            "    return ().__class__.__bases__[0].__subclasses__()\n"
        )
        violations = check_ast_allowlist(escape_code)
        self.assertGreaterEqual(len(violations), 3)

    def test_03_trivial_tests_detector(self) -> None:
        code = "def somar(a: int, b: int) -> int:\n    return a + b\n"
        # Teste tautológico 'True' deve ser rejeitado
        reason_taut = detect_trivial_tests(code, ["True"])
        self.assertIsNotNone(reason_taut)

        # Teste que não chama 'somar' deve ser rejeitado
        reason_unused = detect_trivial_tests(code, ["1 + 1 == 2"])
        self.assertIsNotNone(reason_unused)

        # Teste real que invoca 'somar' deve ser aprovado (None)
        reason_ok = detect_trivial_tests(code, ["somar(2, 3) == 5"])
        self.assertIsNone(reason_ok)

    def test_04_coala_memory_versioned_rag_and_literal_quote_check(self) -> None:
        kb = CoALAMemoryStore(":memory:")
        doc_v1, chunks_v1 = kb.ingest_document(
            source="contrato_sla.md",
            text="Cláusula 4.1: O tempo máximo de resposta para incidentes críticos é de 15 minutos.",
            title="SLA v1",
        )
        # Reingerir versão atualizada do mesmo documento
        doc_v2, chunks_v2 = kb.ingest_document(
            source="contrato_sla.md",
            text="Cláusula 4.1: O tempo máximo de resposta para incidentes críticos foi reduzido para 5 minutos.",
            title="SLA v2",
        )
        # A busca ativa retorna apenas a v2
        hits = kb.search_semantic("incidentes criticos minutos")
        self.assertEqual(len(hits), 1)
        self.assertIn("5 minutos", hits[0].text)

        # Mas o chunk histórico da v1 continua verificável para auditoria de execuções passadas!
        ok_v1, _ = kb.verify_literal_quote(
            chunks_v1[0],
            "O tempo máximo de resposta para incidentes críticos é de 15 minutos",
        )
        self.assertTrue(ok_v1)

        # Citação inventada/alucinada é rejeitada
        ok_fake, _ = kb.verify_literal_quote(
            chunks_v2[0],
            "O tempo máximo de resposta é de 48 horas úteis",
        )
        self.assertFalse(ok_fake)

        # Memória episódica jamais pode ser citada como prova factual
        kb.record_episode("ep_001", "Qual o SLA?", "Acho que 10 min", "APPROVED")
        ok_ep, msg_ep = kb.verify_literal_quote("ep_001", "Acho que 10 min")
        self.assertFalse(ok_ep)
        self.assertIn("Violação CoALA", msg_ep)
        kb.close()

    def test_05_hard_budget_worst_case_reservation(self) -> None:
        budget = HardBudget(max_usd=0.05, max_calls=2)
        r1 = budget.reserve("gemini-2.5-flash", "Prompt curto", max_output_tokens=500)
        budget.settle(r1, "gemini-2.5-flash", input_tokens=50, output_tokens=100)
        r2 = budget.reserve("gemini-2.5-flash", "Segundo prompt", max_output_tokens=500)
        budget.settle(r2, "gemini-2.5-flash", input_tokens=50, output_tokens=100)
        # 3ª chamada deve estourar max_calls=2
        with self.assertRaises(BudgetExceededError):
            budget.reserve("gemini-2.5-flash", "Terceiro prompt", max_output_tokens=500)

    def test_06_smtlib_security_filter(self) -> None:
        status, detail = run_smtlib_formal_check("(set-option :produce-models true)\n(check-sat)")
        self.assertEqual(status, VerdictStatus.REJECTED_GROUNDING)
        self.assertIn("bloqueada por segurança", detail)


if __name__ == "__main__":
    unittest.main()
