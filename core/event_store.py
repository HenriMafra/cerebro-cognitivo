"""
Event Store Epistêmico e Persistência Criptográfica Imutável.
Módulo canônico do Cérebro Cognitivo Fractal Multi-Agente.
Garante imutabilidade (triggers SQLite), encadeamento criptográfico Merkle-DAG,
time-travel debugging, rollback causal e auditoria forense anti-adulteração.
"""

from __future__ import annotations
import copy
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from .schemas import (
    EpistemicEvent,
    compute_sha256,
    new_id,
    utc_now_iso,
    VerdictStatus,
)


def _deep_merge(target: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica mesclagem profunda e determinística de 'patch' sobre 'target'.
    Preserva chaves não modificadas e propaga dicionários aninhados.
    """
    for key, value in patch.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


class EpistemicEventStore:
    """
    Repositório append-only de eventos epistêmicos com persistência SQLite (WAL) e JSONL.
    Implementa garantias matemáticas de integridade forense, encadeamento em hash chain,
    árvore de causalidade Merkle-DAG e time-travel rollback com bifurcação de branches.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        jsonl_path: Optional[str] = None,
    ) -> None:
        """
        Inicializa o repositório de eventos epistêmicos.

        Args:
            db_path: Caminho para o arquivo SQLite ou ':memory:' para volátil.
            jsonl_path: Caminho opcional para persistência de backup/streaming em JSON Lines.
        """
        self.db_path = db_path
        self.jsonl_path = jsonl_path
        self._lock = threading.RLock()

        if self.db_path != ":memory:":
            abs_db_path = os.path.abspath(self.db_path)
            os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)

        if self.jsonl_path:
            abs_jsonl_path = os.path.abspath(self.jsonl_path)
            os.makedirs(os.path.dirname(abs_jsonl_path), exist_ok=True)

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row

        self._configure_pragmas()
        self._create_tables_and_indices()
        self._create_triggers()

    def _configure_pragmas(self) -> None:
        """Configura os PRAGMAs de alta concorrência e integridade do SQLite."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA foreign_keys=ON;")

    def _create_tables_and_indices(self) -> None:
        """Cria as tabelas relacionais e índices epistêmicos."""
        with self._lock:
            cur = self._conn.cursor()
            # Tabela canônica de eventos epistêmicos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS epistemic_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    parent_event_id TEXT,
                    branch_id TEXT NOT NULL,
                    neuron_id TEXT NOT NULL,
                    subagent_role TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    cycle_iteration INTEGER NOT NULL,
                    epistemic_state_json TEXT NOT NULL,
                    delta_changes_json TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                );
            """)

            # Índices de performance para busca em DAG e consultas causais
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_parent ON epistemic_events(parent_event_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_branch ON epistemic_events(branch_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_neuron ON epistemic_events(neuron_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON epistemic_events(timestamp_utc);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_content_hash ON epistemic_events(content_hash);")

            # Tabela de controle de ponteiros head por branch
            cur.execute("""
                CREATE TABLE IF NOT EXISTS branch_heads (
                    branch_id TEXT PRIMARY KEY,
                    head_event_id TEXT NOT NULL,
                    head_hash TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );
            """)
            self._conn.commit()

    def _create_triggers(self) -> None:
        """
        Cria triggers rigorosos no SQLite para impor imutabilidade absoluta (Append-Only).
        Qualquer instrução UPDATE ou DELETE é imediatamente rejeitada e abortada.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_event_update
                BEFORE UPDATE ON epistemic_events
                BEGIN
                    SELECT RAISE(ABORT, 'Epistemic Immutability Violation: Events are append-only and cannot be modified or deleted.');
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_event_delete
                BEFORE DELETE ON epistemic_events
                BEGIN
                    SELECT RAISE(ABORT, 'Epistemic Immutability Violation: Events are append-only and cannot be modified or deleted.');
                END;
            """)
            self._conn.commit()

    def record_event(
        self,
        neuron_id: Any,
        subagent_role: Optional[str] = None,
        event_type: Optional[str] = None,
        epistemic_state: Optional[Dict[str, Any]] = None,
        delta_changes: Optional[Dict[str, Any]] = None,
        verdict: Optional[str] = None,
        confidence_score: Optional[float] = None,
        cycle_iteration: int = 1,
        parent_event_id: Optional[str] = None,
        branch_id: str = "main",
        timestamp_utc: Optional[str] = None,
    ) -> EpistemicEvent:
        """
        Registra atomicamente um novo evento epistêmico, encadeando criptograficamente
        o hash do último evento global inserido e atualizando a cabeça (head) da branch.
        Aceita tanto uma instância de EpistemicEvent como primeiro argumento quanto parâmetros individuais.
        """
        if isinstance(neuron_id, EpistemicEvent):
            _ev = neuron_id
            neuron_id = _ev.neuron_id
            subagent_role = _ev.subagent_role
            event_type = _ev.event_type
            epistemic_state = _ev.epistemic_state
            delta_changes = _ev.delta_changes
            verdict = _ev.verdict
            confidence_score = _ev.confidence_score
            cycle_iteration = _ev.cycle_iteration
            if _ev.parent_event_id is not None:
                parent_event_id = _ev.parent_event_id
            branch_id = _ev.branch_id
            timestamp_utc = _ev.timestamp_utc

        if subagent_role is None or event_type is None:
            raise ValueError("subagent_role e event_type são obrigatórios.")
        if confidence_score is None:
            confidence_score = 1.0
        with self._lock:
            cur = self._conn.cursor()

            # 1. Encadeamento Criptográfico: busca o content_hash do último evento inserido
            cur.execute("SELECT content_hash FROM epistemic_events ORDER BY seq DESC LIMIT 1;")
            last_row = cur.fetchone()
            if last_row:
                previous_event_hash = last_row["content_hash"]
            else:
                previous_event_hash = "GENESIS_BLOCK"

            # 2. Resolução do parent_event_id na branch
            if parent_event_id is None:
                branch_head_id = self.get_branch_head_id(branch_id)
                if branch_head_id:
                    parent_event_id = branch_head_id
                elif branch_id != "main":
                    # Se for uma nova branch sem head, herda o head da 'main' se existir
                    parent_event_id = self.get_branch_head_id("main")
                else:
                    parent_event_id = None

            # Normalização de tipos e serializações
            safe_state = epistemic_state if isinstance(epistemic_state, dict) else {}
            safe_delta = delta_changes if isinstance(delta_changes, dict) else {}
            safe_verdict = verdict.value if isinstance(verdict, VerdictStatus) else str(verdict)
            safe_timestamp = timestamp_utc or utc_now_iso()

            # 3. Instanciação do EpistemicEvent (gera event_id e content_hash canônico)
            event = EpistemicEvent(
                neuron_id=neuron_id,
                subagent_role=subagent_role,
                event_type=event_type,
                epistemic_state=safe_state,
                delta_changes=safe_delta,
                verdict=safe_verdict,
                confidence_score=float(confidence_score),
                cycle_iteration=int(cycle_iteration),
                parent_event_id=parent_event_id,
                branch_id=branch_id,
                previous_event_hash=previous_event_hash,
                timestamp_utc=safe_timestamp,
            )

            # 4. Persistência relacional no SQLite
            state_json = json.dumps(safe_state, sort_keys=True, ensure_ascii=False, default=str)
            delta_json = json.dumps(safe_delta, sort_keys=True, ensure_ascii=False, default=str)

            cur.execute("""
                INSERT INTO epistemic_events (
                    event_id, parent_event_id, branch_id, neuron_id, subagent_role,
                    event_type, cycle_iteration, epistemic_state_json, delta_changes_json,
                    verdict, confidence_score, previous_event_hash, timestamp_utc, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                event.event_id,
                event.parent_event_id,
                event.branch_id,
                event.neuron_id,
                event.subagent_role,
                event.event_type,
                event.cycle_iteration,
                state_json,
                delta_json,
                event.verdict,
                event.confidence_score,
                event.previous_event_hash,
                event.timestamp_utc,
                event.content_hash,
            ))

            # 5. Atualização da tabela de ponteiros de branch
            cur.execute("""
                INSERT INTO branch_heads (branch_id, head_event_id, head_hash, updated_at_utc)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(branch_id) DO UPDATE SET
                    head_event_id = excluded.head_event_id,
                    head_hash = excluded.head_hash,
                    updated_at_utc = excluded.updated_at_utc;
            """, (
                event.branch_id,
                event.event_id,
                event.content_hash,
                event.timestamp_utc,
            ))

            self._conn.commit()

            # 6. Gravação opcional no arquivo JSON Lines (streaming append)
            if self.jsonl_path:
                self._append_to_jsonl(event)

            return event

    def append_event(self, event: EpistemicEvent) -> EpistemicEvent:
        """Alias canônico para record_event recebendo uma instância de EpistemicEvent."""
        return self.record_event(event)

    def _append_to_jsonl(self, event: EpistemicEvent) -> None:
        """Escreve o evento em formato JSONL com flush imediato no disco."""
        try:
            line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
        except Exception as ex:
            # Falha de log secundário não deve abortar transação SQLite principal
            pass

    def _row_to_event(self, row: sqlite3.Row) -> EpistemicEvent:
        """Converte uma linha SQLite no objeto canônico EpistemicEvent."""
        return EpistemicEvent(
            event_id=row["event_id"],
            parent_event_id=row["parent_event_id"],
            branch_id=row["branch_id"],
            neuron_id=row["neuron_id"],
            subagent_role=row["subagent_role"],
            event_type=row["event_type"],
            cycle_iteration=int(row["cycle_iteration"]),
            epistemic_state=json.loads(row["epistemic_state_json"]),
            delta_changes=json.loads(row["delta_changes_json"]),
            verdict=row["verdict"],
            confidence_score=float(row["confidence_score"]),
            previous_event_hash=row["previous_event_hash"],
            timestamp_utc=row["timestamp_utc"],
            content_hash=row["content_hash"],
        )

    def get_event(self, event_id: str) -> Optional[EpistemicEvent]:
        """Recupera um evento epistêmico por seu identificador único."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM epistemic_events WHERE event_id = ?;", (event_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_event(row)

    def get_branch_head_id(self, branch_id: str) -> Optional[str]:
        """Retorna o event_id da cabeça da branch informada, ou None se não existir."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT head_event_id FROM branch_heads WHERE branch_id = ?;", (branch_id,))
            row = cur.fetchone()
            if row:
                return row["head_event_id"]
            # Fallback: consultar diretamente a tabela de eventos
            cur.execute("SELECT event_id FROM epistemic_events WHERE branch_id = ? ORDER BY seq DESC LIMIT 1;", (branch_id,))
            fallback_row = cur.fetchone()
            return fallback_row["event_id"] if fallback_row else None

    def get_branch_head(self, branch_id: str) -> Optional[EpistemicEvent]:
        """Retorna a instância EpistemicEvent na cabeça da branch informada."""
        head_id = self.get_branch_head_id(branch_id)
        if head_id:
            return self.get_event(head_id)
        return None

    def get_all_branch_heads(self) -> Dict[str, str]:
        """Retorna mapeamento de todas as branches ativas para seus respectivos head_event_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT branch_id, head_event_id FROM branch_heads;")
            rows = cur.fetchall()
            return {row["branch_id"]: row["head_event_id"] for row in rows}

    def get_all_events(self) -> List[EpistemicEvent]:
        """Retorna todos os eventos em ordem cronológica estrita de inserção."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM epistemic_events ORDER BY seq ASC;")
            rows = cur.fetchall()
            return [self._row_to_event(r) for r in rows]

    def get_events_by_branch(self, branch_id: str) -> List[EpistemicEvent]:
        """Retorna todos os eventos pertencentes a uma branch em ordem cronológica de inserção."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM epistemic_events WHERE branch_id = ? ORDER BY seq ASC;", (branch_id,))
            rows = cur.fetchall()
            return [self._row_to_event(r) for r in rows]

    def get_events_by_neuron(self, neuron_id: str) -> List[EpistemicEvent]:
        """Retorna todos os eventos emitidos por determinado neurônio."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM epistemic_events WHERE neuron_id = ? ORDER BY seq ASC;", (neuron_id,))
            rows = cur.fetchall()
            return [self._row_to_event(r) for r in rows]

    def count_events(self) -> int:
        """Retorna a quantidade total de eventos registrados."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM epistemic_events;")
            row = cur.fetchone()
            return int(row["total"]) if row else 0

    # -------------------------------------------------------------------------
    # Auditoria Forense Anti-Adulteração
    # -------------------------------------------------------------------------

    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        """
        Auditoria criptográfica exaustiva de toda a cadeia de eventos.
        Verifica sequencialmente:
        1. Encadeamento correto de hashes (previous_event_hash == content_hash anterior).
        2. Bloco gênese ancorado em 'GENESIS_BLOCK'.
        3. Autenticidade do payload de cada evento (content_hash == hash canônico recalculado).

        Returns:
            Tupla (is_valid: bool, violations: List[str]).
        """
        violations: List[str] = []
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM epistemic_events ORDER BY seq ASC;")
            rows = cur.fetchall()

            if not rows:
                return (True, [])

            expected_previous_hash = "GENESIS_BLOCK"

            for idx, row in enumerate(rows):
                evt = self._row_to_event(row)
                seq = row["seq"]

                # Verificação 1: Encadeamento de Hash Linear
                if evt.previous_event_hash != expected_previous_hash:
                    violations.append(
                        f"Quebra de encadeamento no evento '{evt.event_id}' (seq {seq}): "
                        f"previous_event_hash='{evt.previous_event_hash}' difere do esperado='{expected_previous_hash}'."
                    )

                # Verificação 2: Imutabilidade do Conteúdo
                if not evt.verify_integrity():
                    recomputed = evt.compute_canonical_hash()
                    violations.append(
                        f"Adulteração de dados detectada no evento '{evt.event_id}' (seq {seq}): "
                        f"content_hash registrado='{evt.content_hash}', mas hash canônico recalculado='{recomputed}'."
                    )

                # Avança o ponteiro de verificação
                expected_previous_hash = evt.content_hash

        is_valid = len(violations) == 0
        return (is_valid, violations)

    def _unsafe_tamper_for_chaos_test(self, event_id: str, corrupted_state_json: str) -> None:
        """
        MÉTODO DE TESTE DESTRUTIVO PARA ENGENHARIA DE CAOS (Red Team & Auditoria).
        Desabilita temporariamente o trigger de imutabilidade, corrompe o estado epistêmico
        gravado na linha do evento e restaura os triggers, permitindo validar empiricamente
        que verify_chain_integrity() detecta fraudes e adulterações.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DROP TRIGGER IF EXISTS prevent_event_update;")
            cur.execute(
                "UPDATE epistemic_events SET epistemic_state_json = ? WHERE event_id = ?;",
                (corrupted_state_json, event_id),
            )
            self._conn.commit()
            self._create_triggers()

    # -------------------------------------------------------------------------
    # Time-Travel Debugging e Rollback Causal
    # -------------------------------------------------------------------------

    def get_causal_lineage(self, event_id: str) -> List[EpistemicEvent]:
        """
        Recupera a linhagem causal completa no Merkle-DAG desde a raiz gênese até 'event_id'.
        Percorre os ponteiros parent_event_id da folha à raiz e inverte a ordem para
        retornar cronologicamente: [raiz, ..., event_id].
        """
        lineage: List[EpistemicEvent] = []
        curr_id: Optional[str] = event_id
        visited: Set[str] = set()

        while curr_id:
            if curr_id in visited:
                # Previne loops anômalos em grafos corrompidos
                break
            visited.add(curr_id)

            evt = self.get_event(curr_id)
            if not evt:
                break
            lineage.append(evt)
            curr_id = evt.parent_event_id

        lineage.reverse()
        return lineage

    def checkout_state(self, event_id: str) -> Dict[str, Any]:
        """
        Reconstrói o estado determinístico exato do cérebro naquele instante temporal.
        Executa um fold/reduce sequencial sobre a linhagem causal desde a raiz até 'event_id',
        aplicando sucessivamente os 'delta_changes' e mesclando 'state_mutations'.
        """
        lineage = self.get_causal_lineage(event_id)
        if not lineage:
            return {}

        accumulated_state: Dict[str, Any] = {}

        for evt in lineage:
            # 1. Se o evento carrega um baseline ou snapshot de epistemic_state
            if evt.epistemic_state and isinstance(evt.epistemic_state, dict):
                _deep_merge(accumulated_state, copy.deepcopy(evt.epistemic_state))

            # 2. Aplica os delta_changes
            if evt.delta_changes and isinstance(evt.delta_changes, dict):
                _deep_merge(accumulated_state, copy.deepcopy(evt.delta_changes))

                # 3. Mescla mutações explícitas de estado (state_mutations) no nível raiz
                mutations = evt.delta_changes.get("state_mutations")
                if isinstance(mutations, dict):
                    _deep_merge(accumulated_state, copy.deepcopy(mutations))

        return accumulated_state

    def branch_from(
        self,
        target_event_id: str,
        new_branch_id: str,
        reason: str,
        neuron_id: str = "system_arbiter",
    ) -> EpistemicEvent:
        """
        Executa um Rollback Causal e bifurcação de branch no Merkle-DAG.
        Ancora uma nova branch em 'target_event_id', restaura o estado verificado via checkout_state,
        e registra um evento especial de tipo 'CAUSAL_ROLLBACK'.

        Args:
            target_event_id: Evento de ancoragem onde a nova branch nasce.
            new_branch_id: Nome da nova branch.
            reason: Motivação formal do rollback (ex: 'Rejeição lógica V2 no ciclo 3').
            neuron_id: Identificador do agente árbitro (padrão: 'system_arbiter').

        Returns:
            O EpistemicEvent gerado que agora é a cabeça (head) da nova branch.
        """
        target_event = self.get_event(target_event_id)
        if not target_event:
            raise ValueError(f"Evento alvo '{target_event_id}' não existe para realização do rollback causal.")

        restored_state = self.checkout_state(target_event_id)

        rollback_event = self.record_event(
            neuron_id=neuron_id,
            subagent_role="causal_rollback_arbiter",
            event_type="CAUSAL_ROLLBACK",
            epistemic_state=restored_state,
            delta_changes={
                "rollback_target_event_id": target_event_id,
                "target_branch_id": target_event.branch_id,
                "reason": reason,
                "restored_at_utc": utc_now_iso(),
            },
            verdict=VerdictStatus.APPROVED.value,
            confidence_score=1.0,
            cycle_iteration=target_event.cycle_iteration,
            parent_event_id=target_event_id,
            branch_id=new_branch_id,
        )

        return rollback_event

    def export_dag_summary(self) -> Dict[str, Any]:
        """
        Gera métricas completas e a topologia de nós e arestas do DAG causal.

        Returns:
            Dicionário estruturado com total de eventos, branches ativas, total de rollbacks,
            status de integridade criptográfica, lista de vértices (nós) e arestas do DAG.
        """
        all_events = self.get_all_events()
        branch_heads = self.get_all_branch_heads()
        is_valid, violations = self.verify_chain_integrity()
        rollbacks = [e for e in all_events if e.event_type == "CAUSAL_ROLLBACK"]

        nodes = [
            {
                "event_id": e.event_id,
                "parent_event_id": e.parent_event_id,
                "branch_id": e.branch_id,
                "neuron_id": e.neuron_id,
                "subagent_role": e.subagent_role,
                "event_type": e.event_type,
                "verdict": e.verdict,
                "confidence_score": e.confidence_score,
                "cycle_iteration": e.cycle_iteration,
                "content_hash": e.content_hash,
                "previous_event_hash": e.previous_event_hash,
                "timestamp_utc": e.timestamp_utc,
            }
            for e in all_events
        ]

        edges = [
            {
                "source": e.parent_event_id,
                "target": e.event_id,
                "branch_id": e.branch_id,
            }
            for e in all_events
            if e.parent_event_id is not None
        ]

        return {
            "total_events": len(all_events),
            "active_branches": branch_heads,
            "total_branches": len(branch_heads),
            "total_rollbacks": len(rollbacks),
            "chain_integrity_valid": is_valid,
            "integrity_violations": violations,
            "dag_nodes": nodes,
            "dag_edges": edges,
        }

    def close(self) -> None:
        """Fecha a conexão com o banco SQLite com segurança."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    def __enter__(self) -> EpistemicEventStore:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
