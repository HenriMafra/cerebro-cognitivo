# ☁️ Guia Definitivo: Servidor MCP na Nuvem + Obsidian Bidirecional

Este documento descreve como conectar o **Cérebro Cognitivo Fractal** e o Vault **`MY BRAIN`** através do protocolo oficial **MCP (Model Context Protocol)** na nuvem, permitindo que **qualquer sessão de IA (Claude Desktop, Cursor, VS Code, agentes web ou mobile)** acesse suas notas, execute o Córtex e sincronize tudo de forma 100% síncrona e bidirecional com o GitHub.

---

## 🔄 Como Funciona a Sincronização Síncrona e Bidirecional

A sincronização é estritamente livre de *drift* ou estados obsoletos:

```
┌───────────────────────────────────────┐
│ Cliente de IA (Qualquer Nuvem / App)  │
│ Claude / Cursor / Agente / Mobile     │
└──────────────────┬────────────────────┘
                   │ MCP over SSE (GET /sse + POST /messages) ou Direct JSON-RPC
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Servidor MCP Remoto (mcp_brain_server.py)                              │
│                                                                        │
│ 1. [Entrada] git pull --rebase --autostash (absorve notas do celular)  │
│ 2. [Processamento] RAG FTS5 BM25 + Execução Ortogonal V1/V2/V3         │
│ 3. [Saída] Cria notas/canvas + git commit + git push origin HEAD       │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼ (GitHub API / SSH / Token)
┌───────────────────────────────────────┐
│ GitHub: HenriMafra/MY-BRAIN           │ ◄── O Vault Global na Nuvem
└──────────────────┬────────────────────┘
                   │ Auto-Sync via plugin `obsidian-git`
                   ▼
┌───────────────────────────────────────┐
│ Seu Obsidian no Computador ou Celular │ ◄── Você lê e escreve notas locais
└───────────────────────────────────────┘
```

1. **Antes de Buscar ou Raciocinar (`brain_search_coala_rag`, `brain_execute_cortex`):**
   * O servidor MCP executa `git pull --rebase --autostash origin HEAD` no Vault.
   * Se você acabou de editar uma nota no Obsidian no seu celular ou notebook, o cérebro na nuvem puxa essa nota imediatamente e reindexa o BM25 antes de responder.
2. **Após Escrever Notas ou Executar Missões (`brain_write_obsidian_note`, `brain_execute_cortex`):**
   * O servidor grava os arquivos Markdown e os `.canvas` visuais.
   * Executa atômico `git add -A`, `git commit` e `git push origin HEAD`.
   * O seu Obsidian local (com o plugin `obsidian-git` ativo com pull automático a cada 5 ou 10 minutos) recebe as notas e mapas instantaneamente.

---

## 🛠️ Ferramentas MCP Disponíveis

| Ferramenta | Descrição | Bidirecionalidade |
| :--- | :--- | :--- |
| `brain_execute_cortex` | Executa o DAG do Córtex (verificadores V1/V2/V3), gera certificados criptográficos e mapas `.canvas` | Faz pull prévio e push automático de certificados e mapas |
| `brain_search_coala_rag` | Busca semântica FTS5 BM25 com ponteiros de proveniência | Faz pull prévio para absorver axiomas recém-criados |
| `brain_write_obsidian_note` | Cria notas em `01_Axiomas_do_Usuario` ou `02_Conhecimento_Semantico` | Grava, indexa no RAG e envia via git push |
| `brain_sync_vault` | Força sincronização completa (pull $\rightarrow$ reindex $\rightarrow$ push) | Sincroniza ambos os sentidos sob demanda |
| `brain_verify_merkle_chain` | Audita a integridade SHA-256 do SQLite WAL | Validação criptográfica do histórico epistêmico |
| `obsidian_ui_control` | Controla janelas ativas e abre canvas via protocolo `obsidian://` | Interface de usuário |

---

## 🚀 Como Fazer o Deploy do MCP na Nuvem

### Opção 1: Deploy Gratuito no Render.com (1-Click)
1. Faça login no [Render.com](https://render.com).
2. Clique em **New +** $\rightarrow$ **Blueprint**.
3. Conecte seu repositório `HenriMafra/cerebro-cognitivo`. O Render detectará automaticamente o arquivo [`render.yaml`](../render.yaml).
4. Defina a variável de ambiente secreta:
   * `GITHUB_TOKEN`: Seu Personal Access Token do GitHub (com permissão `repo` para ler/escrever no `MY-BRAIN`).
5. O Render fornecerá uma URL pública: `https://cerebro-cognitivo-mcp.onrender.com`.

### Opção 2: Deploy no Railway / Fly.io / VPS Docker
```bash
# Construir e rodar via Docker
docker build -t cerebro-mcp .
docker run -d -p 8080:8080 \
  -e GITHUB_TOKEN="seu_token_aqui" \
  -e MCP_AUTH_TOKEN="sua_chave_secreta_aqui" \
  cerebro-mcp
```

---

## 🔌 Como Conectar nos seus Clientes de IA

### 1. No Cursor / Windsurf / Claude Desktop (via URL SSE na Nuvem)
Adicione no seu arquivo de configuração MCP (`~/.cursor/mcp.json` ou `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cerebro-cognitivo": {
      "url": "https://seu-cerebro.onrender.com/sse",
      "headers": {
        "Authorization": "Bearer SUA_CHAVE_SECRETA_AQUI"
      }
    }
  }
}
```

### 2. No Claude Desktop Local (Modo Stdio Clássico)
```json
{
  "mcpServers": {
    "cerebro-cognitivo": {
      "command": "python3",
      "args": ["/caminho/para/cerebro-cognitivo/mcp_brain_server.py", "--stdio"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/caminho/para/MY-BRAIN"
      }
    }
  }
}
```

---

## 🧪 Testando os Endpoints via Terminal

```bash
# 1. Healthcheck
curl http://localhost:8080/health

# 2. Teste Direto JSON-RPC (Listar Ferramentas)
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'

# 3. Forçar Sincronização Bidirecional
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "brain_sync_vault", "arguments": {}}}'
```
