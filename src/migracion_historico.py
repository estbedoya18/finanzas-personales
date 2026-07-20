"""Migracion idempotente para clasificaciones historicas desplazadas en Sheets."""

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


def _columna(numero: int) -> str:
    resultado = ""
    while numero:
        numero, residuo = divmod(numero - 1, 26)
        resultado = chr(65 + residuo) + resultado
    return resultado


def migrar_clasificaciones_desplazadas(hoja: Any) -> int:
    """Realinea filas antiguas afectadas por la columna ``enviado_telegram``.

    Las versiones anteriores escribian la fila por posicion y no contemplaban esa
    columna heredada. Como consecuencia, desde ``subcategoria`` todos los valores
    quedaron una columna a la izquierda. La firma segura de una fila afectada es
    que ``transferencia_id`` contiene realmente el origen de clasificacion.

    La operacion es idempotente: una fila ya corregida no vuelve a modificarse.
    """
    valores = hoja.get_all_values()
    if len(valores) < 2:
        return 0

    encabezados = valores[0]
    posiciones = {nombre: indice for indice, nombre in enumerate(encabezados)}
    if any(campo not in posiciones for campo in CAMPOS_DESPLAZADOS):
        return 0

    indice_transferencia = posiciones["transferencia_id"]
    indice_clasificador = posiciones["clasificado_por"]
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
