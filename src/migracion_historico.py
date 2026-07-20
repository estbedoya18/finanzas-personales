"""Migracion idempotente para clasificaciones historicas desplazadas en Sheets."""

from typing import Any


CLASIFICADORES = {"sistema", "regla", "ia", "manual"}
CONFIANZAS = {"alta", "media", "baja", "manual", "sin_ia"}


def migrar_clasificaciones_desplazadas(sheets: Any) -> int:
    """Realinea filas antiguas afectadas por la columna `enviado_telegram`.

    Las versiones anteriores