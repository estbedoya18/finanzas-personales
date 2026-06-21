"""Orquestador principal.

Pasos:
  1. Conecta a Gmail y trae los correos etiquetados como Transacciones que aún no han sido procesados
  2. Por cada correo, busca el parser que aplica
  3. Convierte el correo en Transaccion (o lo ignora si no calza ningún patrón)
  4. Escribe las transacciones nuevas al Sheet
  5. Marca cada correo como procesado en Gmail
"""

import logging
import sys

from .gmail_client import GmailClient
from .parsers import PARSERS
from .sheets_client import SheetsClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def procesar() -> int:
    gmail = GmailClient()
    sheets = SheetsClient()

    ya_existentes = sheets.ids_existentes()
    log.info("Sheet ya tiene %d transacciones registradas", len(ya_existentes))

    nuevas = []
    procesados_ids = []
    ignorados = 0

    for correo in gmail.listar_pendientes():
        if correo.id in ya_existentes:
            log.info("Correo %s ya estaba en el Sheet, marcando como procesado", correo.id)
            gmail.marcar_procesado(correo.id)
            continue

        parser_match = None
        for parser in PARSERS:
            if parser.aplica(correo.asunto, correo.cuerpo, correo.remitente):
                parser_match = parser
                break

        if not parser_match:
            log.info("Sin parser para correo %s (asunto: %r)", correo.id, correo.asunto[:80])
            continue

        try:
            tx = parser_match.parsear(correo.id, correo.asunto, correo.cuerpo)
        except Exception as e:
            log.exception("Error parseando correo %s: %s", correo.id, e)
            continue

        if tx is None:
            log.info("Correo %s no es transacción procesable (parser %s lo ignoró)",
                     correo.id, parser_match.banco)
            ignorados += 1
            gmail.marcar_procesado(correo.id)  # lo marcamos para no reintentarlo
            continue

        nuevas.append(tx)
        procesados_ids.append(correo.id)
        log.info("OK: %s %s %s -> %.2f (%s)", tx.banco, tx.tipo, tx.direccion, tx.monto, tx.contraparte)

    if nuevas:
        n = sheets.insertar(nuevas)
        log.info("Insertadas %d transacciones nuevas en el Sheet", n)
    else:
        log.info("No hay transacciones nuevas")

    for correo_id in procesados_ids:
        try:
            gmail.marcar_procesado(correo_id)
        except Exception as e:
            log.exception("Error marcando %s como procesado: %s", correo_id, e)

    log.info("Resumen: %d nuevas, %d ignoradas", len(nuevas), ignorados)
    return len(nuevas)


if __name__ == "__main__":
    try:
        procesar()
    except Exception as e:
        log.exception("Falla fatal: %s", e)
        sys.exit(1)
