"""Cliente de Google Sheets: transacciones, catálogos y revisiones."""

import json
import os
import re
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials

from .categorias import filas_catalogo
from .cuentas import es_identificador_detectable
from .clasificacion import CuentaPropia, ReglaCategoria
from .modelo import Transaccion


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HOJA_TRANSACCIONES = "transacciones"
HOJA_CUENTAS = "cuentas_propias"
HOJA_REGLAS = "reglas_categorias"
HOJA_CATALOGO = "catalogo_categorias"
HOJA_PENDIENTES = "pendientes_revision"

ENCABEZADOS_CUENTAS = [
    "identificador", "banco", "nombre", "tipo", "rol", "alias", "llaves", "activo",
    "cuenta_asociada", "moneda",
]
ENCABEZADOS_REGLAS = [
    "patron", "campo", "categoria", "subcategoria", "naturaleza", "prioridad", "activo",
]
ENCABEZADOS_CATALOGO = ["categoria", "subcategoria", "naturaleza", "activo"]
ENCABEZADOS_PENDIENTES = [
    "id_correo", "fecha_hora", "banco", "monto", "contraparte", "categoria_sugerida",
    "subcategoria_sugerida", "confianza", "explicacion", "estado",
    "categoria_elegida", "subcategoria_elegida",
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
                HOJA_TRANSACCIONES, Transaccion.encabezados(), columnas=25,
            )
        return self._hoja

    def preparar_estructura(self) -> None:
        """Crea hojas y columnas nuevas sin eliminar ni desplazar información existente."""
        self._asegurar_encabezados(self.hoja, Transaccion.encabezados())
        self._obtener_o_crear_hoja(HOJA_CUENTAS, ENCABEZADOS_CUENTAS, columnas=10)
        self._obtener_o_crear_hoja(HOJA_REGLAS, ENCABEZADOS_REGLAS, columnas=10)
        self._obtener_o_crear_hoja(HOJA_CATALOGO, ENCABEZADOS_CATALOGO, columnas=6)
        self._obtener_o_crear_hoja(HOJA_PENDIENTES, ENCABEZADOS_PENDIENTES, columnas=14)
        self._sincronizar_catalogo()

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
        if getattr(hoja, "col_count", 0) < len(encabezados):
            hoja.resize(cols=len(encabezados))
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

    def _sincronizar_catalogo(self) -> None:
        hoja = self.spreadsheet.worksheet(HOJA_CATALOGO)
        existentes = {tuple(map(str, fila[:3])) for fila in hoja.get_all_values()[1:]}
        nuevas = [fila for fila in filas_catalogo() if tuple(fila[:3]) not in existentes]
        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")

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
                estado_revision=valor(fila, "estado_revision") or None,
                categoria_sugerida=valor(fila, "categoria_sugerida") or None,
                subcategoria_sugerida=valor(fila, "subcategoria_sugerida") or None,
                explicacion_clasificacion=valor(fila, "explicacion_clasificacion") or None,
                fila_sheet=numero_fila,
            ))
        return transacciones

    def sincronizar_cuentas_detectadas(self, transacciones: Iterable[Transaccion]) -> None:
        hoja = self.spreadsheet.worksheet(HOJA_CUENTAS)
        existentes = {str(fila.get("identificador", "")) for fila in hoja.get_all_records()}
        nuevas = []
        for tx in transacciones:
            identificador = (tx.cuenta or "").strip()
            if not es_identificador_detectable(identificador) or identificador in existentes:
                continue
            referencia = (tx.referencia or "").lower()
            tipo = "tarjeta_credito" if "cred" in referencia else "tarjeta_debito" if "deb" in referencia else "cuenta"
            nuevas.append([
                identificador, tx.banco, f"{tx.banco} *{identificador}",
                tipo, "sin_definir", "", "", "SI", "", "COP",
            ])
            existentes.add(identificador)
        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")

    def obtener_cuentas_propias(self) -> list[CuentaPropia]:
        filas = self.spreadsheet.worksheet(HOJA_CUENTAS).get_all_records()
        return [
            CuentaPropia(
                identificador=str(fila["identificador"]).strip(),
                banco=str(fila.get("banco", "")),
                nombre=str(fila.get("nombre", "")),
                tipo=str(fila.get("tipo", "cuenta")),
                rol=str(fila.get("rol", "sin_definir")),
                alias=str(fila.get("alias", "")),
                llaves=str(fila.get("llaves", "")),
                activo=str(fila.get("activo", "SI")).upper() != "NO",
                cuenta_asociada=str(fila.get("cuenta_asociada", "")).strip(),
                moneda=str(fila.get("moneda", "COP")).strip() or "COP",
            )
            for fila in filas if str(fila.get("identificador", "")).strip()
        ]

    def obtener_reglas_categorias(self) -> list[ReglaCategoria]:
        reglas = []
        for fila in self.spreadsheet.worksheet(HOJA_REGLAS).get_all_records():
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

    def aplicar_decisiones_pendientes(self, transacciones: Iterable[Transaccion]) -> int:
        por_id = {tx.id_correo: tx for tx in transacciones}
        hoja = self.spreadsheet.worksheet(HOJA_PENDIENTES)
        valores = hoja.get_all_values()
        if len(valores) < 2:
            return 0
        encabezados = {nombre: indice for indice, nombre in enumerate(valores[0])}
        actualizaciones, aplicadas = [], 0

        for numero_fila, fila in enumerate(valores[1:], start=2):
            valor = lambda nombre: fila[encabezados[nombre]] if encabezados[nombre] < len(fila) else ""
            tx = por_id.get(valor("id_correo"))
            categoria = valor("categoria_elegida").strip()
            if tx is None or not categoria:
                continue
            tx.asignar(
                categoria=categoria,
                subcategoria=valor("subcategoria_elegida").strip() or None,
                clasificado_por="manual",
                confianza_clasificacion="manual",
                estado_revision="resuelto",
                categoria_sugerida=None,
                subcategoria_sugerida=None,
            )
            actualizaciones.append({"range": f"J{numero_fila}", "values": [["resuelto"]]})
            aplicadas += 1

        if actualizaciones:
            hoja.batch_update(actualizaciones, value_input_option="USER_ENTERED")
        return aplicadas

    def registrar_reglas_aprendidas(self, transacciones: Iterable[Transaccion]) -> int:
        hoja = self.spreadsheet.worksheet(HOJA_REGLAS)
        existentes = {
            (str(fila.get("patron", "")), str(fila.get("categoria", "")), str(fila.get("subcategoria", "")))
            for fila in hoja.get_all_records()
        }
        nuevas = []
        for tx in transacciones:
            if tx.clasificado_por != "manual" or not tx.categoria or not tx.contraparte:
                continue
            if tx.categoria in {"Sin clasificar", "Pendiente de revisar", "Transferencia interna"}:
                continue
            patron = f"^{re.escape(tx.contraparte.strip())}$"
            clave = (patron, tx.categoria, tx.subcategoria or "")
            if clave not in existentes:
                nuevas.append([patron, "contraparte", tx.categoria, tx.subcategoria or "", tx.naturaleza or "", 20, "SI"])
                existentes.add(clave)
        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")
        return len(nuevas)

    def sincronizar_pendientes(self, transacciones: Iterable[Transaccion]) -> int:
        hoja = self.spreadsheet.worksheet(HOJA_PENDIENTES)
        existentes = {str(fila.get("id_correo", "")) for fila in hoja.get_all_records()}
        nuevas = []
        for tx in transacciones:
            if tx.estado_revision != "pendiente" or tx.id_correo in existentes:
                continue
            nuevas.append([
                tx.id_correo, tx.fecha_hora, tx.banco, tx.monto, tx.contraparte,
                tx.categoria_sugerida or "", tx.subcategoria_sugerida or "",
                tx.confianza_clasificacion or "", tx.explicacion_clasificacion or "",
                "pendiente", "", "",
            ])
            existentes.add(tx.id_correo)
        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")
        return len(nuevas)

    def enlace_pendientes(self) -> str:
        hoja = self.spreadsheet.worksheet(HOJA_PENDIENTES)
        return f"https://docs.google.com/spreadsheets/d/{os.environ['SHEET_ID']}/edit#gid={hoja.id}"

    def actualizar_clasificaciones(self, transacciones: Iterable[Transaccion]) -> int:
        """Actualiza por encabezado para tolerar columnas heredadas intermedias."""
        encabezados = self.hoja.row_values(1)
        posiciones = {nombre: indice + 1 for indice, nombre in enumerate(encabezados)}
        campos = [
            "categoria", "naturaleza", "subcategoria", "cuenta_destino",
            "transferencia_id", "clasificado_por", "confianza_clasificacion",
            "estado_revision", "categoria_sugerida", "subcategoria_sugerida",
            "explicacion_clasificacion",
        ]
        cambios = []
        actualizadas = 0

        for tx in transacciones:
            if not tx.fila_sheet or not tx.requiere_actualizacion:
                continue
            for campo in campos:
                columna = posiciones.get(campo)
                if columna is None:
                    continue
                cambios.append({
                    "range": f"{self._columna(columna)}{tx.fila_sheet}",
                    "values": [[getattr(tx, campo) or ""]],
                })
            actualizadas += 1

        if cambios:
            self.hoja.batch_update(cambios, value_input_option="USER_ENTERED")
        return actualizadas

    def insertar(self, transacciones: Iterable[Transaccion]) -> int:
        """Inserta según el orden real de encabezados de la hoja."""
        encabezados = self.hoja.row_values(1)
        campos_modelo = set(Transaccion.encabezados())
        filas = []
        for tx in transacciones:
            fila = []
            for encabezado in encabezados:
                if encabezado not in campos_modelo:
                    fila.append("")
                    continue
                valor = getattr(tx, encabezado)
                fila.append("" if valor is None else valor)
            filas.append(fila)
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
