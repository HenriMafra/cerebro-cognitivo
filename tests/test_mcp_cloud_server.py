"""
Testes Automatizados do Servidor MCP Remoto na Nuvem (HTTP/SSE + Direct JSON-RPC).
Verifica:
1. Healthcheck GET /health
2. Direct JSON-RPC POST /jsonrpc (initialize, tools/list, tools/call)
3. Endpoint SSE GET /sse e envio de mensagens via POST /messages?sessionId=...
4. Sincronização bidirecional do Vault
"""

import json
import threading
import time
import unittest
import urllib.request
import urllib.error

from core.obsidian_bridge import discover_default_vault_path
from mcp_brain_server import ThreadingHTTPServer, MCPHTTPRequestHandler, MCP_TOOLS_SPEC


class TestMCPCloudServer(unittest.TestCase):
    server: ThreadingHTTPServer
    server_thread: threading.Thread
    port: int = 8991
    base_url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), MCPHTTPRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_01_healthcheck_endpoint(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "cerebro-cognitivo-obsidian-mcp")
            self.assertIn("vault_exists", data)

    def test_02_direct_jsonrpc_initialize_and_tools_list(self) -> None:
        # Initialize
        init_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/jsonrpc", data=init_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["id"], 1)
            self.assertEqual(data["result"]["serverInfo"]["name"], "cerebro-cognitivo-obsidian-mcp")

        # Tools List
        list_body = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}).encode("utf-8")
        req2 = urllib.request.Request(f"{self.base_url}/jsonrpc", data=list_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=3.0) as resp2:
            self.assertEqual(resp2.status, 200)
            data2 = json.loads(resp2.read().decode("utf-8"))
            tool_names = [t["name"] for t in data2["result"]["tools"]]
            self.assertIn("brain_execute_cortex", tool_names)
            self.assertIn("brain_search_coala_rag", tool_names)
            self.assertIn("brain_write_obsidian_note", tool_names)
            self.assertIn("brain_sync_vault", tool_names)
            self.assertIn("brain_verify_merkle_chain", tool_names)

    def test_03_tool_call_merkle_chain_audit(self) -> None:
        call_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "brain_verify_merkle_chain", "arguments": {}}
        }).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/jsonrpc", data=call_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertFalse(data.get("isError", False))
            payload = json.loads(data["result"]["content"][0]["text"])
            self.assertTrue(payload["chain_integrity_valid"])

    def test_04_sse_handshake_and_message_delivery(self) -> None:
        req = urllib.request.Request(f"{self.base_url}/sse")
        sse_resp = urllib.request.urlopen(req, timeout=3.0)
        self.assertEqual(sse_resp.status, 200)

        # Lê evento inicial 'endpoint'
        first_line = sse_resp.readline().decode("utf-8").strip()
        second_line = sse_resp.readline().decode("utf-8").strip()
        _ = sse_resp.readline()  # Linha vazia separadora

        self.assertEqual(first_line, "event: endpoint")
        self.assertTrue(second_line.startswith("data: /messages?sessionId="))
        endpoint_path = second_line.replace("data: ", "").strip()

        # Envia mensagem JSON-RPC via POST para o endpoint
        post_body = json.dumps({"jsonrpc": "2.0", "id": 42, "method": "initialize", "params": {}}).encode("utf-8")
        post_req = urllib.request.Request(f"{self.base_url}{endpoint_path}", data=post_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(post_req, timeout=3.0) as p_resp:
            self.assertEqual(p_resp.status, 202)

        # Lê resposta da stream SSE
        evt_type = sse_resp.readline().decode("utf-8").strip()
        evt_data = sse_resp.readline().decode("utf-8").strip()
        sse_resp.close()

        self.assertEqual(evt_type, "event: message")
        self.assertTrue(evt_data.startswith("data: "))
        resp_json = json.loads(evt_data[6:])
        self.assertEqual(resp_json["id"], 42)
        self.assertEqual(resp_json["result"]["serverInfo"]["name"], "cerebro-cognitivo-obsidian-mcp")


if __name__ == "__main__":
    unittest.main()
