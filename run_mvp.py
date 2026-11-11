"""
Ponto de Entrada Interativo do MVP — Cérebro Cognitivo Fractal Multi-Agente.
Oferece dois modos de operação reais sobre o motor canônico:
1. Modo Servidor Web Interativo (Studio Live em http://127.0.0.1:8765)
2. Modo CLI Interativo no Terminal (`python run_mvp.py --cli` ou `--prompt "..."`)
"""

from __future__ import annotations
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.schemas import (
    Claim,
    HypothesisPayload,
    ProvenancePointer,
    ProvenanceType,
    SynapticSignal,
    VerdictStatus,
)
from core.event_store import EpistemicEventStore
from core.neuron import CognitiveNeuron
from core.cortex import FractalCognitiveCortex
from core.extended_cortex_v3 import ExtendedCognitiveCortexV3, SynapticPlasticityMemory
from core.meta_governance_layer import SevereMetaGovernanceLayer
from core.rag_memory import CoALAMemoryStore
from core.obsidian_bridge import (
    ObsidianVaultBridge,
    ObsidianLocalRestClient,
    discover_default_vault_path,
)
from core.jarvis_voice import JarvisCognitiveAssistant, save_local_env
from dashboard.inspector_generator import generate_telemetry_dashboard
from tests.chaos_benchmark import run_chaos_benchmark


DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB = DATA_DIR / "epistemic_brain.db"
DEFAULT_JSONL = DATA_DIR / "epistemic_events.jsonl"
DEFAULT_RAG_DB = DATA_DIR / "coala_memory.db"
DEFAULT_OBSIDIAN_VAULT = discover_default_vault_path(auto_clone_if_missing=True)


def sync_obsidian_vault(vault_path: Path = DEFAULT_OBSIDIAN_VAULT) -> Dict[str, Any]:
    """
    Sincroniza bidirecionalmente o Vault do Obsidian (MY BRAIN) com o
    CoALAMemoryStore (FTS5 BM25) e o EpistemicEventStore (SQLite WAL).
    """
    bridge = ObsidianVaultBridge(vault_path)
    init_info = bridge.initialize_vault_structure()

    mem_store = CoALAMemoryStore(db_path=str(DEFAULT_RAG_DB))
    plasticity = SynapticPlasticityMemory(db_path=str(DEFAULT_RAG_DB))
    gov = SevereMetaGovernanceLayer(db_path=str(DEFAULT_RAG_DB))
    store = EpistemicEventStore(db_path=str(DEFAULT_DB), jsonl_path=str(DEFAULT_JSONL))
    try:
        ingestion = bridge.ingest_vault_knowledge(mem_store)
        exported_events = bridge.sync_event_store_to_vault(store, max_events=50)
        plasticity.harvest_from_event_store(store)
        hippo_path = bridge.project_plasticity_to_vault(plasticity)
        audit_summary = gov.audit_and_calibrate_brain(store, plasticity)
        gov_out = gov.write_crystalline_dossiers_to_vault(bridge.vault_root, audit_summary, event_store=store)
        bridge._write_specialist_neuron_hubs()
        moc_path = bridge.update_central_moc(event_store=store, ingestion_report=ingestion)
        git_snap = bridge.commit_vault_snapshot("chore(brain-sync): sincronizacao automatica + dossies cristalinos v3.2")
        return {
            "vault_root": init_info["vault_root"],
            "moc_path": str(moc_path),
            "hippocampus_path": str(hippo_path),
            "governance_report_path": gov_out["governance_report_path"],
            "dossiers_written": gov_out["dossiers_written"],
            "architecture_canvas_path": init_info["architecture_canvas_path"],
            "axioms_ingested": ingestion.axioms_ingested,
            "documents_ingested": ingestion.documents_ingested,
            "total_chunks_indexed": ingestion.total_chunks_indexed,
            "exported_events": exported_events,
            "vault_git_snapshot": git_snap,
        }
    finally:
        gov.close()
        plasticity.close()
        mem_store.close()
        store.close()


def execute_objective_in_cortex(objective: str, inject_fault_mode: str = "none") -> Dict[str, Any]:
    """
    Executa um objetivo real no Córtex Global (ou simula injeção de falha controlada
    para demonstrar o Rollback Causal ao vivo) e atualiza o painel de telemetria.
    """
    store = EpistemicEventStore(db_path=str(DEFAULT_DB), jsonl_path=str(DEFAULT_JSONL))
    t0 = time.perf_counter()

    try:
        if inject_fault_mode == "hallucination_v1":
            # Demonstração ao vivo: Iteração 1 alucina sem ProvenancePointer -> V1 bloqueia -> Iteração 2 corrige
            def thinker_v1(sig: SynapticSignal, it: int, neg: List[str]) -> HypothesisPayload:
                if it == 1:
                    return HypothesisPayload(
                        iteration=it,
                        description=f"Hipótese inicial sem lastro para: {objective}",
                        claims=[Claim(statement=f"Suposição não verificada sobre: {objective}", provenance=None)],
                        code_artifact="def solve() -> bool:\n    return True\n",
                        entrypoint_function="solve",
                        expected_invariants=["solve() is True"],
                        negative_constraints_applied=list(neg),
                    )
                prov = ProvenancePointer(
                    source_type=ProvenanceType.AXIOM_USER,
                    reference_id=sig.signal_id,
                    excerpt=f"Axioma validado para: {objective}",
                )
                return HypothesisPayload(
                    iteration=it,
                    description=f"Hipótese corrigida após Rollback V1 para: {objective}",
                    claims=[Claim(statement=f"Solução formalmente ancorada para: {objective}", provenance=prov)],
                    code_artifact="def solve() -> bool:\n    return True\n",
                    entrypoint_function="solve",
                    expected_invariants=["solve() is True"],
                    negative_constraints_applied=list(neg),
                )

            neuron = CognitiveNeuron(
                neuron_id="neuron_live_v1_demo",
                specialty="Auditoria Lógica V1",
                event_store=store,
                max_iterations=3,
                custom_thinker_fn=thinker_v1,
            )
            sig = SynapticSignal(
                source_neuron="user_live_input",
                target_neuron="neuron_live_v1_demo",
                task_intent=objective,
                axioms=[f"Objetivo do usuário: {objective}"],
            )
            cert = neuron.process_signal(sig, branch_id="live_v1_branch")
            result_payload = cert.to_dict()

        elif inject_fault_mode == "runtime_bug_v2":
            # Demonstração ao vivo: Iteração 1 gera ZeroDivisionError -> V2 Sandbox bloqueia -> Iteração 2 corrige
            def thinker_v2(sig: SynapticSignal, it: int, neg: List[str]) -> HypothesisPayload:
                prov = ProvenancePointer(
                    source_type=ProvenanceType.DETERMINISTIC_EXEC,
                    reference_id=sig.signal_id,
                    excerpt=f"Execução em Sandbox para: {objective}",
                )
                if it == 1:
                    return HypothesisPayload(
                        iteration=it,
                        description="Tentativa 1 com erro de execução (ZeroDivisionError)",
                        claims=[Claim(statement="Cálculo aritmético direto.", provenance=prov)],
                        code_artifact="def compute(x: int) -> float:\n    return 100 / (x - x)\n",
                        entrypoint_function="compute",
                        expected_invariants=["compute(10) == 10.0"],
                        negative_constraints_applied=list(neg),
                    )
                return HypothesisPayload(
                    iteration=it,
                    description="Tentativa 2 corrigida após captura de stderr no Sandbox V2",
                    claims=[Claim(statement="Cálculo protegido contra divisão por zero.", provenance=prov)],
                    code_artifact="def compute(x: int) -> float:\n    return 10.0 if x == 10 else float(x)\n",
                    entrypoint_function="compute",
                    expected_invariants=["compute(10) == 10.0"],
                    negative_constraints_applied=list(neg),
                )

            neuron = CognitiveNeuron(
                neuron_id="neuron_live_v2_demo",
                specialty="Sandbox Determinístico V2",
                event_store=store,
                max_iterations=3,
                custom_thinker_fn=thinker_v2,
            )
            sig = SynapticSignal(
                source_neuron="user_live_input",
                target_neuron="neuron_live_v2_demo",
                task_intent=objective,
                axioms=[f"Objetivo do usuário: {objective}"],
            )
            cert = neuron.process_signal(sig, branch_id="live_v2_branch")
            result_payload = cert.to_dict()

        else:
            # Execução completa no Córtex Estendido v3.0 (Tálamo -> 10 Especialistas em 4 Lobos -> Convergência + Hipocampo)
            plasticity = SynapticPlasticityMemory(db_path=str(DEFAULT_RAG_DB))
            try:
                cortex = ExtendedCognitiveCortexV3(event_store=store, plasticity_memory=plasticity)
                cortex_res = cortex.process_v3(objective=objective)
                result_payload = cortex_res.to_dict()
            finally:
                plasticity.close()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        dag_summary = store.export_dag_summary()

        # Atualizar dashboard estático também
        bench_path = DATA_DIR / "chaos_benchmark_report.json"
        bench_data = json.loads(bench_path.read_text(encoding="utf-8")) if bench_path.exists() else None
        generate_telemetry_dashboard(
            dag_summary=dag_summary,
            benchmark_results=bench_data,
            output_html_path=str(PROJECT_ROOT / "dashboard" / "inspector_telemetria.html"),
        )

        # Projeção automática no Vault MY BRAIN do Obsidian (se presente)
        obsidian_projection = None
        if DEFAULT_OBSIDIAN_VAULT.exists():
            bridge = ObsidianVaultBridge(DEFAULT_OBSIDIAN_VAULT)
            bridge.initialize_vault_structure()
            mem_store = CoALAMemoryStore(db_path=str(DEFAULT_RAG_DB))
            plasticity = SynapticPlasticityMemory(db_path=str(DEFAULT_RAG_DB))
            gov = SevereMetaGovernanceLayer(db_path=str(DEFAULT_RAG_DB))
            try:
                ing = bridge.ingest_vault_knowledge(mem_store)
                proj = bridge.project_cortex_run_to_vault(
                    result_payload,
                    objective=objective,
                    event_store=store,
                )
                plasticity.harvest_from_event_store(store)
                hippo_path = bridge.project_plasticity_to_vault(plasticity)
                audit_summary = gov.audit_and_calibrate_brain(store, plasticity)
                gov_out = gov.write_crystalline_dossiers_to_vault(bridge.vault_root, audit_summary, event_store=store)
                bridge._write_specialist_neuron_hubs()
                proj["hippocampus_note"] = str(hippo_path)
                proj["governance_report"] = gov_out["governance_report_path"]
                proj["dossiers_written"] = gov_out["dossiers_written"]
                bridge.update_central_moc(event_store=store, ingestion_report=ing)
                bridge.commit_vault_snapshot(f"feat(cortex-v3.2): {objective[:55]}")
                obsidian_projection = {
                    "vault_root": str(bridge.vault_root),
                    **proj,
                    "axioms_ingested": ing.axioms_ingested,
                    "documents_ingested": ing.documents_ingested,
                    "total_chunks_indexed": ing.total_chunks_indexed,
                }
            finally:
                gov.close()
                plasticity.close()
                mem_store.close()

        return {
            "ok": True,
            "objective": objective,
            "inject_fault_mode": inject_fault_mode,
            "elapsed_ms": round(elapsed_ms, 2),
            "result": result_payload,
            "obsidian": obsidian_projection,
            "dag_summary": {
                "total_events": dag_summary["total_events"],
                "total_branches": dag_summary["total_branches"],
                "total_rollbacks": dag_summary["total_rollbacks"],
                "chain_integrity_valid": dag_summary["chain_integrity_valid"],
            },
        }
    finally:
        store.close()


def run_cli_one_shot(prompt: str, fault_mode: str = "none") -> None:
    print("=" * 78)
    print(" CÉREBRO COGNITIVO FRACTAL MULTI-AGENTE · EXECUÇÃO DO MVP")
    print("=" * 78)
    print(f" -> Estímulo Sensorial: {prompt}")
    print(f" -> Modo de Injeção de Falha: {fault_mode}")
    print("-" * 78)

    response = execute_objective_in_cortex(prompt, inject_fault_mode=fault_mode)
    summary = response["dag_summary"]
    res = response["result"]

    print(f" [STATUS FINAL]      : {res.get('status')}")
    print(f" [TEMPO DE EXECUÇÃO] : {response['elapsed_ms']} ms")
    print(f" [TOTAL DE EVENTOS]  : {summary['total_events']} eventos imutáveis no SQLite WAL")
    print(f" [BRANCHES NO DAG]   : {summary['total_branches']} branches | {summary['total_rollbacks']} rollbacks causais")
    print(f" [CADEIA SHA-256]    : {'100% ÍNTEGRA E VERIFICADA' if summary['chain_integrity_valid'] else 'VIOLAÇÃO DETECTADA'}")

    if "certificates" in res:
        print("\n -> Certificados Emitidos pelos 5 Neurônios Especialistas do Córtex:")
        for nid, cert in res["certificates"].items():
            print(
                f"    • {nid:<28} | Status: {cert['status']:<10} | "
                f"Iterações: {cert['total_iterations']} | Hash: {cert['certificate_hash'][:22]}..."
            )
    else:
        print(
            f"\n -> Certificado do Neurônio ({res.get('neuron_id')}): "
            f"Status={res.get('status')} | Iterações={res.get('total_iterations')} | "
            f"Hash={str(res.get('certificate_hash'))[:24]}..."
        )

    print("-" * 78)
    print(f" Painel de Telemetria atualizado em: {PROJECT_ROOT / 'dashboard' / 'inspector_telemetria.html'}")
    if response.get("obsidian"):
        obs = response["obsidian"]
        print(f" Obsidian Vault (MY BRAIN) sincronizado em: {obs['vault_root']}")
        print(f"   • Nota da Execução : {obs['execution_note']}")
        print(f"   • Canvas Visual    : {obs['execution_canvas']}")
        print(f"   • Memória CoALA    : {obs['axioms_ingested']} axiomas, {obs['documents_ingested']} docs ({obs['total_chunks_indexed']} chunks)")
    print("=" * 78)


class MVPStudioHandler(BaseHTTPRequestHandler):
    """Servidor HTTP local que serve o Painel Interativo e a API de Execução do Cérebro."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path in ("/", "/jarvis"):
            jarvis_html_path = PROJECT_ROOT / "dashboard" / "jarvis_console.html"
            raw = jarvis_html_path.read_text(encoding="utf-8").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path in ("/index.html", "/dashboard"):
            dash_path = PROJECT_ROOT / "dashboard" / "inspector_telemetria.html"
            if not dash_path.exists():
                run_chaos_benchmark()
            html = dash_path.read_text(encoding="utf-8")
            raw = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/jarvis/status":
            jarvis = JarvisCognitiveAssistant(
                db_path=str(DEFAULT_DB),
                jsonl_path=str(DEFAULT_JSONL),
                rag_db_path=str(DEFAULT_RAG_DB),
                vault_path=DEFAULT_OBSIDIAN_VAULT,
            )
            self._send_json(jarvis.get_system_status())
        elif self.path == "/api/status":
            store = EpistemicEventStore(db_path=str(DEFAULT_DB), jsonl_path=str(DEFAULT_JSONL))
            try:
                summary = store.export_dag_summary()
            finally:
                store.close()
            self._send_json({"ok": True, "summary": summary})
        else:
            self.send_error(404, "Rota nao encontrada")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/execute":
            objective = body.get("objective", "Validar invariantes formais do sistema")
            fault_mode = body.get("fault_mode", "none")
            out = execute_objective_in_cortex(objective, inject_fault_mode=fault_mode)
            self._send_json(out)
        elif self.path == "/api/jarvis/command":
            command = body.get("command", "Auditar nota ativa no Obsidian")
            jarvis = JarvisCognitiveAssistant(
                db_path=str(DEFAULT_DB),
                jsonl_path=str(DEFAULT_JSONL),
                rag_db_path=str(DEFAULT_RAG_DB),
                vault_path=DEFAULT_OBSIDIAN_VAULT,
            )
            self._send_json(jarvis.process_command(command))
        elif self.path == "/api/jarvis/config":
            saved = save_local_env(body)
            self._send_json(saved)
        elif self.path == "/api/obsidian/control":
            action = body.get("action", "check_rest_api")
            rel_path = body.get("relative_path", "00_Painel_Central_MOC.md")
            rest = ObsidianLocalRestClient(vault_path=DEFAULT_OBSIDIAN_VAULT)
            if action == "open_graph_view":
                self._send_json(rest.execute_command("graph:open"))
            elif action == "open_file":
                self._send_json(rest.open_file_in_ui(rel_path))
            elif action == "get_active_note":
                self._send_json(rest.get_active_note())
            else:
                self._send_json(rest.check_status())
        else:
            self.send_error(404, "Rota POST nao encontrada")


def main() -> None:
    parser = argparse.ArgumentParser(description="MVP Executável — Cérebro Cognitivo Fractal Multi-Agente")
    parser.add_argument("--prompt", type=str, default=None, help="Executa uma missão diretamente no Córtex via terminal")
    parser.add_argument(
        "--fault",
        type=str,
        default="none",
        choices=["none", "hallucination_v1", "runtime_bug_v2"],
        help="Simula injeção de falha na Iteração 1 para demonstrar o Rollback Causal e auto-correção",
    )
    parser.add_argument("--chaos", action="store_true", help="Reexecuta os 7 cenários da Bateria de Engenharia de Caos")
    parser.add_argument("--sync-obsidian", action="store_true", help="Sincroniza o Vault MY BRAIN do Obsidian com o Cérebro")
    parser.add_argument(
        "--obsidian-vault",
        type=str,
        default=str(DEFAULT_OBSIDIAN_VAULT),
        help="Caminho do Vault do Obsidian (padrão: C:\\Users\\henri.mafra\\Documents\\MY BRAIN)",
    )
    parser.add_argument("--serve", action="store_true", help="Inicia o servidor web J.A.R.V.I.S. + Studio na porta 8765")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host HTTP (use 0.0.0.0 para acesso remoto via Tailscale/LAN)")
    parser.add_argument("--port", type=int, default=8765, help="Porta HTTP para o modo --serve (padrão: 8765)")
    parser.add_argument("--set-gemini-key", type=str, default=None, help="Salva a GEMINI_API_KEY no arquivo .env local")
    args = parser.parse_args()

    if args.set_gemini_key:
        save_local_env({"GEMINI_API_KEY": args.set_gemini_key})
        print(" [OK] GEMINI_API_KEY salva com segurança em .env!")
        return

    if args.sync_obsidian:
        sync_info = sync_obsidian_vault(Path(args.obsidian_vault))
        print("=" * 78)
        print(" SINCRONIZAÇÃO BIDIRECIONAL OBSIDIAN VAULT (MY BRAIN) <-> CÉREBRO COGNITIVO")
        print("=" * 78)
        print(f" [VAULT ROOT]       : {sync_info['vault_root']}")
        print(f" [PAINEL CENTRAL]   : {sync_info['moc_path']}")
        print(f" [CANVAS ARQUITET.] : {sync_info['architecture_canvas_path']}")
        print(f" [AXIOMAS INGERIDOS]: {sync_info['axioms_ingested']} axiomas ativos")
        print(f" [DOCS SEMÂNTICOS]  : {sync_info['documents_ingested']} documentos ({sync_info['total_chunks_indexed']} chunks FTS5 BM25)")
        print(f" [EVENTOS DAG]      : {sync_info['exported_events']} eventos projetados no Graph View")
        print("=" * 78)
        return

    if args.chaos:
        results = run_chaos_benchmark()
        print(f"Bateria de Caos concluída: {results['scenarios_contained']}/{results['total_scenarios']} contidos.")
        return

    if args.prompt:
        run_cli_one_shot(args.prompt, fault_mode=args.fault)
        return

    if args.serve:
        server = HTTPServer((args.host, args.port), MVPStudioHandler)
        url = f"http://127.0.0.1:{args.port}/jarvis"
        print(f"Console de Voz J.A.R.V.I.S. ativo em: {url} (bind={args.host}:{args.port} · Ctrl+C para encerrar)")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        server.serve_forever()
        return

    # Execução padrão demonstrativa se nenhum argumento for passado
    run_cli_one_shot(
        "Projetar, auditar e certificar módulo de verificação criptográfica tolerante a falhas bizantinas",
        fault_mode="none",
    )


if __name__ == "__main__":
    main()
