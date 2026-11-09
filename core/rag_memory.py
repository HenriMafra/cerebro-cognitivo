"""
Memória CoALA (Semântica Versionada com FTS5 BM25, Episódica Não-Citável e Axiomas)
e Conferência Literal de Citações para a Camada V2 de Grounding.
"""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import re
import sqlite3
import threading
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from .schemas import utc_now_iso


def normalize_for_literal_match(text: str) -> str:
    """Normaliza espaços e pontuação leve para conferência literal estrita de citações."""
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed.casefold()


def strip_diacritics(text: str) -> str:
    """Remove acentos para indexação e busca resiliente em português."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    text: str
    sha256: str
    active: bool = True


class CoALAMemoryStore:
    """
    Arquitetura de Memória Tripartite CoALA (Sumers et al., TMLR 2024):
    1. Memória Semântica Versionada (SQLite FTS5 BM25):
       - Reingerir um documento alterado desativa a versão antiga da busca (active=0),
         mas preserva seus chunks para que citações históricas continuem verificáveis!
    2. Memória Episódica (Histórico de Execuções):
       - Recuperável como contexto, mas PROIBIDA de ser citada como ProvenancePointer
         factual (impede auto-citação circular de alucinações passadas).
    3. Memória de Axiomas do Usuário:
       - Premissas declaradas explicitamente pelo usuário, válidas como AXIOM_USER.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kb_documents (
                    doc_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    added_utc TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS kb_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    ord INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    sha256 TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(
                    text, chunk_id UNINDEXED
                );
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    episode_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    request_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_axioms (
                    axiom_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    added_utc TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    def ingest_document(
        self,
        source: str,
        text: str,
        title: Optional[str] = None,
        chunk_size: int = 800,
    ) -> Tuple[str, List[str]]:
        """
        Ingere um documento na memória semântica versionada.
        Se já houver versão anterior do mesmo 'source', marca active=0 sem apagar os chunks antigos.
        """
        content_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        doc_id = f"doc_{hashlib.sha256(f'{source}:{content_sha}'.encode('utf-8')).hexdigest()[:16]}"
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]

        chunks: List[str] = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= chunk_size:
                current = f"{current}\n\n{p}".strip() if current else p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)

        chunk_ids: List[str] = []
        with self._lock:
            cur = self._conn.cursor()
            # Desativa versões anteriores do mesmo source sem deletar seus chunks históricos
            cur.execute(
                "UPDATE kb_documents SET active = 0 WHERE source = ? AND doc_id != ?;",
                (source, doc_id),
            )
            cur.execute(
                "INSERT OR REPLACE INTO kb_documents(doc_id, source, title, sha256, added_utc, active) VALUES (?,?,?,?,?,1);",
                (doc_id, source, title or source, content_sha, utc_now_iso()),
            )
            for idx, c_text in enumerate(chunks):
                c_sha = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
                c_id = f"chk_{hashlib.sha256(f'{doc_id}:{idx}:{c_sha}'.encode('utf-8')).hexdigest()[:16]}"
                chunk_ids.append(c_id)
                cur.execute(
                    "INSERT OR REPLACE INTO kb_chunks(chunk_id, doc_id, ord, text, normalized_text, sha256) VALUES (?,?,?,?,?,?);",
                    (c_id, doc_id, idx, c_text, strip_diacritics(c_text.lower()), c_sha),
                )
                cur.execute(
                    "INSERT INTO kb_chunks_fts(text, chunk_id) VALUES (?, ?);",
                    (strip_diacritics(c_text.lower()), c_id),
                )
            self._conn.commit()
        return doc_id, chunk_ids

    def search_semantic(self, query: str, top_k: int = 5) -> List[KnowledgeChunk]:
        """Busca lexical BM25 via FTS5 (apenas em documentos ativos)."""
        tokens = [
            strip_diacritics(t.lower())
            for t in re.findall(r"\w+", query)
            if len(t) >= 2
        ]
        if not tokens:
            return []
        fts_query = " OR ".join(f'"{t}"' for t in dict.fromkeys(tokens))
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT c.chunk_id, c.doc_id, d.source, d.title, c.text, c.sha256, d.active
                FROM kb_chunks_fts f
                JOIN kb_chunks c ON c.chunk_id = f.chunk_id
                JOIN kb_documents d ON d.doc_id = c.doc_id
                WHERE kb_chunks_fts MATCH ? AND d.active = 1
                ORDER BY bm25(kb_chunks_fts)
                LIMIT ?;
                """,
                (fts_query, top_k),
            ).fetchall()
            return [
                KnowledgeChunk(
                    chunk_id=r["chunk_id"],
                    doc_id=r["doc_id"],
                    source=r["source"],
                    title=r["title"],
                    text=r["text"],
                    sha256=r["sha256"],
                    active=bool(r["active"]),
                )
                for r in rows
            ]

    def get_chunk(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        """Recupera qualquer chunk pelo ID (inclusive de versões históricas inativas para auditoria)."""
        with self._lock:
            r = self._conn.execute(
                """
                SELECT c.chunk_id, c.doc_id, d.source, d.title, c.text, c.sha256, d.active
                FROM kb_chunks c
                JOIN kb_documents d ON d.doc_id = c.doc_id
                WHERE c.chunk_id = ?;
                """,
                (chunk_id,),
            ).fetchone()
            if not r:
                return None
            return KnowledgeChunk(
                chunk_id=r["chunk_id"],
                doc_id=r["doc_id"],
                source=r["source"],
                title=r["title"],
                text=r["text"],
                sha256=r["sha256"],
                active=bool(r["active"]),
            )

    def verify_literal_quote(self, reference_id: str, quoted_excerpt: str) -> Tuple[bool, str]:
        """
        Verifica se 'quoted_excerpt' consta LITERALMENTE dentro do chunk 'reference_id',
        e bloqueia qualquer tentativa de citar memória episódica ('ep_...') como prova factual.
        """
        if reference_id.startswith("ep_"):
            return (
                False,
                f"Violação CoALA: Memória episódica ('{reference_id}') NÃO pode ser citada como fonte factual.",
            )
        chunk = self.get_chunk(reference_id)
        if chunk is None:
            return (False, f"Chunk semântico '{reference_id}' não existe na base de conhecimento.")
        norm_quote = normalize_for_literal_match(quoted_excerpt)
        norm_source = normalize_for_literal_match(chunk.text)
        if len(norm_quote) < 10:
            return (False, f"Citação muito curta ({len(norm_quote)} chars); mínimo de 10 caracteres exigido.")
        if norm_quote not in norm_source:
            return (
                False,
                f"Citação não literal: o trecho '{quoted_excerpt[:50]}...' não aparece literalmente em '{reference_id}'.",
            )
        return (True, f"Citação literal confirmada em '{reference_id}' (doc={chunk.doc_id}).")

    def record_episode(self, episode_id: str, request_text: str, response_text: str, status: str) -> None:
        """Grava uma memória episódica (apenas contexto de conversa, nunca fonte citável)."""
        if not episode_id.startswith("ep_"):
            episode_id = f"ep_{episode_id}"
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO episodic_memories VALUES (?,?,?,?,?);",
                (episode_id, utc_now_iso(), request_text, response_text, status),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
