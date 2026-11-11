"""
Ponte Bidirecional Obsidian Vault <-> Cérebro Cognitivo Fractal Multi-Agente.

Conecta o Vault do Obsidian ("MY BRAIN") ao motor transacional SQLite WAL
(`EpistemicEventStore`) e à Memória Tripartite (`CoALAMemoryStore` com FTS5 BM25):

1. Ingestão Semântica e Axiomática (Obsidian -> Cérebro):
   - Lê notas Markdown em `01_Axiomas_do_Usuario/` e `02_Conhecimento_Semantico/`,
     extraindo metadados YAML Frontmatter e indexando os parágrafos no FTS5 BM25
     versionado para conferência literal de citações pela Camada V2.
2. Projeção Epistêmica e Visual (Cérebro -> Obsidian):
   - Gera hubs neurais em `03_Neuronios_Especialistas/` interligados por `[[wikilinks]]`.
   - Exporta execuções do Córtex, Certificados Criptográficos e Eventos do Merkle-DAG
     (incluindo Rollbacks Causais V1/V2/V3) para `04_Certificados_e_Execucoes/`.
   - Constrói quadros nativos JSON Canvas (`.canvas`) em `05_Mapas_Visuais_Canvas/`
     para visualização interativa da topologia neural diretamente no Obsidian.
   - Configura grupos de cores e setas dirigidas em `.obsidian/graph.json`.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from .event_store import EpistemicEventStore
from .rag_memory import CoALAMemoryStore
from .schemas import utc_now_iso


NEURON_HUB_MAP: Dict[str, Dict[str, Any]] = {
    "neuron_sensory_input": {
        "note_name": "Neuronio_00_Talamo_Sensorial",
        "title": "Tálamo Sensorial Adaptativo (Decomposição Topológica v3.0)",
        "specialty": "Decomposição de Estímulos nos 4 Lobos Corticais e Compilação do ExecutionDAG (Algoritmo de Kahn)",
        "wave": 0,
        "downstream": [
            "Neuronio_01_Logica_e_Matematica",
            "Neuronio_04_Fatos_e_Proveniencia",
            "Neuronio_07_Criptografia_e_Seguranca_ZeroTrust",
        ],
    },
    "neuron_logic_math": {
        "note_name": "Neuronio_01_Logica_e_Matematica",
        "title": "Neurônio Especialista 01 — Lógica Formal & Matemática (Lobo Frontal)",
        "specialty": "Lógica Formal, Invariantes Algébricos e Solvers Z3 SMT-LIB",
        "wave": 1,
        "downstream": [
            "Neuronio_02_Engenharia_de_Sistemas",
            "Neuronio_03_Estrategia_e_Risco",
            "Neuronio_08_Inferencia_Causal_e_Contrafactual",
        ],
    },
    "neuron_epistemic_facts": {
        "note_name": "Neuronio_04_Fatos_e_Proveniencia",
        "title": "Neurônio Especialista 04 — Auditoria Factual & Proveniência (Lobo Temporal)",
        "specialty": "Rastreamento de ProvenancePointers, CoALA RAG FTS5 e Conferência Literal",
        "wave": 1,
        "downstream": [
            "Neuronio_02_Engenharia_de_Sistemas",
            "Neuronio_03_Estrategia_e_Risco",
            "Neuronio_08_Inferencia_Causal_e_Contrafactual",
        ],
    },
    "neuron_crypto_security": {
        "note_name": "Neuronio_07_Criptografia_e_Seguranca_ZeroTrust",
        "title": "Neurônio Especialista 07 — Criptografia Aplicada & Segurança Zero-Trust (Lobo Parietal)",
        "specialty": "Assinaturas Ed25519, Cadeia SHA-256, Âncoras Externas e Auditoria de Superfície de Ataque",
        "wave": 1,
        "downstream": [
            "Neuronio_02_Engenharia_de_Sistemas",
            "Neuronio_03_Estrategia_e_Risco",
            "Neuronio_08_Inferencia_Causal_e_Contrafactual",
        ],
    },
    "neuron_systems_engineering": {
        "note_name": "Neuronio_02_Engenharia_de_Sistemas",
        "title": "Neurônio Especialista 02 — Engenharia de Software & Sistemas (Lobo Executivo)",
        "specialty": "Síntese de Código Verificável, AST Allowlist e Execução em Sandbox V2",
        "wave": 2,
        "downstream": [
            "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
            "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
            "Neuronio_11_Planejador_Recursivo_SubDAG",
        ],
    },
    "neuron_strategy_risk": {
        "note_name": "Neuronio_03_Estrategia_e_Risco",
        "title": "Neurônio Especialista 03 — Planejamento & Gestão de Riscos (Lobo Parietal)",
        "specialty": "Modelagem de Ameaças, BFT Epistêmico, HardBudget e Contenção de Falhas",
        "wave": 2,
        "downstream": [
            "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
            "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
            "Neuronio_11_Planejador_Recursivo_SubDAG",
        ],
    },
    "neuron_causal_counterfactual": {
        "note_name": "Neuronio_08_Inferencia_Causal_e_Contrafactual",
        "title": "Neurônio Especialista 08 — Inferência Causal & Contrafactual (Lobo Frontal)",
        "specialty": "Inferência Causal (Pearl Do-Calculus), Análise de Causa-Raiz e Simulação Contrafactual",
        "wave": 2,
        "downstream": [
            "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
            "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
            "Neuronio_11_Planejador_Recursivo_SubDAG",
        ],
    },
    "neuron_metacognition_calibration": {
        "note_name": "Neuronio_09_Metacognicao_e_Calibracao_Epistemica",
        "title": "Neurônio Especialista 09 — Metacognição & Calibração Epistêmica (Lobo Pré-Frontal)",
        "specialty": "Calibração de Certeza (Brier Score), Detecção de Lacunas Epistêmicas e Auto-Auditoria",
        "wave": 3,
        "downstream": [
            "Neuronio_05_Semantica_e_Didatica",
        ],
    },
    "neuron_episodic_consolidation": {
        "note_name": "Neuronio_10_Hipocampo_Consolidacao_Sinaptica",
        "title": "Neurônio Especialista 10 — Hipocampo & Consolidação Sináptica",
        "specialty": "Plasticidade Sináptica de Longo Prazo e Aprendizado Permanente de Restrições Negativas",
        "wave": 3,
        "downstream": [
            "Neuronio_05_Semantica_e_Didatica",
            "Sabedoria_Sinaptica_Hipocampo",
        ],
    },
    "neuron_autonomous_planner": {
        "note_name": "Neuronio_11_Planejador_Recursivo_SubDAG",
        "title": "Neurônio Especialista 11 — Planejador Recursivo de Sub-DAGs (Córtex Pré-Motor)",
        "specialty": "Decomposição Multi-Horizonte, Alocação de HardBudget e Neurogênese de Sub-DAGs",
        "wave": 3,
        "downstream": [
            "Neuronio_05_Semantica_e_Didatica",
        ],
    },
    "neuron_semantics_didactics": {
        "note_name": "Neuronio_05_Semantica_e_Didatica",
        "title": "Neurônio Especialista 05 — Semântica & Síntese Conceitual (Lobo Temporal)",
        "specialty": "Alinhamento Semântico Estrito, Clareza Estrutural e Consolidação de Artefatos",
        "wave": 3,
        "downstream": [
            "Neuronio_06_Convergencia_e_Sintese",
        ],
    },
    "neuron_convergence_synthesis": {
        "note_name": "Neuronio_06_Convergencia_e_Sintese",
        "title": "Neurônio de Convergência e Síntese Global (Onda Final)",
        "specialty": "Validação de Certificados SHA-256/Ed25519 dos 10 Especialistas e Emissão do Veredito Córtex",
        "wave": 4,
        "downstream": [],
    },
}


@dataclass
class ObsidianIngestionReport:
    """Relatório de ingestão de notas do Obsidian Vault para a memória CoALA."""
    vault_root: str
    axioms_ingested: int
    documents_ingested: int
    total_chunks_indexed: int
    document_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timestamp_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_root": self.vault_root,
            "axioms_ingested": self.axioms_ingested,
            "documents_ingested": self.documents_ingested,
            "total_chunks_indexed": self.total_chunks_indexed,
            "document_map": self.document_map,
            "timestamp_utc": self.timestamp_utc,
        }


DEFAULT_GITHUB_VAULT_REPO = "https://github.com/HenriMafra/MY-BRAIN.git"


def discover_default_vault_path(auto_clone_if_missing: bool = False) -> Path:
    """
    Descobre de forma multiplataforma (Windows, Linux, macOS, Sessão em Nuvem/Codespaces)
    a localização do Vault `MY BRAIN` / `MY-BRAIN`.
    Se `auto_clone_if_missing=True` e o Vault não existir na máquina/container da nuvem,
    faz `git clone https://github.com/HenriMafra/MY-BRAIN.git` automaticamente!
    """
    env_override = (
        os.environ.get("OBSIDIAN_VAULT_PATH")
        or os.environ.get("MY_BRAIN_VAULT_PATH")
        or ""
    ).strip()
    if env_override:
        return Path(env_override)

    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        Path(r"C:\Users\henri.mafra\Documents\MY BRAIN"),
        Path.home() / "Documents" / "MY BRAIN",
        Path.home() / "Documents" / "MY-BRAIN",
        Path.home() / "MY-BRAIN",
        Path.home() / "MY BRAIN",
        project_root.parent / "MY-BRAIN",
        project_root.parent / "MY BRAIN",
        project_root / "MY-BRAIN",
    ]
    for cand in candidates:
        try:
            if cand.exists():
                return cand
        except Exception:
            continue

    target_clone = Path.home() / "Documents" / "MY-BRAIN"
    if not target_clone.parent.exists():
        target_clone = project_root.parent / "MY-BRAIN"

    if auto_clone_if_missing:
        try:
            target_clone.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", DEFAULT_GITHUB_VAULT_REPO, str(target_clone)],
                capture_output=True,
                text=True,
                timeout=25.0,
            )
            if target_clone.exists():
                return target_clone
        except Exception:
            pass

    return candidates[0]


def resolve_vault_root(vault_path: str | Path) -> Path:
    """
    Resolve de forma inteligente a raiz real do Vault do Obsidian.
    Se o usuário indicar `Documents/MY BRAIN` e o Obsidian tiver criado
    `Documents/MY BRAIN/MY BRAIN/.obsidian`, retorna automaticamente a pasta interna.
    """
    base = Path(vault_path).resolve()
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
        return base

    if (base / ".obsidian").is_dir():
        return base

    # Verifica subpasta homônima (ex.: MY BRAIN/MY BRAIN/.obsidian)
    nested_same_name = base / base.name
    if (nested_same_name / ".obsidian").is_dir():
        return nested_same_name

    # Verifica se existe exatamente uma subpasta com .obsidian
    subdirs_with_obsidian = [
        d for d in base.iterdir() if d.is_dir() and (d / ".obsidian").is_dir()
    ]
    if len(subdirs_with_obsidian) == 1:
        return subdirs_with_obsidian[0]

    return base


def parse_markdown_frontmatter(raw_markdown: str) -> Tuple[Dict[str, str], str]:
    """
    Extrai metadados simples de YAML Frontmatter (`--- ... ---`) e retorna `(metadata, body)`.
    """
    text = raw_markdown.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text.strip()

    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", text, flags=re.DOTALL)
    if not match:
        return {}, text.strip()

    yaml_block, body = match.group(1), match.group(2)
    meta: Dict[str, str] = {}
    for line in yaml_block.splitlines():
        line_str = line.strip()
        if not line_str or line_str.startswith("#") or ":" not in line_str:
            continue
        k, v = line_str.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body.strip()


class ObsidianVaultBridge:
    """
    Ponte Bidirecional entre o Vault do Obsidian (`MY BRAIN`) e o Cérebro Cognitivo Fractal.
    """

    DIR_AXIOMS = "01_Axiomas_do_Usuario"
    DIR_SEMANTIC = "02_Conhecimento_Semantico"
    DIR_NEURONS = "03_Neuronios_Especialistas"
    DIR_EXECUTIONS = "04_Certificados_e_Execucoes"
    DIR_EVENTS = "04_Certificados_e_Execucoes/Eventos_Merkle_DAG"
    DIR_CANVAS = "05_Mapas_Visuais_Canvas"
    DIR_HIPPOCAMPUS = "06_Sabedoria_Consolidada_Hipocampo"
    DIR_GOVERNANCE = "07_Governanca_Homeostase_e_Dossies"
    MOC_FILENAME = "00_Painel_Central_MOC.md"

    def __init__(self, vault_path: str | Path) -> None:
        self.vault_root: Path = resolve_vault_root(vault_path)

    def _ensure_directories(self) -> None:
        for rel in (
            self.DIR_AXIOMS,
            self.DIR_SEMANTIC,
            self.DIR_NEURONS,
            self.DIR_EXECUTIONS,
            self.DIR_EVENTS,
            self.DIR_CANVAS,
            self.DIR_HIPPOCAMPUS,
            self.DIR_GOVERNANCE,
        ):
            (self.vault_root / rel).mkdir(parents=True, exist_ok=True)

    def configure_obsidian_graph(self) -> None:
        """
        Configura `.obsidian/graph.json` com setas direcionais causais e grupos cromáticos
        para que o Graph View do Obsidian diferencie imediatamente:
        - Painel Central (Ouro)
        - Axiomas do Usuário (Ciano)
        - Conhecimento Semântico CoALA (Verde Esmeralda)
        - Neurônios Especialistas (Violeta)
        - Hipocampo Sináptico (Rosa/Magenta)
        - Governança e Dossiês Cristalinos (Âmbar/Laranja)
        - Eventos de Rollback Causal / Rejeição (Vermelho)
        - Certificados e Eventos Aprovados (Azul)
        """
        obs_dir = self.vault_root / ".obsidian"
        obs_dir.mkdir(parents=True, exist_ok=True)
        graph_file = obs_dir / "graph.json"

        existing: Dict[str, Any] = {}
        if graph_file.exists():
            try:
                existing = json.loads(graph_file.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        color_groups = [
            {"query": "file:00_Painel_Central_MOC", "color": {"a": 1, "rgb": 16096779}},
            {"query": f"path:{self.DIR_AXIOMS}", "color": {"a": 1, "rgb": 439996}},
            {"query": f"path:{self.DIR_SEMANTIC}", "color": {"a": 1, "rgb": 1096065}},
            {"query": f"path:{self.DIR_NEURONS}", "color": {"a": 1, "rgb": 9133302}},
            {"query": f"path:{self.DIR_HIPPOCAMPUS}", "color": {"a": 1, "rgb": 15426466}},
            {"query": f"path:{self.DIR_GOVERNANCE}", "color": {"a": 1, "rgb": 16090651}},
            {"query": "tag:#verdict/REJECTED", "color": {"a": 1, "rgb": 15680580}},
            {"query": f"path:{self.DIR_EXECUTIONS}", "color": {"a": 1, "rgb": 3900150}},
        ]

        existing.update(
            {
                "showArrow": True,
                "showTags": False,
                "showOrphans": True,
                "hideUnresolved": False,
                "colorGroups": color_groups,
                "nodeSizeMultiplier": 1.15,
                "lineSizeMultiplier": 1.1,
            }
        )
        graph_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    def initialize_vault_structure(self) -> Dict[str, Any]:
        """
        Inicializa a estrutura completa do Vault `MY BRAIN`:
        - Pastas organizacionais numeradas
        - Grupos de cores do Graph View
        - Axiomas iniciais do usuário (`01_Axiomas_do_Usuario/`)
        - Base de Conhecimento Semântico inicial (`02_Conhecimento_Semantico/`)
        - Hubs dos 7 Neurônios do Córtex (`03_Neuronios_Especialistas/`)
        - Quadro Visual `.canvas` da Arquitetura (`05_Mapas_Visuais_Canvas/`)
        - Painel Central MOC (`00_Painel_Central_MOC.md`) e atualização do `Bem-vindo.md`
        """
        self._ensure_directories()
        self.configure_obsidian_graph()
        self._seed_starter_axioms()
        self._seed_starter_knowledge_base()
        self._write_specialist_neuron_hubs()
        canvas_arch_path = self._write_architecture_canvas()
        moc_path = self.update_central_moc()
        self._update_welcome_note()

        return {
            "vault_root": str(self.vault_root),
            "moc_path": str(moc_path),
            "architecture_canvas_path": str(canvas_arch_path),
        }

    def _seed_starter_axioms(self) -> None:
        axioms_dir = self.vault_root / self.DIR_AXIOMS
        starter_axioms = [
            (
                "Axioma_01_Fidelidade_Epistemica.md",
                "ax_fidelidade_epistemica",
                "Fidelidade Epistêmica e Proibição de Alucinação",
                (
                    "Toda afirmação factual ou técnica emitida pelo Cérebro Cognitivo deve possuir um "
                    "ProvenancePointer verificável apontando para um axioma explícito do usuário "
                    "(AXIOM_USER), documento semântico indexado com citação literal (RAG_DOCUMENT), "
                    "execução determinística em sandbox (DETERMINISTIC_EXEC) ou prova formal Z3 (FORMAL_PROOF)."
                ),
            ),
            (
                "Axioma_02_Isolamento_Zero_Trust.md",
                "ax_isolamento_zero_trust",
                "Isolamento Zero-Trust e Imutabilidade Criptográfica",
                (
                    "Nenhum neurônio gerador pode aprovar seu próprio trabalho. Todo artefato passa "
                    "obrigatoriamente pelo crivo ortogonal V1 (Auditoria de Proveniência), V2 (Sandbox AST "
                    "Allowlist + Detector de Testes Triviais + Citação Literal) e V3 (Crítico Adversarial "
                    "Duplo-Cego + Z3 SMT-LIB), com eventos selados por SHA-256 e assinatura Ed25519."
                ),
            ),
            (
                "Axioma_03_Diretrizes_Operacionais_Jarvis.md",
                "ax_diretrizes_jarvis",
                "Diretrizes do Assistente Cognitivo Pessoal (MY BRAIN)",
                (
                    "O Vault MY BRAIN no Obsidian atua como a superfície de memória de longo prazo e "
                    "inspeção visual do usuário. Notas adicionadas em 01_Axiomas_do_Usuario têm peso de "
                    "premissa inegociável, e notas em 02_Conhecimento_Semantico compõem a base documental "
                    "versionada do sistema."
                ),
            ),
        ]

        for filename, axiom_id, title, body in starter_axioms:
            fpath = axioms_dir / filename
            if not fpath.exists():
                content = (
                    "---\n"
                    f"type: user_axiom\n"
                    f"axiom_id: {axiom_id}\n"
                    f"title: \"{title}\"\n"
                    f"status: active\n"
                    f"created_utc: {utc_now_iso()}\n"
                    "tags:\n"
                    "  - axiom\n"
                    "  - my_brain\n"
                    "---\n\n"
                    f"# {title}\n\n"
                    f"{body}\n\n"
                    "---\n"
                    "**Conectado a:** [[00_Painel_Central_MOC]] | [[Neuronio_01_Logica_e_Matematica]] | [[Neuronio_04_Fatos_e_Proveniencia]]\n"
                )
                fpath.write_text(content, encoding="utf-8")

    def _seed_starter_knowledge_base(self) -> None:
        kb_dir = self.vault_root / self.DIR_SEMANTIC
        starter_docs = [
            (
                "KB_01_Arquitetura_Cerebro_Cognitivo_Fractal.md",
                "Arquitetura do Cérebro Cognitivo Fractal Multi-Agente v2.0",
                (
                    "O Cérebro Cognitivo Fractal Multi-Agente opera sobre uma topologia em dois níveis "
                    "auto-similares: o Macro-Córtex em Grafo Acíclico Dirigido (ExecutionDAG ordenado pelo "
                    "Algoritmo de Kahn) e o Micro-Córtex composto de 8 estágios internos em cada Neurônio.\n\n"
                    "Cada Neurônio Composto executa o loop fechado de geração e verificação ortogonal: "
                    "(1) Micro-Córtex de Contexto, (2) Subagente Pensador, (3) Verificador V1 de Lógica e "
                    "Proveniência, (4) Verificador V2 de Sandbox Determinístico e Citação Literal, "
                    "(5) Verificador V3 Adversarial Duplo-Cego e Z3 SMT-LIB, (6) Árbitro Epistêmico BFT, "
                    "(7) Consolidador de Estado e (8) Motor de Rollback Causal com Restrições Negativas."
                ),
                ["[[Neuronio_00_Talamo_Sensorial]]", "[[Neuronio_06_Convergencia_e_Sintese]]"],
            ),
            (
                "KB_02_Criptografia_Merkle_DAG_e_Ed25519.md",
                "Criptografia Forense: Cadeia SHA-256, Assinaturas Ed25519 e Âncoras Externas",
                (
                    "O EpistemicEventStore utiliza SQLite em modo WAL com triggers BEFORE UPDATE e BEFORE DELETE "
                    "que impedem qualquer mutação ou exclusão de eventos históricos. Cada EpistemicEvent "
                    "calcula seu content_hash via SHA-256 canônico encadeado ao previous_event_hash.\n\n"
                    "Na versão v2.0, o módulo EpistemicSigner adiciona assinaturas digitais assimétricas "
                    "Ed25519 (RFC 8032) por evento e o ExternalHashAnchor publica recibos de ancoragem "
                    "append-only fora do banco SQLite, eliminando o risco de reescrita coordenada da cadeia."
                ),
                ["[[Neuronio_02_Engenharia_de_Sistemas]]", "[[Neuronio_03_Estrategia_e_Risco]]"],
            ),
            (
                "KB_03_Memoria_CoALA_e_Verificacao_Formal_Z3.md",
                "Memória Tripartite CoALA (FTS5 BM25) e Verificação Formal Z3 SMT-LIB",
                (
                    "A arquitetura de memória CoALA separa estritamente três substratos: Memória Semântica "
                    "Versionada indexada via SQLite FTS5 BM25, Memória Episódica de execuções passadas e "
                    "Memória de Axiomas do Usuário.\n\n"
                    "Para impedir cascatas de auto-alucinação, a Memória Episódica é proibida de ser citada "
                    "como ProvenancePointer factual. Além disso, toda citação RAG_DOCUMENT exige que o trecho "
                    "quoted_excerpt conste literalmente no chunk ativo ou histórico verificado pela Camada V2."
                ),
                ["[[Neuronio_01_Logica_e_Matematica]]", "[[Neuronio_04_Fatos_e_Proveniencia]]"],
            ),
        ]

        for filename, title, body, links in starter_docs:
            fpath = kb_dir / filename
            if not fpath.exists():
                links_str = " | ".join(["[[00_Painel_Central_MOC]]"] + links)
                content = (
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
                    f"**Referenciado por:** {links_str}\n"
                )
                fpath.write_text(content, encoding="utf-8")

    def _write_specialist_neuron_hubs(self) -> None:
        neurons_dir = self.vault_root / self.DIR_NEURONS
        for neuron_id, info in NEURON_HUB_MAP.items():
            note_path = neurons_dir / f"{info['note_name']}.md"
            downstream_links = (
                ", ".join(f"[[{d}]]" for d in info["downstream"])
                if info["downstream"]
                else "*(Nó Terminal de Convergência)*"
            )
            content = (
                "---\n"
                "type: cognitive_neuron\n"
                f"neuron_id: {neuron_id}\n"
                f"wave: {info['wave']}\n"
                f"specialty: \"{info['specialty']}\"\n"
                "tags:\n"
                "  - neuron\n"
                f"  - wave_{info['wave']}\n"
                "---\n\n"
                f"# {info['title']}\n\n"
                f"- **ID Canônico no Córtex**: `{neuron_id}`\n"
                f"- **Onda Topológica (Algoritmo de Kahn)**: Onda `{info['wave']}`\n"
                f"- **Especialidade Epistêmica**: {info['specialty']}\n"
                f"- **Conexões Sinápticas de Saída (Downstream)**: {downstream_links}\n"
                f"- **Dossiê Arquitetural e Epistêmico Cristalino**: [[Dossie_{neuron_id}]]\n"
                f"- **Camada de Meta-Governança**: [[00_Relatorio_Severo_Meta_Governanca]]\n"
                f"- **Painel Central**: [[00_Painel_Central_MOC]]\n\n"
                "## Micro-Arquitetura Interna (8 Estágios Auto-Similares)\n\n"
                "1. **Micro-Córtex de Contexto**: Filtra sinais sinápticos, axiomas e restrições negativas.\n"
                "2. **Subagente Pensador (`Thinker`)**: Formula `HypothesisPayload` estruturada com `ProvenancePointer`.\n"
                "3. **Verificador V1 (Lógica & Proveniência)**: Exige lastro epistêmico em 100% das afirmações.\n"
                "4. **Verificador V2 (Sandbox & Citação Literal)**: AST Allowlist, detector de testes triviais e conferência literal CoALA RAG.\n"
                "5. **Verificador V3 (Crítico Duplo-Cego & Z3)**: Auditoria adversarial sem viés de confirmação e solver formal Z3.\n"
                "6. **Árbitro Epistêmico BFT**: Regra de Unanimidade Estrita ($V_1 \\land V_2 \\land V_3$).\n"
                "7. **Consolidador de Estado**: Emite `NeuronCertificate` selado com hash SHA-256.\n"
                "8. **Motor de Rollback Causal**: Bifurca a árvore em caso de rejeição e injeta `NegativeConstraint`.\n"
            )
            note_path.write_text(content, encoding="utf-8")

    def ingest_vault_knowledge(self, memory_store: CoALAMemoryStore) -> ObsidianIngestionReport:
        """
        Escaneia `01_Axiomas_do_Usuario/` e `02_Conhecimento_Semantico/` no Vault `MY BRAIN`,
        ingere axiomas e documentos na memória tripartite `CoALAMemoryStore` (FTS5 BM25)
        e retorna um `ObsidianIngestionReport` detalhado.
        """
        self._ensure_directories()
        axioms_count = 0
        docs_count = 0
        chunks_count = 0
        doc_map: Dict[str, Dict[str, Any]] = {}

        # 1. Ingerir Axiomas do Usuário
        axioms_dir = self.vault_root / self.DIR_AXIOMS
        for md_file in sorted(axioms_dir.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            meta, body = parse_markdown_frontmatter(raw)
            clean_body = self._strip_footer_links(body)
            axiom_id = meta.get("axiom_id") or f"ax_{md_file.stem.lower()}"
            title = meta.get("title") or md_file.stem
            registered_ax_id = memory_store.add_user_axiom(axiom_id=axiom_id, statement=clean_body)
            doc_id, chunk_ids = memory_store.ingest_document(
                source=f"obsidian://axioms/{md_file.name}",
                text=clean_body,
                title=title,
            )
            axioms_count += 1
            docs_count += 1
            chunks_count += len(chunk_ids)
            doc_map[md_file.name] = {
                "kind": "user_axiom",
                "axiom_id": registered_ax_id,
                "doc_id": doc_id,
                "chunk_ids": chunk_ids,
                "title": title,
            }

        # 2. Ingerir Conhecimento Semântico Versionado
        kb_dir = self.vault_root / self.DIR_SEMANTIC
        for md_file in sorted(kb_dir.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            meta, body = parse_markdown_frontmatter(raw)
            clean_body = self._strip_footer_links(body)
            title = meta.get("title") or md_file.stem
            doc_id, chunk_ids = memory_store.ingest_document(
                source=f"obsidian://semantic/{md_file.name}",
                text=clean_body,
                title=title,
            )
            docs_count += 1
            chunks_count += len(chunk_ids)
            doc_map[md_file.name] = {
                "kind": "semantic_knowledge",
                "doc_id": doc_id,
                "chunk_ids": chunk_ids,
                "title": title,
            }

        return ObsidianIngestionReport(
            vault_root=str(self.vault_root),
            axioms_ingested=axioms_count,
            documents_ingested=docs_count,
            total_chunks_indexed=chunks_count,
            document_map=doc_map,
        )

    @staticmethod
    def _strip_footer_links(markdown_body: str) -> str:
        """Remove rodapés de navegação (`**Conectado a:**` / `**Referenciado por:**`) para indexação limpa."""
        lines = []
        for line in markdown_body.splitlines():
            if line.strip().startswith("**Conectado a:**") or line.strip().startswith("**Referenciado por:**"):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def project_cortex_run_to_vault(
        self,
        cortex_result: Any,
        objective: str,
        event_store: Optional[EpistemicEventStore] = None,
    ) -> Dict[str, str]:
        """
        Projeta uma execução completa do Córtex (`CortexExecutionResult` ou `dict`)
        para dentro do Vault `MY BRAIN`:
        - Cria a nota mestre da execução em `04_Certificados_e_Execucoes/Execucao_<dag_id>.md`
        - Cria notas individuais para cada Certificado de Neurônio emitido
        - Sincroniza os eventos do Merkle-DAG (incluindo Rollbacks Causais)
        - Gera o quadro visual `.canvas` da execução (`02_Ultima_Execucao_Cortex_DAG.canvas`)
        - Atualiza o `00_Painel_Central_MOC.md`
        """
        self._ensure_directories()
        self._write_specialist_neuron_hubs()
        res_dict = cortex_result.to_dict() if hasattr(cortex_result, "to_dict") else dict(cortex_result)

        dag_id = res_dict.get("dag_id", "dag_live")
        status = res_dict.get("status", "APPROVED")
        exec_ms = res_dict.get("execution_time_ms", 0.0)
        conv_evt = res_dict.get("convergence_event_id", "evt_none")
        certificates: Dict[str, Any] = res_dict.get("certificates", {})

        exec_note_name = f"Execucao_{dag_id}"
        exec_note_path = self.vault_root / self.DIR_EXECUTIONS / f"{exec_note_name}.md"

        cert_links: List[str] = []
        for node_id, cert in certificates.items():
            cert_id = cert.get("certificate_id", f"cert_{node_id}")
            neuron_id = cert.get("neuron_id", "neuron_unknown")
            neuron_hub = NEURON_HUB_MAP.get(neuron_id, {}).get("note_name", "00_Painel_Central_MOC")
            cert_status = cert.get("status", "APPROVED")
            cert_hash = cert.get("certificate_hash", "")
            conf = cert.get("confidence_score", 0.0)
            iters = cert.get("total_iterations", 1)
            head_evt = cert.get("head_event_id", "")
            hyp = cert.get("final_hypothesis") or {}
            hyp_desc = hyp.get("description") or "Sem descrição"
            code_art = hyp.get("code_artifact") or ""
            claims = hyp.get("claims") or []

            cert_note_name = f"Cert_{dag_id}_{node_id}"
            cert_links.append(f"- [[{cert_note_name}]] (`{neuron_id}` -> `{cert_status}`, Hash: `{cert_hash[:16]}...`)")

            claims_md = "\n".join(
                f"  - **Afirmação**: {c.get('statement', '')}\n"
                f"    - *Proveniência*: `{(c.get('provenance') or {}).get('source_type', 'NONE')}` "
                f"(Ref: `{(c.get('provenance') or {}).get('reference_id', 'N/A')}`)"
                for c in claims
            ) or "  - *(Nenhuma afirmação registrada)*"

            verifiers_md = "\n".join(
                f"  - **{vr.get('verifier_layer')}**: `{vr.get('status')}` (Score: `{vr.get('score')}`)"
                for vr in cert.get("verifier_reports", [])
            ) or "  - *(Sem relatórios anexados)*"

            cert_md = (
                "---\n"
                "type: neuron_certificate\n"
                f"certificate_id: {cert_id}\n"
                f"dag_id: {dag_id}\n"
                f"node_id: {node_id}\n"
                f"neuron_id: {neuron_id}\n"
                f"status: {cert_status}\n"
                f"iterations: {iters}\n"
                f"confidence_score: {conf}\n"
                f"certificate_hash: {cert_hash}\n"
                "tags:\n"
                "  - certificate\n"
                f"  - verdict/{cert_status}\n"
                "---\n\n"
                f"# Certificado Epistêmico: `{node_id}` ({neuron_id})\n\n"
                f"- **Execução Pai**: [[{exec_note_name}]]\n"
                f"- **Neurônio Especialista**: [[{neuron_hub}]]\n"
                f"- **Status Final**: `{cert_status}`\n"
                f"- **Iterações Internas (Loop V1/V2/V3)**: `{iters}`\n"
                f"- **Score de Confiança Epistêmica**: `{conf}`\n"
                f"- **Hash SHA-256 do Certificado**: `{cert_hash}`\n"
                f"- **Evento Head no Merkle-DAG**: [[{head_evt}]]\n\n"
                "## Hipótese Certificada\n\n"
                f"> {hyp_desc}\n\n"
                "### Afirmações e Ponteiros de Proveniência\n"
                f"{claims_md}\n\n"
                "### Vereditos Ortogonais (V1 / V2 / V3)\n"
                f"{verifiers_md}\n\n"
                "### Artefato de Código Verificado em Sandbox\n"
                "```python\n"
                f"{code_art.strip()}\n"
                "```\n"
            )
            (self.vault_root / self.DIR_EXECUTIONS / f"{cert_note_name}.md").write_text(cert_md, encoding="utf-8")

        exec_md = (
            "---\n"
            "type: cortex_execution\n"
            f"dag_id: {dag_id}\n"
            f"status: {status}\n"
            f"execution_time_ms: {exec_ms}\n"
            f"convergence_event_id: {conv_evt}\n"
            f"timestamp_utc: {utc_now_iso()}\n"
            "tags:\n"
            "  - cortex_run\n"
            f"  - verdict/{status}\n"
            "---\n\n"
            f"# Execução do Córtex Global: `{dag_id}`\n\n"
            f"- **Objetivo / Estímulo Sensorial**: *{objective}*\n"
            f"- **Status de Convergência**: `{status}`\n"
            f"- **Tempo de Processamento**: `{exec_ms} ms`\n"
            f"- **Evento de Convergência no Merkle-DAG**: [[{conv_evt}]]\n"
            f"- **Tálamo Sensorial**: [[Neuronio_00_Talamo_Sensorial]]\n"
            f"- **Árbitro de Convergência**: [[Neuronio_06_Convergencia_e_Sintese]]\n"
            f"- **Painel Central**: [[00_Painel_Central_MOC]]\n\n"
            "## Certificados Emitidos pelos Neurônios Especialistas\n\n"
            + ("\n".join(cert_links) if cert_links else "- *(Execução de neurônio único)*")
            + "\n"
        )
        exec_note_path.write_text(exec_md, encoding="utf-8")

        if event_store is not None:
            self.sync_event_store_to_vault(event_store, max_events=45)

        canvas_exec_path = self._write_latest_execution_canvas(res_dict, objective)
        moc_path = self.update_central_moc(event_store=event_store)

        return {
            "execution_note": str(exec_note_path),
            "execution_canvas": str(canvas_exec_path),
            "moc_note": str(moc_path),
        }

    def sync_event_store_to_vault(self, event_store: EpistemicEventStore, max_events: int = 45) -> int:
        """
        Exporta eventos do `EpistemicEventStore` (priorizando eventos de Rollback Causal,
        rejeições V1/V2/V3, aprovações de neurônios e os eventos mais recentes) para
        `04_Certificados_e_Execucoes/Eventos_Merkle_DAG/`, conectados por `[[parent_event_id]]`.
        """
        self._ensure_directories()
        all_events = event_store.get_all_events()
        if not all_events:
            return 0

        # Seleciona eventos prioritários (rollbacks, rejeições, convergências) + últimos eventos
        priority = [
            e for e in all_events
            if e.verdict == "REJECTED"
            or "ROLLBACK" in e.event_type
            or "APPROVED" in e.event_type
            or "CONVERGENCE" in e.event_type
        ]
        recent = all_events[-max_events:]
        selected_map = {e.event_id: e for e in (priority + recent)}
        # Garante também que os pais imediatos dos selecionados estejam presentes para não quebrar elos no grafo
        all_by_id = {e.event_id: e for e in all_events}
        for e in list(selected_map.values()):
            if e.parent_event_id and e.parent_event_id in all_by_id:
                selected_map[e.parent_event_id] = all_by_id[e.parent_event_id]

        events_dir = self.vault_root / self.DIR_EVENTS
        count = 0
        for evt in selected_map.values():
            neuron_hub = NEURON_HUB_MAP.get(evt.neuron_id, {}).get("note_name", "00_Painel_Central_MOC")
            parent_link = f"[[{evt.parent_event_id}]]" if evt.parent_event_id else "*(Evento Gênesis)*"
            verdict_tag = f"verdict/{evt.verdict}"

            evt_md = (
                "---\n"
                "type: epistemic_event\n"
                f"event_id: {evt.event_id}\n"
                f"parent_event_id: {evt.parent_event_id or 'GENESIS'}\n"
                f"branch_id: {evt.branch_id}\n"
                f"neuron_id: {evt.neuron_id}\n"
                f"event_type: {evt.event_type}\n"
                f"verdict: {evt.verdict}\n"
                f"cycle_iteration: {evt.cycle_iteration}\n"
                f"confidence_score: {evt.confidence_score}\n"
                f"content_hash: {evt.content_hash}\n"
                f"previous_event_hash: {evt.previous_event_hash}\n"
                "tags:\n"
                "  - merkle_event\n"
                f"  - {verdict_tag}\n"
                f"  - event/{evt.event_type}\n"
                "---\n\n"
                f"# Evento Epistêmico `{evt.event_id}` ({evt.event_type})\n\n"
                f"- **Evento Pai (Causalidade Merkle-DAG)**: {parent_link}\n"
                f"- **Neurônio Origem**: [[{neuron_hub}]] (`{evt.neuron_id}`)\n"
                f"- **Papel do Subagente**: `{evt.subagent_role}`\n"
                f"- **Branch**: `{evt.branch_id}` (Iteração `{evt.cycle_iteration}`)\n"
                f"- **Veredito**: `{evt.verdict}` (Confiança: `{evt.confidence_score}`)\n"
                f"- **Hash SHA-256 (`content_hash`)**: `{evt.content_hash}`\n"
                f"- **Hash Anterior (`previous_event_hash`)**: `{evt.previous_event_hash}`\n"
                f"- **Timestamp UTC**: `{evt.timestamp_utc}`\n\n"
                "## Delta Causal (`delta_changes`)\n"
                "```json\n"
                f"{json.dumps(evt.delta_changes, indent=2, ensure_ascii=False)}\n"
                "```\n\n"
                "## Estado Epistêmico (`epistemic_state`)\n"
                "```json\n"
                f"{json.dumps(evt.epistemic_state, indent=2, ensure_ascii=False)}\n"
                "```\n"
            )
            (events_dir / f"{evt.event_id}.md").write_text(evt_md, encoding="utf-8")
            count += 1
        return count

    def _write_architecture_canvas(self) -> Path:
        """
        Gera um arquivo nativo JSON Canvas (`.canvas`) do Obsidian em
        `05_Mapas_Visuais_Canvas/01_Arquitetura_Macro_e_Micro_Cortex.canvas`.
        Cores oficiais do JSON Canvas Obsidian:
        "1"=Vermelho, "2"=Laranja, "3"=Amarelo, "4"=Verde, "5"=Ciano, "6"=Roxo.
        """
        canvas_path = self.vault_root / self.DIR_CANVAS / "01_Arquitetura_Macro_e_Micro_Cortex.canvas"
        nodes = [
            {
                "id": "node_moc",
                "type": "text",
                "x": -520,
                "y": 180,
                "width": 320,
                "height": 170,
                "color": "3",
                "text": "### 🧠 MY BRAIN (Obsidian Vault)\n\n- [[00_Painel_Central_MOC]]\n- Axiomas (`01_Axiomas_do_Usuario`)\n- RAG CoALA (`02_Conhecimento_Semantico`)",
            },
            {
                "id": "node_thalamus",
                "type": "text",
                "x": -100,
                "y": 180,
                "width": 320,
                "height": 170,
                "color": "6",
                "text": "### 📡 Onda 0: Tálamo Sensorial\n\n[[Neuronio_00_Talamo_Sensorial]]\nDecompõe o objetivo em um `ExecutionDAG` livre de ciclos (Algoritmo de Kahn).",
            },
            {
                "id": "node_n1",
                "type": "text",
                "x": 320,
                "y": 20,
                "width": 340,
                "height": 160,
                "color": "5",
                "text": "### 📐 Onda 1: Lógica & Matemática\n\n[[Neuronio_01_Logica_e_Matematica]]\nInvariantes formais, Condorcet e Solver Z3 SMT-LIB.",
            },
            {
                "id": "node_n4",
                "type": "text",
                "x": 320,
                "y": 340,
                "width": 340,
                "height": 160,
                "color": "5",
                "text": "### 📚 Onda 1: Fatos & Proveniência\n\n[[Neuronio_04_Fatos_e_Proveniencia]]\nBusca FTS5 BM25 e conferência literal de citações.",
            },
            {
                "id": "node_n2",
                "type": "text",
                "x": 760,
                "y": 20,
                "width": 340,
                "height": 160,
                "color": "4",
                "text": "### ⚙️ Onda 2: Engenharia de Sistemas\n\n[[Neuronio_02_Engenharia_de_Sistemas]]\nSíntese de código Python, AST Allowlist e Sandbox V2.",
            },
            {
                "id": "node_n3",
                "type": "text",
                "x": 760,
                "y": 340,
                "width": 340,
                "height": 160,
                "color": "2",
                "text": "### 🛡️ Onda 2: Estratégia & Risco\n\n[[Neuronio_03_Estrategia_e_Risco]]\nBFT Epistêmico, HardBudget e contenção de falhas.",
            },
            {
                "id": "node_n5",
                "type": "text",
                "x": 1200,
                "y": 180,
                "width": 340,
                "height": 170,
                "color": "6",
                "text": "### 🎓 Onda 3: Semântica & Didática\n\n[[Neuronio_05_Semantica_e_Didatica]]\nAlinhamento semântico estrito e consolidação.",
            },
            {
                "id": "node_conv",
                "type": "text",
                "x": 1640,
                "y": 180,
                "width": 360,
                "height": 190,
                "color": "4",
                "text": "### ✅ Onda 4: Convergência & Síntese\n\n[[Neuronio_06_Convergencia_e_Sintese]]\nValida hashes SHA-256 + assinaturas Ed25519 + âncoras externas e grava no SQLite WAL.",
            },
            {
                "id": "node_micro",
                "type": "text",
                "x": 520,
                "y": 580,
                "width": 620,
                "height": 210,
                "color": "1",
                "text": "### 🔬 Micro-Córtex Interno (Dentro de Cada Neurônio Especialista)\n\n`Thinker` ➔ **V1** (Proveniência) ∧ **V2** (Sandbox AST + Citação Literal) ∧ **V3** (Crítico Duplo-Cego + Z3)\nSe `V1 ∧ V2 ∧ V3 == True` ➔ Emite `NeuronCertificate` (`APPROVED`)\nSe qualquer verificador rejeitar ➔ **Motor de Rollback Causal** bifurca branch e injeta `NegativeConstraint`!",
            },
        ]

        edges = [
            {"id": "e1", "fromNode": "node_moc", "fromSide": "right", "toNode": "node_thalamus", "toSide": "left", "label": "Axiomas + RAG"},
            {"id": "e2", "fromNode": "node_thalamus", "fromSide": "right", "toNode": "node_n1", "toSide": "left", "label": "Onda 1"},
            {"id": "e3", "fromNode": "node_thalamus", "fromSide": "right", "toNode": "node_n4", "toSide": "left", "label": "Onda 1"},
            {"id": "e4", "fromNode": "node_n1", "fromSide": "right", "toNode": "node_n2", "toSide": "left", "label": "Invariantes"},
            {"id": "e5", "fromNode": "node_n1", "fromSide": "right", "toNode": "node_n3", "toSide": "left", "label": "Limites"},
            {"id": "e6", "fromNode": "node_n4", "fromSide": "right", "toNode": "node_n2", "toSide": "left", "label": "Proveniência"},
            {"id": "e7", "fromNode": "node_n4", "fromSide": "right", "toNode": "node_n3", "toSide": "left", "label": "Fatos"},
            {"id": "e8", "fromNode": "node_n2", "fromSide": "right", "toNode": "node_n5", "toSide": "left", "label": "Artefato"},
            {"id": "e9", "fromNode": "node_n3", "fromSide": "right", "toNode": "node_n5", "toSide": "left", "label": "Riscos"},
            {"id": "e10", "fromNode": "node_n5", "fromSide": "right", "toNode": "node_conv", "toSide": "left", "label": "Síntese"},
        ]

        canvas_data = {"nodes": nodes, "edges": edges}
        canvas_path.write_text(json.dumps(canvas_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return canvas_path

    def _write_latest_execution_canvas(self, res_dict: Dict[str, Any], objective: str) -> Path:
        """
        Gera um quadro JSON Canvas (`.canvas`) dinâmico com os resultados reais da última execução do Córtex.
        """
        canvas_path = self.vault_root / self.DIR_CANVAS / "02_Ultima_Execucao_Cortex_DAG.canvas"
        dag_id = res_dict.get("dag_id", "dag_live")
        status = res_dict.get("status", "APPROVED")
        exec_ms = res_dict.get("execution_time_ms", 0.0)
        certificates: Dict[str, Any] = res_dict.get("certificates", {})

        nodes: List[Dict[str, Any]] = [
            {
                "id": "stim",
                "type": "text",
                "x": -380,
                "y": 180,
                "width": 340,
                "height": 190,
                "color": "6",
                "text": (
                    f"### 🎯 Estímulo Sensorial\n\n"
                    f"**Objetivo**: {objective}\n\n"
                    f"- **DAG ID**: `{dag_id}`\n"
                    f"- **Nota**: [[Execucao_{dag_id}]]"
                ),
            }
        ]
        edges: List[Dict[str, Any]] = []

        cert_items = list(certificates.items())
        for idx, (node_id, cert) in enumerate(cert_items):
            col = idx // 3
            row = idx % 3
            cx = 80 + col * 420
            cy = -120 + row * 260
            c_status = cert.get("status", "APPROVED")
            c_color = "4" if c_status == "APPROVED" else "1"
            c_hash = str(cert.get("certificate_hash", ""))[:16]
            c_iters = cert.get("total_iterations", 1)
            c_conf = cert.get("confidence_score", 0.0)
            neuron_id = cert.get("neuron_id", node_id)
            cert_note = f"Cert_{dag_id}_{node_id}"

            nodes.append(
                {
                    "id": f"cert_{node_id}",
                    "type": "text",
                    "x": cx,
                    "y": cy,
                    "width": 350,
                    "height": 210,
                    "color": c_color,
                    "text": (
                        f"### 🧩 `{node_id}`\n"
                        f"**Neurônio**: `{neuron_id}`\n"
                        f"- **Status**: `{c_status}` (Iterações: `{c_iters}`)\n"
                        f"- **Confiança**: `{c_conf}`\n"
                        f"- **Hash**: `{c_hash}...`\n"
                        f"- [[{cert_note}]]"
                    ),
                }
            )
            edges.append(
                {
                    "id": f"edge_stim_{node_id}",
                    "fromNode": "stim",
                    "fromSide": "right",
                    "toNode": f"cert_{node_id}",
                    "toSide": "left",
                    "label": f"Onda {idx + 1}",
                }
            )
            edges.append(
                {
                    "id": f"edge_{node_id}_conv",
                    "fromNode": f"cert_{node_id}",
                    "fromSide": "right",
                    "toNode": "conv_final",
                    "toSide": "left",
                }
            )

        conv_color = "4" if status == "APPROVED" else "1"
        max_col = max((len(cert_items) - 1) // 3, 0) + 1
        nodes.append(
            {
                "id": "conv_final",
                "type": "text",
                "x": 80 + max_col * 420 + 60,
                "y": 140,
                "width": 360,
                "height": 210,
                "color": conv_color,
                "text": (
                    f"### 🏁 Convergência Córtex\n\n"
                    f"- **Veredito Global**: `{status}`\n"
                    f"- **Tempo Total**: `{exec_ms} ms`\n"
                    f"- **Certificados Verificados**: `{len(certificates)}`\n"
                    f"- [[Neuronio_06_Convergencia_e_Sintese]]"
                ),
            }
        )

        canvas_path.write_text(
            json.dumps({"nodes": nodes, "edges": edges}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return canvas_path

    def update_central_moc(
        self,
        event_store: Optional[EpistemicEventStore] = None,
        ingestion_report: Optional[ObsidianIngestionReport] = None,
    ) -> Path:
        """
        Gera ou atualiza o Mapa de Conteúdo Central (`00_Painel_Central_MOC.md`) na raiz do Vault.
        """
        moc_path = self.vault_root / self.MOC_FILENAME

        # Coleta estatísticas do Event Store se disponível
        total_events = "N/A"
        total_branches = "N/A"
        total_rollbacks = "N/A"
        chain_status = "100% ÍNTEGRA (SHA-256 + Ed25519)"
        if event_store is not None:
            summary = event_store.export_dag_summary()
            total_events = str(summary.get("total_events", 0))
            total_branches = str(summary.get("total_branches", 0))
            total_rollbacks = str(summary.get("total_rollbacks", 0))
            chain_status = (
                "100% ÍNTEGRA E VERIFICADA"
                if summary.get("chain_integrity_valid", True)
                else "VIOLAÇÃO DETECTADA"
            )

        axiom_files = sorted((self.vault_root / self.DIR_AXIOMS).glob("*.md"))
        kb_files = sorted((self.vault_root / self.DIR_SEMANTIC).glob("*.md"))
        dyn_neuron_files = sorted((self.vault_root / self.DIR_NEURONS).glob("Neuronio_Dinamico_*.md"))
        dossier_files = sorted((self.vault_root / self.DIR_GOVERNANCE).glob("Dossie_*.md"))
        exec_files = sorted(
            (self.vault_root / self.DIR_EXECUTIONS).glob("Execucao_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        rollback_events = sorted((self.vault_root / self.DIR_EVENTS).glob("*.md"))[:12]

        axioms_list_md = "\n".join(f"- [[{f.stem}]]" for f in axiom_files) or "- *(Nenhum axioma)*"
        kb_list_md = "\n".join(f"- [[{f.stem}]]" for f in kb_files) or "- *(Nenhum documento)*"
        dyn_neurons_md = (
            "\n".join(f"- [[{f.stem}]] *(Macro-Neurônio Dinâmico Ativo)*" for f in dyn_neuron_files)
            if dyn_neuron_files
            else "- *(Nenhum neurônio dinâmico criado ainda — fale sobre um tema inédito para acionar a Neurogênese!)*"
        )
        dossiers_list_md = (
            "\n".join(f"- [[{f.stem}]]" for f in dossier_files)
            if dossier_files
            else "- *(Execute a sincronização para gerar os Dossiês Cristalinos)*"
        )
        exec_list_md = "\n".join(f"- [[{f.stem}]]" for f in exec_files[:10]) or "- *(Nenhuma execução registrada)*"
        events_list_md = "\n".join(f"- [[{f.stem}]]" for f in rollback_events) or "- *(Nenhum evento exportado)*"

        ing_info = ""
        if ingestion_report is not None:
            ing_info = (
                f"- **Última Ingestão CoALA FTS5**: `{ingestion_report.axioms_ingested}` axiomas, "
                f"`{ingestion_report.documents_ingested}` documentos, "
                f"`{ingestion_report.total_chunks_indexed}` chunks indexados para verificação literal V2.\n"
            )

        content = (
            "---\n"
            "type: moc_dashboard\n"
            "title: \"Painel Central — MY BRAIN (Cérebro Cognitivo Fractal v3.2 + Meta-Governança)\"\n"
            f"updated_utc: {utc_now_iso()}\n"
            "tags:\n"
            "  - moc\n"
            "  - my_brain\n"
            "---\n\n"
            "# 🧠 Painel Central — MY BRAIN (`Cérebro Cognitivo Fractal v3.2`)\n\n"
            "> **Bem-vindo ao Córtex Visual Estendido (12 Nós Canônicos + Macro-Neurônios Dinâmicos + Camada Severa de Meta-Governança)!**\n"
            "> Pressione `Ctrl + G` no Obsidian para abrir o **Graph View** com setas causais e grupos cromáticos pré-configurados, ou abra os quadros interativos em `05_Mapas_Visuais_Canvas/`.\n\n"
            "## 📊 Telemetria Forense em Tempo Real\n\n"
            f"- **Integridade Criptográfica da Cadeia**: `{chain_status}`\n"
            f"- **Eventos Imutáveis no SQLite WAL**: `{total_events}`\n"
            f"- **Branches no Merkle-DAG**: `{total_branches}` | **Rollbacks Causais Contidos**: `{total_rollbacks}`\n"
            f"{ing_info}\n"
            "---\n\n"
            "## ⚖️ Camada Severa de Meta-Governança, Calibração e Poda Sináptica (`07_Governanca_Homeostase_e_Dossies/`)\n\n"
            "- 👉 **[[00_Relatorio_Severo_Meta_Governanca|📋 Relatório Executivo da Camada Severa de Meta-Governança, Pesos Sinápticos e Poda]]**\n"
            "- **Dossiês Arquiteturais e Epistêmicos Cristalinos (Todos os Neurônios Ativos e Podados)**:\n"
            f"{dossiers_list_md}\n\n"
            "---\n\n"
            "## 🗺️ Quadros Visuais Interativos (Obsidian Canvas)\n\n"
            "- [[01_Arquitetura_Macro_e_Micro_Cortex.canvas|📐 01. Arquitetura Completa Macro e Micro-Córtex (Canvas)]]\n"
            "- [[02_Ultima_Execucao_Cortex_DAG.canvas|⚡ 02. Última Execução do Córtex em DAG (Canvas)]]\n"
            "- [[Sabedoria_Sinaptica_Hipocampo|🧬 03. Hipocampo: Sabedoria Sináptica & Restrições Aprendidas]]\n\n"
            "---\n\n"
            "## 🧬 Topologia Estendida: 12 Nós Neurais em 4 Lobos Corticais (`03_Neuronios_Especialistas/`)\n\n"
            "1. **Onda 0 (Entrada Sensorial Adaptativa)**:\n"
            "   - [[Neuronio_00_Talamo_Sensorial]] · ([[Dossie_neuron_sensory_input|Dossiê Cristalino]])\n"
            "2. **Onda 1 (Fundação Formal, Factual e Criptográfica)**:\n"
            "   - [[Neuronio_01_Logica_e_Matematica]] *(Lobo Frontal Formal)* · ([[Dossie_neuron_logic_math|Dossiê]])\n"
            "   - [[Neuronio_04_Fatos_e_Proveniencia]] *(Lobo Temporal Semântico)* · ([[Dossie_neuron_epistemic_facts|Dossiê]])\n"
            "   - [[Neuronio_07_Criptografia_e_Seguranca_ZeroTrust]] *(Lobo Parietal Criptográfico)* · ([[Dossie_neuron_crypto_security|Dossiê]])\n"
            "3. **Onda 2 (Engenharia, Causalidade e Risco BFT)**:\n"
            "   - [[Neuronio_02_Engenharia_de_Sistemas]] *(Lobo Executivo de Engenharia)* · ([[Dossie_neuron_systems_engineering|Dossiê]])\n"
            "   - [[Neuronio_03_Estrategia_e_Risco]] *(Lobo Parietal de Risco & BFT)* · ([[Dossie_neuron_strategy_risk|Dossiê]])\n"
            "   - [[Neuronio_08_Inferencia_Causal_e_Contrafactual]] *(Lobo Frontal Do-Calculus)* · ([[Dossie_neuron_causal_counterfactual|Dossiê]])\n"
            "4. **Onda 3 (Metacognição, Hipocampo, Planejamento Recursivo e Semântica)**:\n"
            "   - [[Neuronio_09_Metacognicao_e_Calibracao_Epistemica]] *(Lobo Pré-Frontal Metacognitivo)* · ([[Dossie_neuron_metacognition_calibration|Dossiê]])\n"
            "   - [[Neuronio_10_Hipocampo_Consolidacao_Sinaptica]] *(Hipocampo de Plasticidade)* · ([[Dossie_neuron_episodic_consolidation|Dossiê]])\n"
            "   - [[Neuronio_11_Planejador_Recursivo_SubDAG]] *(Córtex Pré-Motor Recursivo)* · ([[Dossie_neuron_autonomous_planner|Dossiê]])\n"
            "   - [[Neuronio_05_Semantica_e_Didatica]] *(Lobo Temporal de Síntese)* · ([[Dossie_neuron_semantics_didactics|Dossiê]])\n"
            "5. **Onda 4 (Veredito Córtex Global)**:\n"
            "   - [[Neuronio_06_Convergencia_e_Sintese]] · ([[Dossie_neuron_convergence_synthesis|Dossiê Cristalino]])\n\n"
            "### ✨ Neocórtex Dinâmico (Macro-Neurônios Criados por Neurogênese Ontológica)\n\n"
            f"{dyn_neurons_md}\n\n"
            "---\n\n"
            "## 💎 Axiomas do Usuário (`01_Axiomas_do_Usuario/`)\n"
            "*Qualquer nota criada nesta pasta é ingerida como `AXIOM_USER` inegociável pelo Cérebro:*\n\n"
            f"{axioms_list_md}\n\n"
            "---\n\n"
            "## 📚 Conhecimento Semântico Versionado (`02_Conhecimento_Semantico/`)\n"
            "*Indexado via SQLite FTS5 BM25 com conferência literal de citações pela Camada V2:*\n\n"
            f"{kb_list_md}\n\n"
            "---\n\n"
            "## 🛡️ Execuções e Certificados do Córtex (`04_Certificados_e_Execucoes/`)\n\n"
            f"{exec_list_md}\n\n"
            "### 🔗 Amostra de Eventos do Merkle-DAG (`Eventos_Merkle_DAG/`)\n\n"
            f"{events_list_md}\n"
        )
        moc_path.write_text(content, encoding="utf-8")

        # Atualiza também o README.md na raiz do Vault para visualização direta no GitHub (repositório MY-BRAIN)
        readme_path = self.vault_root / "README.md"
        readme_md = (
            "# 🧠 MY BRAIN — Cérebro Cognitivo Fractal Multi-Agente (Obsidian Vault & Especificação Cristalina)\n\n"
            "Repositório oficial do Vault **`MY BRAIN`**, conectado bidirecionalmente ao motor transacional "
            "**Cérebro Cognitivo Fractal Multi-Agente v3.2**.\n\n"
            "## 🏛️ Estrutura Arquitetural do Vault\n\n"
            "- **[`00_Painel_Central_MOC.md`](./00_Painel_Central_MOC.md)**: Mapa de Conteúdo Central (MOC) e Telemetria Forense.\n"
            "- **[`01_Axiomas_do_Usuario/`](./01_Axiomas_do_Usuario/)**: Premissas e diretrizes inegociáveis (`AXIOM_USER`).\n"
            "- **[`02_Conhecimento_Semantico/`](./02_Conhecimento_Semantico/)**: Base documental versionada indexada via SQLite FTS5 BM25 (`RAG_DOCUMENT`).\n"
            "- **[`03_Neuronios_Especialistas/`](./03_Neuronios_Especialistas/)**: Os 12 Nós Neurais Canônicos distribuídos em 4 Lobos Corticais + Macro-Neurônios Dinâmicos criados por Neurogênese Ontológica.\n"
            "- **[`04_Certificados_e_Execucoes/`](./04_Certificados_e_Execucoes/)**: Certificados criptográficos SHA-256/Ed25519 e Eventos do Merkle-DAG.\n"
            "- **[`05_Mapas_Visuais_Canvas/`](./05_Mapas_Visuais_Canvas/)**: Quadros interativos JSON Canvas (`.canvas`) nativos do Obsidian.\n"
            "- **[`06_Sabedoria_Consolidada_Hipocampo/`](./06_Sabedoria_Consolidada_Hipocampo/)**: Memória de Plasticidade Sináptica de Longo Prazo (`NEGATIVE_CONSTRAINT` + `DISTILLED_INVARIANT`).\n"
            "- **[`07_Governanca_Homeostase_e_Dossies/`](./07_Governanca_Homeostase_e_Dossies/)**: **Camada Severa de Meta-Governança, Calibração Sináptica ($W_i$), Poda (`DORMANT_PRUNED`) e Dossiês Cristalinos de 100% dos Neurônios**.\n"
            "  - 👉 **[`00_Relatorio_Severo_Meta_Governanca.md`](./07_Governanca_Homeostase_e_Dossies/00_Relatorio_Severo_Meta_Governanca.md)**\n\n"
            "## ⚖️ Governança Epistêmica e Poda Sináptica\n\n"
            "Todo neurônio criado no Cérebro (seja nativo, seja um Macro-Neurônio nascido por Neurogênese Dinâmica como `neuron_dyn_fisica_avancada`, "
            "ou um neurônio de pico nichado desativado por poda sináptica como `neuron_dyn_dilatacao_temporal_aplicada`) possui um **Dossiê Arquitetural e Epistêmico Cristalino** "
            "auditado em [`07_Governanca_Homeostase_e_Dossies/`](./07_Governanca_Homeostase_e_Dossies/).\n"
        )
        readme_path.write_text(readme_md, encoding="utf-8")
        return moc_path

    def project_plasticity_to_vault(self, plasticity_memory: Any) -> Path:
        """
        Exporta as regras de Plasticidade Sináptica de Longo Prazo (`NEGATIVE_CONSTRAINT` de Rollbacks
        e `DISTILLED_INVARIANT` de execuções aprovadas) para `06_Sabedoria_Consolidada_Hipocampo/`.
        """
        self._ensure_directories()
        hippo_dir = self.vault_root / self.DIR_HIPPOCAMPUS
        rules = plasticity_memory.list_all_rules(limit=60)

        neg_rules = [r for r in rules if r.rule_type == "NEGATIVE_CONSTRAINT"]
        inv_rules = [r for r in rules if r.rule_type == "DISTILLED_INVARIANT"]

        neg_md = "\n".join(
            f"- **`{r.rule_id}`** (Neurônio: `{r.neuron_id}` · Origem: [[{r.source_event_id}]]): {r.rule_text}"
            for r in neg_rules
        ) or "- *(Nenhuma restrição negativa acumulada)*"

        inv_md = "\n".join(
            f"- **`{r.rule_id}`** (Neurônio: [[{NEURON_HUB_MAP.get(r.neuron_id, {}).get('note_name', '00_Painel_Central_MOC')}]] · Confiança: `{r.confidence}`): {r.rule_text}"
            for r in inv_rules[:25]
        ) or "- *(Nenhum invariante destilado ainda)*"

        hub_path = hippo_dir / "Sabedoria_Sinaptica_Hipocampo.md"
        content = (
            "---\n"
            "type: hippocampus_plasticity\n"
            "title: \"Sabedoria Sináptica Consolidada (Hipocampo v3.0)\"\n"
            f"total_rules: {len(rules)}\n"
            f"negative_constraints: {len(neg_rules)}\n"
            f"distilled_invariants: {len(inv_rules)}\n"
            f"updated_utc: {utc_now_iso()}\n"
            "tags:\n"
            "  - hippocampus\n"
            "  - synaptic_plasticity\n"
            "---\n\n"
            "# 🧬 Hipocampo — Sabedoria Sináptica Consolidada de Longo Prazo\n\n"
            "- **Conectado ao Painel Central**: [[00_Painel_Central_MOC]]\n"
            "- **Neurônio Gestor**: [[Neuronio_10_Hipocampo_Consolidacao_Sinaptica]]\n"
            f"- **Total de Regras Sinápticas Ativas**: `{len(rules)}` (`{len(neg_rules)}` anticorpos anti-falha + `{len(inv_rules)}` invariantes certificados)\n\n"
            "## 🛡️ Anticorpos Epistêmicos (`NEGATIVE_CONSTRAINT` Aprendidos de Rollbacks Causais)\n"
            "*Injetados automaticamente nas próximas execuções para impedir reincidência de erros V1/V2/V3:*\n\n"
            f"{neg_md}\n\n"
            "---\n\n"
            "## 💎 Invariantes Certificados Destilados (`DISTILLED_INVARIANT`)\n\n"
            f"{inv_md}\n"
        )
        hub_path.write_text(content, encoding="utf-8")
        return hub_path

    def _update_welcome_note(self) -> None:
        welcome_path = self.vault_root / "Bem-vindo.md"
        content = (
            "# Bem-vindo ao MY BRAIN 🧠\n\n"
            "Este Vault do Obsidian está conectado de forma bidirecional ao motor transacional do "
            "**Cérebro Cognitivo Fractal Multi-Agente v2.0** (`cerebro_cognitivo`).\n\n"
            "👉 **Acesse agora o Painel Central**: [[00_Painel_Central_MOC]]\n\n"
            "### Como usar seu Cérebro no Obsidian:\n"
            "1. **Abrir o Grafo Neural**: Pressione `Ctrl + G` para visualizar os Neurônios, Axiomas, Base de Conhecimento, Certificados e Rollbacks Causais coloridos automaticamente.\n"
            "2. **Inspecionar o Canvas Visual**: Abra `05_Mapas_Visuais_Canvas/01_Arquitetura_Macro_e_Micro_Cortex.canvas` ou `02_Ultima_Execucao_Cortex_DAG.canvas`.\n"
            "3. **Ensinar Novos Fatos ou Axiomas**: Crie qualquer nota Markdown em `01_Axiomas_do_Usuario/` ou `02_Conhecimento_Semantico/` e execute `python run_mvp.py --sync-obsidian`.\n"
        )
        welcome_path.write_text(content, encoding="utf-8")

    def build_obsidian_uri(self, relative_file_path: str) -> str:
        """
        Gera uma URI nativa `obsidian://open?vault=...&file=...` que funciona sem plugins
        para abrir uma nota ou `.canvas` diretamente na janela ativa do aplicativo Obsidian.
        """
        vault_name = urllib.parse.quote(self.vault_root.name)
        clean_file = relative_file_path.replace("\\", "/").lstrip("/")
        file_encoded = urllib.parse.quote(clean_file)
        return f"obsidian://open?vault={vault_name}&file={file_encoded}"

    def open_in_obsidian_app(self, relative_file_path: str) -> str:
        """Dispara o protocolo nativo `obsidian://` no sistema operacional para focar a nota/canvas."""
        uri = self.build_obsidian_uri(relative_file_path)
        try:
            webbrowser.open(uri)
        except Exception:
            pass
        return uri

    def commit_vault_snapshot(self, message: str = "chore(brain-sync): snapshot automatico do Cerebro Cognitivo") -> Dict[str, Any]:
        """
        Garante que o Vault tenha `.gitignore` seguro (excluindo `workspace.json` e chaves do Local REST API,
        mas preservando a configuração de auto-sync do `obsidian-git`) e cria um commit Git atômico
        com `git pull --rebase --autostash` e `git push origin HEAD` automáticos para a nuvem!
        """
        gitignore_path = self.vault_root / ".gitignore"
        safe_gitignore = (
            "# Ignorar estados voláteis de janela e segredos de API local\n"
            ".obsidian/workspace.json\n"
            ".obsidian/workspace-mobile.json\n"
            ".obsidian/cache\n"
            ".obsidian/plugins/obsidian-local-rest-api/data.json\n"
            ".trash/\n"
            ".DS_Store\n"
            "Thumbs.db\n"
        )
        gitignore_path.write_text(safe_gitignore, encoding="utf-8")
        try:
            if not (self.vault_root / ".git").exists():
                subprocess.run(
                    ["git", "init"],
                    cwd=str(self.vault_root),
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self.vault_root),
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.vault_root),
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if not (status_proc.stdout or "").strip():
                return {"committed": False, "reason": "working_tree_clean"}

            commit_proc = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.vault_root),
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            pushed = False
            remote_proc = subprocess.run(
                ["git", "remote"],
                cwd=str(self.vault_root),
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if "origin" in (remote_proc.stdout or "").splitlines():
                try:
                    subprocess.run(
                        ["git", "pull", "--rebase", "--autostash", "origin", "HEAD"],
                        cwd=str(self.vault_root),
                        capture_output=True,
                        text=True,
                        timeout=10.0,
                    )
                    push_proc = subprocess.run(
                        ["git", "push", "origin", "HEAD"],
                        cwd=str(self.vault_root),
                        capture_output=True,
                        text=True,
                        timeout=10.0,
                    )
                    pushed = push_proc.returncode == 0
                except Exception:
                    pushed = False
            return {
                "committed": commit_proc.returncode == 0,
                "pushed_to_github": pushed,
                "stdout": (commit_proc.stdout or "").strip(),
            }
        except Exception as e:
            return {"committed": False, "error": str(e)}


class ObsidianLocalRestClient:
    """
    Cliente nativo zero-dependência para o plugin comunitário `Local REST API` do Obsidian
    (por padrão em `https://127.0.0.1:27124` ou `http://127.0.0.1:27123`).

    Descobre automaticamente a `apiKey` e a `port` em `.obsidian/plugins/obsidian-local-rest-api/data.json`
    quando o Vault `MY BRAIN` está presente no disco!
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        vault_path: Optional[str | Path] = None,
        timeout_sec: float = 3.0,
    ) -> None:
        discovered_key = ""
        discovered_url = ""
        target_vault = vault_path or discover_default_vault_path()
        try:
            v_root = resolve_vault_root(target_vault)
            plugin_cfg = v_root / ".obsidian" / "plugins" / "obsidian-local-rest-api" / "data.json"
            if plugin_cfg.exists():
                cfg_data = json.loads(plugin_cfg.read_text(encoding="utf-8"))
                discovered_key = str(cfg_data.get("apiKey", "")).strip()
                port = cfg_data.get("port", 27124)
                discovered_url = f"https://127.0.0.1:{port}"
        except Exception:
            pass

        self.api_key = (
            api_key
            or os.environ.get("OBSIDIAN_API_KEY", "")
            or discovered_key
        ).strip()
        self.base_url = (
            base_url
            or os.environ.get("OBSIDIAN_REST_URL", "")
            or discovered_url
            or "https://127.0.0.1:27124"
        ).rstrip("/")
        self.timeout_sec = timeout_sec
        # O plugin Local REST API usa certificado auto-assinado em localhost:27124
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[bytes] = None,
        content_type: str = "application/json",
        accept: str = "application/json",
    ) -> Tuple[int, str]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Accept": accept,
            "Content-Type": content_type,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            if url.startswith("https://"):
                with urllib.request.urlopen(req, timeout=self.timeout_sec, context=self._ssl_ctx) as resp:
                    return resp.status, resp.read().decode("utf-8", errors="replace")
            else:
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            return e.code, err_body
        except Exception as e:
            return 0, str(e)

    def check_status(self) -> Dict[str, Any]:
        """Verifica se o plugin Local REST API está online e autenticado no Obsidian."""
        code, raw = self._request("GET", "/")
        if code == 200:
            try:
                data = json.loads(raw)
                return {"online": True, "authenticated": bool(data.get("authenticated")), "raw": data}
            except Exception:
                return {"online": True, "authenticated": False, "raw": raw}
        return {"online": False, "authenticated": False, "status_code": code, "error": raw}

    def get_active_note(self) -> Dict[str, Any]:
        """Retorna o conteúdo e metadados da nota que o usuário está olhando agora no Obsidian."""
        code, raw = self._request("GET", "/active/", accept="application/vnd.olrapi.note+json")
        if code == 200:
            try:
                return {"ok": True, "note": json.loads(raw)}
            except Exception:
                return {"ok": True, "content": raw}
        return {"ok": False, "status_code": code, "error": raw}

    def open_file_in_ui(self, relative_path: str, new_leaf: bool = False) -> Dict[str, Any]:
        """Manda a interface do Obsidian abrir imediatamente uma nota ou `.canvas`."""
        encoded = urllib.parse.quote(relative_path.replace("\\", "/").lstrip("/"))
        query = "?newLeaf=true" if new_leaf else ""
        code, raw = self._request("POST", f"/open/{encoded}{query}")
        return {"ok": code in (200, 204), "status_code": code, "response": raw}

    def execute_command(self, command_id: str) -> Dict[str, Any]:
        """Executa qualquer comando nativo do Obsidian (ex.: `graph:open`, `app:reload`)."""
        encoded = urllib.parse.quote(command_id)
        code, raw = self._request("POST", f"/commands/{encoded}/")
        return {"ok": code in (200, 204), "status_code": code, "response": raw}

