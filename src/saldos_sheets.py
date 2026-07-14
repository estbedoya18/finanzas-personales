"""Persistencia de saldos iniciales y calculados en Google Sheets."""

from datetime import datetime
from typing import Iterable

import gspread

from .clasificacion import CuentaPropia
from .saldos import SaldoCalculado, SaldoInicial, es_cuenta_con_saldo


HOJA_INICIALES = "saldos_iniciales"
HOJA_ACTUALES = "saldos_actuales"
ENCABEZADOS_INICIALES = [
    "cuenta", "nombre", "fecha_corte", "saldo_inicial", "moneda", "activo",
]
ENCABEZADOS_ACTUALES = [
    "cuenta", "nombre", "fecha_corte", "saldo_inicial", "entradas", "salidas",
    "saldo_calculado", "movimientos_contabilizados", "ultima_transaccion",
    "actualizado_en",
]


class SaldosSheets:
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet

    def preparar_estructura(self) -> None:
        self._obtener_o_crear(HOJA_INICIALES, ENCABEZADOS_INICIALES)
        self._obtener_o_crear(HOJA_ACTUALES, ENCABEZADOS_ACTUALES)

    def sincronizar_cuentas(self, cuentas: Iterable[CuentaPropia]) -> int:
        hoja = self.spreadsheet.worksheet(HOJA_INICIALES)
        existentes = {
            str(fila.get("cuenta", "")).strip()
            for fila in hoja.get_all_records()
        }
        nuevas = [
            [
                cuenta.identificador,
                cuenta.nombre or cuenta.identificador,
                "",
                "",
                cuenta.moneda or "COP",
                "SI",
            ]
            for cuenta in cuentas
            if es_cuenta_con_saldo(cuenta)
            and cuenta.identificador not in existentes
        ]
        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")
        return len(nuevas)

    def cargar_iniciales(self) -> list[SaldoInicial]:
        iniciales = []
        for fila in self.spreadsheet.worksheet(HOJA_INICIALES).get_all_records():
            if str(fila.get("activo", "SI")).upper() == "NO":
                continue
            cuenta = str(fila.get("cuenta", "")).strip()
            fecha = str(fila.get("fecha_corte", "")).strip()
            saldo = fila.get("saldo_inicial", "")
            if not cuenta or not fecha or saldo in {"", None}:
                continue
            try:
                iniciales.append(SaldoInicial(
                    cuenta=cuenta,
                    fecha_corte=datetime.fromisoformat(fecha),
                    saldo=self._monto(saldo),
                ))
            except (TypeError, ValueError):
                continue
        return iniciales

    def guardar_actuales(self, saldos: Iterable[SaldoCalculado]) -> int:
        hoja = self.spreadsheet.worksheet(HOJA_ACTUALES)
        filas = [
            [
                saldo.cuenta,
                saldo.nombre,
                saldo.fecha_corte,
                saldo.saldo_inicial,
                saldo.entradas,
                saldo.salidas,
                saldo.saldo_actual,
                saldo.movimientos,
                saldo.ultima_transaccion,
                datetime.now().isoformat(timespec="seconds"),
            ]
            for saldo in saldos
        ]
        hoja.clear()
        hoja.append_rows(
            [ENCABEZADOS_ACTUALES, *filas],
            value_input_option="USER_ENTERED",
        )
        return len(filas)

    def _obtener_o_crear(self, nombre: str, encabezados: list[str]):
        try:
            hoja = self.spreadsheet.worksheet(nombre)
        except gspread.WorksheetNotFound:
            hoja = self.spreadsheet.add_worksheet(
                nombre, rows=1000, cols=len(encabezados) + 2,
            )
            hoja.append_row(encabezados)
            return hoja
        if hoja.col_count < len(encabezados):
            hoja.resize(cols=len(encabezados))
        if not hoja.row_values(1):
            hoja.append_row(encabezados)
        return hoja

    @staticmethod
    def _monto(valor) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)
        texto = str(valor).strip().replace("$", "").replace(" ", "")
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif texto.count(".") > 1:
            texto = texto.replace(".", "")
        elif "," in texto:
            texto = texto.replace(",", ".")
        return float(texto)
