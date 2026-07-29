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
            "8401", banco="Bancolombia", nombre="Bancolombia operativa",
            tipo="cuenta_ahorros", cuenta_asociada="",
        ),
        CuentaPropia(
            "2913", banco="Bancolombia", nombre="Débito 2913",
            tipo="tarjeta_debito", cuenta_asociada="8401",
        ),
        CuentaPropia("7353", banco="Lulo Bank", nombre="Lulo ahorro", tipo="cuenta_ahorros"),
        CuentaPropia("7884", banco="Bancolombia", nombre="Crédito", tipo="tarjeta_credito"),
        CuentaPropia("Ahorros", banco="Bancolombia", nombre="Descripción genérica", tipo="cuenta"),
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
    assert "Ahorros" not in por_cuenta
    assert no_mapeados == 0


def test_ignora_movimientos_anteriores_al_corte():
    cuenta = CuentaPropia("8401", banco="Bancolombia", tipo="cuenta_ahorros")
    inicial = SaldoInicial(
        "8401", datetime.fromisoformat("2026-07-13T12:00:00"), 100_000,
    )
    movimiento = _tx(
        fecha_hora="2026-07-13T11:59:00", cuenta="8401", monto=50_000,
    )

    saldos, _ = CalculadorSaldos([cuenta], [inicial]).calcular([movimiento])

    assert saldos[0].saldo_actual == 100_000
    assert saldos[0].movimientos == 0


def test_contabiliza_horas_de_un_digito_desde_google_sheets():
    cuentas = [
        CuentaPropia("8401", banco="Bancolombia", nombre="Bancolombia", tipo="cuenta_ahorros"),
        CuentaPropia(
            "2913", banco="Bancolombia", nombre="Débito 2913",
            tipo="tarjeta_debito", cuenta_asociada="8401",
        ),
    ]
    inicial = SaldoInicial(
        "8401", datetime.fromisoformat("2026-07-20T00:00:00"), 100_000,
    )
    movimientos = [
        _tx(
            id_correo="transferencia-15000",
            fecha_hora="2026-07-21 7:34:00",
            tipo="transferencia_enviada",
            monto=15_000,
            cuenta="8401",
        ),
        _tx(
            id_correo="compra-12600",
            fecha_hora="2026-07-22 7:55:00",
            monto=12_600,
            cuenta="2913",
        ),
        _tx(
            id_correo="compra-12700",
            fecha_hora="2026-07-22 20:27:00",
            monto=12_700,
            cuenta="2913",
        ),
    ]

    saldos, no_mapeados = CalculadorSaldos(cuentas, [inicial]).calcular(movimientos)

    assert saldos[0].salidas == 40_300
    assert saldos[0].saldo_actual == 59_700
    assert saldos[0].movimientos == 3
    assert saldos[0].ultima_transaccion == "2026-07-22 20:27:00"
    assert no_mapeados == 0


def test_mapea_nomina_con_cuenta_generica_al_unico_deposito_del_banco():
    cuentas = [
        CuentaPropia("8401", banco="Bancolombia", tipo="cuenta_ahorros"),
        CuentaPropia("7353", banco="Lulo Bank", tipo="cuenta_ahorros"),
    ]
    iniciales = [
        SaldoInicial("8401", datetime(2026, 7, 20), 0),
        SaldoInicial("7353", datetime(2026, 7, 20), 60_338),
    ]
    nomina = _tx(
        id_correo="nomina-generica",
        fecha_hora="2026-07-28T12:06:00",
        banco="Bancolombia",
        tipo="transferencia_recibida",
        direccion="entrada",
        cuenta="Ahorros",
        monto=2_322_754,
    )

    saldos, no_mapeados = CalculadorSaldos(cuentas, iniciales).calcular([nomina])
    por_cuenta = {saldo.cuenta: saldo for saldo in saldos}

    assert por_cuenta["8401"].entradas == 2_322_754
    assert por_cuenta["8401"].saldo_actual == 2_322_754
    assert por_cuenta["7353"].saldo_actual == 60_338
    assert no_mapeados == 0
