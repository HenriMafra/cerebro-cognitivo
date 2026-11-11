"""
Servidor MCP (Model Context Protocol — JSON-RPC 2.0 via Stdio e HTTP/SSE Remoto na Nuvem)
do Cérebro Cognitivo Fractal Multi-Agente + Obsidian (MY BRAIN).

Conexão Bidirecional e Síncrona:
- Vault -> Cérebro: Git pull automático antes de buscas e execuções para absorver notas feitas no PC/mobile.
- Cérebro -> Vault: Git commit e push atômico a cada nota gerada ou missão executada pelo Córtex.

Modos de Operação:
1. Modo Stdio Local (padrão): Para uso direto no Claude Desktop, Cursor ou IDE local.
2. Modo Servidor HTTP/SSE na Nuvem: Para deploy no Render, Railway, Fly.io, Cloud Run ou VPS.
   - Endpoint SSE: GET /sse (conforme especificação oficial MCP SSE)
   - Endpoint Mensagens: POST /messages?sessionId=...
   - Endpoint Direto JSON-RPC: POST /jsonrpc ou POST /
   - Endpoint Healthcheck: GET /health ou GET /

Expõe 6 ferramentas MCP padronizadas sem dependências externas:
1. `brain_execute_cortex`: Executa missão no Córtex Global com verificação V1/V2/V3 e projeta Canvas no Vault.
2. `brain_search_coala_rag`: Busca semântica BM25 FTS5 com proveniência de chunk_id.
3. `brain_write_obsidian_note`: Cria/atualiza Axioma ou Conhecimento Semântico com push automático.
4. `brain_sync_vault`: Força sincronização bidirecional completa (pull -> reindex -> commit -> push).
5. `brain_verify_merkle_chain`: Audita a integridade criptográfica SHA-256 no SQLite WAL.
6. `obsidian_ui_control`: Interage com o Obsidian via Local REST API ou protocolo nativo obsidian://.
"""

from __future__ import annotations
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
from typing import Any, Dict, List, Optional
import urllib.parse
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_store import EpistemicEventStore
from core.obsidian_bridge import (
    ObsidianLocalRestClient,
    ObsidianVaultBridge,
    discover_default_vault_path,
)
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
            "Executa um objetivo no Córtex Cognitivo Fractal (Neurônios Especialistas em DAG com "
            "verificação ortogonal V1 Lógica / V2 Sandbox AST / V3 Red Team e Rollback Causal), "
            "projetando certificados, árvore Merkle-DAG e o quadro visual .canvas no Vault MY BRAIN com push automático."
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
            "a partir do Vault MY BRAIN do Obsidian, sincronizando antes com o GitHub para garantir notas frescas."
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
            "(como Axioma do Usuário ou Conhecimento Semântico), indexa imediatamente no RAG "
            "e faz git commit e push para o GitHub sincronizando o dispositivo do usuário."
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
        "name": "brain_sync_vault",
        "description": (
            "Executa sincronização bidirecional completa com o GitHub (git pull origin HEAD -> "
            "reindexação RAG CoALA -> atualização de MOC e Dossiês -> git push origin HEAD) "
            "garantindo que o Cérebro e o Obsidian em qualquer máquina estejam 100% alinhados."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
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
            "Controla a interface gráfica do Obsidian via Local REST API (se ativa) ou protocolo "
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
    """Executa uma ferramenta MCP e retorna o resultado estruturado de forma síncrona e bidirecional."""
    if name == "brain_execute_cortex":
        objective = str(arguments.get("objective", "Auditar invariantes do sistema"))
        fault_mode = str(arguments.get("fault_mode", "none"))

        # 1. Puxa atualizações recentes do Obsidian antes de raciocinar
        if DEFAULT_OBSIDIAN_VAULT.exists():
            bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
            bridge.pull_vault_updates()

        # 2. Executa a missão no Córtex (que projeta artefatos e faz push automático ao finalizar)
        res = execute_objective_in_cortex(objective=objective, inject_fault_mode=fault_mode)
        return res

    if name == "brain_search_coala_rag":
        query = str(arguments.get("query", ""))
        top_k = int(arguments.get("top_k", 5))

        # Puxa notas recentes do GitHub para absorver mudanças feitas no celular ou desktop
        if DEFAULT_OBSIDIAN_VAULT.exists():
            bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
            bridge.pull_vault_updates()

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

        # Puxa atualizações antes de criar nova nota para evitar conflitos de branch
        bridge.pull_vault_updates()

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

        # Sincroniza RAG e faz commit + push automático para a nuvem
        sync_info = sync_obsidian_vault(DEFAULT_OBSIDIAN_VAULT)
        pushed = sync_info.get("vault_git_snapshot", {}).get("pushed_to_github", False)

        return {
            "ok": True,
            "note_path": str(note_path),
            "pushed_to_github": pushed,
            "sync_summary": sync_info,
        }

    if name == "brain_sync_vault":
        bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
        pull_result = bridge.pull_vault_updates()
        sync_summary = sync_obsidian_vault(DEFAULT_OBSIDIAN_VAULT)
        return {
            "bidirectional_sync_completed": True,
            "git_pull": pull_result,
            "vault_root": sync_summary.get("vault_root"),
            "axioms_active": sync_summary.get("axioms_ingested"),
            "documents_indexed": sync_summary.get("documents_ingested"),
            "chunks_fts5": sync_summary.get("total_chunks_indexed"),
            "exported_dag_events": sync_summary.get("exported_events"),
            "git_snapshot": sync_summary.get("vault_git_snapshot"),
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
                    "version": "3.2.0",
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
    """Loop principal JSON-RPC 2.0 via stdin/stdout para hosts MCP locais."""
    # Garante que o Vault do Obsidian esteja localizado e inicializado
    global DEFAULT_OBSIDIAN_VAULT
    DEFAULT_OBSIDIAN_VAULT = discover_default_vault_path(auto_clone_if_missing=True)

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


# ==============================================================================
# SERVIDOR HTTP / SSE REMOTO NA NUVEM (MCP OVER SSE + DIRECT JSON-RPC)
# ==============================================================================

SSE_SESSIONS: Dict[str, queue.Queue] = {}
SSE_LOCK = threading.Lock()


def check_mcp_auth(headers: Any, query_params: Dict[str, List[str]]) -> bool:
    """Verifica autenticação por token se MCP_AUTH_TOKEN estiver definido."""
    expected_token = (os.environ.get("MCP_AUTH_TOKEN") or "").strip()
    if not expected_token:
        return True

    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if hmac.compare_digest(token, expected_token):
            return True

    if "token" in query_params:
        if hmac.compare_digest(query_params["token"][0], expected_token):
            return True

    return False


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP com suporte a SSE, JSON-RPC direto e CORS."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[MCP-HTTP] {self.command} {self.path} - {format % args}\n")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Healthcheck
        if parsed.path in ("/", "/health", "/api/health"):
            vault_exists = DEFAULT_OBSIDIAN_VAULT.exists()
            payload = {
                "status": "healthy",
                "service": "cerebro-cognitivo-obsidian-mcp",
                "version": "3.2.0",
                "transport": "HTTP/SSE + Direct JSON-RPC",
                "vault_root": str(DEFAULT_OBSIDIAN_VAULT),
                "vault_exists": vault_exists,
                "active_sse_sessions": len(SSE_SESSIONS),
                "server_time_utc": utc_now_iso(),
            }
            raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        # MCP SSE Stream
        if parsed.path == "/sse":
            if not check_mcp_auth(self.headers, query_params):
                self.send_error(401, "Unauthorized: Token de autenticação inválido ou ausente")
                return

            session_id = uuid.uuid4().hex
            msg_queue: queue.Queue = queue.Queue()
            with SSE_LOCK:
                SSE_SESSIONS[session_id] = msg_queue

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self._send_cors_headers()
            self.end_headers()

            endpoint_uri = f"/messages?sessionId={session_id}"
            init_chunk = f"event: endpoint\r\ndata: {endpoint_uri}\r\n\r\n".encode("utf-8")
            self.wfile.write(init_chunk)
            self.wfile.flush()

            try:
                while True:
                    try:
                        msg = msg_queue.get(timeout=15.0)
                        chunk = f"event: message\r\ndata: {json.dumps(msg, ensure_ascii=False)}\r\n\r\n".encode("utf-8")
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\r\n\r\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with SSE_LOCK:
                    SSE_SESSIONS.pop(session_id, None)
            return

        self.send_error(404, "Rota GET não encontrada")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed.query)

        if not check_mcp_auth(self.headers, query_params):
            self.send_error(401, "Unauthorized: Token de autenticação inválido ou ausente")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            req_json = json.loads(raw_body)
        except Exception as e:
            self.send_error(400, f"JSON inválido: {e}")
            return

        # MCP SSE Message POST
        if parsed.path in ("/messages", "/message"):
            session_id = query_params.get("sessionId", [""])[0]
            with SSE_LOCK:
                session_queue = SSE_SESSIONS.get(session_id)

            if not session_queue:
                self.send_error(404, f"Sessão SSE não encontrada ou expirada: {session_id}")
                return

            response_payload = handle_jsonrpc_request(req_json)
            if response_payload is not None:
                session_queue.put(response_payload)

            ack = json.dumps({"status": "accepted", "sessionId": session_id}).encode("utf-8")
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.send_header("Content-Length", str(len(ack)))
            self.end_headers()
            self.wfile.write(ack)
            return

        # Direct HTTP JSON-RPC POST (/jsonrpc ou /)
        if parsed.path in ("/jsonrpc", "/", "/api/mcp"):
            response_payload = handle_jsonrpc_request(req_json)
            raw_resp = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.send_header("Content-Length", str(len(raw_resp)))
            self.end_headers()
            self.wfile.write(raw_resp)
            return

        self.send_error(404, "Rota POST não encontrada")


def serve_http(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Inicia o servidor MCP HTTP/SSE multi-threaded para deploy em nuvem."""
    global DEFAULT_OBSIDIAN_VAULT
    DEFAULT_OBSIDIAN_VAULT = discover_default_vault_path(auto_clone_if_missing=True)

    if DEFAULT_OBSIDIAN_VAULT.exists():
        bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
        bridge.initialize_vault_structure()
        bridge.pull_vault_updates()
        sync_obsidian_vault(DEFAULT_OBSIDIAN_VAULT)

    server = ThreadingHTTPServer((host, port), MCPHTTPRequestHandler)
    print("=" * 78)
    print(" CÉREBRO COGNITIVO · SERVIDOR MCP REMOTO NA NUVEM (HTTP/SSE + JSON-RPC)")
    print("=" * 78)
    print(f" -> Endereço HTTP   : http://{host}:{port}")
    print(f" -> Endpoint SSE    : http://{host}:{port}/sse")
    print(f" -> Endpoint JSONRPC: http://{host}:{port}/jsonrpc")
    print(f" -> Healthcheck     : http://{host}:{port}/health")
    print(f" -> Vault Local     : {DEFAULT_OBSIDIAN_VAULT}")
    print(f" -> Sincronização   : Bidirecional Ativa (Git Pull on Request / Push on Write)")
    print("=" * 78)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor MCP encerrado.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor MCP do Cérebro Cognitivo Fractal (Stdio & HTTP/SSE Nuvem)")
    parser.add_argument("--stdio", action="store_true", default=False, help="Executa no modo stdio (padrão se nenhum host/porta for passado)")
    parser.add_argument("--sse", "--http", action="store_true", default=False, help="Executa como servidor HTTP SSE para acesso remoto/nuvem")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"), help="Host para o servidor HTTP (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")), help="Porta para o servidor HTTP (padrão: 8080 ou $PORT)")
    parser.add_argument("--vault-path", type=str, default=None, help="Caminho personalizado para o Vault MY-BRAIN")
    args = parser.parse_args()

    if args.vault_path:
        global DEFAULT_OBSIDIAN_VAULT
        DEFAULT_OBSIDIAN_VAULT = Path(args.vault_path)

    # Se a variável de ambiente PORT estiver presente (ex: Render, Railway, Fly, Cloud Run)
    # ou se a flag --sse/--http for passada, inicia o servidor HTTP/SSE na nuvem.
    is_cloud_env = bool(os.environ.get("PORT")) or args.sse
    if is_cloud_env and not args.stdio:
        serve_http(host=args.host, port=args.port)
    else:
        serve_stdio()


if __name__ == "__main__":
    main()
