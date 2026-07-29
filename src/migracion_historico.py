"""Migraciones idempotentes para transacciones históricas en Google Sheets."""

import re
from typing import Any


CLASIFICADORES = {"sistema", "regla", "ia", "manual"}
CONFIANZAS = {"alta", "media", "baja", "manual", "sin_ia"}
CAMPOS_DESPLAZADOS = [
    "enviado_telegram",
    "subcategoria",
    "cuenta_destino",
    "transferencia_id",
    "clasificado_por",
    "confianza_clasificacion",
    "estado_revision",
    "categoria_sugerida",
    "subcategoria_sugerida",
    "explicacion_clasificacion",
]

_RE_LULO_DESTINO = re.compile(
    r"Destino\s+(?:ahorro|cuenta)\s*[•·\-]\s*(\d+)",
    re.IGNORECASE,
)
_RE_LULO_ORIGEN = re.compile(
    r"Origen\s+cuenta\s*[•·\-]\s*(\d+)",
    re.IGNORECASE,
)
_RE_LULO_REMITENTE = re.compile(
    r"Recibiste\s+\$[\d.,]+\s+de\s+(.+?)"
    r"(?=\s+Origen\s+cuenta|\s+Destino\s+(?:ahorro|cuenta)|"
    r"\s+ID\.?\s*transacci[oó]n|\s+Fecha\s+|\s+Hora\s+|$)",
    re.IGNORECASE,
)


def _columna(numero: int) -> str:
    resultado = ""
    while numero:
        numero, residuo = divmod(numero - 1, 26)
        resultado = chr(65 + residuo) + resultado
    return resultado


def migrar_clasificaciones_desplazadas(hoja: Any) -> int:
    """Realinea filas antiguas afectadas por la columna ``enviado_telegram``."""
    valores = hoja.get_all_values()
    if len(valores) < 2:
        return 0

    encabezados = valores[0]
    posiciones = {nombre: indice for indice, nombre in enumerate(encabezados)}
    if any(campo not in posiciones for campo in CAMPOS_DESPLAZADOS):
        return 0

    cambios = []
    migradas = 0

    for numero_fila, fila in enumerate(valores[1:], start=2):
        def valor(nombre: str) -> str:
            indice = posiciones[nombre]
            return fila[indice] if indice < len(fila) else ""

        supuesto_clasificador = valor("transferencia_id").strip().lower()
        supuesto_confianza = valor("clasificado_por").strip().lower()
        if supuesto_clasificador not in CLASIFICADORES:
            continue
        if supuesto_confianza and supuesto_confianza not in CONFIANZAS:
            continue

        realineados = {
            "enviado_telegram": "",
            "subcategoria": valor("enviado_telegram"),
            "cuenta_destino": valor("subcategoria"),
            "transferencia_id": valor("cuenta_destino"),
            "clasificado_por": valor("transferencia_id"),
            "confianza_clasificacion": valor("clasificado_por"),
            "estado_revision": valor("confianza_clasificacion"),
            "categoria_sugerida": valor("estado_revision"),
            "subcategoria_sugerida": valor("categoria_sugerida"),
            "explicacion_clasificacion": valor("subcategoria_sugerida"),
        }

        for campo, nuevo_valor in realineados.items():
            columna = posiciones[campo] + 1
            cambios.append({
                "range": f"{_columna(columna)}{numero_fila}",
                "values": [[nuevo_valor]],
            })
        migradas += 1

    if cambios:
        hoja.batch_update(cambios, value_input_option="USER_ENTERED")
    return migradas


def migrar_cuentas_lulo_recibidas(hoja: Any) -> int:
    """Corrige entradas de Lulo guardadas con la cuenta de origen.

    Los correos reales incluyen ambos campos, por ejemplo ``Origen cuenta • 8401``
    y ``Destino ahorro • 7353``. Versiones anteriores usaban siempre el origen como
    cuenta del movimiento, por lo que la entrada se acreditaba a Bancolombia en vez
    de Lulo. La migración usa exclusivamente el destino explícito del correo y es
    idempotente.
    """
    valores = hoja.get_all_values()
    if len(valores) < 2:
        return 0

    encabezados = valores[0]
    posiciones = {nombre: indice for indice, nombre in enumerate(encabezados)}
    requeridos = {
        "banco", "tipo", "cuenta", "contraparte", "referencia", "descripcion_raw",
    }
    if not requeridos.issubset(posiciones):
        return 0

    cambios = []
    migradas = 0

    for numero_fila, fila in enumerate(valores[1:], start=2):
        def valor(nombre: str) -> str:
            indice = posiciones[nombre]
            return fila[indice] if indice < len(fila) else ""

        if not valor("banco").strip().lower().startswith("lulo"):
            continue
        if valor("tipo").strip().lower() != "transferencia_recibida":
            continue

        descripcion = valor("descripcion_raw")
        destino = _RE_LULO_DESTINO.search(descripcion)
        if not destino:
            continue

        nuevos = {"cuenta": destino.group(1)}
        if origen := _RE_LULO_ORIGEN.search(descripcion):
            nuevos["referencia"] = origen.group(1)
        if remitente := _RE_LULO_REMITENTE.search(descripcion):
            nuevos["contraparte"] = remitente.group(1).strip()

        cambios_fila = 0
        for campo, nuevo_valor in nuevos.items():
            if valor(campo).strip() == nuevo_valor:
                continue
            columna = posiciones[campo] + 1
            cambios.append({
                "range": f"{_columna(columna)}{numero_fila}",
                "values": [[nuevo_valor]],
            })
            cambios_fila += 1

        if cambios_fila:
            migradas += 1

    if cambios:
        hoja.batch_update(cambios, value_input_option="USER_ENTERED")
    return migradas
