"""Modelo de datos para una transacción normalizada."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaccion:
    """Una transacción financiera normalizada, lista para escribirse al Sheet."""

    id_correo: str
    fecha_hora: str
    banco: str
    tipo: str
    monto: float
    direccion: str
    cuenta: str
    contraparte: str
    descripcion_raw: str
    referencia: Optional[str] = None
    categoria: Optional[str] = None
    procesado_en: str = field(default_factory=lambda: datetime.now().isoformat())
    origen: str = "gmail"

    naturaleza: Optional[str] = None
    subcategoria: Optional[str] = None
    cuenta_destino: Optional[str] = None
    transferencia_id: Optional[str] = None
    clasificado_por: Optional[str] = None
    confianza_clasificacion: Optional[str] = None
    estado_revision: Optional[str] = None
    categoria_sugerida: Optional[str] = None
    subcategoria_sugerida: Optional[str] = None
    explicacion_clasificacion: Optional[str] = None

    fila_sheet: int = field(default=0, repr=False, compare=False)
    requiere_actualizacion: bool = field(default=False, repr=False, compare=False)

    def asignar(self, **campos: Optional[str]) -> None:
        for campo, valor in campos.items():
            if getattr(self, campo) != valor:
                setattr(self, campo, valor)
                if self.fila_sheet:
                    self.requiere_actualizacion = True

    def to_row(self) -> list:
        return [getattr(self, encabezado) or "" for encabezado in self.encabezados()]

    @staticmethod
    def encabezados() -> list:
        return [
            "id_correo", "fecha_hora", "banco", "tipo", "monto", "direccion",
            "cuenta", "contraparte", "referencia", "categoria",
            "descripcion_raw", "procesado_en", "origen", "naturaleza", "subcategoria",
            "cuenta_destino", "transferencia_id", "clasificado_por",
            "confianza_clasificacion", "estado_revision", "categoria_sugerida",
            "subcategoria_sugerida", "explicacion_clasificacion",
        ]
