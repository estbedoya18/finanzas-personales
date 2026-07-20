"""Parser para correos de alertasynotificaciones@an.notificacionesbancolombia.com.

Maneja:
  1. Compra con tarjeta
  2. Transferencia recibida
  3. Pago de nómina recibido
  4. Transferencia enviada a cuenta
  5. Pago con código QR
  6. Transferencia enviada con Bre-B
"""

import re
from typing import Optional

from ..modelo import Transaccion
from ..normalizar import normalizar_monto, normalizar_fecha, normalizar_hora, combinar_fecha_hora
from .base import ParserBase


_MONTO = r"(?:COP\s*)?\$?\s*[\d.,]+"
_FECHA = r"\d{1,2}/\d{1,2}/\d{2,4}"
_HORA = r"\d{1,2}:\d{2}"


class BancolombiaParser(ParserBase):
    banco = "Bancolombia"
    remitente = "alertasynotificaciones@an.notificacionesbancolombia.com"
    ASUNTOS_VALIDOS = ("alertas y notificaciones",)

    RE_COMPRA = re.compile(
        rf"Compraste\s+({_MONTO})\s+en\s+(.+?)\s+con\s+tu\s+(T\.Deb|T\.Cred)\s+\*(\d+),?\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )
    RE_RECIBIDA = re.compile(
        rf"recibiste una transferencia de\s+(.+?)\s+por\s+({_MONTO})\s+en tu cuenta\s+\*?(\d+)\s+conectada a la llave\s+(\S+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )
    RE_NOMINA = re.compile(
        rf"recibiste\s+un\s+pago\s+de\s+n[oó]mina\s+de\s+(.+?)\s+por\s+({_MONTO})\s+en\s+tu\s+cuenta\s+de\s+(.+?)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )
    RE_ENVIADA_CUENTA = re.compile(
        rf"Transferiste\s+({_MONTO})\s+desde\s+tu\s+cuenta\s+\*?(\d+)\s+a\s+la\s+cuenta\s+\*?(\d+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )
    RE_PAGO_QR = re.compile(
        rf"pagaste\s+({_MONTO})\s+por\s+c[oó]digo\s+QR\s+desde\s+tu\s+cuenta\s+\*?(\d+)\s+a\s+la\s+llave\s+(\S+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )
    RE_ENVIADA_LLAVE = re.compile(
        rf"transferiste\s+({_MONTO})\s+a\s+la\s+llave\s+(\S+)\s+desde\s+tu\s+cuenta\s+\*?(\d+)\s+a\s+(.+?)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )

    def aplica(self, asunto: str, cuerpo: str, remitente: str) -> bool:
        if self.remitente not in remitente.lower():
            return False
        asunto_l = asunto.lower()
        return any(asunto_l.startswith(a) or a in asunto_l for a in self.ASUNTOS_VALIDOS)

    def parsear(self, id_correo: str, asunto: str, cuerpo: str) -> Optional[Transaccion]:
        texto = re.sub(r"\s+", " ", cuerpo)

        if m := self.RE_COMPRA.search(texto):
            monto_s, comercio, tarjeta, ult4, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="compra",
                monto=normalizar_monto(monto_s),
                direccion="salida",
                cuenta=ult4,
                contraparte=comercio.strip(),
                referencia=tarjeta,
                descripcion_raw=texto[:500],
            )

        if m := self.RE_NOMINA.search(texto):
            empresa, monto_s, tipo_cuenta, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="transferencia_recibida",
                monto=normalizar_monto(monto_s),
                direccion="entrada",
                cuenta=tipo_cuenta.strip(),
                contraparte=empresa.strip(),
                referencia="Nómina",
                categoria="Ingresos",
                naturaleza="ingreso",
                subcategoria="Nómina",
                clasificado_por="regla",
                confianza_clasificacion="alta",
                estado_revision="resuelto",
                descripcion_raw=texto[:500],
            )

        if m := self.RE_RECIBIDA.search(texto):
            remitente_p, monto_s, cuenta, llave, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="transferencia_recibida",
                monto=normalizar_monto(monto_s),
                direccion="entrada",
                cuenta=cuenta,
                contraparte=remitente_p.strip(),
                referencia=llave,
                descripcion_raw=texto[:500],
            )

        if m := self.RE_PAGO_QR.search(texto):
            monto_s, cuenta, llave, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="pago_qr",
                monto=normalizar_monto(monto_s),
                direccion="salida",
                cuenta=cuenta,
                contraparte=llave,
                referencia=llave,
                descripcion_raw=texto[:500],
            )

        if m := self.RE_ENVIADA_LLAVE.search(texto):
            monto_s, llave, cuenta, beneficiario, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="transferencia_enviada",
                monto=normalizar_monto(monto_s),
                direccion="salida",
                cuenta=cuenta,
                contraparte=beneficiario.strip(),
                referencia=llave,
                descripcion_raw=texto[:500],
            )

        if m := self.RE_ENVIADA_CUENTA.search(texto):
            monto_s, cuenta_origen, cuenta_destino, fecha, hora = m.groups()
            return Transaccion(
                id_correo=id_correo,
                fecha_hora=combinar_fecha_hora(normalizar_fecha(fecha), normalizar_hora(hora)),
                banco=self.banco,
                tipo="transferencia_enviada",
                monto=normalizar_monto(monto_s),
                direccion="salida",
                cuenta=cuenta_origen,
                contraparte=f"cuenta *{cuenta_destino}",
                referencia=cuenta_destino,
                descripcion_raw=texto[:500],
            )

        return None
