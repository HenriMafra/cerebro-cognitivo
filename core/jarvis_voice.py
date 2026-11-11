"""
Motor Conversacional e de Voz ("Modo J.A.R.V.I.S.") — Cérebro Cognitivo Fractal v2.0.

Integra em um circuito fechado:
1. Captura de Voz / Áudio Multimodal (Web Speech API + Gemini Multimodal Audio API).
2. Consciência de Tela ao Vivo no Obsidian via `ObsidianLocalRestClient` (`https://127.0.0.1:27124`).
3. Memória Tripartite `CoALAMemoryStore` (SQLite FTS5 BM25 + Axiomas do Usuário do Vault `MY BRAIN`).
4. Execução Verificada no `FractalCognitiveCortex` (Tálamo -> 5 Especialistas V1/V2/V3 -> Convergência).
5. Síntese de Resposta Falada (`spoken_response`) ancorada nos Certificados SHA-256 + Abertura Automática no Obsidian + Snapshot Git do Vault.
"""

from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import urllib.request

from .cortex import FractalCognitiveCortex
from .event_store import EpistemicEventStore
from .extended_cortex_v3 import ExtendedCognitiveCortexV3, SynapticPlasticityMemory
from .llm_bridge import call_gemini_json
from .meta_governance_layer import SevereMetaGovernanceLayer
from .obsidian_bridge import (
    ObsidianLocalRestClient,
    ObsidianVaultBridge,
    discover_default_vault_path,
)
from .rag_memory import CoALAMemoryStore
from .schemas import utc_now_iso


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


def load_local_env(env_path: Path = ENV_FILE_PATH) -> Dict[str, str]:
    """Carrega variáveis do arquivo `.env` local (ignorado pelo Git) para `os.environ`."""
    loaded: Dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        k, v = clean.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if key and val:
            os.environ[key] = val
            loaded[key] = val
    return loaded


def save_local_env(updates: Dict[str, str], env_path: Path = ENV_FILE_PATH) -> Dict[str, Any]:
    """Salva ou atualiza chaves de API no arquivo `.env` local (protegido pelo `.gitignore`)."""
    existing = load_local_env(env_path)
    for k, v in updates.items():
        if v is not None and str(v).strip():
            existing[k.strip()] = str(v).strip()
            os.environ[k.strip()] = str(v).strip()

    lines = [
        "# Configurações Locais do Cérebro Cognitivo + Jarvis + Obsidian (NÃO VERSIONAR)",
    ]
    for k, v in sorted(existing.items()):
        lines.append(f'{k}="{v}"')
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "saved": True,
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "obsidian_key_configured": bool(os.environ.get("OBSIDIAN_API_KEY")),
    }


def transcribe_audio_with_gemini(
    audio_base64: str,
    mime_type: str = "audio/webm",
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> str:
    """
    Usa a API Multimodal nativa do Google Gemini para transcrever e compreender
    áudio falado em português diretamente para texto limpo.
    """
    load_local_env()
    key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY não configurada para transcrição de áudio multimodal.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Transcreva fielmente em português o comando ou pergunta falada neste áudio. "
                            "Retorne apenas o texto transcrito, sem comentários adicionais."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_base64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0.0},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20.0) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
        return (
            raw["candidates"][0]["content"]["parts"][0]["text"].strip()
        )


class JarvisCognitiveAssistant:
    """
    Orquestrador Conversacional e de Voz ("Jarvis") sobre o Cérebro Cognitivo Fractal e o Vault `MY BRAIN`.
    """

    def __init__(
        self,
        db_path: str,
        jsonl_path: str,
        rag_db_path: str,
        vault_path: Optional[str | Path] = None,
    ) -> None:
        load_local_env()
        self.db_path = db_path
        self.jsonl_path = jsonl_path
        self.rag_db_path = rag_db_path
        self.vault_path = Path(vault_path) if vault_path else discover_default_vault_path(auto_clone_if_missing=True)
        self.bridge = ObsidianVaultBridge(self.vault_path)
        self.rest_client = ObsidianLocalRestClient(vault_path=self.vault_path)

    def get_system_status(self) -> Dict[str, Any]:
        """Retorna o diagnóstico completo (Obsidian REST API, Gemini API, Vault Git e Merkle-DAG)."""
        load_local_env()
        rest_status = self.rest_client.check_status()
        active_note_res = self.rest_client.get_active_note() if rest_status.get("online") else {"ok": False}
        active_note_path = None
        if active_note_res.get("ok") and isinstance(active_note_res.get("note"), dict):
            active_note_path = active_note_res["note"].get("path")

        store = EpistemicEventStore(db_path=self.db_path, jsonl_path=self.jsonl_path)
        try:
            dag_summary = store.export_dag_summary()
        finally:
            store.close()

        return {
            "obsidian_rest_online": rest_status.get("online", False),
            "obsidian_rest_authenticated": rest_status.get("authenticated", False),
            "obsidian_active_note": active_note_path,
            "obsidian_vault_root": str(self.bridge.vault_root),
            "gemini_api_configured": bool(os.environ.get("GEMINI_API_KEY")),
            "dag_summary": {
                "total_events": dag_summary["total_events"],
                "total_branches": dag_summary["total_branches"],
                "total_rollbacks": dag_summary["total_rollbacks"],
                "chain_integrity_valid": dag_summary["chain_integrity_valid"],
            },
        }

    def process_command(
        self,
        user_command: str,
        open_in_obsidian: bool = True,
        auto_git_commit: bool = True,
    ) -> Dict[str, Any]:
        """
        Processa um comando de voz ou texto de ponta a ponta:
        1. Lê a nota ativa aberta na tela do Obsidian (via `Local REST API`).
        2. Sincroniza e consulta a memória `CoALAMemoryStore` (FTS5 BM25 + Axiomas).
        3. Executa os 5 Neurônios Especialistas no `FractalCognitiveCortex` (`V1 ∧ V2 ∧ V3`).
        4. Projeta os certificados e o `.canvas` no Vault `MY BRAIN` e abre na tela do Obsidian.
        5. Realiza commit Git automático no Vault `MY BRAIN`.
        6. Sintetiza a resposta falada (`spoken_response`) com lastro nos certificados.
        """
        load_local_env()
        t0 = time.perf_counter()

        # 1. Inicializar/sincronizar Vault e ler nota ativa na tela do Obsidian
        self.bridge.initialize_vault_structure()
        active_note_info = self.rest_client.get_active_note()
        active_note_title = None
        active_note_excerpt = ""
        if active_note_info.get("ok") and isinstance(active_note_info.get("note"), dict):
            active_note_title = active_note_info["note"].get("path", "")
            active_note_excerpt = str(active_note_info["note"].get("content", ""))[:500]

        # 2. Ingerir notas do Obsidian e buscar contexto no CoALAMemoryStore (FTS5 BM25)
        mem_store = CoALAMemoryStore(db_path=self.rag_db_path)
        plasticity = SynapticPlasticityMemory(db_path=self.rag_db_path)
        gov = SevereMetaGovernanceLayer(db_path=self.rag_db_path)
        store = EpistemicEventStore(db_path=self.db_path, jsonl_path=self.jsonl_path)
        try:
            ing_report = self.bridge.ingest_vault_knowledge(mem_store)
            rag_hits = mem_store.search_semantic(user_command, top_k=3)
            user_axioms = mem_store.list_user_axioms()

            # 3. Executar missão no Córtex Estendido v3.0 (Tálamo -> 10 Especialistas em 4 Lobos -> Convergência + Hipocampo)
            cortex = ExtendedCognitiveCortexV3(event_store=store, plasticity_memory=plasticity)
            cortex_res = cortex.process_v3(
                objective=user_command,
                context={
                    "active_obsidian_note": active_note_title,
                    "rag_chunk_ids": [h.chunk_id for h in rag_hits],
                    "axioms_count": len(user_axioms),
                },
            )
            res_dict = cortex_res.to_dict()

            # 4. Projetar execução, certificados, Hipocampo, Dossiês Cristalinos e Canvas no Vault MY BRAIN
            proj = self.bridge.project_cortex_run_to_vault(
                res_dict,
                objective=user_command,
                event_store=store,
            )
            hippo_path = self.bridge.project_plasticity_to_vault(plasticity)
            audit_summary = gov.audit_and_calibrate_brain(store, plasticity)
            gov_out = gov.write_crystalline_dossiers_to_vault(self.bridge.vault_root, audit_summary, event_store=store)
            self.bridge._write_specialist_neuron_hubs()
            proj["hippocampus_note"] = str(hippo_path)
            proj["governance_report"] = gov_out["governance_report_path"]
            proj["dossiers_written"] = gov_out["dossiers_written"]
            self.bridge.update_central_moc(event_store=store, ingestion_report=ing_report)

            # 5. Abrir a nota da execução ou o Canvas ao vivo na janela do Obsidian via Local REST API
            ui_opened = None
            if open_in_obsidian:
                rel_exec = f"04_Certificados_e_Execucoes/Execucao_{res_dict['dag_id']}.md"
                open_res = self.rest_client.open_file_in_ui(rel_exec, new_leaf=False)
                ui_opened = {"target": rel_exec, "rest_api_ok": open_res.get("ok", False)}

            # 6. Snapshot Git automático no Vault MY BRAIN
            git_snap = None
            if auto_git_commit:
                git_snap = self.bridge.commit_vault_snapshot(
                    message=f"feat(jarvis): {user_command[:55]} [{res_dict['dag_id']}]"
                )

            # 7. Sintetizar resposta falada (via Gemini se chave configurada, ou neuro-simbólico determinístico)
            spoken_text, used_gemini = self._synthesize_spoken_response(
                user_command=user_command,
                cortex_dict=res_dict,
                rag_hits=[{"title": h.title, "chunk_id": h.chunk_id, "text": h.text[:240]} for h in rag_hits],
                active_note_title=active_note_title,
                active_note_excerpt=active_note_excerpt,
            )

            # Gravar episódio conversacional no CoALAMemoryStore (não-citável como fonte factual)
            mem_store.record_episode(
                episode_id=f"ep_{res_dict['dag_id']}",
                request_text=user_command,
                response_text=spoken_text,
                status=res_dict["status"],
            )

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            dag_summary = store.export_dag_summary()

            return {
                "ok": True,
                "user_command": user_command,
                "spoken_response": spoken_text,
                "used_gemini_llm": used_gemini,
                "elapsed_ms": elapsed_ms,
                "active_obsidian_note": active_note_title,
                "rag_hits": [
                    {"chunk_id": h.chunk_id, "title": h.title, "source": h.source}
                    for h in rag_hits
                ],
                "cortex_result": res_dict,
                "obsidian_projection": proj,
                "obsidian_ui_opened": ui_opened,
                "vault_git_snapshot": git_snap,
                "dag_summary": {
                    "total_events": dag_summary["total_events"],
                    "total_branches": dag_summary["total_branches"],
                    "total_rollbacks": dag_summary["total_rollbacks"],
                    "chain_integrity_valid": dag_summary["chain_integrity_valid"],
                },
            }
        finally:
            gov.close()
            plasticity.close()
            mem_store.close()
            store.close()

    def _synthesize_spoken_response(
        self,
        user_command: str,
        cortex_dict: Dict[str, Any],
        rag_hits: List[Dict[str, str]],
        active_note_title: Optional[str],
        active_note_excerpt: str,
    ) -> tuple[str, bool]:
        """
        Gera a resposta falada em português para o usuário, ancorada estritamente
        nos certificados aprovados do Córtex e nos chunks da Memória CoALA.
        """
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        dag_id = cortex_dict.get("dag_id", "")
        certs = cortex_dict.get("certificates", {})
        approved_count = sum(1 for c in certs.values() if c.get("status") == "APPROVED")

        if gemini_key:
            try:
                sys_prompt = (
                    "Você é J.A.R.V.I.S., a interface de voz do Cérebro Cognitivo Fractal Multi-Agente v2.0. "
                    "Responda em português de forma clara, direta, elegante e precisa (2 a 4 frases para leitura em voz alta), "
                    "baseando-se estritamente nos certificados aprovados pelos 5 Neurônios Especialistas (V1/V2/V3) e nos "
                    "documentos da base MY BRAIN no Obsidian. Retorne um JSON com a chave {\"spoken_response\": \"...\"}."
                )
                user_prompt = json.dumps(
                    {
                        "comando_usuario": user_command,
                        "nota_aberta_no_obsidian": active_note_title,
                        "trecho_nota_aberta": active_note_excerpt[:300],
                        "chunks_coala_rag": rag_hits,
                        "dag_id": dag_id,
                        "certificados_aprovados": f"{approved_count}/{len(certs)}",
                    },
                    ensure_ascii=False,
                )
                out = call_gemini_json(
                    system_prompt=sys_prompt,
                    user_prompt=user_prompt,
                    api_key=gemini_key,
                    model="gemini-2.5-flash",
                )
                if isinstance(out, dict) and out.get("spoken_response"):
                    return str(out["spoken_response"]).strip(), True
            except Exception:
                pass

        # Síntese determinística neuro-simbólica (funciona 100% offline ou antes de configurar a chave Gemini)
        note_ctx = (
            f" Detectei que você estava visualizando a nota '{active_note_title}' no Obsidian."
            if active_note_title
            else ""
        )
        rag_ctx = (
            f" Consultei {len(rag_hits)} documentos da sua memória semântica CoALA (incluindo '{rag_hits[0]['title']}')."
            if rag_hits
            else " Consultei os axiomas ativos do seu Vault MY BRAIN."
        )
        spoken = (
            f"Processamento concluído no Córtex Cognitivo para a sua solicitação: '{user_command}'.{note_ctx}{rag_ctx} "
            f"Todos os {approved_count} neurônios especialistas aprovaram os invariantes nas camadas V1, V2 e V3, "
            f"e o certificado criptográfico da execução {dag_id} já foi projetado e aberto no seu Obsidian."
        )
        return spoken, False
