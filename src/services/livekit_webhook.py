import base64
import hashlib
import hmac
import json
import time
from typing import NamedTuple


class WebhookError(Exception):
    pass


class LiveStart(NamedTuple):
    user_id: str
    name: str
    avatar_url: str | None = None


DISCORD_CDN = "https://cdn.discordapp.com/"


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def verify_webhook(
    body: bytes,
    authorization: str | None,
    *,
    api_key: str,
    api_secret: str,
    now: float | None = None,
    leeway: float = 10,
) -> dict:
    """Valida a assinatura de um webhook do LiveKit e devolve o evento.

    O LiveKit envia no Authorization um JWT HS256 emitido pela chave configurada
    em `webhook.api_key`, com o SHA-256 do corpo na claim `sha256`. Implementado
    com a biblioteca padrão para não trazer o SDK do LiveKit só para isso.
    """
    if not authorization:
        raise WebhookError("cabeçalho Authorization ausente")
    token = authorization.strip()
    if token[:7].lower() == "bearer ":
        token = token[7:].strip()
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        claims = json.loads(_b64url_decode(payload_b64))
        signature = _b64url_decode(signature_b64)
    except ValueError as error:
        raise WebhookError("token malformado") from error
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise WebhookError("algoritmo não suportado")
    expected = hmac.new(
        api_secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise WebhookError("assinatura inválida")
    if not isinstance(claims, dict) or claims.get("iss") != api_key:
        raise WebhookError("emissor inválido")

    now = time.time() if now is None else now
    expires = claims.get("exp")
    if not isinstance(expires, (int, float)) or now > expires + leeway:
        raise WebhookError("token expirado")
    not_before = claims.get("nbf")
    if isinstance(not_before, (int, float)) and now + leeway < not_before:
        raise WebhookError("token ainda não é válido")

    digest = base64.b64encode(hashlib.sha256(body).digest())
    checksum = claims.get("sha256")
    if not isinstance(checksum, str) or not hmac.compare_digest(checksum.encode(), digest):
        raise WebhookError("checksum do corpo não confere")

    try:
        event = json.loads(body)
    except ValueError as error:
        raise WebhookError("corpo não é JSON") from error
    if not isinstance(event, dict):
        raise WebhookError("corpo não é um objeto")
    return event


def screen_share_started(event: dict) -> LiveStart | None:
    """Reconhece o início de um compartilhamento de tela no fckjj.

    O token-server usa `<discordId>#<sufixo>` como identity; o sufixo muda a
    cada aba, então só o discordId identifica a pessoa.
    """
    if event.get("event") != "track_published":
        return None
    track = event.get("track")
    participant = event.get("participant")
    if not isinstance(track, dict) or not isinstance(participant, dict):
        return None
    # protojson serializa enums pelo nome; o número cobre um emissor que não o faça.
    if track.get("source") not in ("SCREEN_SHARE", 3):
        return None
    identity = participant.get("identity")
    if not isinstance(identity, str) or not identity:
        return None
    name = participant.get("name")
    if not isinstance(name, str) or not name.strip():
        name = "Alguém"
    return LiveStart(
        user_id=identity.split("#", 1)[0],
        name=name.strip(),
        avatar_url=_avatar_url(participant),
    )


def _avatar_url(participant: dict) -> str | None:
    # O token-server grava {"avatarUrl": ...} em metadata. Só a CDN do Discord
    # é aceita: o valor vira imagem no embed e não deve apontar para outro lugar.
    try:
        metadata = json.loads(participant.get("metadata") or "{}")
    except (TypeError, ValueError):
        return None
    url = metadata.get("avatarUrl") if isinstance(metadata, dict) else None
    return url if isinstance(url, str) and url.startswith(DISCORD_CDN) else None
