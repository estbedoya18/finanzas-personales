"""Pruebas para migraciones históricas."""

from src.migracion_historico import (
    migrar_clasificaciones_desplazadas,
    migrar_cuentas_lulo_recibidas,
)


class HojaFalsa:
    def __init__(self, valores=None):
        self.valores = valores or [
            [
                "id_correo", "fecha_hora", "banco", "tipo", "monto", "direccion",
                "cuenta", "contraparte", "referencia", "categoria", "descripcion_raw",
                "procesado_en", "naturaleza", "enviado_telegram", "subcategoria",
                "cuenta_destino", "transferencia_id", "clasificado_por",
                "confianza_clasificacion", "estado_revision", "categoria_sugerida",
                "subcategoria_sugerida", "explicacion_clasificacion",
            ],
            [
                "correo-1", "2026-07-01T10:00:00", "Bancolombia", "compra", "10000",
                "salida", "8401", "COMERCIO", "", "Alimentación", "Compra",
                "2026-07-01T10:01:00", "gasto",
                "Restaurantes", "", "", "regla", "alta", "resuelto", "", "",
                "Clasificación conocida", "",
            ],
        ]
        self.cambios = []

    def get_all_values(self):
        return self.valores

    def batch_update(self, cambios, value_input_option=None):
        self.cambios.extend(cambios)
        for cambio in cambios:
            rango = cambio["range"]
            letras = "".join(c for c in rango if c.isalpha())
            fila = int("".join(c for c in rango if c.isdigit())) - 1
            columna = 0
            for letra in letras:
                columna = columna * 26 + ord(letra) - 64
            columna -= 1
            while len(self.valores[fila]) <= columna:
                self.valores[fila].append("")
            self.valores[fila][columna] = cambio["values"][0][0]


def test_migra_fila_desplazada_y_no_la_repite():
    hoja = HojaFalsa()

    assert migrar_clasificaciones_desplazadas(hoja) == 1

    encabezados = {nombre: i for i, nombre in enumerate(hoja.valores[0])}
    fila = hoja.valores[1]
    assert fila[encabezados["enviado_telegram"]] == ""
    assert fila[encabezados["subcategoria"]] == "Restaurantes"
    assert fila[encabezados["clasificado_por"]] == "regla"
    assert fila[encabezados["confianza_clasificacion"]] == "alta"
    assert fila[encabezados["estado_revision"]] == "resuelto"
    assert fila[encabezados["explicacion_clasificacion"]] == "Clasificación conocida"

    assert migrar_clasificaciones_desplazadas(hoja) == 0


def test_migra_entrada_lulo_a_cuenta_destino_y_no_la_repite():
    encabezados = [
        "id_correo", "fecha_hora", "banco", "tipo", "monto", "direccion",
        "cuenta", "contraparte", "referencia", "categoria", "descripcion_raw",
    ]
    descripcion = (
        "Recibiste $1,114,000 de ESTEBAN BEDOYA MARTINEZ "
        "Origen cuenta • 8401 Destino ahorro • 7353 "
        "ID. transacción • 147936915 Fecha 28 de julio de 2026 Hora 12:21 p.m."
    )
    hoja = HojaFalsa([
        encabezados,
        [
            "lulo-1", "2026-07-28T12:21:00", "Lulo", "transferencia_recibida",
            "1114000", "entrada", "8401", descripcion, "", "Transferencia interna",
            descripcion,
        ],
    ])

    assert migrar_cuentas_lulo_recibidas(hoja) == 1

    posiciones = {nombre: i for i, nombre in enumerate(encabezados)}
    fila = hoja.valores[1]
    assert fila[posiciones["cuenta"]] == "7353"
    assert fila[posiciones["referencia"]] == "8401"
    assert fila[posiciones["contraparte"]] == "ESTEBAN BEDOYA MARTINEZ"

    assert migrar_cuentas_lulo_recibidas(hoja) == 0
