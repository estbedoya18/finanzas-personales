"""Pruebas del motor de clasificación contable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clasificacion import ClasificadorFinanciero, CuentaPropia, ReglaCategoria
from src.modelo import Transaccion


def _tx(**cambios) -> Transaccion:
    datos = {
        "id_correo": "correo",
        "fecha_hora": "2026-06-01T09:00:00",
        "banco": "Bancolombia",
        "tipo": "compra",
        "monto": 10000.0,
        "direccion": "salida",
        "cuenta": "8401",
        "contraparte": "COMERCIO",
        "descripcion_raw": "Compra en COMERCIO",
    }
    datos.update(cambios)
    return Transaccion(**datos)


def test_empareja_transferencia_entre_cuentas_propias():
    salida = _tx(
        id_correo="salida",
        tipo="transferencia_enviada",
        monto=500000.0,
        referencia="3012347353",
        contraparte="cuenta *3012347353",
    )
    entrada = _tx(
        id_correo="entrada",
        fecha_hora="2026-06-01T09:03:00",
        banco="Lulo",
        tipo="transferencia_recibida",
        direccion="entrada",
        cuenta="7353",
        monto=500000.0,
        contraparte="Esteban",
    )
    cuentas = [
        CuentaPropia("8401", nombre="Bancolombia principal"),
        CuentaPropia("7353", nombre="Lulo ahorro"),
    ]

    ClasificadorFinanciero(cuentas, []).clasificar([salida, entrada])

    assert salida.naturaleza == "interno"
    assert entrada.naturaleza == "interno"
    assert salida.transferencia_id == entrada.transferencia_id
    assert salida.cuenta_destino == "7353"
    print("✓ transferencia interna emparejada")


def test_transferencia_recibida_por_llave_bre_b_es_interna():
    entrada = _tx(
        id_correo="breb-entrada",
        tipo="transferencia_recibida",
        direccion="entrada",
        cuenta="8401",
        contraparte="Transferencia Bre-B desde la llave @mi-lulo",
    )
    cuentas = [
        CuentaPropia("8401", nombre="Bancolombia principal"),
        CuentaPropia("7353", nombre="Lulo ahorro", llaves="@mi-lulo|ahorro@correo.com"),
    ]

    ClasificadorFinanciero(cuentas, []).clasificar([entrada])

    assert entrada.naturaleza == "interno"
    assert entrada.categoria == "Transferencia interna"
    assert entrada.cuenta_destino == "8401"
    assert entrada.subcategoria == "Desde Lulo ahorro"


def test_regla_categoria_y_valor_por_defecto():
    compra = _tx(
        id_correo="spotify",
        contraparte="SPOTIFY",
        descripcion_raw="Compra SPOTIFY",
    )
    regla = ReglaCategoria(
        patron="spotify",
        campo="contraparte",
        categoria="Suscripciones",
        subcategoria="Streaming",
        prioridad=1,
    )

    ClasificadorFinanciero([], [regla]).clasificar([compra])

    assert compra.naturaleza == "gasto"
    assert compra.categoria == "Suscripciones"
    assert compra.subcategoria == "Streaming"
    assert compra.clasificado_por == "regla"
    print("✓ categoría por regla")


def test_gasto_sin_regla_y_sin_ia_queda_pendiente():
    transferencia = _tx(
        id_correo="externa-sin-regla",
        tipo="transferencia_enviada",
        contraparte="cuenta *3164538803",
        referencia="3164538803",
        descripcion_raw="Transferencia a cuenta externa",
    )

    ClasificadorFinanciero([], []).clasificar([transferencia])

    assert transferencia.naturaleza == "gasto"
    assert transferencia.categoria == "Pendiente de revisar"
    assert transferencia.clasificado_por == "sistema"
    assert transferencia.confianza_clasificacion == "sin_ia"
    assert transferencia.estado_revision == "pendiente"
    assert transferencia.explicacion_clasificacion


def test_categoria_existente_se_conserva_como_manual():
    compra = _tx(categoria="Mascotas", contraparte="PET SHOP")
    regla = ReglaCategoria(patron="PET", categoria="Otro", prioridad=1)

    ClasificadorFinanciero([], [regla]).clasificar([compra])

    assert compra.categoria == "Mascotas"
    assert compra.clasificado_por == "manual"
    print("✓ clasificación manual conservada")


if __name__ == "__main__":
    test_empareja_transferencia_entre_cuentas_propias()
    test_transferencia_recibida_por_llave_bre_b_es_interna()
    test_regla_categoria_y_valor_por_defecto()
    test_gasto_sin_regla_y_sin_ia_queda_pendiente()
    test_categoria_existente_se_conserva_como_manual()
    print("\n✅ Todos los tests de clasificación pasaron")
