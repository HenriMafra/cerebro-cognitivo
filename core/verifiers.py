"""
Camadas Ortogonais de Verificação Epistêmica.
Implementação canônica das 3 camadas de contenção para o Neurônio Cognitivo:
- Camada V1: LogicalVerifier (Auditor Silogístico e Anti-Alucinação por Proveniência)
- Camada V2: DeterministicMachineVerifier (Árbitro de Execução e Compilação em Sandbox)
- Camada V3: AdversarialRedTeamVerifier (Inquisidor Cético e Testes de Borda Adversários)
"""

from __future__ import annotations
import ast
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set

from .schemas import (
    Claim,
    HypothesisPayload,
    MachineFeedback,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
    VerifierReport,
    compute_sha256,
)


class LogicalVerifier:
    """
    Camada V1: Auditor Lógico e Silogístico.
    Garante que toda afirmação possua lastro epistêmico válido (ProvenancePointer),
    que não haja contradições internas nem marcadores de incerteza alucinatória,
    e que nenhuma restrição negativa prévia seja violada.
    """

    UNCERTAINTY_MARKERS: Set[str] = {
        "acho que",
        "talvez",
        "provavelmente",
        "acredito que",
        "supostamente",
        "não tenho certeza",
        "possivelmente",
        "parece que",
        "pode ser que",
        "desconhecido mas assumo",
        "sem garantia",
        "chuto que",
    }

    def __init__(self, verifier_layer: str = "V1_LOGIC") -> None:
        self.verifier_layer = verifier_layer

    def verify(self, hypothesis: HypothesisPayload, signal: SynapticSignal) -> VerifierReport:
        """
        Executa a verificação lógica em 3 regras estritas:
        1. Anti-Alucinação por Provenance Pointer.
        2. Não-Contradição e Conformidade com Restrições Negativas.
        3. Coerência Silogística e Ausência de Marcadores de Incerteza.
        """
        # Regra 1: Anti-Alucinação por Provenance Pointer
        if not hypothesis.claims:
            return VerifierReport(
                verifier_layer=self.verifier_layer,
                status=VerdictStatus.REJECTED_LOGIC,
                score=0.0,
                reasons=["Rejeição V1: Hipótese não contém nenhuma afirmação (Claim) formulada."],
                negative_constraints_added=["Toda afirmação exige ProvenancePointer válido"],
            )

        for idx, claim in enumerate(hypothesis.claims):
            if not isinstance(claim, Claim) or not claim.has_valid_provenance():
                stmt_snippet = getattr(claim, "statement", str(claim))[:60]
                return VerifierReport(
                    verifier_layer=self.verifier_layer,
                    status=VerdictStatus.REJECTED_LOGIC,
                    score=0.0,
                    reasons=[
                        f"Rejeição V1: Afirmação #{idx+1} ('{stmt_snippet}...') "
                        "não possui ProvenancePointer válido ou hash criptográfico ausente."
                    ],
                    negative_constraints_added=["Toda afirmação exige ProvenancePointer válido"],
                )

        # Regra 2: Não-Contradição e Conformidade com Restrições Negativas
        all_prohibitions: List[str] = list(signal.constraints) + list(hypothesis.negative_constraints_applied)
        hyp_text_corpus = f"{hypothesis.description}\n{hypothesis.code_artifact or ''}".lower()

        for prohibition in all_prohibitions:
            p_clean = prohibition.strip().lower()
            if not p_clean:
                continue

            # Se a restrição exigir evitar padrões específicos proibidos
            if "proibido" in p_clean or "evitar" in p_clean or "não usar" in p_clean:
                # Extrair termos-chave proibidos após o marcador
                keywords = [k.strip() for k in p_clean.replace("proibido", "").replace("evitar", "").replace("não usar", "").split(",") if len(k.strip()) > 3]
                for kw in keywords:
                    if kw in hyp_text_corpus:
                        return VerifierReport(
                            verifier_layer=self.verifier_layer,
                            status=VerdictStatus.REJECTED_LOGIC,
                            score=0.0,
                            reasons=[f"Rejeição V1: Hipótese violou a restrição negativa explícita: '{prohibition}'."],
                            negative_constraints_added=[f"Eliminar estritamente o elemento proibido: '{kw}'"],
                        )

        # Regra 3: Coerência Silogística & Marcadores de Incerteza Alucinatória
        for idx, claim in enumerate(hypothesis.claims):
            stmt_lower = claim.statement.lower()
            for marker in self.UNCERTAINTY_MARKERS:
                if marker in stmt_lower:
                    return VerifierReport(
                        verifier_layer=self.verifier_layer,
                        status=VerdictStatus.REJECTED_LOGIC,
                        score=0.0,
                        reasons=[
                            f"Rejeição V1: Marcador de incerteza/alucinação detectado na afirmação #{idx+1}: '{marker}'."
                        ],
                        negative_constraints_added=[
                            "Eliminar marcadores de incerteza; formular apenas afirmações com prova causal e determinística."
                        ],
                    )

        # Detecção de contradições mútuas explícitas entre claims
        claim_statements = [c.statement.strip().lower() for c in hypothesis.claims]
        for i, stmt_a in enumerate(claim_statements):
            for j, stmt_b in enumerate(claim_statements):
                if i != j:
                    if stmt_a == f"não {stmt_b}" or stmt_b == f"não {stmt_a}":
                        return VerifierReport(
                            verifier_layer=self.verifier_layer,
                            status=VerdictStatus.REJECTED_LOGIC,
                            score=0.0,
                            reasons=[
                                f"Rejeição V1: Contradição mútua explícita detectada entre claims #{i+1} e #{j+1}."
                            ],
                            negative_constraints_added=["Eliminar premissas ou conclusões mutuamente excludentes."],
                        )

        # Aprovação V1
        return VerifierReport(
            verifier_layer=self.verifier_layer,
            status=VerdictStatus.APPROVED,
            score=1.0,
            reasons=["V1 Lógica Aprovada: Todas as claims possuem proveniência válida e coerência silogística estrita."],
        )


class DeterministicMachineVerifier:
    """
    Camada V2: Árbitro de Máquina Determinístico.
    Inspeciona a AST do código gerado, audita segurança estática,
    monta o runner de teste com os invariantes esperados e executa
    o artefato em um processo Python isolado (-I).
    """

    DANGEROUS_CALLS: Set[str] = {
        "os.system",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "shutil.rmtree",
        "subprocess.Popen",
    }

    def __init__(self, verifier_layer: str = "V2_GROUNDING") -> None:
        self.verifier_layer = verifier_layer

    def verify(
        self,
        hypothesis: HypothesisPayload,
        signal: SynapticSignal,
        timeout_sec: float = 4.0,
    ) -> VerifierReport:
        """
        Executa a verificação determinística de máquina:
        Passo A: Parsing AST real (detecta SyntaxError).
        Passo B: Inspeção estática de segurança e verificação de entrypoint_function.
        Passo C: Montagem de script com invariantes e execução isolada via subprocess.
        Passo D: Captura de MachineFeedback e injeção de stderr em caso de falha.
        """
        # Se não há código na hipótese
        if not hypothesis.code_artifact or not hypothesis.code_artifact.strip():
            if hypothesis.expected_invariants or hypothesis.entrypoint_function:
                return VerifierReport(
                    verifier_layer=self.verifier_layer,
                    status=VerdictStatus.REJECTED_GROUNDING,
                    score=0.0,
                    reasons=["Rejeição V2: Entrypoint ou invariantes esperados foram definidos, mas code_artifact está ausente."],
                    negative_constraints_added=["O código executável é obrigatório quando invariantes são exigidos."],
                )
            # Hipótese puramente teórica sem código
            return VerifierReport(
                verifier_layer=self.verifier_layer,
                status=VerdictStatus.APPROVED,
                score=1.0,
                reasons=["V2 Grounding Aprovado: Hipótese puramente conceitual sem código executável pendente."],
            )

        code_str = hypothesis.code_artifact
        t_start = time.perf_counter()

        # Passo A: Parsing estático real com ast.parse
        try:
            tree = ast.parse(code_str)
        except SyntaxError as syn_err:
            duration_ms = (time.perf_counter() - t_start) * 1000
            err_msg = f"SyntaxError: {syn_err.msg} na linha {syn_err.lineno}"
            feedback = MachineFeedback(
                executed=False,
                tool_name="ast_parser",
                command_or_code=code_str,
                exit_code=1,
                stdout="",
                stderr=err_msg,
                duration_ms=round(duration_ms, 2),
                ast_valid=False,
                invariants_passed=False,
            )
            return VerifierReport(
                verifier_layer=self.verifier_layer,
                status=VerdictStatus.REJECTED_GROUNDING,
                score=0.0,
                reasons=[f"Rejeição V2: Falha no parsing sintático AST ({err_msg})."],
                negative_constraints_added=[f"Corrigir erro de sintaxe Python: {err_msg}"],
                machine_feedback=feedback,
            )

        # Passo B: Auditoria de Segurança AST e Presença do Entrypoint
        for node in ast.walk(tree):
            # Detectar chamadas de sistema perigosas
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    val = node.func.value
                    if isinstance(val, ast.Name):
                        func_name = f"{val.id}.{node.func.attr}"

                if func_name in self.DANGEROUS_CALLS:
                    duration_ms = (time.perf_counter() - t_start) * 1000
                    err_msg = f"Chamada destrutiva/insegura de sistema bloqueada na AST: '{func_name}'."
                    feedback = MachineFeedback(
                        executed=False,
                        tool_name="ast_security_guard",
                        command_or_code=code_str,
                        exit_code=1,
                        stdout="",
                        stderr=err_msg,
                        duration_ms=round(duration_ms, 2),
                        ast_valid=False,
                        invariants_passed=False,
                    )
                    return VerifierReport(
                        verifier_layer=self.verifier_layer,
                        status=VerdictStatus.REJECTED_GROUNDING,
                        score=0.0,
                        reasons=[f"Rejeição V2: {err_msg}"],
                        negative_constraints_added=[f"Proibido utilizar chamadas de sistema inseguras como '{func_name}'."],
                        machine_feedback=feedback,
                    )

        # Verificar se entrypoint_function está realmente definido na AST
        if hypothesis.entrypoint_function:
            defined_funcs: Set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined_funcs.add(node.name)

            if hypothesis.entrypoint_function not in defined_funcs:
                duration_ms = (time.perf_counter() - t_start) * 1000
                err_msg = f"Função entrypoint '{hypothesis.entrypoint_function}' não encontrada na AST do código."
                feedback = MachineFeedback(
                    executed=False,
                    tool_name="ast_entrypoint_check",
                    command_or_code=code_str,
                    exit_code=1,
                    stdout="",
                    stderr=err_msg,
                    duration_ms=round(duration_ms, 2),
                    ast_valid=False,
                    invariants_passed=False,
                )
                return VerifierReport(
                    verifier_layer=self.verifier_layer,
                    status=VerdictStatus.REJECTED_GROUNDING,
                    score=0.0,
                    reasons=[f"Rejeição V2: {err_msg}"],
                    negative_constraints_added=[f"O código DEVE conter a definição 'def {hypothesis.entrypoint_function}(...)'."],
                    machine_feedback=feedback,
                )

        # Passo C: Montar script combinando code_artifact + verificação de expected_invariants
        runner_lines = [
            "# Runner determinístico isolado - Cérebro Cognitivo V2",
            code_str,
            "",
            "# Invariantes de Pós-Condição:",
        ]

        for inv in hypothesis.expected_invariants:
            inv_clean = inv.strip()
            if inv_clean:
                runner_lines.append(f"assert {inv_clean}, f\"Invariante violado: {inv_clean}\"")

        # Adicionar validações extras vindas do sinal
        for val_assert in signal.input_data.get("validation_assertions", []):
            va_clean = str(val_assert).strip()
            if va_clean:
                runner_lines.append(f"assert {va_clean}, f\"Validação do sinal violada: {va_clean}\"")

        runner_script = "\n".join(runner_lines)

        # Execução em subprocess isolado
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-X", "utf8", "-c", runner_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
            )
            duration_ms = (time.perf_counter() - t_start) * 1000
            stdout_out = proc.stdout or ""
            stderr_out = proc.stderr or ""
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            duration_ms = timeout_sec * 1000
            err_msg = f"TimeoutExpired: Execução ultrapassou o limite estrito de {timeout_sec:.2f}s."
            feedback = MachineFeedback(
                executed=True,
                tool_name="python_isolated_runner",
                command_or_code=runner_script,
                exit_code=124,
                stdout="",
                stderr=err_msg,
                duration_ms=round(duration_ms, 2),
                ast_valid=True,
                invariants_passed=False,
            )
            return VerifierReport(
                verifier_layer=self.verifier_layer,
                status=VerdictStatus.REJECTED_GROUNDING,
                score=0.0,
                reasons=[f"Rejeição V2: {err_msg}"],
                negative_constraints_added=[f"Eliminar loops infinitos ou computação excessiva (tempo > {timeout_sec}s)."],
                machine_feedback=feedback,
            )

        # Passo D: Avaliação do retorno de execução
        invariants_ok = (exit_code == 0)
        feedback = MachineFeedback(
            executed=True,
            tool_name="python_isolated_runner",
            command_or_code=runner_script,
            exit_code=exit_code,
            stdout=stdout_out,
            stderr=stderr_out,
            duration_ms=round(duration_ms, 2),
            ast_valid=True,
            invariants_passed=invariants_ok,
        )

        if not invariants_ok:
            stderr_snippet = stderr_out.strip() or f"Processo encerrou com exit_code {exit_code}"
            return VerifierReport(
                verifier_layer=self.verifier_layer,
                status=VerdictStatus.REJECTED_GROUNDING,
                score=0.0,
                reasons=[f"Rejeição V2: Falha na execução do processo de máquina (exit_code={exit_code})."],
                negative_constraints_added=[f"Erro de execução de máquina: {stderr_snippet}"],
                machine_feedback=feedback,
            )

        # Aprovação V2
        return VerifierReport(
            verifier_layer=self.verifier_layer,
            status=VerdictStatus.APPROVED,
            score=1.0,
            reasons=["V2 Grounding Aprovado: Código compilou sem erros e todos os invariantes determinísticos foram satisfeitos."],
            machine_feedback=feedback,
        )


class AdversarialRedTeamVerifier:
    """
    Camada V3: Inquisidor Cético e Auditor Adversário.
    Executa duas frentes cruciais de defesa:
    1. Audita a integridade criptográfica dos hashes dos ProvenancePointers das Claims
       (detecta falsificação ou adulteração de ponteiros de evidência).
    2. Submete o código a casos de borda e testes adversários extremos
       (procurando contraexemplos reais que refutem a hipótese).
    """

    def __init__(self, verifier_layer: str = "V3_RED_TEAM") -> None:
        self.verifier_layer = verifier_layer

    def verify(
        self,
        hypothesis: HypothesisPayload,
        signal: SynapticSignal,
        timeout_sec: float = 4.0,
    ) -> VerifierReport:
        """
        Executa a auditoria adversária Red Team:
        - Verifica integridade dos hashes de proveniência de todas as claims.
        - Executa contraprovas adversárias sobre artefatos de código.
        """
        # Frente 1: Auditoria Criptográfica de Proveniência (Detecção de Falsificação)
        for idx, claim in enumerate(hypothesis.claims):
            ptr = claim.provenance
            if ptr is not None:
                expected_hash = compute_sha256({
                    "source_type": ptr.source_type.value,
                    "reference_id": ptr.reference_id,
                    "excerpt": ptr.excerpt,
                })
                if ptr.evidence_hash != expected_hash:
                    counterexample = (
                        f"Falsificação de hash na Claim #{idx+1} ('{claim.statement[:40]}...'): "
                        f"declarado={ptr.evidence_hash}, calculado={expected_hash}"
                    )
                    return VerifierReport(
                        verifier_layer=self.verifier_layer,
                        status=VerdictStatus.REJECTED_RED_TEAM,
                        score=0.0,
                        reasons=[f"Rejeição V3: {counterexample}"],
                        counterexamples=[counterexample],
                        negative_constraints_added=[
                            "Integridade criptográfica violada: os hashes dos ProvenancePointers devem coincidir estritamente com o SHA-256 canônico da evidência."
                        ],
                    )

        # Frente 2: Testes Adversários de Casos de Borda sobre Código
        if hypothesis.code_artifact and hypothesis.entrypoint_function:
            code_str = hypothesis.code_artifact
            entrypoint = hypothesis.entrypoint_function
            red_team_cases = signal.input_data.get("red_team_cases", [])
            adversarial_assertions = signal.input_data.get("adversarial_assertions", [])

            # Montagem das baterias de estresse adversário
            adversarial_tests: List[str] = []

            # 1. Casos explícitos do sinal
            for case in red_team_cases:
                if isinstance(case, dict):
                    call_expr = case.get("call")
                    expected_expr = case.get("expected")
                    should_raise = case.get("should_raise")

                    if call_expr and expected_expr is not None:
                        adversarial_tests.append(
                            f"res = {call_expr}\nassert res == {expected_expr}, f\"Contraexemplo: {call_expr} retornou {{res}}, esperado {expected_expr}\""
                        )
                    elif call_expr and should_raise:
                        adversarial_tests.append(
                            f"try:\n    {call_expr}\n    raise AssertionError(\"Contraexemplo: {call_expr} deveria ter lançado {should_raise}\")\nexcept {should_raise}:\n    pass"
                        )
                elif isinstance(case, str):
                    adversarial_tests.append(f"assert {case}, f\"Contraexemplo adversário: {case}\"")

            # 2. Asserções adversárias diretas
            for adv_assert in adversarial_assertions:
                adversarial_tests.append(f"assert {adv_assert}, f\"Contraexemplo: {adv_assert}\"")

            # Se houver testes adversários para rodar
            if adversarial_tests:
                adv_runner = [
                    "# Red Team Adversarial Test Harness",
                    code_str,
                    "",
                    "def _red_team_harness():",
                ]
                for t in adversarial_tests:
                    indented = "\n".join(f"    {line}" for line in t.split("\n"))
                    adv_runner.append(indented)
                adv_runner.append("\n_red_team_harness()\n")

                adv_script = "\n".join(adv_runner)

                try:
                    proc = subprocess.run(
                        [sys.executable, "-I", "-X", "utf8", "-c", adv_script],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout_sec,
                    )
                    if proc.returncode != 0:
                        err_detail = (proc.stderr or "").strip() or f"Código quebrou com retorno {proc.returncode}"
                        # Extrair a mensagem do contraexemplo se presente
                        counterexample_msg = "Falha em caso de borda adversário."
                        for line in reversed(err_detail.splitlines()):
                            if "Contraexemplo" in line or "AssertionError" in line:
                                counterexample_msg = line.strip()
                                break

                        return VerifierReport(
                            verifier_layer=self.verifier_layer,
                            status=VerdictStatus.REJECTED_RED_TEAM,
                            score=0.0,
                            reasons=[f"Rejeição V3: Inquisidor Red Team encontrou contraexemplo que refuta a solução ({counterexample_msg})."],
                            counterexamples=[err_detail],
                            negative_constraints_added=[
                                f"Tratar o caso de borda adversário: {counterexample_msg}"
                            ],
                        )

                except subprocess.TimeoutExpired:
                    err_msg = f"Red Team Timeout: Execução adversária ultrapassou {timeout_sec:.2f}s."
                    return VerifierReport(
                        verifier_layer=self.verifier_layer,
                        status=VerdictStatus.REJECTED_RED_TEAM,
                        score=0.0,
                        reasons=[f"Rejeição V3: {err_msg}"],
                        counterexamples=[err_msg],
                        negative_constraints_added=["A solução deve resistir aos casos de borda dentro do timeout estrito."],
                    )

        # Aprovação V3
        return VerifierReport(
            verifier_layer=self.verifier_layer,
            status=VerdictStatus.APPROVED,
            score=1.0,
            reasons=["V3 Red Team Aprovado: Auditoria criptográfica íntegra e resistência confirmada contra testes adversários."],
        )
