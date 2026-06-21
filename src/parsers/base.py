"""Clase base para los parsers de bancos."""

from abc import ABC, abstractmethod
from typing import Optional
from ..modelo import Transaccion


class ParserBase(ABC):
    """Cada banco hereda de aquí y debe implementar dos cosas:

    - aplica(): decide si un correo dado le corresponde a este parser.
    - parsear(): convierte el correo en una Transaccion (o None si no es transacción).
    """

    banco: str = ""

    # Dirección de remitente esperada para los correos de este banco.
    # El orquestador puede usarla como pre-filtro antes de llamar a aplica().
    remitente: str = ""

    @abstractmethod
    def aplica(self, asunto: str, cuerpo: str, remitente: str) -> bool:
        """Devuelve True si este parser puede manejar el correo."""

    @abstractmethod
    def parsear(self, id_correo: str, asunto: str, cuerpo: str) -> Optional[Transaccion]:
        """Devuelve una Transaccion si el correo es procesable, None si debe ignorarse."""
