# Cérebro Cognitivo Fractal Multi-Agente (`cerebro_cognitivo`)

Implementação de referência, validada empiricamente, da arquitetura de **Redes Neurais Cognitivas Compostas**, **Event Sourcing Epistêmico em Merkle-DAG** e **Verificação Ortogonal em 3 Camadas (Lógica, Grounding Determinístico e Red Team Adversário)**.

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
├── docs/
│   ├── 00_arquitetura_canonica.html           # Especificação Visual Canônica (Mermaid + PDF-ready)
│   ├── 01_fundamentos_cientificos.md          # Provas matemáticas (Condorcet, BFT, Merkle-DAG)
│   └── 02_manual_auditoria_e_metricas.md      # Relatório empírico da bateria de Engenharia de Caos
├── core/
│   ├── __init__.py                            # Exportação pública do núcleo
│   ├── schemas.py                             # Contratos tipados, ProvenancePointer e Hashes SHA-256
│   ├── event_store.py                         # Event Store imutável (SQLite WAL + Triggers Append-Only)
│   ├── verifiers.py                           # Verificadores V1 (Lógica), V2 (Sandbox) e V3 (Red Team)
│   ├── llm_bridge.py                          # Conector multi-provedor + Motor Neurosimbólico Determinístico
│   ├── neuron.py                              # O Neurônio Cognitivo Composto (8 estágios + Rollback Causal)
│   └── cortex.py                              # Orquestrador Macro em DAG (Tálamo, Especialistas e Convergência)
├── tests/
│   ├── test_unit_core.py                      # Testes unitários determinísticos de todos os módulos
│   └── chaos_benchmark.py                     # Bateria de Engenharia de Caos e Injeção de Falhas
└── dashboard/
    ├── inspector_generator.py                 # Gerador do painel de auditoria forense
    └── inspector_telemetria.html              # Dashboard interativo com árvore de eventos e métricas reais
```

---

## 3. Garantias de Versionamento e Imutabilidade Epistêmica

O sistema opera sob **duplo versionamento**:
1. **Versionamento de Código e Documentação via Git**: Cada camada arquitetural é registrada em commits atômicos auditáveis.
2. **Versionamento de Pensamento e Estado via Event Sourcing (`EpistemicEventStore`)**:
   - Armazenado em SQLite3 no modo `WAL` (*Write-Ahead Logging*) protegido por *triggers* `BEFORE UPDATE` e `BEFORE DELETE` que abortam qualquer tentativa de mutação histórica.
   - Cada evento contém `previous_event_hash` e `content_hash` (`SHA-256`), formando uma cadeia criptográfica verificável via `verify_chain_integrity()`.
   - Suporta **Time-Travel Debugging** (`checkout_state(event_id)`) e **Rollback Causal** (`branch_from(event_id, new_branch, reason)`).

---

## 4. Como Executar os Testes e a Bateria de Engenharia de Caos

No terminal (a partir da raiz `cerebro_cognitivo/`):

```bash
# 1. Executar a suíte de testes unitários determinísticos
python -m unittest discover -s tests -p "test_*.py" -v

# 2. Executar a Bateria de Engenharia de Caos e gerar o Dashboard de Telemetria
python tests/chaos_benchmark.py
```
