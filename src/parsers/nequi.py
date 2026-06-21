"""Parser para Nequi.

NOTA: Nequi no envía notificaciones por correo de fábrica. Solo extractos
mensuales (PDF) y avisos eventuales. Hay tres caminos para integrar Nequi:

  1. SMS forwarder en Android (apps tipo SMS Forwarder) que reenvíen los
     SMS de Nequi al correo de finanzas. Este parser leería esos correos.
  2. Procesar el extracto mensual cuando llegue (parser de PDF aparte).
  3. Captura manual vía bot de Telegram.

Por ahora este parser está en stub.
"""

from typing import Optional
from ..modelo import Transaccion
from .base import ParserBase


class NequiParser(ParserBase):
    banco = "Nequi"
    remitente = ""  # depende de la estrategia de integración

    def aplica(self, asunto: str, cuerpo: str, remitente: str) -> bool:
        return False  # deshabilitado hasta definir estrategia

    def parsear(self, id_correo: str, asunto: str, cuerpo: str) -> Optional[Transaccion]:
        return None
