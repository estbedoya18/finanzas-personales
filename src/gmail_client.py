"""Cliente de Gmail.

Usa OAuth con refresh token, que es el patrón apto para correr en GitHub Actions
sin intervención humana. Los secretos GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y
GMAIL_REFRESH_TOKEN deben estar configurados como variables de entorno.
"""

import base64
import os
import re
from dataclasses import dataclass
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Etiqueta que se aplica después de procesar correctamente un correo.
ETIQUETA_PROCESADO = "Procesado/Finanzas"

# Etiqueta padre de las notificaciones bancarias.
ETIQUETA_TRANSACCIONES = "Transacciones"


@dataclass
class Correo:
    id: str
    remitente: str
    asunto: str
    cuerpo: str


def _cargar_credenciales() -> Credentials:
    """Carga y actualiza las credenciales OAuth de Gmail."""
    credenciales = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )

    credenciales.refresh(Request())
    return credenciales


def _decodificar_base64_url(data: str) -> str:
    """Decodifica contenido Base64 URL-safe usado por la API de Gmail."""
    if not data:
        return ""

    try:
        return base64.urlsafe_b64decode(data).decode(
            "utf-8",
            errors="ignore",
        )
    except (ValueError, TypeError):
        return ""


def _limpiar_html(html: str) -> str:
    """Convierte un HTML básico en texto legible."""
    texto = re.sub(r"<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r"<script.*?</script>", " ", texto, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def _extraer_texto(payload: dict) -> str:
    """Recorre las partes MIME y reconstruye el texto del correo."""
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return _decodificar_base64_url(data)

    partes = payload.get("parts", [])

    if partes:
        textos_planos: list[str] = []
        textos_html: list[str] = []

        for parte in partes:
            texto = _extraer_texto(parte)

            if not texto:
                continue

            if parte.get("mimeType") == "text/html":
                textos_html.append(texto)
            else:
                textos_planos.append(texto)

        if textos_planos:
            return "\n".join(textos_planos)

        if textos_html:
            return "\n".join(textos_html)

    if mime_type == "text/html" and data:
        html = _decodificar_base64_url(data)
        return _limpiar_html(html)

    return ""


class GmailClient:
    def __init__(self) -> None:
        self.service = build(
            "gmail",
            "v1",
            credentials=_cargar_credenciales(),
        )
        self._etiquetas_cache: dict[str, str] | None = None

    def _obtener_etiquetas(self) -> dict[str, str]:
        """Obtiene las etiquetas de Gmail indexadas por nombre."""
        if self._etiquetas_cache is None:
            respuesta = (
                self.service.users()
                .labels()
                .list(userId="me")
                .execute()
            )

            self._etiquetas_cache = {
                etiqueta["name"]: etiqueta["id"]
                for etiqueta in respuesta.get("labels", [])
            }

        return self._etiquetas_cache

    def _obtener_o_crear_etiqueta(self, nombre: str) -> str:
        """Devuelve el ID de una etiqueta y la crea cuando no existe."""
        etiquetas = self._obtener_etiquetas()

        if nombre in etiquetas:
            return etiquetas[nombre]

        nueva_etiqueta = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": nombre,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )

        etiquetas[nombre] = nueva_etiqueta["id"]
        return nueva_etiqueta["id"]

    def _obtener_etiquetas_transacciones(self) -> dict[str, str]:
        """Obtiene la etiqueta padre Transacciones y todas sus subetiquetas."""
        # Garantiza que la etiqueta padre exista.
        self._obtener_o_crear_etiqueta(ETIQUETA_TRANSACCIONES)

        etiquetas = self._obtener_etiquetas()
        prefijo = f"{ETIQUETA_TRANSACCIONES}/"

        return {
            nombre: etiqueta_id
            for nombre, etiqueta_id in etiquetas.items()
            if nombre == ETIQUETA_TRANSACCIONES
            or nombre.startswith(prefijo)
        }

    def _obtener_mensaje_completo(self, id_correo: str) -> dict:
        """Consulta un correo completo por su identificador."""
        return (
            self.service.users()
            .messages()
            . """Consulta un correo completo por su identificador."""
        return (
            self.service.users()
            .messages()
            .get(
                userId="me",
                id=id_correo,
                format="full",
            )
            .execute()
        )

    @staticmethod
    def _extraer_headers(mensaje: dict) -> dict[str, str]:
        """Convierte los encabezados del correo en un diccionario."""
        payload = mensaje.get("payload", {})
        headers = payload.get("headers", [])

        return {
            header.get("name", "").lower(): header.get("value", "")
            for header in headers
            if header.get("name")
        }

    def listar_pendientes(
        self,
        max_resultados: int = 50,
    ) -> Iterator[Correo]:
        """
        Devuelve correos bancarios que todavía no han sido procesados.

        Consulta tanto la etiqueta padre como todas sus subetiquetas:

        - Transacciones
        - Transacciones/Bancolombia
        - Transacciones/Lulo
        - Cualquier subetiqueta bancaria futura

        También evita devolver dos veces un correo que tenga más de una
        etiqueta de transacciones.
        """
        if max_resultados <= 0:
            return

        etiqueta_procesado_id = self._obtener_o_crear_etiqueta(
            ETIQUETA_PROCESADO
        )

        etiquetas_transacciones = self._obtener_etiquetas_transacciones()

        ids_vistos: set[str] = set()
        total_devuelto = 0

        for _, etiqueta_id in etiquetas_transacciones.items():
            page_token: str | None = None

            while total_devuelto < max_resultados:
                parametros = {
                    "userId": "me",
                    "labelIds": [etiqueta_id],
                    "maxResults": min(
                        100,
                        max_resultados - total_devuelto,
                    ),
                }

                if page_token:
                    parametros["pageToken"] = page_token

                respuesta = (
                    self.service.users()
                    .messages()
                    .list(**parametros)
                    .execute()
                )

                for mensaje_resumen in respuesta.get("messages", []):
                    id_correo = mensaje_resumen.get("id")

                    if not id_correo:
                        continue

                    # Evita duplicados cuando un correo tiene la etiqueta
                    # padre y además una subetiqueta bancaria.
                    if id_correo in ids_vistos:
                        continue

                    ids_vistos.add(id_correo)

                    mensaje = self._obtener_mensaje_completo(id_correo)
                    etiquetas_mensaje = mensaje.get("labelIds", [])

                    # Ignora correos que ya fueron procesados.
                    if etiqueta_procesado_id in etiquetas_mensaje:
                        continue

                    headers = self._extraer_headers(mensaje)
                    payload = mensaje.get("payload", {})

                    yield Correo(
                        id=id_correo,
                        remitente=headers.get("from", ""),
                        asunto=headers.get("subject", ""),
                        cuerpo=_extraer_texto(payload),
                    )

                    total_devuelto += 1

                    if total_devuelto >= max_resultados:
                        return

                page_token = respuesta.get("nextPageToken")

                if not page_token:
                    break

    def marcar_procesado(self, id_correo: str) -> None:
        """Marca un correo para evitar volver a procesarlo."""
        etiqueta_procesado_id = self._obtener_o_crear_etiqueta(
            ETIQUETA_PROCESADO
        )

        (
            self.service.users()
            .messages()
            .modify(
                userId="me",
                id=id_correo,
                body={
                    "addLabelIds": [etiqueta_procesado_id],
                },
            )
            .execute()
        )
