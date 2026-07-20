"""Regresiones del orden contable, nómina y reglas de naturaleza."""

from src.clasificacion import ClasificadorFinanciero, ReglaCategoria
from src.modelo import Transaccion
from src.parsers.bancolombia import BancolombiaParser


def _tx(**cambios) -> Transaccion:
    datos = {
        "id_correo": "movimiento",
        "fecha_hora": "2026-07-20T10:00:00",
        "banco": "Bancolombia",
        "tipo": "transferencia_enviada",
        "monto": 10000.0,
        "direccion": "salida",
        "cuenta": "8401",
        "contraparte": "PERSONA",
        "descripcion_raw": "Transferencia",
    }
    datos.update(cambios)
    return Transaccion(**datos)


def test_categoria_existente_no_deja_naturaleza_vacia():
    tx = _tx(
        tipo="transferencia_recibida",
        direccion="entrada",
        categoria="Ingresos",
        subcategoria="Reembolso",
    )

    ClasificadorFinanciero([], []).clasificar([tx])

    assert tx.naturaleza == "ingreso"
    assert tx.categoria == "Ingresos"


def test_regla_no_puede_convertir_salida_en_ingreso():
    tx = _tx(contraparte="JUAN PEREZ")
    regla = ReglaCategoria(
        patron="JUAN PEREZ",
        campo="contraparte",
        categoria="Ingresos",
        subcategoria="Otros ingresos",
        naturaleza="ingreso",
    )

    ClasificadorFinanciero([], [regla]).clasificar([tx])

    assert tx.naturaleza == "gasto"


def test_nomina_usa_catalogo_actual():
    parser = BancolombiaParser()
    cuerpo = (
        "Bancolombia: Recibiste un pago de Nómina de BTG PACTUAL S.A. "
        "por $1,786,733.00 en tu cuenta de Ahorros el 10/07/2026 a las 16:42."
    )

    tx = parser.parsear("nomina", "Alertas y Notificaciones", cuerpo)

    assert tx is not None
    assert tx.direccion == "entrada"
    assert tx.naturaleza == "ingreso"
    assert tx.categoria == "Ingresos"
    assert tx.subcategoria == "Nómina"
    assert tx.clasificado_por == "regla"
