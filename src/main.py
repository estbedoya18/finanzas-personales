"""Orquestador: ingesta, contabilidad determinista y clasificación IA."""

import logging
import os
import sys

from .clasificacion import ClasificadorFinanciero
from .clasificador_ia import ClasificadorIA
from .gmail_client import GmailClient
from .migracion_historico import migrar_clasificaciones_desplazadas
from .notificador_telegram import NotificadorTelegram
from .parsers import PARSERS
from .planificacion_sheets import PlanificacionSheets
from .saldos import CalculadorSaldos
from .saldos_sheets import SaldosSheets
from .sheets_client import SheetsClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _reclasificar_historico() -> bool:
    return os.getenv("RECLASIFICAR_HISTORICO", "false").lower() in {"1", "true", "si", "yes"}


def procesar() -> int:
    gmail = GmailClient()
    sheets = SheetsClient()
    sheets.preparar_estructura()
    planificacion = PlanificacionSheets(sheets.spreadsheet)
    planificacion.preparar_estructura()

    migradas = migrar_clasificaciones_desplazadas(sheets.hoja)
    if migradas:
        log.info("Migración histórica: %d filas realineadas", migradas)

    saldos_sheets = SaldosSheets(sheets.spreadsheet)
    saldos_sheets.preparar_estructura()

    existentes = sheets.cargar_transacciones()
    sheets.aplicar_decisiones_pendientes(existentes)
    ya_existentes = {tx.id_correo for tx in existentes}
    log.info("Sheet ya tiene %d transacciones registradas", len(ya_existentes))

    manuales = [
        tx for tx in planificacion.cargar_movimientos_manuales()
        if tx.id_correo not in ya_existentes
    ]
    ids_manuales = {
        tx.id_correo.split(":", 2)[1]
        for tx in manuales
        if tx.id_correo.startswith("manual:") and ":" in tx.id_correo
    }

    nuevas_gmail = []
    procesados_ids = []
    ignorados = 0

    for correo in gmail.listar_pendientes():
        if correo.id in ya_existentes:
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

        nuevas_gmail.append(transaccion)
        procesados_ids.append(correo.id)
        log.info("OK: %s %.2f (%s)", transaccion.tipo, transaccion.monto, transaccion.contraparte)

    nuevas = [*manuales, *nuevas_gmail]
    todas = [*existentes, *nuevas]
    sheets.sincronizar_cuentas_detectadas(todas)
    cuentas = sheets.obtener_cuentas_propias()
    saldos_sheets.sincronizar_cuentas(cuentas)

    ids_permitidos_ia = {tx.id_correo for tx in nuevas}
    if _reclasificar_historico():
        ids_permitidos_ia.update(
            tx.id_correo for tx in existentes
            if tx.clasificado_por != "manual" and tx.naturaleza != "interno"
        )

    ia = ClasificadorIA()
    if not ia.disponible:
        log.warning("OPENAI_API_KEY no configurada: se dejarán como sin_ia sin llamada externa")

    clasificador = ClasificadorFinanciero(
        cuentas,
        sheets.obtener_reglas_categorias(),
        clasificador_ia=ia,
    )
    clasificador.clasificar(todas, ids_permitidos_ia)
    aprendidas = sheets.registrar_reglas_aprendidas(todas)

    actualizadas = sheets.actualizar_clasificaciones(existentes)
    insertadas = sheets.insertar(nuevas)
    pendientes_nuevas = [tx for tx in nuevas if tx.estado_revision == "pendiente"]
    sheets.sincronizar_pendientes(todas)

    calculador_saldos = CalculadorSaldos(
        cuentas, saldos_sheets.cargar_iniciales(),
    )
    saldos_actuales, movimientos_no_mapeados = calculador_saldos.calcular(todas)
    saldos_guardados = saldos_sheets.guardar_actuales(saldos_actuales)
    log.info(
        "Saldos: %d cuentas calculadas, %d sin saldo inicial, %d movimientos no mapeados",
        saldos_guardados,
        len(calculador_saldos.cuentas_sin_saldo_inicial()),
        movimientos_no_mapeados,
    )

    if ids_manuales:
        marcados = planificacion.marcar_procesados(ids_manuales)
        log.info("Movimientos manuales procesados: %d", marcados)

    if pendientes_nuevas:
        enviado = NotificadorTelegram().notificar_pendientes(
            pendientes_nuevas, sheets.enlace_pendientes(),
        )
        log.info("Aviso Telegram de pendientes: %s", "enviado" if enviado else "no configurado")

    log.info(
        "Base contable: %d históricas actualizadas, %d nuevas Gmail, %d manuales, %d reglas aprendidas, %d ignoradas",
        actualizadas, len(nuevas_gmail), len(manuales), aprendidas, ignorados,
    )

    for correo_id in procesados_ids:
        try:
            gmail.marcar_procesado(correo_id)
        except Exception as error:
            log.exception("Error marcando %s: %s", correo_id, error)

    return insertadas


if __name__ == "__main__":
    try:
        procesar()
    except Exception as error:
        log.exception("Falla fatal: %s", error)
        sys.exit(1)
