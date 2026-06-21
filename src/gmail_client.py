"""Cliente de Gmail.

Usa OAuth con refresh token, que es el patrón apto para correr en GitHub Actions
sin intervención humana. Los secretos GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y
GMAIL_REFRESH_TOKEN deben estar configurados como variables de entorno.
"""

import base64
import os
from dataclasses import dataclass
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Etiqueta que aplicamos a cada correo después de procesarlo, para no procesarlo dos veces.
ETIQUETA_PROCESADO = "Procesado/Finanzas"

# Solo procesamos correos con esta etiqueta padre (los filtros de Gmail los etiquetan así).
ETIQUETA_TRANSACCIONES = "Transacciones"


@dataclass
class Correo:
    id: str
    remitente: str
    asunto: str
    cuerpo: str


def _cargar_credenciales() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    creds.refresh(Request())
    return creds


def _extraer_texto(payload: dict) -> str:
    """Recorre las partes del MIME y reconstruye el texto plano del correo."""
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    if "parts" in payload:
        partes = []
        for parte in payload["parts"]:
            txt = _extraer_texto(parte)
            if txt:
                partes.append(txt)
        if partes:
            return "\n".join(partes)

    # Fallback: si no hay text/plain, usamos el HTML pero limpiamos las etiquetas.
    if payload.get("mimeType") == "text/html" and "data" in payload.get("body", {}):
        import re as _re
        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        return _re.sub(r"<[^>]+>", " ", html)

    return ""


class GmailClient:
    def __init__(self):
        self.service = build("gmail", "v1", credentials=_cargar_credenciales())
        self._etiquetas_cache = None

    def _obtener_etiquetas(self) -> dict:
        if self._etiquetas_cache is None:
            res = self.service.users().labels().list(userId="me").execute()
            self._etiquetas_cache = {l["name"]: l["id"] for l in res.get("labels", [])}
        return self._etiquetas_cache

    def _obtener_o_crear_etiqueta(self, nombre: str) -> str:
        etiquetas = self._obtener_etiquetas()
        if nombre in etiquetas:
            return etiquetas[nombre]
        nueva = self.service.users().labels().create(
            userId="me",
            body={"name": nombre, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
        ).execute()
        self._etiquetas_cache[nombre] = nueva["id"]
        return nueva["id"]

    def listar_pendientes(self, max_resultados: int = 50) -> Iterator[Correo]:
        """Devuelve correos con la etiqueta Transacciones que aún no han sido procesados."""
        etiqueta_id = self._obtener_o_crear_etiqueta(ETIQUETA_TRANSACCIONES)
        etiqueta_proc_id = self._obtener_o_crear_etiqueta(ETIQUETA_PROCESADO)

        # Query: tiene la etiqueta de transacciones, NO tiene la de procesado
        query = f"label:{ETIQUETA_TRANSACCIONES} -label:{ETIQUETA_PROCESADO.replace('/', '-')}"

        res = self.service.users().messages().list(
            userId="me", labelIds=[etiqueta_id], maxResults=max_resultados,
        ).execute()

        for msg_meta in res.get("messages", []):
            # Saltamos los que ya tienen la etiqueta de procesado
            if etiqueta_proc_id in (msg_meta.get("labelIds") or []):
                continue

            msg = self.service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full",
            ).execute()

            # Doble chequeo de procesado (la query no siempre filtra perfecto)
            if etiqueta_proc_id in msg.get("labelIds", []):
                continue

            headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
            yield Correo(
                id=msg["id"],
                remitente=headers.get("from", ""),
                asunto=headers.get("subject", ""),
                cuerpo=_extraer_texto(msg["payload"]),
            )

    def marcar_procesado(self, id_correo: str) -> None:
        etiqueta_proc_id = self._obtener_o_crear_etiqueta(ETIQUETA_PROCESADO)
        self.service.users().messages().modify(
            userId="me",
            id=id_correo,
            body={"addLabelIds": [etiqueta_proc_id]},
        ).execute()
