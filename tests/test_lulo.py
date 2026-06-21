"""Test del parser de Lulo con el correo real de muestra."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.lulo import LuloParser


parser = LuloParser()
REMITENTE = "Notificaciones Lulo bank <notificaciones@lulobank.com>"


def test_envio_breB():
    asunto = "¡Envío con Bre-B exitoso! 💸"
    cuerpo = """ícono de app Lulo
Conoce los detalles de tu transacción
Realizaste una transferencia a santiago lopez por $28,000
Origen cuenta • 7353
Llave • @SANTIAGOL1587
ID. transacción • 140089505
Costo de envío ¡Sin costo!
GMF (4x1,000) $112
Fecha 20 de junio de 2026
Hora 3:44 a.m.
"""
    assert parser.aplica(asunto, cuerpo, REMITENTE)
    tx = parser.parsear("lulo1", asunto, cuerpo)
    assert tx is not None
    assert tx.banco == "Lulo"
    assert tx.tipo == "transferencia_enviada"
    assert tx.monto == 28000.0
    assert tx.contraparte == "santiago lopez"
    assert tx.cuenta == "7353"
    assert tx.referencia == "@SANTIAGOL1587"
    assert tx.fecha_hora.startswith("2026-06-20T03:44")
    print("✓ envío Bre-B Lulo")


def test_ignora_pse_fallido():
    """Un pago PSE fallido NO debe procesarse como transacción."""
    asunto = "Pago PSE fallido"
    cuerpo = "No pudimos hacer tu pago PSE a Icetex por $495.826. Espera 20 min..."
    assert not parser.aplica(asunto, cuerpo, REMITENTE)
    print("✓ ignora PSE fallido")


def test_ignora_verificacion():
    """Códigos OTP no son transacciones."""
    asunto = "Verificación de seguridad Lulo bank"
    cuerpo = "Tu código para pago PSE es: 1918. Si no lo pediste, repórtalo."
    assert not parser.aplica(asunto, cuerpo, REMITENTE)
    print("✓ ignora verificación OTP")


def test_ignora_credito_aprobado():
    """Ofertas de crédito no son transacciones."""
    asunto = "Tienes un crédito aprobado por $2,000,000"
    cuerpo = "Pagos 100% online: debita desde tu Lulo cuenta..."
    assert not parser.aplica(asunto, cuerpo, REMITENTE)
    print("✓ ignora oferta de crédito")


if __name__ == "__main__":
    test_envio_breB()
    test_ignora_pse_fallido()
    test_ignora_verificacion()
    test_ignora_credito_aprobado()
    print("\n✅ Todos los tests de Lulo pasaron")
