# Auditoria Cruzada Comparativa: `cerebro_cognitivo` vs. `cerebro-fractal`

Este documento registra a análise técnica comparativa entre as duas implementações independentes derivadas da especificação arquitetural canônica (`cerebro-de-agentes-arquitetura.html`):
- **Este Projeto**: `c:\Users\henri.mafra\Documents\CRIPTOGRAFIA\cerebro_cognitivo`
- **Projeto Irmão Auditado (Somente Leitura)**: `c:\Users\henri.mafra\Documents\CRIPTOGRAFIA\cerebro-fractal`

---

## 1. O Que o `cerebro-fractal` Fez Melhor (e que Já Absorvemos na v2.0)

| Achado no `cerebro-fractal` | Por que era superior | Como absorvemos no `cerebro_cognitivo` (Commit `31e8c7e`) |
| :--- | :--- | :--- |
| **1. Assinatura Assimétrica Ed25519 + Âncoras Externas** (`events/signing.py`) | Cadeias apenas com hash SHA-256 permitem que quem tem escrita no disco recalcule a cadeia desde o bloco gênese. A assinatura assimétrica + âncora externa torna a reescrita total detectável. | Implementado [`core/crypto_signing.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/crypto_signing.py) com `EventSigner` (Ed25519 / HMAC determinístico) e `ExternalAnchor`. |
| **2. Política AST por Allowlist + Bloqueio de Introspecção** (`grounding/ast_policy.py`) | Uma *denylist* simples deixa passar escapes de sandbox via `().__class__.__bases__[0].__subclasses__()` ou imports indiretos. | Implementado `check_ast_allowlist()` em [`core/formal_z3.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/formal_z3.py) com `ALLOWED_STDLIB_MODULES` e bloqueio de `DENIED_INTROSPECTION_ATTRS`. |
| **3. Detector de Testes Triviais / Tautologias** (`trivial_tests_reason`) | Impede que um agente engane a Camada V2 gerando código com `assert True` ou testes que sequer chamam a função criada. | Implementado `detect_trivial_tests()` em [`core/formal_z3.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/formal_z3.py) verificando AST dos invariantes contra os símbolos definidos no código. |
| **4. Verificação Formal SMT-LIB com Z3** (`grounding/formal.py`) | Executa provas formais reais em SMT-LIB 2.0 (buscando `unsat` para $\neg P$) e bloqueia comandos perigosos (`(set-option`, `(include`). | Implementado `run_smtlib_formal_check()` em [`core/formal_z3.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/formal_z3.py) suportando módulo `z3` e binário `z3` CLI. |
| **5. Memória CoALA + RAG SQLite FTS5 Versionado + Citação Literal** (`rag/store.py`) | Separa Memória Semântica (com conferência literal de trechos e versionamento sem quebrar citações antigas) de Memória Episódica (proibida como fonte factual para impedir auto-citação circular). | Implementado [`core/rag_memory.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/rag_memory.py) com `CoALAMemoryStore`, FTS5 BM25 sem diacríticos e `verify_literal_quote()`. |
| **6. Orçamento Rígido com Reserva de Pior Caso + `GroundingLevel`** (`budget.py`) | Reserva o custo de pior caso antes de chamadas paralelas e substitui scores arbitrários por níveis discretos (`MACHINE_VERIFIED`, `LLM_REVIEWED`, `UNVERIFIED`). | Implementado [`core/budget.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/budget.py) com `HardBudget`, `VerificationProfile` e `GroundingLevel`. |

---

## 2. O Que o Nosso `cerebro_cognitivo` Fez Melhor (e que Falta no `cerebro-fractal`)

| Capacidade do `cerebro_cognitivo` | Estado no `cerebro-fractal` | Vantagem Técnica do Nosso Projeto |
| :--- | :--- | :--- |
| **1. Time-Travel Debugging (`checkout_state`) e Rollback/Fork Causal Operacional (`branch_from`)** | **Adiado no Roadmap** (declarado na linha 41 de `AUDITORIA-SPEC-v1.md`: *"falta o comando de replay/fork"*). | Nosso [`core/event_store.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/event_store.py) reconstrói o estado exato de qualquer vértice histórico via *fold/reduce* (`checkout_state`) e cria bifurcações reais de branch (`branch_from`) a cada falha em V1/V2/V3. |
| **2. Dashboard Visual Interativo de Telemetria (`inspector_telemetria.html`) + Servidor Web (`run_mvp.py`)** | **Inexistente** (apenas CLI em modo texto). | Nosso [`dashboard/inspector_telemetria.html`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/dashboard/inspector_telemetria.html) renderiza o grafo DAG real da execução em SVG/Mermaid, filtros por branch/veredito, modal de inspeção JSON e servidor HTTP local (`run_mvp.py --serve`). |
| **3. Suporte Multi-Família Nativo (Google Gemini API + OpenAI/Atria + Fallback Simbólico)** | **Acoplado exclusivamente à Anthropic** (`anthropic_provider.py`; deixou Gemini como item futuro no roadmap). | Nosso [`core/llm_bridge.py`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/core/llm_bridge.py) já possui conector nativo para **Google Gemini API (`GEMINI_API_KEY`)**, OpenAI/Atria e motor determinístico offline sem depender de `.venv` externa. |
| **4. Deduções Matemáticas Analíticas Completas (`01_fundamentos_cientificos.md`)** | Revisão qualitativa de literatura sem as provas analíticas fechadas. | Nosso [`docs/01_fundamentos_cientificos.md`](file:///c:/Users/henri.mafra/Documents/CRIPTOGRAFIA/cerebro_cognitivo/docs/01_fundamentos_cientificos.md) demonstra analiticamente o limite assintótico da variância no Teorema de Condorcet correlacionado ($\lim_{n\to\infty}\operatorname{Var}(\bar{X}_n) = \rho p(1-p)$) e o protocolo *Epistemic BFT*. |
| **5. Portabilidade Zero-Dependência (Stdlib-First)** | Exige `.venv` pesada instalada para conseguir importar o pacote. | Nosso núcleo roda imediatamente no Python padrão do sistema em `< 0.5s` (41 testes unitários + 7 cenários de caos), ativando extensões (`cryptography`, `z3`) dinamicamente quando presentes. |
