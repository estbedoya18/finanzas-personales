"""Pruebas del prototipo de saldos de cuentas."""

from datetime import datetime

from src.clasificacion import CuentaPropia
from src.modelo import Transaccion
from src.saldos import CalculadorSaldos, SaldoInicial


def _tx(**cambios) -> Transaccion:
    datos = {
        "id_correo": "movimiento",
        "fecha_hora": "2026-07-13T10:00:00",
        "banco": "Bancolombia",
        "tipo": "compra",
        "monto": 10000.0,
        "direccion": "salida",
        "cuenta": "2913",
        "contraparte": "COMERCIO",
        "descripcion_raw": "Compra",
    }
    datos.update(cambios)
    return Transaccion(**datos)


def test_calcula_saldo_y_mapea_tarjeta_debito():
    cuentas = [
        CuentaPropia(
            "8401", nombre="Bancolombia operativa",
            tipo="cuenta_ahorros", cuenta_asociada="",
        ),
        CuentaPropia(
            "2913", nombre="Débito 2913",
            tipo="tarjeta_debito", cuenta_asociada="8401",
        ),
        CuentaPropia("7353", nombre="Lulo ahorro", tipo="cuenta_ahorros"),
        CuentaPropia("7884", nombre="Crédito", tipo="tarjeta_credito"),
    ]
    iniciales = [
        SaldoInicial("8401", datetime.fromisoformat("2026-07-13T00:00:00"), 1_000_000),
        SaldoInicial("7353", datetime.fromisoformat("2026-07-13T00:00:00"), 500_000),
    ]
    movimientos = [
        _tx(),
        _tx(
            id_correo="nomina", tipo="transferencia_recibida",
            direccion="entrada", cuenta="8401", monto=3_000_000,
        ),
        _tx(
            id_correo="lulo", tipo="transferencia_enviada",
            cuenta="8401", monto=1_000_000,
        ),
        _tx(id_correo="credito", cuenta="7884", monto=250_000),
    ]

    saldos, no_mapeados = CalculadorSaldos(cuentas, iniciales).calcular(movimientos)
    por_cuenta = {saldo.cuenta: saldo for saldo in saldos}

    assert por_cuenta["8401"].saldo_actual == 2_990_000
    assert por_cuenta["8401"].movimientos == 3
    assert por_cuenta["7353"].saldo_actual == 500_000
    assert no_mapeados == 0


def test_ignora_movimientos_anteriores_al_corte():
    cuenta = CuentaPropia("8401", tipo="cuenta_ahorros")
    inicial = SaldoInicial(
        "8401", datetime.fromisoformat("2026-07-13T12:00:00"), 100_000,
    )
    movimiento = _tx(
        fecha_hora="2026-07-13T11:59:00", cuenta="8401", monto=50_000,
    )

    saldos, _ = CalculadorSaldos([cuenta], [inicial]).calcular([movimiento])

    assert saldos[0].saldo_actual == 100_000
    assert saldos[0].movimientos == 0
