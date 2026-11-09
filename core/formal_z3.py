"""
Política AST Baseada em Allowlist Estrita, Detector de Testes Triviais (Tautologias)
e Verificador Formal SMT-LIB via Z3 Solver.
"""

from __future__ import annotations
import ast
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import FrozenSet, List, Optional, Set, Tuple

from .schemas import VerdictStatus

ALLOWED_STDLIB_MODULES: FrozenSet[str] = frozenset({
    "abc", "array", "base64", "binascii", "bisect", "calendar", "cmath", "collections",
    "contextlib", "copy", "dataclasses", "datetime", "decimal", "enum", "fractions",
    "functools", "graphlib", "hashlib", "heapq", "hmac", "itertools", "json", "math",
    "numbers", "operator", "pprint", "random", "re", "secrets", "statistics", "string",
    "struct", "textwrap", "time", "typing", "unicodedata", "uuid", "zlib",
})

DENIED_BUILTIN_CALLS: FrozenSet[str] = frozenset({
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "globals", "locals", "vars", "help", "exit", "quit", "memoryview",
})

DENIED_INTROSPECTION_ATTRS: FrozenSet[str] = frozenset({
    "__class__", "__bases__", "__base__", "__mro__", "__subclasses__", "__globals__",
    "__builtins__", "__code__", "__closure__", "__dict__", "__getattribute__",
    "__import__", "__loader__", "__spec__", "__self__", "__func__", "__reduce__",
    "__reduce_ex__", "__getstate__", "__setstate__", "__init_subclass__",
    "f_globals", "f_locals", "f_back", "f_builtins", "gi_frame", "cr_frame", "tb_frame",
})


@dataclass(frozen=True)
class ASTPolicyViolation:
    lineno: int
    message: str

    def __str__(self) -> str:
        return f"Linha {self.lineno}: {self.message}"


def check_ast_allowlist(
    code: str,
    allowed_modules: FrozenSet[str] = ALLOWED_STDLIB_MODULES,
) -> List[ASTPolicyViolation]:
    """
    Aplica política de segurança estática baseada em Allowlist de módulos
    e bloqueio de introspecção de frames/objetos Python (defesa contra sandbox escape).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [ASTPolicyViolation(exc.lineno or 0, f"Erro de sintaxe: {exc.msg}")]

    violations: List[ASTPolicyViolation] = []
    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in allowed_modules:
                    violations.append(
                        ASTPolicyViolation(lineno, f"Import de módulo fora da allowlist: '{alias.name}'")
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                violations.append(ASTPolicyViolation(lineno, "Import relativo não permitido"))
            root = (node.module or "").split(".")[0]
            if root not in allowed_modules:
                violations.append(
                    ASTPolicyViolation(lineno, f"Import de módulo fora da allowlist: '{node.module}'")
                )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fname = node.func.id
            if fname in DENIED_BUILTIN_CALLS:
                violations.append(ASTPolicyViolation(lineno, f"Chamada builtin proibida: {fname}()"))
            elif fname in ("getattr", "setattr", "delattr"):
                attr_arg = node.args[1] if len(node.args) > 1 else None
                if not (isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str)):
                    violations.append(ASTPolicyViolation(lineno, f"{fname}() dinâmico não permitido"))
                elif attr_arg.value.startswith("__") or attr_arg.value in DENIED_INTROSPECTION_ATTRS:
                    violations.append(
                        ASTPolicyViolation(lineno, f"{fname}() com atributo proibido: '{attr_arg.value}'")
                    )
        elif isinstance(node, ast.Attribute) and node.attr in DENIED_INTROSPECTION_ATTRS:
            violations.append(
                ASTPolicyViolation(lineno, f"Acesso a atributo de introspecção proibido: '.{node.attr}'")
            )
    return violations


def detect_trivial_tests(code: str, invariant_expressions: List[str]) -> Optional[str]:
    """
    Detecta se os testes/invariantes são triviais ou tautológicos (ex: 'assert True' ou '1 == 1')
    e garante que pelo menos um símbolo definido no código seja referenciado nos invariantes.
    """
    if not invariant_expressions:
        return "Nenhum invariante/teste fornecido para comprovar o funcionamento do código."
    try:
        code_tree = ast.parse(code)
    except SyntaxError:
        return None

    defined_symbols: Set[str] = set()
    for n in ast.walk(code_tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_symbols.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    defined_symbols.add(t.id)

    referenced_symbols: Set[str] = set()
    non_trivial_count = 0

    for expr in invariant_expressions:
        clean = expr.strip()
        if clean.startswith("assert "):
            clean = clean[7:].strip()
        try:
            expr_tree = ast.parse(clean, mode="eval")
        except SyntaxError:
            return f"Invariante com erro de sintaxe: '{expr}'"

        if not isinstance(expr_tree.body, ast.Constant):
            non_trivial_count += 1
        for n in ast.walk(expr_tree):
            if isinstance(n, ast.Name):
                referenced_symbols.add(n.id)

    if non_trivial_count == 0:
        return "Todos os invariantes são constantes triviais (ex: 'True'); nenhum teste real executado."
    if defined_symbols and not (defined_symbols & referenced_symbols):
        return (
            f"Os invariantes não invocam nenhuma função/símbolo definido no código ({sorted(defined_symbols)})."
        )
    return None


def run_smtlib_formal_check(
    smtlib_script: str,
    expected_sat: str = "unsat",
    timeout_ms: int = 4000,
) -> Tuple[VerdictStatus, str]:
    """
    Executa uma verificação formal SMT-LIB 2.0 via Z3 (módulo Python ou binário z3).
    Convenção: para provar uma propriedade P, afirma-se (not P) e espera-se 'unsat'.
    Bloqueia diretivas perigosas como (set-option, (include, (reset, (exit.
    """
    lowered = smtlib_script.lower()
    for forbidden in ("(set-option", "(include", "(reset", "(exit"):
        if forbidden in lowered:
            return (
                VerdictStatus.REJECTED_GROUNDING,
                f"Diretiva SMT-LIB bloqueada por segurança: '{forbidden}'",
            )

    # 1. Tenta módulo z3 se instalado no Python atual
    try:
        import z3  # type: ignore
        solver = z3.Solver()
        solver.set("timeout", timeout_ms)
        solver.from_string(smtlib_script)
        res = solver.check()
        got = "sat" if res == z3.sat else ("unsat" if res == z3.unsat else "unknown")
        if got == expected_sat:
            return (VerdictStatus.APPROVED, f"Z3 confirmou '{got}' (esperado: '{expected_sat}').")
        return (
            VerdictStatus.REJECTED_GROUNDING,
            f"Z3 refutou a prova: esperado '{expected_sat}', obtido '{got}'.",
        )
    except ImportError:
        pass
    except Exception as exc:
        return (VerdictStatus.REJECTED_GROUNDING, f"Erro Z3: {exc}")

    # 2. Tenta binário z3 no PATH do sistema
    z3_bin = shutil.which("z3")
    if z3_bin:
        full_smt = smtlib_script.strip() + "\n(check-sat)\n"
        try:
            proc = subprocess.run(
                [z3_bin, "-in", f"-T:{max(1, timeout_ms // 1000)}"],
                input=full_smt,
                capture_output=True,
                text=True,
                timeout=(timeout_ms / 1000.0) + 1.0,
            )
            out_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            got = out_lines[-1] if out_lines else "unknown"
            if got == expected_sat:
                return (VerdictStatus.APPROVED, f"Z3 CLI confirmou '{got}'.")
            return (
                VerdictStatus.REJECTED_GROUNDING,
                f"Z3 CLI refutou: esperado '{expected_sat}', obtido '{got}'.",
            )
        except Exception as exc:
            return (VerdictStatus.REJECTED_GROUNDING, f"Falha ao executar Z3 CLI: {exc}")

    return (
        VerdictStatus.REJECTED_GROUNDING,
        "Solver Z3 não encontrado no ambiente (resultado INCONCLUSIVO nunca aprova por omissão).",
    )
