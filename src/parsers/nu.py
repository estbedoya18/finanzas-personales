"""Parser para Nu Colombia.

TODO: Completar cuando tengamos correos de muestra reales.
La estructura es la misma de bancolombia.py / lulo.py:
  1. Identifica el remitente exacto
  2. Define lista blanca de asuntos
  3. Escribe regex para cada tipo de transacción
"""

from typing import Optional
from ..modelo import Transaccion
from .base import ParserBase


class NuParser(ParserBase):
    banco = "Nu"
    remitente = "notificaciones@nu.com.co"  # TODO: confirmar dirección real

    def aplica(self, asunto: str, cuerpo: str, remitente: str) -> bool:
        return self.remitente in remitente.lower()

    def parsear(self, id_correo: str, asunto: str, cuerpo: str) -> Optional[Transaccion]:
        # TODO: implementar
        return None
