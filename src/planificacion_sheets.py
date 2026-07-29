"""Hojas auxiliares para presupuesto, metas y movimientos manuales."""

from datetime import datetime
import logging
from typing import Iterable

import gspread
from gspread.utils import DateTimeOption, ValueRenderOption

from .modelo import Transaccion


log = logging.getLogger(__name__)

HOJA_PRESUPUESTOS = "presupuestos"
HOJA_METAS = "metas_ahorro"
HOJA_MOVIMIENTOS_METAS = "movimientos_metas"
HOJA_MOVIMIENTOS_MANUALES = "movimientos_manuales"
HOJA_TELEGRAM_SESIONES = "telegram_sesiones"
HOJA_NOTIFICACIONES = "notificaciones_log"

ENCABEZADOS_PRESUPUESTOS = [
    "id_presupuesto", "periodo", "categoria", "monto_presupuestado",
    "activo", "creado_en", "actualizado_en",
]
ENCABEZADOS_METAS = [
    "id_meta", "nombre", "tipo", "monto_objetivo", "fecha_objetivo",
    "cuenta_asociada", "activo", "creado_en", "actualizado_en",
]
ENCABEZADOS_MOVIMIENTOS_METAS = [
    "id_movimiento", "fecha_hora", "id_meta", "tipo_movimiento", "monto",
    "descripcion", "origen", "creado_en",
]
ENCABEZADOS_MOVIMIENTOS_MANUALES = [
    "id_movimiento", "fecha_hora", "tipo", "monto", "direccion", "cuenta",
    "cuenta_destino", "categoria", "subcategoria", "contraparte", "descripcion",
    "origen", "estado", "creado_en", "procesado_en",
]
ENCABEZADOS_TELEGRAM_SESIONES = [
    "chat_id", "flujo", "paso", "datos_temporales", "actualizado_en",
]
ENCABEZADOS_NOTIFICACIONES = [
    "id_notificacion", "fecha_hora", "tipo", "canal", "estado", "detalle",
]


class PlanificacionSheets:
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet

    def preparar_estructura(self) -> None:
        self._obtener_o_crear(HOJA_PRESUPUESTOS, ENCABEZADOS_PRESUPUESTOS)
        self._obtener_o_crear(HOJA_METAS, ENCABEZADOS_METAS)
        self._obtener_o_crear(HOJA_MOVIMIENTOS_METAS, ENCABEZADOS_MOVIMIENTOS_METAS)
        self._obtener_o_crear(HOJA_MOVIMIENTOS_MANUALES, ENCABEZADOS_MOVIMIENTOS_MANUALES)
        self._obtener_o_crear(HOJA_TELEGRAM_SESIONES, ENCABEZADOS_TELEGRAM_SESIONES)
        self._obtener_o_crear(HOJA_NOTIFICACIONES, ENCABEZADOS_NOTIFICACIONES)
        self._asegurar_cuenta_efectivo()

    def cargar_movimientos_manuales(self) -> list[Transaccion]:
        hoja = self.spreadsheet.worksheet(HOJA_MOVIMIENTOS_MANUALES)
        valores = hoja.get_values(
            value_render_option=ValueRenderOption.unformatted,
            date_time_render_option=DateTimeOption.formatted_string,
        )
        if len(valores) < 2:
            return []

        encabezados = [str(valor).strip() for valor in valores[0]]
        filas = []
        for valores_fila in valores[1:]:
            filas.append({
                encabezado: valores_fila[indice] if indice < len(valores_fila) else ""
                for indice, encabezado in enumerate(encabezados)
                if encabezado
            })
        return self.normalizar_movimientos_manuales(filas)

    @staticmethod
    def normalizar_movimientos_manuales(filas: Iterable[dict]) -> list[Transaccion]:
        resultado: list[Transaccion] = []
        for fila in filas:
            estado = str(fila.get("estado", "confirmado")).strip().lower()
            if estado not in {"confirmado", "aprobado", "procesar"}:
                continue

            identificador = str(fila.get("id_movimiento", "")).strip()
            if not identificador:
                continue

            tipo = str(fila.get("tipo", "")).strip().lower()
            fecha = str(fila.get("fecha_hora", "")).strip()
            try:
                monto = PlanificacionSheets._monto(fila.get("monto", 0))
            except (TypeError, ValueError):
                log.warning(
                    "Movimiento manual %s ignorado: monto inválido %r",
                    identificador,
                    fila.get("monto"),
                )
                continue
            if monto <= 0:
                log.warning(
                    "Movimiento manual %s ignorado: el monto debe ser mayor que cero",
                    identificador,
                )
                continue

            cuenta = str(fila.get("cuenta", "")).strip()
            destino = str(fila.get("cuenta_destino", "")).strip()
            categoria = str(fila.get("categoria", "")).strip() or None
            subcategoria = str(fila.get("subcategoria", "")).strip() or None
            contraparte = str(fila.get("contraparte", "")).strip() or "Movimiento manual"
            descripcion = str(fila.get("descripcion", "")).strip()
            origen = str(fila.get("origen", "manual")).strip() or "manual"
            direccion = str(fila.get("direccion", "")).strip().lower()

            if tipo == "retiro_efectivo":
                destino = destino or "EFECTIVO"
                transferencia_id = f"manual:{identificador}"
                resultado.extend([
                    Transaccion(
                        id_correo=f"{transferencia_id}:salida",
                        fecha_hora=fecha,
                        banco="Manual",
                        tipo="transferencia_enviada",
                        monto=monto,
                        direccion="salida",
                        cuenta=cuenta,
                        contraparte=destino,
                        referencia=destino,
                        categoria="Transferencia interna",
                        subcategoria="Retiro hacia efectivo",
                        descripcion_raw=descripcion or "Retiro hacia efectivo",
                        origen=origen,
                        naturaleza="interno",
                        cuenta_destino=destino,
                        transferencia_id=transferencia_id,
                        clasificado_por="sistema",
                        confianza_clasificacion="alta",
                        estado_revision="resuelto",
                    ),
                    Transaccion(
                        id_correo=f"{transferencia_id}:entrada",
                        fecha_hora=fecha,
                        banco="Manual",
                        tipo="transferencia_recibida",
                        monto=monto,
                        direccion="entrada",
                        cuenta=destino,
                        contraparte=cuenta,
                        referencia=cuenta,
                        categoria="Transferencia interna",
                        subcategoria="Ingreso a efectivo",
                        descripcion_raw=descripcion or "Ingreso a efectivo",
                        origen=origen,
                        naturaleza="interno",
                        cuenta_destino=destino,
                        transferencia_id=transferencia_id,
                        clasificado_por="sistema",
                        confianza_clasificacion="alta",
                        estado_revision="resuelto",
                    ),
                ])
                continue

            if tipo == "gasto_efectivo":
                cuenta = cuenta or "EFECTIVO"
                direccion = "salida"
                tipo_normalizado = "compra"
            elif tipo == "ingreso_efectivo":
                cuenta = cuenta or "EFECTIVO"
                direccion = "entrada"
                tipo_normalizado = "ingreso_manual"
            else:
                tipo_normalizado = "ajuste_manual"
                if direccion not in {"entrada", "salida"}:
                    continue

            resultado.append(Transaccion(
                id_correo=f"manual:{identificador}",
                fecha_hora=fecha,
                banco="Manual",
                tipo=tipo_normalizado,
                monto=monto,
                direccion=direccion,
                cuenta=cuenta,
                contraparte=contraparte,
                referencia=f"manual:{identificador}",
                categoria=categoria,
                subcategoria=subcategoria,
                descripcion_raw=descripcion or contraparte,
                origen=origen,
                clasificado_por="manual" if categoria else None,
                confianza_clasificacion="manual" if categoria else None,
                estado_revision="resuelto" if categoria else None,
            ))

        return resultado

    def marcar_procesados(self, ids: set[str]) -> int:
        if not ids:
            return 0
        hoja = self.spreadsheet.worksheet(HOJA_MOVIMIENTOS_MANUALES)
        valores = hoja.get_all_values()
        if len(valores) < 2:
            return 0
        encabezados = {nombre: indice for indice, nombre in enumerate(valores[0])}
        indice_id = encabezados.get("id_movimiento")
        indice_procesado = encabezados.get("procesado_en")
        if indice_id is None or indice_procesado is None:
            return 0
        actualizaciones = []
        ahora = datetime.now().isoformat(timespec="seconds")
        for numero_fila, fila in enumerate(valores[1:], start=2):
            valor = fila[indice_id] if indice_id < len(fila) else ""
            if valor in ids:
                actualizaciones.append({
                    "range": f"{self._columna(indice_procesado + 1)}{numero_fila}",
                    "values": [[ahora]],
                })
        if actualizaciones:
            hoja.batch_update(actualizaciones, value_input_option="USER_ENTERED")
        return len(actualizaciones)

    def _asegurar_cuenta_efectivo(self) -> None:
        try:
            hoja = self.spreadsheet.worksheet("cuentas_propias")
        except gspread.WorksheetNotFound:
            return
        existentes = {
            str(fila.get("identificador", "")).strip().upper()
            for fila in hoja.get_all_records()
        }
        if "EFECTIVO" not in existentes:
            hoja.append_row([
                "EFECTIVO", "Manual", "Efectivo", "efectivo", "operativa",
                "cash", "", "SI", "", "COP",
            ], value_input_option="USER_ENTERED")

    def _obtener_o_crear(self, nombre: str, encabezados: list[str]):
        try:
            hoja = self.spreadsheet.worksheet(nombre)
        except gspread.WorksheetNotFound:
            hoja = self.spreadsheet.add_worksheet(
                nombre, rows=1000, cols=len(encabezados) + 2,
            )
            hoja.append_row(encabezados)
            return hoja
        actuales = hoja.row_values(1)
        if hoja.col_count < len(encabezados):
            hoja.resize(cols=len(encabezados))
        if not actuales:
            hoja.append_row(encabezados)
        else:
            faltantes = [item for item in encabezados if item not in actuales]
            if faltantes:
                inicio = len(actuales) + 1
                fin = inicio + len(faltantes) - 1
                hoja.update(
                    f"{self._columna(inicio)}1:{self._columna(fin)}1",
                    [faltantes],
                    value_input_option="USER_ENTERED",
                )
        return hoja

    @staticmethod
    def _monto(valor) -> float:
        if isinstance(valor, (int, float)):
            return abs(float(valor))
        texto = str(valor or "").strip().replace("$", "").replace(" ", "")
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")
        return abs(float(texto or 0))

    @staticmethod
    def _columna(numero: int) -> str:
        resultado = ""
        while numero:
            numero, residuo = divmod(numero - 1, 26)
            resultado = chr(65 + residuo) + resultado
        return resultado
