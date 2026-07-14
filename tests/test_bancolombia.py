"""Tests del parser de Bancolombia usando los 5 correos reales de muestra."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.bancolombia import BancolombiaParser


parser = BancolombiaParser()
REMITENTE = "Alertas y Notificaciones <alertasynotificaciones@an.notificacionesbancolombia.com>"


def test_compra():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: Compraste $7.500,00 en BUNUELO SAN FERNANDO con tu T.Deb *2913, el 09/06/2026 a las 17:09. Si tienes dudas, encuentranos aqui..."
    assert parser.aplica(asunto, cuerpo, REMITENTE)
    tx = parser.parsear("test1", asunto, cuerpo)
    assert tx is not None
    assert tx.banco == "Bancolombia"
    assert tx.tipo == "compra"
    assert tx.monto == 7500.0
    assert tx.contraparte == "BUNUELO SAN FERNANDO"
    assert tx.cuenta == "2913"
    assert tx.referencia == "T.Deb"
    assert tx.direccion == "salida"
    assert tx.fecha_hora.startswith("2026-06-09T17:09")
    print("✓ compra")


def test_compra_credito_cop():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: Compraste COP43.700,00 en LA MIGUERIA con tu T.Cred *7884, el 01/06/2026 a las 18:54. Si tienes dudas..."
    tx = parser.parsear("test1b", asunto, cuerpo)
    assert tx is not None
    assert tx.monto == 43700.0
    assert tx.referencia == "T.Cred"
    assert tx.cuenta == "7884"
    print("✓ compra crédito COP")


def test_transferencia_recibida():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: esteban, recibiste una transferencia de ESTEBAN BEDOYA por $49,000.00 en tu cuenta *8401 conectada a la llave @estebanb0850 el 09/06/26 a las 08:33. Con llaves es de una y gratis."
    tx = parser.parsear("test2", asunto, cuerpo)
    assert tx is not None
    assert tx.tipo == "transferencia_recibida"
    assert tx.monto == 49000.0
    assert tx.contraparte == "ESTEBAN BEDOYA"
    assert tx.cuenta == "8401"
    assert tx.direccion == "entrada"
    assert tx.referencia == "@estebanb0850"
    print("✓ transferencia recibida")


def test_pago_nomina():
    asunto = "Alertas y Notificaciones"
    cuerpo = (
        "Bancolombia: Recibiste un pago de Nómina de EMPRESA DE PRUEBA S.A. "
        "por $1,234,567.89 en tu cuenta de Ahorros el 10/07/2026 a las 16:42. "
        "Si tienes dudas, llámanos."
    )
    tx = parser.parsear("test-nomina", asunto, cuerpo)
    assert tx is not None
    assert tx.tipo == "transferencia_recibida"
    assert tx.monto == 1234567.89
    assert tx.direccion == "entrada"
    assert tx.cuenta == "Ahorros"
    assert tx.contraparte == "EMPRESA DE PRUEBA S.A."
    assert tx.referencia == "Nómina"
    assert tx.categoria == "Salario"
    assert tx.fecha_hora.startswith("2026-07-10T16:42")
    print("✓ pago de nómina")


def test_transferencia_enviada_a_cuenta():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: Transferiste $25,000.00 desde tu cuenta 8401 a la cuenta *3012348018 el 09/06/2026 a las 08:39. ¿Dudas? Llamanos al 018000931987."
    tx = parser.parsear("test3", asunto, cuerpo)
    assert tx is not None
    assert tx.tipo == "transferencia_enviada"
    assert tx.monto == 25000.0
    assert tx.cuenta == "8401"
    assert tx.contraparte == "cuenta *3012348018"
    print("✓ transferencia enviada a cuenta")


def test_pago_qr():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: ESTEBAN BEDOYA MARTINEZ pagaste $12,500.00 por codigo QR desde tu cuenta *8401 a la llave 0092385858 el 09/06/2026 a las 10:46. Con codigo QR es facil y de una."
    tx = parser.parsear("test4", asunto, cuerpo)
    assert tx is not None
    assert tx.tipo == "pago_qr"
    assert tx.monto == 12500.0
    assert tx.cuenta == "8401"
    print("✓ pago QR")


def test_transferencia_brepb_a_llave():
    asunto = "Alertas y Notificaciones Bancolombia"
    cuerpo = "Bancolombia: ESTEBAN, transferiste $7,882.00 a la llave @ariza929 desde tu cuenta *8401 a Leidy Diana Ariza Chavarría el 09/06/26 a las 17:42. Con Bre-b es de una y gratis."
    tx = parser.parsear("test5", asunto, cuerpo)
    assert tx is not None
    assert tx.tipo == "transferencia_enviada"
    assert tx.monto == 7882.0
    assert tx.cuenta == "8401"
    assert tx.contraparte == "Leidy Diana Ariza Chavarría"
    assert tx.referencia == "@ariza929"
    print("✓ transferencia Bre-B a llave")


def test_ignora_no_transaccional():
    """Un correo que no es de notificaciones (ej. ofertas de empleo) debe ser rechazado por aplica()."""
    asunto = "Nuevas ofertas de trabajo publicadas en empleo.grupobancolombia.com"
    cuerpo = "Ha recibido este correo electrónico porque se unió a la comunidad de talentos..."
    remitente_otro = "bancolombi-jobnotif@bancolombia.com.co"
    assert not parser.aplica(asunto, cuerpo, remitente_otro)
    print("✓ ignora correos no transaccionales")


if __name__ == "__main__":
    test_compra()
    test_compra_credito_cop()
    test_transferencia_recibida()
    test_pago_nomina()
    test_transferencia_enviada_a_cuenta()
    test_pago_qr()
    test_transferencia_brepb_a_llave()
    test_ignora_no_transaccional()
    print("\n✅ Todos los tests de Bancolombia pasaron")
