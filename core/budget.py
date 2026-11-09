"""
Controlador de Orçamento Rígido com Reserva de Pior Caso (Hard Worst-Case Budget)
e Perfis de Verificação (LIGHT, STANDARD, STRICT).
Impede que ondas paralelas de neurônios estourem o teto financeiro ou de chamadas.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import threading
from typing import Dict


class VerificationProfile(str, Enum):
    """Perfis de verificação explícitos (custo x garantia)."""
    LIGHT = "light"          # Apenas V2 determinístico (custo zero de revisão LLM)
    STANDARD = "standard"    # V2 determinístico + V1 lógico
    STRICT = "strict"        # Expansor + V2 determinístico + V1 lógico + V3 Red Team


class GroundingLevel(str, Enum):
    """Níveis discretos de lastro epistêmico (substitui floats não calibrados)."""
    MACHINE_VERIFIED = "machine_verified"  # 100% verificado por AST/Sandbox/Z3/Citação literal
    LLM_REVIEWED = "llm_reviewed"          # Revisado por LLM independente
    UNVERIFIED = "unverified"              # Sem verificação de máquina


@dataclass(frozen=True)
class ModelPricing:
    """Preço em USD por 1 milhão de tokens."""
    input_per_m: float
    output_per_m: float


MODEL_PRICING_TABLE: Dict[str, ModelPricing] = {
    "gemini-2.5-pro": ModelPricing(1.25, 10.00),
    "gemini-2.5-flash": ModelPricing(0.15, 0.60),
    "gemini-2.0-flash": ModelPricing(0.10, 0.40),
    "claude-opus-4-6": ModelPricing(5.00, 25.00),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00),
    "gpt-4o": ModelPricing(2.50, 10.00),
    "Atria-Dawn": ModelPricing(0.50, 2.00),
    "deterministic/local": ModelPricing(0.0, 0.0),
}

DEFAULT_CONSERVATIVE_PRICE = ModelPricing(10.00, 50.00)


class BudgetExceededError(RuntimeError):
    """Exceção levantada quando o teto de orçamento ou de chamadas é atingido."""
    pass


class HardBudget:
    """
    Orçamento com reserva de pior caso antes de cada chamada.
    Garante que 'spent_usd + reserved_usd' jamais ultrapasse 'max_usd'.
    """

    def __init__(self, max_usd: float = 1.00, max_calls: int = 60) -> None:
        if max_usd <= 0:
            raise ValueError("max_usd deve ser estritamente positivo.")
        self.max_usd = float(max_usd)
        self.max_calls = int(max_calls)
        self.spent_usd = 0.0
        self.reserved_usd = 0.0
        self.calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._lock = threading.RLock()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimativa conservadora (~3 chars por token + margem)."""
        return (len(text) // 3) + 16

    def worst_case_usd(self, model: str, prompt_text: str, max_output_tokens: int = 1024) -> float:
        p = MODEL_PRICING_TABLE.get(model, DEFAULT_CONSERVATIVE_PRICE)
        in_toks = self.estimate_tokens(prompt_text)
        return (in_toks * p.input_per_m + max_output_tokens * p.output_per_m) / 1_000_000.0

    def reserve(self, model: str, prompt_text: str, max_output_tokens: int = 1024) -> float:
        amount = self.worst_case_usd(model, prompt_text, max_output_tokens)
        with self._lock:
            if self.calls >= self.max_calls:
                raise BudgetExceededError(
                    f"Limite de chamadas excedido ({self.calls}/{self.max_calls})."
                )
            if self.spent_usd + self.reserved_usd + amount > self.max_usd:
                raise BudgetExceededError(
                    f"Teto de orçamento excedido: gasto=${self.spent_usd:.4f} + "
                    f"reservado=${self.reserved_usd:.4f} + pior_caso=${amount:.4f} > max=${self.max_usd:.4f}"
                )
            self.reserved_usd += amount
            self.calls += 1
            return amount

    def settle(self, reservation: float, model: str, input_tokens: int, output_tokens: int) -> float:
        p = MODEL_PRICING_TABLE.get(model, DEFAULT_CONSERVATIVE_PRICE)
        actual = (input_tokens * p.input_per_m + output_tokens * p.output_per_m) / 1_000_000.0
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reservation)
            self.spent_usd += actual
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            return actual
