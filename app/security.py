"""Sécurité de l'API : authentification Bearer et barrière d'upload.

Deux niveaux :
1. `UploadGuardMiddleware` (ASGI) : vérifie le token et la taille annoncée AVANT
   que le corps de la requête soit lu. Une requête sans token ou trop lourde ne
   coûte donc ni lecture réseau complète, ni mémoire, ni inférence.
2. `require_token` (dépendance FastAPI) : seconde vérification au niveau de la
   route, qui sert aussi à afficher le bouton « Authorize » dans Swagger.

RGPD : aucune image n'est écrite sur disque. Starlette bascule normalement les
uploads de plus de 1 Mo dans un fichier temporaire ; on relève ce seuil au-dessus
de la taille maximale acceptée, et le middleware refuse tout ce qui le dépasse.
"""

from __future__ import annotations

import json
import logging
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.formparsers import MultiPartParser
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Marge pour l'enveloppe multipart (boundaries, en-têtes de la partie)
MULTIPART_OVERHEAD = 64 * 1024
PROTECTED_PATHS = ("/predict",)


def keep_uploads_in_memory(settings: Settings) -> None:
    """Empêche Starlette d'écrire les uploads sur disque (spool en RAM jusqu'à la limite)."""
    MultiPartParser.spool_max_size = settings.max_upload_bytes + MULTIPART_OVERHEAD + 1024 * 1024


def is_valid_token(token: str | None, settings: Settings) -> bool:
    if not token or not settings.api_tokens:
        return False  # aucune configuration => on refuse tout (fail closed)
    # compare_digest : comparaison à temps constant (pas de timing attack)
    return any(secrets.compare_digest(token.encode(), t.encode()) for t in settings.api_tokens)


def extract_bearer(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, credentials = header_value.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


bearer_scheme = HTTPBearer(auto_error=False, description="Token d'API (variable d'environnement API_TOKEN)")


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    token = credentials.credentials if credentials else None
    if not is_valid_token(token, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification manquant ou invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class UploadGuardMiddleware:
    """Rejette au plus tôt : 401 (token) puis 411/413 (taille), sans lire le corps."""

    def __init__(self, app: ASGIApp, settings: Settings | None = None):
        self.app = app
        self.settings = settings or get_settings()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] not in PROTECTED_PATHS or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}

        if not is_valid_token(extract_bearer(headers.get("authorization")), self.settings):
            client = scope.get("client") or ("?", 0)
            logger.warning("auth_refusee path=%s client=%s", scope["path"], client[0])
            await self._reject(send, 401, "Token d'authentification manquant ou invalide.",
                               extra_headers=[(b"www-authenticate", b"Bearer")])
            return

        length = headers.get("content-length")
        if length is None:
            await self._reject(send, 411, "En-tête Content-Length requis.")
            return
        try:
            declared = int(length)
        except ValueError:
            await self._reject(send, 400, "Content-Length invalide.")
            return
        if declared > self.settings.max_upload_bytes + MULTIPART_OVERHEAD:
            await self._reject(
                send, 413,
                f"Fichier trop volumineux. Maximum : {self.settings.max_upload_bytes / 1_048_576:.0f} Mo.",
            )
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send: Send, status_code: int, detail: str, extra_headers: list | None = None) -> None:
        body = json.dumps({"detail": detail}, ensure_ascii=False).encode()
        headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
        headers += extra_headers or []
        # "connection: close" : on ne lit pas le corps restant, on ferme la connexion proprement
        headers.append((b"connection", b"close"))
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        await send({"type": "http.response.body", "body": body})
