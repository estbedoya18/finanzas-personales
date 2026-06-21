"""Modelo de datos para una transacción normalizada."""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaccion:
    """Una transacción financiera normalizada, lista para escribirse al Sheet."""

    id_correo: str                 # Gmail message ID (clave para deduplicación)
    fecha_hora: str                # ISO 8601: 2026-06-09T17:09:00
    banco: str                     # Bancolombia | Lulo | Nu | Nequi
    tipo: str                      # compra | transferencia_enviada | transferencia_recibida | pago_qr | pago_pse
    monto: float                   # siempre positivo
    direccion: str                 # entrada | salida
    cuenta: str                    # últimos dígitos de la cuenta propia
    contraparte: str               # comercio, persona o entidad
    descripcion_raw: str           # texto crudo original
    referencia: Optional[str] = None     # llave Bre-B, ID transacción, número de comprobante, etc.
    categoria: Optional[str] = None      # se llena después, manual o auto
    procesado_en: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_row(self) -> list:
        """Convierte la transacción a una fila plana para Google Sheets."""
        return [
            self.id_correo,
            self.fecha_hora,
            self.banco,
            self.tipo,
            self.monto,
            self.direccion,
            self.cuenta,
            self.contraparte,
            self.referencia or "",
            self.categoria or "",
            self.descripcion_raw,
            self.procesado_en,
        ]

    @staticmethod
    def encabezados() -> list:
        return [
            "id_correo", "fecha_hora", "banco", "tipo", "monto", "direccion",
            "cuenta", "contraparte", "referencia", "categoria",
            "descripcion_raw", "procesado_en",
        ]
