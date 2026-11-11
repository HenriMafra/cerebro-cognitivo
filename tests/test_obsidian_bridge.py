"""
Suíte de Testes Unitários e de Integração para a Ponte Bidirecional Obsidian Vault (MY BRAIN).
Valida:
1. Resolução inteligente de raiz aninhada (`MY BRAIN/MY BRAIN/.obsidian`).
2. Inicialização estrutural do Vault (pastas, hubs neurais, `.obsidian/graph.json`, `.canvas` e MOC).
3. Ingestão semântica e axiomática no `CoALAMemoryStore` (FTS5 BM25 + Citação Literal V2).
4. Projeção de execução do `FractalCognitiveCortex` e eventos do `EpistemicEventStore` para notas Markdown e JSON Canvas.
"""

from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_ROOT.parent))

from core.cortex import FractalCognitiveCortex
from core.event_store import EpistemicEventStore
from core.obsidian_bridge import (
    NEURON_HUB_MAP,
    ObsidianVaultBridge,
    parse_markdown_frontmatter,
    resolve_vault_root,
)
from core.rag_memory import CoALAMemoryStore


class TestObsidianVaultBridge(unittest.TestCase):
    def test_01_resolve_nested_obsidian_root(self) -> None:
        """Garante que `MY BRAIN/MY BRAIN/.obsidian` seja detectado automaticamente."""
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "MY BRAIN"
            inner = outer / "MY BRAIN"
            (inner / ".obsidian").mkdir(parents=True, exist_ok=True)

            resolved = resolve_vault_root(outer)
            self.assertEqual(resolved, inner.resolve())

    def test_02_parse_markdown_frontmatter(self) -> None:
        raw = (
            "---\n"
            "type: user_axiom\n"
            "axiom_id: ax_test_01\n"
            "title: \"Meu Axioma\"\n"
            "---\n\n"
            "Corpo do axioma com texto verificável.\n"
        )
        meta, body = parse_markdown_frontmatter(raw)
        self.assertEqual(meta["type"], "user_axiom")
        self.assertEqual(meta["axiom_id"], "ax_test_01")
        self.assertEqual(meta["title"], "Meu Axioma")
        self.assertEqual(body, "Corpo do axioma com texto verificável.")

    def test_03_initialize_and_ingest_vault_into_coala_rag(self) -> None:
        """Testa inicialização completa do Vault e conferência literal de citação V2 sobre notas do Obsidian."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "MY BRAIN" / "MY BRAIN"
            (vault_dir / ".obsidian").mkdir(parents=True, exist_ok=True)

            bridge = ObsidianVaultBridge(Path(tmp) / "MY BRAIN")
            init_res = bridge.initialize_vault_structure()
            self.assertEqual(Path(init_res["vault_root"]), vault_dir.resolve())

            # Verifica criação dos 7 neurônios especialistas/córtex
            for info in NEURON_HUB_MAP.values():
                hub_file = vault_dir / bridge.DIR_NEURONS / f"{info['note_name']}.md"
                self.assertTrue(hub_file.exists(), f"Hub neural ausente: {hub_file}")

            # Verifica configuração de cores e setas no graph.json
            graph_cfg = json.loads((vault_dir / ".obsidian" / "graph.json").read_text(encoding="utf-8"))
            self.assertTrue(graph_cfg["showArrow"])
            self.assertGreaterEqual(len(graph_cfg["colorGroups"]), 5)

            # Ingestão para CoALAMemoryStore
            mem = CoALAMemoryStore(":memory:")
            try:
                report = bridge.ingest_vault_knowledge(mem)
                self.assertGreaterEqual(report.axioms_ingested, 3)
                self.assertGreaterEqual(report.documents_ingested, 6)
                self.assertGreaterEqual(report.total_chunks_indexed, 6)

                axioms = mem.list_user_axioms()
                self.assertGreaterEqual(len(axioms), 3)

                # Busca BM25 FTS5 sobre nota do Obsidian e verificação literal V2
                hits = mem.search_semantic("Ed25519 ExternalHashAnchor SQLite WAL", top_k=3)
                self.assertTrue(len(hits) >= 1)
                top_chunk = hits[0]
                ok, msg = mem.verify_literal_quote(
                    top_chunk.chunk_id,
                    "assinaturas digitais assimétricas Ed25519 (RFC 8032)",
                )
                self.assertTrue(ok, msg)
            finally:
                mem.close()

    def test_04_project_cortex_execution_and_canvas(self) -> None:
        """Executa o Córtex Global e projeta certificados, eventos e `.canvas` no Vault."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "MY BRAIN"
            bridge = ObsidianVaultBridge(vault_dir)
            bridge.initialize_vault_structure()

            store = EpistemicEventStore(":memory:")
            try:
                cortex = FractalCognitiveCortex(event_store=store)
                objective = "Certificar integração bidirecional Obsidian MY BRAIN com Merkle-DAG"
                res = cortex.process(objective=objective)

                proj = bridge.project_cortex_run_to_vault(res, objective=objective, event_store=store)
                self.assertTrue(Path(proj["execution_note"]).exists())
                self.assertTrue(Path(proj["execution_canvas"]).exists())
                self.assertTrue(Path(proj["moc_note"]).exists())

                canvas_obj = json.loads(Path(proj["execution_canvas"]).read_text(encoding="utf-8"))
                self.assertIn("nodes", canvas_obj)
                self.assertIn("edges", canvas_obj)
                self.assertGreaterEqual(len(canvas_obj["nodes"]), 7)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
