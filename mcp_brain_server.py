"""
Servidor MCP (Model Context Protocol — JSON-RPC 2.0 via stdio) do Cérebro Cognitivo + Obsidian (MY BRAIN).

Expõe 5 ferramentas MCP padronizadas (`tools/list` e `tools/call`) sem dependências externas:
1. `brain_execute_cortex`: Executa uma missão no Córtex Global (Tálamo -> 5 Especialistas V1/V2/V3 -> Convergência)
   e projeta certificados e quadros `.canvas` diretamente no Vault `MY BRAIN`.
2. `brain_search_coala_rag`: Busca semântica BM25 FTS5 sobre o Vault `MY BRAIN` com `chunk_id` para citação literal V2.
3. `brain_write_obsidian_note`: Cria/atualiza um Axioma (`01_Axiomas_do_Usuario`) ou Conhecimento Semântico
   (`02_Conhecimento_Semantico`) no Obsidian e reindexa imediatamente no `CoALAMemoryStore`.
4. `brain_verify_merkle_chain`: Executa auditoria forense completa da cadeia `SHA-256` no SQLite WAL.
5. `obsidian_ui_control`: Interage em tempo real com a janela do Obsidian via plugin `Local REST API`
   (`127.0.0.1:27124`) ou protocolo nativo `obsidian://open`.
"""

from __future__ import annotations
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_store import EpistemicEventStore
from core.obsidian_bridge import ObsidianLocalRestClient, ObsidianVaultBridge
from core.rag_memory import CoALAMemoryStore
from core.schemas import utc_now_iso
from run_mvp import (
    DEFAULT_DB,
    DEFAULT_JSONL,
    DEFAULT_OBSIDIAN_VAULT,
    DEFAULT_RAG_DB,
    execute_objective_in_cortex,
    sync_obsidian_vault,
)


MCP_TOOLS_SPEC: List[Dict[str, Any]] = [
    {
        "name": "brain_execute_cortex",
        "description": (
            "Executa um objetivo no Córtex Cognitivo Fractal (5 Neurônios Especialistas em DAG com "
            "verificação ortogonal V1/V2/V3 e Rollback Causal) e projeta os certificados e o quadro "
            ".canvas no Vault MY BRAIN do Obsidian."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "description": "Objetivo ou problema a ser decomposto, verificado e certificado pelo Córtex.",
                },
                "fault_mode": {
                    "type": "string",
                    "enum": ["none", "hallucination_v1", "runtime_bug_v2"],
                    "default": "none",
                },
            },
            "required": ["objective"],
        },
    },
    {
        "name": "brain_search_coala_rag",
        "description": (
            "Busca conhecimento semântico versionado (SQLite FTS5 BM25) e axiomas do usuário ingeridos "
            "a partir do Vault MY BRAIN do Obsidian, retornando chunk_ids verificáveis pela Camada V2."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Termos de busca semântica/lexical.",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_write_obsidian_note",
        "description": (
            "Cria ou atualiza uma nota Markdown estruturada no Vault MY BRAIN do Obsidian "
            "(como Axioma do Usuário ou Conhecimento Semântico) e indexa imediatamente no CoALAMemoryStore."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["axiom", "semantic"],
                    "description": "'axiom' grava em 01_Axiomas_do_Usuario; 'semantic' grava em 02_Conhecimento_Semantico.",
                },
                "title": {
                    "type": "string",
                    "description": "Título da nota.",
                },
                "content": {
                    "type": "string",
                    "description": "Corpo em Markdown (pode conter [[wikilinks]]).",
                },
            },
            "required": ["category", "title", "content"],
        },
    },
    {
        "name": "brain_verify_merkle_chain",
        "description": (
            "Audita a integridade criptográfica SHA-256 de todos os eventos do EpistemicEventStore (SQLite WAL) "
            "e sincroniza o painel central do Obsidian."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "obsidian_ui_control",
        "description": (
            "Controla a interface gráfica ao vivo do Obsidian via Local REST API (se ativa) ou protocolo "
            "nativo obsidian:// (abrir notas/canvas, consultar nota ativa na tela, abrir Graph View)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_rest_api", "get_active_note", "open_file", "open_graph_view"],
                },
                "relative_path": {
                    "type": "string",
                    "description": "Caminho relativo dentro do Vault MY BRAIN (usado quando action='open_file').",
                },
            },
            "required": ["action"],
        },
    },
]


def handle_mcp_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executa uma ferramenta MCP e retorna o resultado estruturado."""
    if name == "brain_execute_cortex":
        objective = str(arguments.get("objective", "Auditar invariantes do sistema"))
        fault_mode = str(arguments.get("fault_mode", "none"))
        res = execute_objective_in_cortex(objective=objective, inject_fault_mode=fault_mode)
        return res

    if name == "brain_search_coala_rag":
        query = str(arguments.get("query", ""))
        top_k = int(arguments.get("top_k", 5))
        sync_obsidian_vault(DEFAULT_OBSIDIAN_VAULT)
        mem = CoALAMemoryStore(db_path=str(DEFAULT_RAG_DB))
        try:
            chunks = mem.search_semantic(query=query, top_k=top_k)
            axioms = mem.list_user_axioms()
            return {
                "query": query,
                "active_user_axioms": axioms,
                "semantic_hits": [
                    {
                        "chunk_id": c.chunk_id,
                        "doc_id": c.doc_id,
                        "source": c.source,
                        "title": c.title,
                        "text": c.text,
                        "sha256": c.sha256,
                    }
                    for c in chunks
                ],
            }
        finally:
            mem.close()

    if name == "brain_write_obsidian_note":
        category = str(arguments.get("category", "semantic"))
        title = str(arguments.get("title", "Nova Nota"))
        body = str(arguments.get("content", ""))
        bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
        bridge.initialize_vault_structure()

        safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title.strip()).strip("_")
        if category == "axiom":
            target_dir = bridge.vault_root / bridge.DIR_AXIOMS
            filename = f"Axioma_{safe_slug}.md"
            md_text = (
                "---\n"
                "type: user_axiom\n"
                f"axiom_id: ax_{safe_slug.lower()}\n"
                f"title: \"{title}\"\n"
                "status: active\n"
                f"created_utc: {utc_now_iso()}\n"
                "tags:\n"
                "  - axiom\n"
                "  - my_brain\n"
                "---\n\n"
                f"# {title}\n\n"
                f"{body}\n\n"
                "---\n"
                "**Conectado a:** [[00_Painel_Central_MOC]]\n"
            )
        else:
            target_dir = bridge.vault_root / bridge.DIR_SEMANTIC
            filename = f"KB_{safe_slug}.md"
            md_text = (
                "---\n"
                "type: semantic_knowledge\n"
                f"title: \"{title}\"\n"
                "version: 2.0\n"
                f"updated_utc: {utc_now_iso()}\n"
                "tags:\n"
                "  - knowledge_base\n"
                "  - coala_rag\n"
                "---\n\n"
                f"# {title}\n\n"
                f"{body}\n\n"
                "---\n"
                "**Referenciado por:** [[00_Painel_Central_MOC]]\n"
            )

        note_path = target_dir / filename
        note_path.write_text(md_text, encoding="utf-8")
        sync_info = sync_obsidian_vault(DEFAULT_OBSIDIAN_VAULT)
        return {
            "ok": True,
            "note_path": str(note_path),
            "sync_summary": sync_info,
        }

    if name == "brain_verify_merkle_chain":
        store = EpistemicEventStore(db_path=str(DEFAULT_DB), jsonl_path=str(DEFAULT_JSONL))
        try:
            valid, violations = store.verify_chain_integrity()
            summary = store.export_dag_summary()
            return {
                "chain_integrity_valid": valid,
                "violations": violations,
                "total_events": summary["total_events"],
                "total_branches": summary["total_branches"],
                "total_rollbacks": summary["total_rollbacks"],
            }
        finally:
            store.close()

    if name == "obsidian_ui_control":
        action = str(arguments.get("action", "check_rest_api"))
        rel_path = str(arguments.get("relative_path", "00_Painel_Central_MOC.md"))
        bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
        rest = ObsidianLocalRestClient()

        if action == "check_rest_api":
            status = rest.check_status()
            status["native_uri_ready"] = True
            status["vault_root"] = str(bridge.vault_root)
            return status

        if action == "get_active_note":
            return rest.get_active_note()

        if action == "open_graph_view":
            res = rest.execute_command("graph:open")
            if not res.get("ok"):
                uri = bridge.open_in_obsidian_app("00_Painel_Central_MOC.md")
                res["fallback_uri_triggered"] = uri
            return res

        if action == "open_file":
            res = rest.open_file_in_ui(rel_path)
            if not res.get("ok"):
                uri = bridge.open_in_obsidian_app(rel_path)
                res["fallback_uri_triggered"] = uri
            return res

    raise ValueError(f"Ferramenta MCP desconhecida: '{name}'")


def handle_jsonrpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Processa uma mensagem JSON-RPC 2.0 do protocolo MCP."""
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params") or {}

    # Notificações JSON-RPC não possuem id e não esperam resposta
    if req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "cerebro-cognitivo-obsidian-mcp",
                    "version": "2.0.0",
                },
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS_SPEC},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments") or {}
        try:
            payload = handle_mcp_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, indent=2, ensure_ascii=False),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Erro MCP: {e}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve_stdio() -> None:
    """Loop principal JSON-RPC 2.0 via stdin/stdout para hosts MCP."""
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
            resp = handle_jsonrpc_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve_stdio()
