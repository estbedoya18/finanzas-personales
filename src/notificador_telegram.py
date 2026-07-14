"""Notificaciones opcionales de transacciones que requieren revisión."""

import json
import os
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

from .modelo import Transaccion


class NotificadorTelegram:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    @property
    def disponible(self) -> bool:
        return bool(self.token and self.chat_id)

    def notificar_pendientes(self, transacciones: Iterable[Transaccion], enlace: str) -> bool:
        pendientes = list(transacciones)
        if not pendientes or not self.disponible:
            return False

        detalle = "\n".join(
            f"${tx.monto:,.0f} — {tx.contraparte} "
            f"(sugiere: {tx.categoria_sugerida or 'sin sugerencia'})"
            for tx in pendientes[:10]
        )
        adicional = "" if len(pendientes) <= 10 else f"\n• y {len(pendientes) - 10} más"
        texto = (
            "Necesito tu confirmación para clasificar estos movimientos:\n"
            f"{detalle}{adicional}\n\n"
            f"Ábrelos aquí y escribe tu categoría elegida: {enlace}"
        )
        return self._enviar(texto)

    def _enviar(self, texto: str) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        datos = json.dumps({"chat_id": self.chat_id, "text": texto}).encode("utf-8")
        solicitud = Request(url, data=datos, headers={"Content-Type": "application/json"})
        try:
            with urlopen(solicitud, timeout=15) as respuesta:
                return 200 <= respuesta.status < 300
        except (URLError, TimeoutError):
            return False
