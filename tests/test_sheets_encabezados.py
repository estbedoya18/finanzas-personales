"""Pruebas de escritura por encabezado con columnas heredadas."""

from src.modelo import Transaccion
from src.sheets_client import SheetsClient


class HojaFalsa:
    def __init__(self):
        self.encabezados = [
            "id_correo", "fecha_hora", "banco", "tipo", "monto", "direccion",
            "cuenta", "contraparte", "referencia", "categoria", "descripcion_raw",
            "procesado_en", "naturaleza", "enviado_telegram", "subcategoria",
            "cuenta_destino", "transferencia_id", "clasificado_por",
            "confianza_clasificacion", "estado_revision", "categoria_sugerida",
            "subcategoria_sugerida", "explicacion_clasificacion",
        ]
        self.filas = []
        self.cambios = []

    def row_values(self, numero):
        return self.encabezados if numero == 1 else []

    def append_rows(self, filas, value_input_option=None):
        self.filas.extend(filas)

    def batch_update(self, cambios, value_input_option=None):
        self.cambios.extend(cambios)


def _cliente(hoja):
    cliente = object.__new__(SheetsClient)
    cliente._hoja = hoja
    return cliente


def _tx():
    return Transaccion(
        id_correo="correo",
        fecha_hora="2026-07-20T10:00:00",
        banco="Bancolombia",
        tipo="compra",
        monto=10000,
        direccion="salida",
        cuenta="2913",
        contraparte="COMERCIO",
        descripcion_raw="Compra",
        naturaleza="gasto",
        subcategoria="Mercado",
        clasificado_por="regla",
        confianza_clasificacion="alta",
        estado_revision="resuelto",
    )


def test_insertar_respeta_columna_heredada():
    hoja = HojaFalsa()
    cliente = _cliente(hoja)

    cliente.insertar([_tx()])

    fila = hoja.filas[0]
    assert fila[13] == ""
    assert fila[14] == "Mercado"
    assert fila[17] == "regla"
    assert fila[18] == "alta"


def test_actualizar_usa_nombre_de_encabezado():
    hoja = HojaFalsa()
    cliente = _cliente(hoja)
    tx = _tx()
    tx.fila_sheet = 2
    tx.requiere_actualizacion = True

    cliente.actualizar_clasificaciones([tx])

    rangos = {cambio["range"] for cambio in hoja.cambios}
    assert "O2" in rangos
    assert "R2" in rangos
    assert "S2" in rangos
