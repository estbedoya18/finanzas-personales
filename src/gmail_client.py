"""Cliente de Gmail.

Usa OAuth con refresh token, que es el patrón apto para correr en GitHub Actions
sin intervención humana. Los secretos GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y
GMAIL_REFRESH_TOKEN deben estar configurados como variables de entorno.
"""

import base64
import logging
import os
from dataclasses import dataclass
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


log = logging.getLogger(__name__)

# Etiqueta que aplicamos a cada correo después de procesarlo, para no procesarlo dos veces.
ETIQUETA_PROCESADO = "Procesado/Finanzas"

# Los filtros de Gmail aplican estas etiquetas hijas. En Gmail, una etiqueta hija
# no implica que el mensaje también tenga aplicada la etiqueta padre.
ETIQUETAS_TRANSACCIONES = (
    "Transacciones/Bancolombia",
    "Transacciones/Lulo",
)


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

        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="ignore"
        )
        return _re.sub(r"<[^>]+>", " ", html)

    return ""


class GmailClient:
    def __init__(self):
        self.service = build("gmail", "v1", credentials=_cargar_credenciales())
        self._etiquetas_cache = None

    def _obtener_etiquetas(self) -> dict:
        if self._etiquetas_cache is None:
            res = self.service.users().labels().list(userId="me").execute()
            self._etiquetas_cache = {
                etiqueta["name"]: etiqueta["id"]
                for etiqueta in res.get("labels", [])
            }
        return self._etiquetas_cache

    def _obtener_o_crear_etiqueta(self, nombre: str) -> str:
        etiquetas = self._obtener_etiquetas()
        if nombre in etiquetas:
            return etiquetas[nombre]

        nueva = self.service.users().labels().create(
            userId="me",
            body={
                "name": nombre,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
        self._etiquetas_cache[nombre] = nueva["id"]
        return nueva["id"]

    def listar_pendientes(self, max_resultados: int = 200) -> Iterator[Correo]:
        """Devuelve correos bancarios etiquetados que aún no han sido procesados.

        Recorre las etiquetas hijas configuradas para cada banco, pagina los
        resultados y deduplica por Gmail message ID.
        """
        if max_resultados <= 0:
            return

        etiqueta_procesado_id = self._obtener_o_crear_etiqueta(ETIQUETA_PROCESADO)
        ids_revisados = set()
        emitidos = 0

        for nombre_etiqueta in ETIQUETAS_TRANSACCIONES:
            etiqueta_id = self._obtener_o_crear_etiqueta(nombre_etiqueta)
            page_token = None
            encontrados = 0

            while True:
                restantes = max_resultados - emitidos
                if restantes <= 0:
                    log.info(
                        "Se alcanzó el límite de %d correos pendientes",
                        max_resultados,
                    )
                    return

                respuesta = self.service.users().messages().list(
                    userId="me",
                    labelIds=[etiqueta_id],
                    maxResults=min(100, restantes),
                    pageToken=page_token,
                ).execute()

                mensajes = respuesta.get("messages", [])
                encontrados += len(mensajes)

                for mensaje_meta in mensajes:
                    mensaje_id = mensaje_meta["id"]
                    if mensaje_id in ids_revisados:
                        continue
                    ids_revisados.add(mensaje_id)

                    mensaje = self.service.users().messages().get(
                        userId="me",
                        id=mensaje_id,
                        format="full",
                    ).execute()

                    if etiqueta_procesado_id in mensaje.get("labelIds", []):
                        continue

                    headers = {
                        header["name"].lower(): header["value"]
                        for header in mensaje["payload"].get("headers", [])
                    }

                    yield Correo(
                        id=mensaje_id,
                        remitente=headers.get("from", ""),
                        asunto=headers.get("subject", ""),
                        cuerpo=_extraer_texto(mensaje["payload"]),
                    )
                    emitidos += 1

                    if emitidos >= max_resultados:
                        log.info(
                            "Se alcanzó el límite de %d correos pendientes",
                            max_resultados,
                        )
                        return

                page_token = respuesta.get("nextPageToken")
                if not page_token:
                    break

            log.info(
                "Etiqueta %s: %d mensajes encontrados",
                nombre_etiqueta,
                encontrados,
            )

        log.info("Total de correos pendientes entregados: %d", emitidos)

    def marcar_procesado(self, id_correo: str) -> None:
        etiqueta_procesado_id = self._obtener_o_crear_etiqueta(ETIQUETA_PROCESADO)
        self.service.users().messages().modify(
            userId="me",
            id=id_correo,
            body={"addLabelIds": [etiqueta_procesado_id]},
        ).execute()
