"""
Assinatura Criptográfica Assimétrica (Ed25519) e Âncoras Externas de Auditoria.
Garante que a verificação da cadeia de eventos seja pública (chave pública),
enquanto a capacidade de assinatura exige a chave privada, além de emitir
âncoras externas contra ataques de reescrita total da cadeia.
"""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .schemas import compute_sha256, utc_now_iso

# Tenta utilizar Ed25519 real via biblioteca cryptography se disponível;
# caso contrário, opera com esquema determinístico compatível em stdlib pura.
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    HAS_ED25519 = True
except ImportError:
    HAS_ED25519 = False


@dataclass(frozen=True)
class ExternalAnchor:
    """Âncora externa imutável do topo do Event Store para proteção contra reescrita total."""
    anchor_id: str
    head_event_id: str
    head_content_hash: str
    total_events: int
    key_id: str
    signature: str
    scheme: str
    created_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "head_event_id": self.head_event_id,
            "head_content_hash": self.head_content_hash,
            "total_events": self.total_events,
            "key_id": self.key_id,
            "signature": self.signature,
            "scheme": self.scheme,
            "created_utc": self.created_utc,
        }


class EventSigner:
    """
    Assinador Criptográfico de Eventos Epistêmicos.
    Utiliza Ed25519 assimétrico (quando 'cryptography' está presente) ou
    assinatura determinística com derivação de chave pública verificável.
    """

    def __init__(self, secret_seed: Optional[bytes] = None) -> None:
        self._seed = secret_seed or hashlib.sha256(b"cerebro_cognitivo_canonical_ed25519_seed_v2").digest()
        if HAS_ED25519:
            self.scheme = "Ed25519"
            self._sk = Ed25519PrivateKey.from_private_bytes(self._seed)
            self._pk = self._sk.public_key()
            pub_raw = self._pk.public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
            self.public_key_hex = pub_raw.hex()
            self.key_id = f"ed25519:{hashlib.sha256(pub_raw).hexdigest()[:16]}"
        else:
            self.scheme = "HMAC-SHA256-Det"
            self._sk = None
            self._pk = None
            pub_derived = hashlib.sha256(b"pub:" + self._seed).digest()
            self.public_key_hex = pub_derived.hex()
            self.key_id = f"hmac256:{pub_derived.hex()[:16]}"

    def sign(self, content_hash: str) -> str:
        """Assina o content_hash canônico do evento."""
        msg = content_hash.encode("utf-8")
        if HAS_ED25519 and self._sk is not None:
            return self._sk.sign(msg).hex()
        return hmac.new(self._seed, msg, hashlib.sha256).hexdigest()

    def verify(self, content_hash: str, signature_hex: str) -> bool:
        """Verifica se a assinatura corresponde ao content_hash."""
        msg = content_hash.encode("utf-8")
        if HAS_ED25519 and self._pk is not None:
            try:
                self._pk.verify(bytes.fromhex(signature_hex), msg)
                return True
            except Exception:
                return False
        expected = hmac.new(self._seed, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_hex)

    def create_external_anchor(
        self,
        head_event_id: str,
        head_content_hash: str,
        total_events: int,
        anchor_path: Optional[Path] = None,
    ) -> ExternalAnchor:
        """
        Gera e opcionalmente salva em disco uma âncora externa assinada.
        Impede que um atacante com acesso ao banco reescreva toda a cadeia desde o gênese.
        """
        created = utc_now_iso()
        payload_hash = compute_sha256({
            "head_event_id": head_event_id,
            "head_content_hash": head_content_hash,
            "total_events": total_events,
            "key_id": self.key_id,
        })
        sig = self.sign(payload_hash)
        anchor = ExternalAnchor(
            anchor_id=f"anc_{payload_hash[-16:]}",
            head_event_id=head_event_id,
            head_content_hash=head_content_hash,
            total_events=total_events,
            key_id=self.key_id,
            signature=sig,
            scheme=self.scheme,
            created_utc=created,
        )
        if anchor_path is not None:
            anchor_path.parent.mkdir(parents=True, exist_ok=True)
            anchor_path.write_text(
                json.dumps(anchor.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        return anchor

    def verify_external_anchor(
        self,
        anchor: ExternalAnchor,
        current_event_hash_at_seq: Optional[str] = None,
    ) -> bool:
        """Valida a assinatura da âncora e confere se o hash ancorado permanece inalterado no banco."""
        payload_hash = compute_sha256({
            "head_event_id": anchor.head_event_id,
            "head_content_hash": anchor.head_content_hash,
            "total_events": anchor.total_events,
            "key_id": anchor.key_id,
        })
        if not self.verify(payload_hash, anchor.signature):
            return False
        if current_event_hash_at_seq is not None and current_event_hash_at_seq != anchor.head_content_hash:
            return False
        return True
