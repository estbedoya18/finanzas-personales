"""Orquestador: ingesta desde Gmail y aplicación de la base contable."""

import logging
import sys

from .clasificacion import ClasificadorFinanciero
from .gmail_client import GmailClient
from .parsers import PARSERS
from .sheets_client import SheetsClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def procesar() -> int:
    gmail = GmailClient()
    sheets = SheetsClient()
    sheets.preparar_estructura()

    existentes = sheets.cargar_transacciones()
    ya_existentes = {tx.id_correo for tx in existentes}
    log.info("Sheet ya tiene %d transacciones registradas", len(ya_existentes))

    nuevas = []
    procesados_ids = []
    ignorados = 0

    for correo in gmail.listar_pendientes():
        if correo.id in ya_existentes:
            log.info("Correo %s ya estaba en el Sheet, marcando como procesado", correo.id)
            gmail.marcar_procesado(correo.id)
            continue

        parser_match = next(
            (parser for parser in PARSERS if parser.aplica(correo.asunto, correo.cuerpo, correo.remitente)),
            None,
        )
        if not parser_match:
            log.info("Sin parser para correo %s (asunto: %r)", correo.id, correo.asunto[:80])
            continue

        try:
            transaccion = parser_match.parsear(correo.id, correo.asunto, correo.cuerpo)
        except Exception as error:
            log.exception("Error parseando correo %s: %s", correo.id, error)
            continue

        if transaccion is None:
            ignorados += 1
            gmail.marcar_procesado(correo.id)
            continue

        nuevas.append(transaccion)
        procesados_ids.append(correo.id)
        log.info(
            "OK: %s %s %s -> %.2f (%s)",
            transaccion.banco, transaccion.tipo, transaccion.direccion,
            transaccion.monto, transaccion.contraparte,
        )

    todas = [*existentes, *nuevas]
    sheets.sincronizar_cuentas_detectadas(todas)
    clasificador = ClasificadorFinanciero(
        sheets.obtener_cuentas_propias(),
        sheets.obtener_reglas_categorias(),
    )
    clasificador.clasificar(todas)

    actualizadas = sheets.actualizar_clasificaciones(existentes)
    insertadas = sheets.insertar(nuevas)
    log.info("Base contable: %d filas históricas actualizadas", actualizadas)
    log.info("Insertadas %d transacciones nuevas", insertadas)

    for correo_id in procesados_ids:
        try:
            gmail.marcar_procesado(correo_id)
        except Exception as error:
            log.exception("Error marcando %s como procesado: %s", correo_id, error)

    log.info("Resumen: %d nuevas, %d ignoradas", len(nuevas), ignorados)
    return insertadas


if __name__ == "__main__":
    try:
        procesar()
    except Exception as error:
        log.exception("Falla fatal: %s", error)
        sys.exit(1)
