from datetime import datetime

from src.clasificacion import CuentaPropia
from src.planificacion_sheets import PlanificacionSheets
from src.saldos import CalculadorSaldos, SaldoInicial


def test_retiro_hacia_efectivo_crea_dos_lados_internos():
    movimientos = PlanificacionSheets.normalizar_movimientos_manuales([{
        "id_movimiento": "m1",
        "fecha_hora": "2026-07-20T18:00:00",
        "tipo": "retiro_efectivo",
        "monto": 50000,
        "cuenta": "8401",
        "cuenta_destino": "EFECTIVO",
        "descripcion": "Retiro en cajero",
        "origen": "telegram",
        "estado": "confirmado",
    }])

    assert len(movimientos) == 2
    assert {tx.direccion for tx in movimientos} == {"entrada", "salida"}
    assert all(tx.naturaleza == "interno" for tx in movimientos)
    assert movimientos[0].transferencia_id == movimientos[1].transferencia_id

    cuentas = [
        CuentaPropia("8401", tipo="cuenta_ahorros", nombre="Bancolombia"),
        CuentaPropia("EFECTIVO", tipo="efectivo", nombre="Efectivo"),
    ]
    iniciales = [
        SaldoInicial("8401", datetime(2026, 7, 20), 100000),
        SaldoInicial("EFECTIVO", datetime(2026, 7, 20), 0),
    ]
    saldos, no_mapeados = CalculadorSaldos(cuentas, iniciales).calcular(movimientos)
    por_cuenta = {saldo.cuenta: saldo.saldo_actual for saldo in saldos}

    assert por_cuenta["8401"] == 50000
    assert por_cuenta["EFECTIVO"] == 50000
    assert no_mapeados == 0


def test_gasto_en_efectivo_es_salida_real():
    movimientos = PlanificacionSheets.normalizar_movimientos_manuales([{
        "id_movimiento": "m2",
        "fecha_hora": "2026-07-20T19:00:00",
        "tipo": "gasto_efectivo",
        "monto": 18000,
        "categoria": "Alimentación",
        "descripcion": "Almuerzo",
        "estado": "confirmado",
    }])

    assert len(movimientos) == 1
    tx = movimientos[0]
    assert tx.cuenta == "EFECTIVO"
    assert tx.direccion == "salida"
    assert tx.tipo == "compra"
    assert tx.categoria == "Alimentación"
    assert tx.origen == "manual"
