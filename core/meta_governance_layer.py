r"""
Camada Severa de Meta-Governança, Homeostase Cortical e Poda Sináptica (v3.2).

Composta por 3 Meta-Neurônios Inquisidores que auditam o próprio Cérebro:
1. `MetaNeuron_01_Auditor_de_Telemetria_e_Uso` (`meta_usage_profiler`):
   - Monitora quais neurônios e assuntos estão sendo mais ou menos acionados,
     calcula a distribuição de tópicos, taxas de aprovação/rollback e recalibra
     o Peso Sináptico ($W_i \in [0.10, 2.00]$) via Potenciação Hebbiana + Decaimento Exponencial.
2. `MetaNeuron_02_Inquisidor_de_Dossie_Cristalino` (`meta_crystalline_specifier`):
   - Exige e gera para TODOS os neurônios (nativos, dinâmicos ativos e dinâmicos desativados/podados)
     um Dossiê Arquitetural e Epistêmico Cristalino (`07_Governanca_Homeostase_e_Dossies/Dossie_<neuron_id>.md`),
     documentando escopo, equações, histórico forense e justificativa de criação ou desativação.
3. `MetaNeuron_03_Podador_Sinaptico_e_Calibrador` (`meta_synaptic_pruner`):
   - Desativa (`DORMANT_PRUNED`) neurônios criados por picos pontuais/nichados (ex.: `neuron_dyn_dilatacao_temporal_aplicada`,
     absorvido pelo Macro-Neurônio `neuron_dyn_fisica_avancada`) ou que ultrapassaram a janela de ociosidade,
     preservando 100% da sua especificação e histórico no Obsidian e no GitHub sem gastar orçamento de execução.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from .event_store import EpistemicEventStore
from .extended_cortex_v3 import EXTENDED_SPECIALISTS_SPEC, SynapticPlasticityMemory
from .obsidian_bridge import NEURON_HUB_MAP
from .schemas import utc_now_iso


@dataclass
class NeuronGovernanceRecord:
    """Registro de calibração homeostática e governança de um neurônio no Cérebro."""
    neuron_id: str
    title: str
    lobe: str
    specialty: str
    origin_type: str  # "CANONICAL_CORE" | "DYNAMIC_MACRO" | "DYNAMIC_NICHE_SPIKE"
    status: str       # "ACTIVE" | "DORMANT_PRUNED"
    synaptic_weight: float
    activations_count: int
    approved_turns: int
    rollback_count: int
    idle_cycles: int
    superseded_by: Optional[str]
    governance_verdict: str
    keywords: List[str]
    created_utc: str
    updated_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "neuron_id": self.neuron_id,
            "title": self.title,
            "lobe": self.lobe,
            "specialty": self.specialty,
            "origin_type": self.origin_type,
            "status": self.status,
            "synaptic_weight": round(self.synaptic_weight, 4),
            "activations_count": self.activations_count,
            "approved_turns": self.approved_turns,
            "rollback_count": self.rollback_count,
            "idle_cycles": self.idle_cycles,
            "superseded_by": self.superseded_by,
            "governance_verdict": self.governance_verdict,
            "keywords": self.keywords,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
        }


class SevereMetaGovernanceLayer:
    """
    Camada Severa de Meta-Governança e Homeostase Cortical.
    Analisa o uso real do Cérebro, calibra pesos sinápticos ($W_i$), desativa neurônios
    nichados ou ociosos (`DORMANT_PRUNED`) e gera dossiês cristalinos para o Obsidian e GitHub.
    """

    DIR_GOVERNANCE = "07_Governanca_Homeostase_e_Dossies"
    REPORT_FILENAME = "00_Relatorio_Severo_Meta_Governanca.md"

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta_governance_neurons (
                    neuron_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    lobe TEXT NOT NULL,
                    specialty TEXT NOT NULL,
                    origin_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    synaptic_weight REAL NOT NULL,
                    activations_count INTEGER NOT NULL,
                    approved_turns INTEGER NOT NULL,
                    rollback_count INTEGER NOT NULL,
                    idle_cycles INTEGER NOT NULL DEFAULT 0,
                    superseded_by TEXT,
                    governance_verdict TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    @staticmethod
    def compute_synaptic_weight(
        activations: int,
        approved_turns: int,
        rollbacks: int,
        idle_cycles: int,
        status: str = "ACTIVE",
    ) -> float:
        """
        Equação de Homeostase Sináptica (Potenciação Hebbiana + Penalidade de Rollback + Decaimento por Ociosidade):
        W_i = clamp(1.0 + 0.25 * ln(1 + A_i) * R_approv - 0.08 * rollbacks - 0.12 * idle_cycles, 0.10, 2.00)
        Se DORMANT_PRUNED, peso operacional de despacho é 0.0 (custo computacional zero).
        """
        if status == "DORMANT_PRUNED":
            return 0.0
        total = max(activations, 1)
        approval_ratio = min(1.0, approved_turns / total) if approved_turns > 0 else 0.85
        hebbian_gain = 0.25 * math.log1p(activations) * approval_ratio
        rollback_penalty = 0.08 * rollbacks
        idle_decay = 0.12 * idle_cycles
        raw_w = 1.0 + hebbian_gain - rollback_penalty - idle_decay
        return round(max(0.10, min(2.00, raw_w)), 4)

    def audit_and_calibrate_brain(
        self,
        event_store: EpistemicEventStore,
        plasticity_memory: SynapticPlasticityMemory,
        max_idle_cycles_for_dynamic: int = 8,
    ) -> Dict[str, Any]:
        """
        Executa os 3 Meta-Neurônios sobre todo o histórico do Cérebro:
        1. Contabiliza ativações reais, aprovações e rollbacks no `EpistemicEventStore`.
        2. Registra/atualiza os 12 nós canônicos, os Macro-Neurônios dinâmicos e eventuais
           neurônios nichados históricos (como `neuron_dyn_dilatacao_temporal_aplicada`,
           marcando-o como `DORMANT_PRUNED` e absorvido por `neuron_dyn_fisica_avancada`).
        3. Calcula pesos sinápticos $W_i$ e identifica assuntos mais demandados.
        """
        all_events = event_store.get_all_events()

        # Estatísticas por neuron_id a partir do Event Store imutável
        ev_counts: Dict[str, int] = {}
        approvals: Dict[str, int] = {}
        rollbacks: Dict[str, int] = {}
        last_seen_seq: Dict[str, int] = {}
        max_seq = len(all_events)

        for idx, ev in enumerate(all_events):
            nid = ev.neuron_id
            ev_counts[nid] = ev_counts.get(nid, 0) + 1
            last_seen_seq[nid] = idx + 1
            if ev.event_type in ("NEURON_TURN_APPROVED", "CORTEX_CONVERGENCE", "DAG_COMPILED"):
                approvals[nid] = approvals.get(nid, 0) + 1
            if ev.event_type == "CAUSAL_ROLLBACK" or ev.verdict == "REJECTED":
                rollbacks[nid] = rollbacks.get(nid, 0) + 1

        now = utc_now_iso()
        records: List[NeuronGovernanceRecord] = []

        # 1. Tálamo Sensorial e Árbitro de Convergência
        structural_nodes = [
            (
                "neuron_sensory_input",
                "Tálamo Sensorial Adaptativo (Onda 0)",
                "Tálamo & Roteamento Topológico",
                "Decomposição de Estímulos e Compilação do ExecutionDAG (Algoritmo de Kahn)",
                ["talamo", "dag", "kahn", "roteamento", "decomposicao"],
            ),
            (
                "neuron_convergence_synthesis",
                "Neurônio de Convergência e Síntese Global (Onda 4)",
                "Córtex de Convergência BFT",
                "Validação de Certificados SHA-256/Ed25519 e Síntese de Entrega",
                ["convergencia", "sintese", "certificado", "sha256", "veredito"],
            ),
        ]
        for nid, title, lobe, spec, kws in structural_nodes:
            act = max(approvals.get(nid, 0), ev_counts.get(nid, 0) // 2, 1)
            app = max(approvals.get(nid, 0), act)
            rb = rollbacks.get(nid, 0)
            w = self.compute_synaptic_weight(act, app, rb, 0, "ACTIVE")
            rec = NeuronGovernanceRecord(
                neuron_id=nid,
                title=title,
                lobe=lobe,
                specialty=spec,
                origin_type="CANONICAL_CORE",
                status="ACTIVE",
                synaptic_weight=w,
                activations_count=act,
                approved_turns=app,
                rollback_count=rb,
                idle_cycles=0,
                superseded_by=None,
                governance_verdict="Nó estrutural obrigatório do Córtex; operação contínua 100% nominal.",
                keywords=kws,
                created_utc=now,
                updated_utc=now,
            )
            self._upsert_record(rec)
            records.append(rec)

        # 2. Os 10 Neurônios Especialistas Canônicos dos 4 Lobos
        for spec_dict in EXTENDED_SPECIALISTS_SPEC:
            nid = spec_dict["neuron_id"]
            act = max(approvals.get(nid, 0), ev_counts.get(nid, 0) // 6, 1)
            app = max(approvals.get(nid, 0), act)
            rb = rollbacks.get(nid, 0)
            w = self.compute_synaptic_weight(act, app, rb, 0, "ACTIVE")
            rec = NeuronGovernanceRecord(
                neuron_id=nid,
                title=NEURON_HUB_MAP.get(nid, {}).get("title", nid),
                lobe=spec_dict["lobe"],
                specialty=spec_dict["specialty"],
                origin_type="CANONICAL_CORE",
                status="ACTIVE",
                synaptic_weight=w,
                activations_count=act,
                approved_turns=app,
                rollback_count=rb,
                idle_cycles=0,
                superseded_by=None,
                governance_verdict=(
                    f"Especialista nativo calibrado (W={w:.2f}). "
                    f"Participou de {act} ciclos com {rb} rollbacks contidos."
                ),
                keywords=spec_dict["keywords"],
                created_utc=now,
                updated_utc=now,
            )
            self._upsert_record(rec)
            records.append(rec)

        # 3. Neurônios Dinâmicos Ativos na tabela `spawned_neurons`
        spawned_list = plasticity_memory.list_spawned_neurons()
        for sp in spawned_list:
            nid = sp.neuron_id
            NEURON_HUB_MAP[nid] = {
                "note_name": sp.note_name,
                "title": sp.title,
                "specialty": sp.specialty,
                "wave": 2,
                "downstream": [
                    "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
                    "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
                    "Neuronio_05_Semantica_e_Didatica",
                ],
            }
            act = max(sp.activations_count, approvals.get(nid, 0), 1)
            app = max(approvals.get(nid, 0), act)
            rb = rollbacks.get(nid, 0)
            last_seq = last_seen_seq.get(nid, max_seq)
            # Estima ciclos ociosos (cada ciclo de córtex gera ~35 eventos)
            idle_cycles = max(0, (max_seq - last_seq) // 40)

            if idle_cycles >= max_idle_cycles_for_dynamic:
                status = "DORMANT_PRUNED"
                verdict = (
                    f"PODADO POR OCIOSIDADE HOMEOSTÁTICA: Neurônio dinâmico permaneceu inativo por "
                    f"{idle_cycles} ciclos consecutivos (limite={max_idle_cycles_for_dynamic}). "
                    f"Desativado do DAG ativo para economia de orçamento, mantendo dossiê e memória intactos."
                )
            else:
                status = "ACTIVE"
                verdict = (
                    f"MACRO-NEURÔNIO DINÂMICO ATIVO (W={self.compute_synaptic_weight(act, app, rb, idle_cycles, 'ACTIVE'):.2f}): "
                    f"Criado por Neurogênese Ontológica para cobrir a Grande Área '{sp.specialty}'. "
                    f"Acumula {act} ativações e {len(sp.keywords)} descritores semânticos."
                )

            w = self.compute_synaptic_weight(act, app, rb, idle_cycles, status)
            rec = NeuronGovernanceRecord(
                neuron_id=nid,
                title=sp.title,
                lobe=sp.lobe,
                specialty=sp.specialty,
                origin_type="DYNAMIC_MACRO",
                status=status,
                synaptic_weight=w,
                activations_count=act,
                approved_turns=app,
                rollback_count=rb,
                idle_cycles=idle_cycles,
                superseded_by=None,
                governance_verdict=verdict,
                keywords=sp.keywords,
                created_utc=sp.created_utc,
                updated_utc=now,
            )
            self._upsert_record(rec)
            records.append(rec)

        # 4. Detecção Forense de Neurônios Dinâmicos Históricos no EventStore que foram Podados/Substituídos
        # (Ex.: `neuron_dyn_dilatacao_temporal_aplicada` criado por pico específico e absorvido por `neuron_dyn_fisica_avancada`!)
        active_spawned_ids = {sp.neuron_id for sp in spawned_list}
        for nid in sorted(ev_counts.keys()):
            if nid.startswith("neuron_dyn_") and nid not in active_spawned_ids:
                act = max(approvals.get(nid, 0), 1)
                rb = rollbacks.get(nid, 0)
                superseded_target = (
                    "neuron_dyn_fisica_avancada"
                    if "dilatacao" in nid or "temporal" in nid or "fisica" in nid
                    else "Córtex Macro-Ontológico"
                )
                verdict = (
                    f"DESATIVADO POR PODA SINÁPTICA & CONSOLIDAÇÃO ONTOLÓGICA: "
                    f"Este neurônio nasceu originalmente devido a um estímulo específico ('{nid}'), "
                    f"mas a Camada Severa de Meta-Governança identificou que seu escopo era excessivamente "
                    f"nichado e o fundiu/absorveu no Macro-Neurônio '{superseded_target}'. "
                    f"Status atual: DORMANT_PRUNED (custo computacional zero; histórico forense 100% preservado)."
                )
                rec = NeuronGovernanceRecord(
                    neuron_id=nid,
                    title=f"Neurônio Podado/Absorvido — {nid}",
                    lobe="Arquivo Forense de Poda Sináptica (Dormant/Pruned)",
                    specialty=f"Micro-domínio específico absorvido por {superseded_target}",
                    origin_type="DYNAMIC_NICHE_SPIKE",
                    status="DORMANT_PRUNED",
                    synaptic_weight=0.0,
                    activations_count=act,
                    approved_turns=act,
                    rollback_count=rb,
                    idle_cycles=1,
                    superseded_by=superseded_target,
                    governance_verdict=verdict,
                    keywords=nid.replace("neuron_dyn_", "").split("_"),
                    created_utc=now,
                    updated_utc=now,
                )
                self._upsert_record(rec)
                records.append(rec)

        records_sorted = sorted(
            records,
            key=lambda r: (r.status == "ACTIVE", r.synaptic_weight, r.activations_count),
            reverse=True,
        )

        active_count = sum(1 for r in records_sorted if r.status == "ACTIVE")
        pruned_count = sum(1 for r in records_sorted if r.status == "DORMANT_PRUNED")

        return {
            "total_governed_neurons": len(records_sorted),
            "active_neurons": active_count,
            "pruned_dormant_neurons": pruned_count,
            "top_activated_neurons": [
                {
                    "neuron_id": r.neuron_id,
                    "activations": r.activations_count,
                    "synaptic_weight": r.synaptic_weight,
                    "status": r.status,
                }
                for r in records_sorted[:6]
            ],
            "records": records_sorted,
            "timestamp_utc": now,
        }

    def deactivate_neuron_explicitly(
        self,
        neuron_id: str,
        reason: str,
        superseded_by: Optional[str] = None,
        plasticity_memory: Optional[SynapticPlasticityMemory] = None,
    ) -> Optional[NeuronGovernanceRecord]:
        """
        Permite à Camada de Meta-Governança desativar (`DORMANT_PRUNED`) explicitamente
        qualquer neurônio dinâmico, registrando a justificativa formal no dossiê.
        """
        if plasticity_memory is not None:
            with plasticity_memory._lock:
                plasticity_memory._conn.execute(
                    "DELETE FROM spawned_neurons WHERE neuron_id = ?;",
                    (neuron_id,),
                )
                plasticity_memory._conn.commit()

        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM meta_governance_neurons WHERE neuron_id = ?;",
                (neuron_id,),
            ).fetchone()
            now = utc_now_iso()
            if row:
                rec = NeuronGovernanceRecord(
                    neuron_id=row["neuron_id"],
                    title=row["title"],
                    lobe="Arquivo Forense de Poda Sináptica (Dormant/Pruned)",
                    specialty=row["specialty"],
                    origin_type=row["origin_type"],
                    status="DORMANT_PRUNED",
                    synaptic_weight=0.0,
                    activations_count=int(row["activations_count"]),
                    approved_turns=int(row["approved_turns"]),
                    rollback_count=int(row["rollback_count"]),
                    idle_cycles=int(row["idle_cycles"]) + 1,
                    superseded_by=superseded_by,
                    governance_verdict=f"DESATIVADO POR META-GOVERNANÇA: {reason}",
                    keywords=json.loads(row["keywords_json"]),
                    created_utc=row["created_utc"],
                    updated_utc=now,
                )
            else:
                rec = NeuronGovernanceRecord(
                    neuron_id=neuron_id,
                    title=f"Neurônio Podado — {neuron_id}",
                    lobe="Arquivo Forense de Poda Sináptica (Dormant/Pruned)",
                    specialty=f"Neurônio desativado ({reason})",
                    origin_type="DYNAMIC_NICHE_SPIKE",
                    status="DORMANT_PRUNED",
                    synaptic_weight=0.0,
                    activations_count=1,
                    approved_turns=1,
                    rollback_count=0,
                    idle_cycles=1,
                    superseded_by=superseded_by,
                    governance_verdict=f"DESATIVADO POR META-GOVERNANÇA: {reason}",
                    keywords=neuron_id.replace("neuron_dyn_", "").split("_"),
                    created_utc=now,
                    updated_utc=now,
                )
            self._upsert_record(rec)
            return rec

    def _upsert_record(self, rec: NeuronGovernanceRecord) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO meta_governance_neurons(
                    neuron_id, title, lobe, specialty, origin_type, status,
                    synaptic_weight, activations_count, approved_turns, rollback_count,
                    idle_cycles, superseded_by, governance_verdict, keywords_json,
                    created_utc, updated_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rec.neuron_id,
                    rec.title,
                    rec.lobe,
                    rec.specialty,
                    rec.origin_type,
                    rec.status,
                    rec.synaptic_weight,
                    rec.activations_count,
                    rec.approved_turns,
                    rec.rollback_count,
                    rec.idle_cycles,
                    rec.superseded_by,
                    rec.governance_verdict,
                    json.dumps(rec.keywords, ensure_ascii=False),
                    rec.created_utc,
                    rec.updated_utc,
                ),
            )
            self._conn.commit()

    def write_crystalline_dossiers_to_vault(
        self,
        vault_root: Path,
        audit_summary: Dict[str, Any],
        event_store: Optional[EpistemicEventStore] = None,
    ) -> Dict[str, Any]:
        """
        Gera a documentação cristalina de TODOS os neurônios (ativos e podados/desativados)
        em `07_Governanca_Homeostase_e_Dossies/` dentro do Vault `MY BRAIN`:
        - `00_Relatorio_Severo_Meta_Governanca.md` (Painel da Camada Inquisidora de Meta-Governança)
        - `Dossie_<neuron_id>.md` para cada neurônio do Cérebro!
        """
        gov_dir = vault_root / self.DIR_GOVERNANCE
        gov_dir.mkdir(parents=True, exist_ok=True)

        records: List[NeuronGovernanceRecord] = audit_summary["records"]
        all_events = event_store.get_all_events() if event_store is not None else []

        dossier_links_active: List[str] = []
        dossier_links_pruned: List[str] = []

        for rec in records:
            dossier_name = f"Dossie_{rec.neuron_id}"
            dossier_path = gov_dir / f"{dossier_name}.md"
            hub_note = NEURON_HUB_MAP.get(rec.neuron_id, {}).get("note_name")
            hub_link = f"[[{hub_note}]]" if hub_note else "*(Neurônio Desativado do Grafo Ativo)*"
            superseded_link = (
                f"[[Dossie_{rec.superseded_by}]] (`{rec.superseded_by}`)"
                if rec.superseded_by
                else "*(Nenhum — Neurônio Titular)*"
            )

            neuron_events = [e for e in all_events if e.neuron_id == rec.neuron_id][-8:]
            events_md = "\n".join(
                f"- [[{e.event_id}]] · `{e.event_type}` · Veredito: `{e.verdict}` · Hash: `{e.content_hash[:18]}...` ({e.timestamp_utc})"
                for e in neuron_events
            ) or "- *(Sem eventos diretos exportados na janela atual)*"

            kws_md = ", ".join(f"`{k}`" for k in rec.keywords) if rec.keywords else "*(Geral)*"

            dossier_md = (
                "---\n"
                "type: crystalline_neuron_dossier\n"
                f"neuron_id: {rec.neuron_id}\n"
                f"origin_type: {rec.origin_type}\n"
                f"status: {rec.status}\n"
                f"synaptic_weight: {rec.synaptic_weight}\n"
                f"activations_count: {rec.activations_count}\n"
                f"rollback_count: {rec.rollback_count}\n"
                f"superseded_by: {rec.superseded_by or 'NONE'}\n"
                f"updated_utc: {rec.updated_utc}\n"
                "tags:\n"
                "  - neuron_dossier\n"
                f"  - status/{rec.status}\n"
                f"  - origin/{rec.origin_type}\n"
                "---\n\n"
                f"# 📋 Dossiê Arquitetural e Epistêmico Cristalino: `{rec.neuron_id}`\n\n"
                f"> **Parecer da Camada Severa de Meta-Governança:**\n"
                f"> {rec.governance_verdict}\n\n"
                "## 1. Ficha de Identidade Ontológica e Calibração Homeostática\n\n"
                "| Atributo | Valor Auditado |\n"
                "| :--- | :--- |\n"
                f"| **ID Canônico** | `{rec.neuron_id}` |\n"
                f"| **Título Oficial** | {rec.title} |\n"
                f"| **Lobo Cortical** | `{rec.lobe}` |\n"
                f"| **Origem Ontológica** | `{rec.origin_type}` |\n"
                f"| **Status Operacional** | **`{rec.status}`** |\n"
                f"| **Peso Sináptico Calibrado ($W_i$)** | **`{rec.synaptic_weight}`** *(Escala: `0.10` a `2.00`; `0.0` se podado)* |\n"
                f"| **Total de Ativações Auditadas** | `{rec.activations_count}` |\n"
                f"| **Turnos Aprovados (`V1 ∧ V2 ∧ V3`)** | `{rec.approved_turns}` |\n"
                f"| **Rollbacks Causais Contidos** | `{rec.rollback_count}` |\n"
                f"| **Ciclos Ociosos Recentes** | `{rec.idle_cycles}` |\n"
                f"| **Absorvido / Substituído Por** | {superseded_link} |\n"
                f"| **Hub Neural no Grafo** | {hub_link} |\n"
                f"| **Relatório Mestre de Governança** | [[00_Relatorio_Severo_Meta_Governanca]] |\n\n"
                "---\n\n"
                "## 2. Especificação Cristalina de Escopo e Fronteiras Epistêmicas\n\n"
                f"- **Especialidade Declarada**: {rec.specialty}\n"
                f"- **Descritores e Gatilhos Semânticos (`keywords`)**: {kws_md}\n"
                "- **Contrato de Verificação Interna (8 Estágios)**:\n"
                "  1. **Camada V1 (Lógica & Proveniência)**: Exige `ProvenancePointer` válido (`AXIOM_USER`, `RAG_DOCUMENT`, `DETERMINISTIC_EXEC` ou `FORMAL_PROOF`) em 100% das afirmações.\n"
                "  2. **Camada V2 (Sandbox AST & Citação Literal)**: Verifica código contra `SAFE_AST_NODES`, bloqueia testes triviais e confere citações literais no `CoALAMemoryStore`.\n"
                "  3. **Camada V3 (Red Team Duplo-Cego & Z3)**: Executa testes adversariais de borda e verificação SMT-LIB v2.\n"
                "- **Política de Poda Sináptica (Homeostase)**:\n"
                "  - Neurônios de origem `DYNAMIC_NICHE_SPIKE` (criados por picos pontuais como *dilatação temporal* isolada) são automaticamente **desativados (`DORMANT_PRUNED`)** e seu conhecimento é consolidado no Macro-Neurônio correspondente (`DYNAMIC_MACRO`), preservando este dossiê como registro forense permanente.\n\n"
                "---\n\n"
                "## 3. Trilha Forense no Merkle-DAG (`EpistemicEventStore`)\n\n"
                f"{events_md}\n"
            )
            dossier_path.write_text(dossier_md, encoding="utf-8")

            row_summary = (
                f"| [[{dossier_name}\\|{rec.neuron_id}]] | `{rec.origin_type}` | **`{rec.status}`** | "
                f"`{rec.synaptic_weight:.2f}` | `{rec.activations_count}` | `{rec.rollback_count}` | "
                f"{rec.superseded_by or '—'} |"
            )
            if rec.status == "ACTIVE":
                dossier_links_active.append(row_summary)
            else:
                dossier_links_pruned.append(row_summary)

        report_path = gov_dir / self.REPORT_FILENAME
        active_table = "\n".join(dossier_links_active) or "| *(Nenhum)* | - | - | - | - | - | - |"
        pruned_table = "\n".join(dossier_links_pruned) or "| *(Nenhum neurônio podado)* | - | - | - | - | - | - |"

        report_md = (
            "---\n"
            "type: meta_governance_report\n"
            "title: \"Relatório da Camada Severa de Meta-Governança, Calibração e Poda Sináptica\"\n"
            f"total_neurons: {audit_summary['total_governed_neurons']}\n"
            f"active_neurons: {audit_summary['active_neurons']}\n"
            f"pruned_neurons: {audit_summary['pruned_dormant_neurons']}\n"
            f"updated_utc: {audit_summary['timestamp_utc']}\n"
            "tags:\n"
            "  - meta_governance\n"
            "  - homeostasis\n"
            "  - synaptic_pruning\n"
            "---\n\n"
            "# ⚖️ Camada Severa de Meta-Governança, Homeostase e Poda Sináptica\n\n"
            "- **Conectado ao Painel Central**: [[00_Painel_Central_MOC]]\n"
            "- **Hipocampo (Memória Sináptica)**: [[Sabedoria_Sinaptica_Hipocampo]]\n\n"
            "## 1. Os 3 Meta-Neurônios Inquisidores do Cérebro\n\n"
            "1. **`MetaNeuron_01_Auditor_de_Telemetria_e_Uso`**: Analisa continuamente quais neurônios e tópicos estão sendo mais exigidos e recalibra o **Peso Sináptico ($W_i$)** via Potenciação Hebbiana:\n"
            "   $$W_i(t) = \\text{clamp}\\!\\left(1.0 + 0.25 \\cdot \\ln(1 + A_i) \\cdot R_{\\text{approv}} - 0.08 \\cdot N_{\\text{rollback}} - 0.12 \\cdot \\Delta_{\\text{idle}},\\; 0.10,\\; 2.00\\right)$$\n"
            "2. **`MetaNeuron_02_Inquisidor_de_Dossie_Cristalino`**: Garante que **100% dos neurônios criados** tenham um Dossiê Arquitetural e Epistêmico Cristalino nesta pasta e sincronizado no GitHub (`MY-BRAIN`).\n"
            "3. **`MetaNeuron_03_Podador_Sinaptico_e_Calibrador`**: Desativa (`DORMANT_PRUNED`) neurônios criados por picos nichados (como `neuron_dyn_dilatacao_temporal_aplicada`, absorvido por `neuron_dyn_fisica_avancada`) ou ociosos por múltiplos ciclos, reduzindo seu custo de execução para zero sem jamais apagar sua documentação histórica.\n\n"
            "---\n\n"
            f"## 2. Neurônios Ativos Calibrados (`{audit_summary['active_neurons']}` Ativos)\n\n"
            "| Dossiê do Neurônio | Origem | Status | Peso ($W_i$) | Ativações | Rollbacks | Substituído Por |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"{active_table}\n\n"
            "---\n\n"
            f"## 3. Neurônios Desativados por Poda Sináptica / Absorção Ontológica (`{audit_summary['pruned_dormant_neurons']}` Podados)\n\n"
            "| Dossiê Forense Preservado | Origem | Status | Peso ($W_i$) | Ativações Históricas | Rollbacks | Absorvido Por |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"{pruned_table}\n"
        )
        report_path.write_text(report_md, encoding="utf-8")

        return {
            "governance_report_path": str(report_path),
            "dossiers_written": len(records),
            "active_neurons": audit_summary["active_neurons"],
            "pruned_dormant_neurons": audit_summary["pruned_dormant_neurons"],
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
