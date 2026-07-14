"""Cliente de Google Sheets y persistencia de la base contable."""

import json
import os
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials

from .clasificacion import CuentaPropia, ReglaCategoria
from .modelo import Transaccion


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HOJA_TRANSACCIONES = "transacciones"
HOJA_CUENTAS = "cuentas_propias"
HOJA_REGLAS = "reglas_categorias"

ENCABEZADOS_CUENTAS = [
    "identificador", "banco", "nombre", "tipo", "rol", "alias", "llaves", "activo",
]
ENCABEZADOS_REGLAS = [
    "patron", "campo", "categoria", "subcategoria", "naturaleza", "prioridad", "activo",
]


class SheetsClient:
    def __init__(self):
        info = json.loads(os.environ["GOOGLE_SHEETS_CREDENTIALS_JSON"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        self.cliente = gspread.authorize(creds)
        self.spreadsheet = self.cliente.open_by_key(os.environ["SHEET_ID"])
        self._hoja = None

    @property
    def hoja(self):
        if self._hoja is None:
            self._hoja = self._obtener_o_crear_hoja(
                HOJA_TRANSACCIONES, Transaccion.encabezados(), columnas=20,
            )
        return self._hoja

    def preparar_estructura(self) -> None:
        """Crea catálogos y agrega columnas nuevas sin modificar datos existentes."""
        self._asegurar_encabezados(self.hoja, Transaccion.encabezados())
        self._obtener_o_crear_hoja(HOJA_CUENTAS, ENCABEZADOS_CUENTAS, columnas=10)
        self._obtener_o_crear_hoja(HOJA_REGLAS, ENCABEZADOS_REGLAS, columnas=10)

    def _obtener_o_crear_hoja(self, nombre: str, encabezados: list[str], columnas: int):
        try:
            hoja = self.spreadsheet.worksheet(nombre)
        except gspread.WorksheetNotFound:
            hoja = self.spreadsheet.add_worksheet(nombre, rows=1000, cols=columnas)
            hoja.append_row(encabezados)
            return hoja

        self._asegurar_encabezados(hoja, encabezados)
        return hoja

    def _asegurar_encabezados(self, hoja, encabezados: list[str]) -> None:
        actuales = hoja.row_values(1)
        if not actuales:
            hoja.append_row(encabezados)
            return

        faltantes = [encabezado for encabezado in encabezados if encabezado not in actuales]
        if faltantes:
            inicio = len(actuales) + 1
            fin = inicio + len(faltantes) - 1
            hoja.update(
                f"{self._columna(inicio)}1:{self._columna(fin)}1",
                [faltantes],
                value_input_option="USER_ENTERED",
            )

    def ids_existentes(self) -> set[str]:
        return {tx.id_correo for tx in self.cargar_transacciones()}

    def cargar_transacciones(self) -> list[Transaccion]:
        valores = self.hoja.get_all_values()
        if len(valores) < 2:
            return []

        encabezados = {nombre: indice for indice, nombre in enumerate(valores[0])}

        def valor(fila: list[str], nombre: str) -> str:
            indice = encabezados.get(nombre)
            return fila[indice] if indice is not None and indice < len(fila) else ""

        transacciones = []
        for numero_fila, fila in enumerate(valores[1:], start=2):
            if not valor(fila, "id_correo"):
                continue
            try:
                monto = float(valor(fila, "monto") or 0)
            except ValueError:
                monto = 0.0

            transacciones.append(Transaccion(
                id_correo=valor(fila, "id_correo"),
                fecha_hora=valor(fila, "fecha_hora"),
                banco=valor(fila, "banco"),
                tipo=valor(fila, "tipo"),
                monto=monto,
                direccion=valor(fila, "direccion"),
                cuenta=valor(fila, "cuenta"),
                contraparte=valor(fila, "contraparte"),
                referencia=valor(fila, "referencia") or None,
                categoria=valor(fila, "categoria") or None,
                descripcion_raw=valor(fila, "descripcion_raw"),
                procesado_en=valor(fila, "procesado_en"),
                naturaleza=valor(fila, "naturaleza") or None,
                subcategoria=valor(fila, "subcategoria") or None,
                cuenta_destino=valor(fila, "cuenta_destino") or None,
                transferencia_id=valor(fila, "transferencia_id") or None,
                clasificado_por=valor(fila, "clasificado_por") or None,
                confianza_clasificacion=valor(fila, "confianza_clasificacion") or None,
                fila_sheet=numero_fila,
            ))
        return transacciones

    def sincronizar_cuentas_detectadas(self, transacciones: Iterable[Transaccion]) -> None:
        """Registra instrumentos propios vistos en el historial, sin sobrescribir configuración."""
        hoja = self.spreadsheet.worksheet(HOJA_CUENTAS)
        existentes = {fila.get("identificador", "") for fila in hoja.get_all_records()}
        nuevas = []

        for tx in transacciones:
            identificador = (tx.cuenta or "").strip()
            if not identificador or identificador in existentes:
                continue
            referencia = (tx.referencia or "").lower()
            tipo = "tarjeta_credito" if "cred" in referencia else "tarjeta_debito" if "deb" in referencia else "cuenta"
            nuevas.append([
                identificador, tx.banco, f"{tx.banco} *{identificador}", tipo,
                "sin_definir", "", "", "SI",
            ])
            existentes.add(identificador)

        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")

    def obtener_cuentas_propias(self) -> list[CuentaPropia]:
        hoja = self.spreadsheet.worksheet(HOJA_CUENTAS)
        cuentas = []
        for fila in hoja.get_all_records():
            identificador = str(fila.get("identificador", "")).strip()
            if not identificador:
                continue
            cuentas.append(CuentaPropia(
                identificador=identificador,
                banco=str(fila.get("banco", "")),
                nombre=str(fila.get("nombre", "")),
                tipo=str(fila.get("tipo", "cuenta")),
                rol=str(fila.get("rol", "sin_definir")),
                alias=str(fila.get("alias", "")),
                llaves=str(fila.get("llaves", "")),
                activo=str(fila.get("activo", "SI")).upper() != "NO",
            ))
        return cuentas

    def obtener_reglas_categorias(self) -> list[ReglaCategoria]:
        hoja = self.spreadsheet.worksheet(HOJA_REGLAS)
        reglas = []
        for fila in hoja.get_all_records():
            patron = str(fila.get("patron", "")).strip()
            if not patron:
                continue
            try:
                prioridad = int(fila.get("prioridad") or 100)
            except (TypeError, ValueError):
                prioridad = 100
            reglas.append(ReglaCategoria(
                patron=patron,
                campo=str(fila.get("campo", "texto")) or "texto",
                categoria=str(fila.get("categoria", "")),
                subcategoria=str(fila.get("subcategoria", "")),
                naturaleza=str(fila.get("naturaleza", "")),
                prioridad=prioridad,
                activo=str(fila.get("activo", "SI")).upper() != "NO",
            ))
        return reglas

    def actualizar_clasificaciones(self, transacciones: Iterable[Transaccion]) -> int:
        cambios = []
        for tx in transacciones:
            if not tx.fila_sheet or not tx.requiere_actualizacion:
                continue
            cambios.extend([
                {"range": f"J{tx.fila_sheet}", "values": [[tx.categoria or ""]]},
                {"range": f"M{tx.fila_sheet}:R{tx.fila_sheet}", "values": [[
                    tx.naturaleza or "", tx.subcategoria or "", tx.cuenta_destino or "",
                    tx.transferencia_id or "", tx.clasificado_por or "",
                    tx.confianza_clasificacion or "",
                ]]},
            ])
        if cambios:
            self.hoja.batch_update(cambios, value_input_option="USER_ENTERED")
        return len(cambios) // 2

    def insertar(self, transacciones: Iterable[Transaccion]) -> int:
        filas = [tx.to_row() for tx in transacciones]
        if not filas:
            return 0
        self.hoja.append_rows(filas, value_input_option="USER_ENTERED")
        return len(filas)

    @staticmethod
    def _columna(numero: int) -> str:
        resultado = ""
        while numero:
            numero, residuo = divmod(numero - 1, 26)
            resultado = chr(65 + residuo) + resultado
        return resultado
