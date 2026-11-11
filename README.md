# Cérebro Cognitivo Fractal Multi-Agente (`cerebro_cognitivo`)

Implementação de referência, validada empiricamente, da arquitetura de **Redes Neurais Cognitivas Compostas**, **Event Sourcing Epistêmico em Merkle-DAG** e **Verificação Ortogonal em 3 Camadas (Lógica, Grounding Determinístico e Red Team Adversário)**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/HenriMafra/cerebro-cognitivo)
*(Deploy gratuito em 1 clique do Servidor MCP HTTP/SSE na nuvem)*

---

## 1. Visão Geral da Arquitetura

Diferente de sistemas baseados em LLMs solitários ou debates puramente verbais (sujeitos a *Common-Mode Failure* e alucinação consensual), cada **Neurônio** desta rede opera como um microcircuito fechado de 8 estágios, onde nenhuma inferência é emitida pelo Axônio sem antes sobreviver a três barreiras independentes:

1. **Camada V1 (`LogicalVerifier`)**: Exige **Ponteiros de Proveniência (`ProvenancePointer`)** criptograficamente assinados em 100% das afirmações, verifica coerência silogística e bloqueia violações de restrições negativas acumuladas.
2. **Camada V2 (`DeterministicMachineVerifier`)**: Analisa a Árvore Sintática Abstrata (`AST`) do artefato de código e o executa em um **processo isolado real (Sandbox)**, validando todas as pré e pós-condições matemáticas (`expected_invariants`).
3. **Camada V3 (`AdversarialRedTeamVerifier`)**: Atua como um inquisidor cético que gera e executa entradas de borda adversárias (*fuzzing* de limites, zeros, negativos, coleções vazias, condições de contorno) e audita os hashes SHA-256 de proveniência contra falsificação.

---

## 2. Estrutura de Diretórios

```text
cerebro_cognitivo/
├── README.md                                  # Manual de Arquitetura e Operação
├── run_mvp.py                                 # Entrypoint CLI / Studio HTTP / Sincronizador Obsidian
├── docs/
│   ├── 00_arquitetura_canonica.html           # Especificação Visual Canônica (Mermaid + PDF-ready)
│   ├── 01_fundamentos_cientificos.md          # Provas matemáticas (Condorcet, BFT, Merkle-DAG)
│   ├── 02_manual_auditoria_e_metricas.md      # Relatório empírico da bateria de Engenharia de Caos
│   └── 03_auditoria_cruzada_cerebro_fractal.md # Auditoria Comparativa Cruzada e Evolução v2.0
├── core/
│   ├── __init__.py                            # Exportação pública do núcleo
│   ├── schemas.py                             # Contratos tipados, ProvenancePointer e Hashes SHA-256
│   ├── event_store.py                         # Event Store imutável (SQLite WAL + Triggers Append-Only)
│   ├── crypto_signing.py                      # Assinatura Ed25519 (RFC 8032) + ExternalHashAnchor
│   ├── rag_memory.py                          # Memória Tripartite CoALA (FTS5 BM25 + Citação Literal V2)
│   ├── formal_z3.py                           # Verificador Formal SMT-LIB v2 (Z3 Solver)
│   ├── budget.py                              # HardBudget com Reserva Pessimista Worst-Case
│   ├── obsidian_bridge.py                     # Ponte Bidirecional Obsidian Vault (MY BRAIN) + JSON Canvas
│   ├── verifiers.py                           # Verificadores V1 (Lógica), V2 (Sandbox AST) e V3 (Red Team)
│   ├── llm_bridge.py                          # Conector multi-provedor (Gemini / OpenAI) + Motor Determinístico
│   ├── neuron.py                              # O Neurônio Cognitivo Composto (8 estágios + Rollback Causal)
│   └── cortex.py                              # Orquestrador Macro em DAG (Tálamo, Especialistas e Convergência)
├── tests/
│   ├── test_event_store.py                    # Testes do SQLite WAL, triggers, Time-Travel e Rollback
│   ├── test_neuron_and_verifiers.py           # Testes do Neurônio Composto e Verificadores V1/V2/V3
│   ├── test_cortex_and_dashboard.py           # Testes do Algoritmo de Kahn, Córtex DAG e Telemetria
│   ├── test_v2_upgrades.py                    # Testes v2.0 (Ed25519, CoALA FTS5, AST Allowlist, Z3, Budget)
│   ├── test_obsidian_bridge.py                # Testes da Ponte Bidirecional Obsidian Vault (MY BRAIN)
│   └── chaos_benchmark.py                     # Bateria de Engenharia de Caos e Injeção de Falhas (7 cenários)
└── dashboard/
    ├── inspector_generator.py                 # Gerador do painel de auditoria forense
    └── inspector_telemetria.html              # Dashboard interativo com árvore de eventos e métricas reais
```

---

## 3. Garantias de Versionamento e Imutabilidade Epistêmica

O sistema opera sob **triplo versionamento e projeção visual**:
1. **Versionamento de Código e Documentação via Git**: Cada camada arquitetural é registrada em commits atômicos auditáveis.
2. **Versionamento de Pensamento e Estado via Event Sourcing (`EpistemicEventStore`)**:
   - Armazenado em SQLite3 no modo `WAL` (*Write-Ahead Logging*) protegido por *triggers* `BEFORE UPDATE` e `BEFORE DELETE` que abortam qualquer tentativa de mutação histórica.
   - Cada evento contém `previous_event_hash` e `content_hash` (`SHA-256`), além de suporte a assinatura `Ed25519` e ancoragem externa (`ExternalHashAnchor`).
   - Suporta **Time-Travel Debugging** (`checkout_state(event_id)`) e **Rollback Causal** (`branch_from(event_id, new_branch, reason)`).
3. **Superfície Neural Bidirecional no Obsidian Vault (`MY BRAIN`)**:
   - Ingere axiomas do usuário (`01_Axiomas_do_Usuario/`) e notas semânticas (`02_Conhecimento_Semantico/`) diretamente para a memória `CoALAMemoryStore` (SQLite FTS5 BM25) com conferência literal de citações pela Camada V2.
   - Projeta os 7 Neurônios do Córtex, Certificados Criptográficos, Eventos do Merkle-DAG e quadros visuais nativos `.canvas` para o Graph View do Obsidian.

---

## 4. Como Executar os Testes, o MVP e a Sincronização com o Obsidian

No terminal (a partir da raiz `cerebro_cognitivo/`):

```bash
# 1. Executar toda a suíte de testes unitários (63 testes determinísticos)
python -m unittest discover -s tests -p "test_*.py" -v

# 2. Executar a Bateria de Engenharia de Caos (7 cenários adversariais)
python tests/chaos_benchmark.py

# 3. Sincronizar bidirecionalmente com o Vault MY BRAIN no Obsidian
python run_mvp.py --sync-obsidian

# 4. Executar uma missão no Córtex Global e projetar o DAG e Canvas no Obsidian
python run_mvp.py --prompt "Projetar e certificar protocolo de autenticação zero-trust"
```
