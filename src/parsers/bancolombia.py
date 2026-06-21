"""Parser para correos de alertasynotificaciones@an.notificacionesbancolombia.com.

Maneja los 5 tipos de notificación transaccional identificados:
  1. Compra con tarjeta (débito o crédito)
  2. Transferencia recibida (con llave)
  3. Transferencia enviada a cuenta
  4. Pago con código QR
  5. Transferencia enviada con Bre-B (a llave)
"""

import re
from typing import Optional

from ..modelo import Transaccion
from ..normalizar import normalizar_monto, normalizar_fecha, normalizar_hora, combinar_fecha_hora
from .base import ParserBase


# Componente reutilizable: un monto puede venir como $1.234,56 o $1,234.56 o COP1.234,56 etc.
_MONTO = r"(?:COP\s*)?\$?\s*[\d.,]+"
# Componente reutilizable: una fecha DD/MM/YY o DD/MM/YYYY
_FECHA = r"\d{1,2}/\d{1,2}/\d{2,4}"
# Componente reutilizable: hora HH:MM
_HORA = r"\d{1,2}:\d{2}"


class BancolombiaParser(ParserBase):
    banco = "Bancolombia"
    remitente = "alertasynotificaciones@an.notificacionesbancolombia.com"

    # Lista blanca: solo procesamos correos cuyo asunto empiece con alguna de estas frases.
    # Todo lo demás (ofertas de empleo, extractos, marketing) se ignora.
    ASUNTOS_VALIDOS = (
        "alertas y notificaciones",
    )

    # --- Patrones (todos case-insensitive) ---
    # 1. Compra: "Compraste $7.500,00 en BUNUELO SAN FERNANDO con tu T.Deb *2913, el 09/06/2026 a las 17:09"
    RE_COMPRA = re.compile(
        rf"Compraste\s+({_MONTO})\s+en\s+(.+?)\s+con\s+tu\s+(T\.Deb|T\.Cred)\s+\*(\d+),?\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )

    # 2. Transferencia recibida con llave:
    # "recibiste una transferencia de ESTEBAN BEDOYA por $49,000.00 en tu cuenta *8401 conectada a la llave @estebanb0850 el 09/06/26 a las 08:33"
    RE_RECIBIDA = re.compile(
        rf"recibiste una transferencia de\s+(.+?)\s+por\s+({_MONTO})\s+en tu cuenta\s+\*?(\d+)\s+conectada a la llave\s+(\S+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )

    # 3. Transferencia enviada a cuenta:
    # "Transferiste $25,000.00 desde tu cuenta 8401 a la cuenta *3012348018 el 09/06/2026 a las 08:39"
    RE_ENVIADA_CUENTA = re.compile(
        rf"Transferiste\s+({_MONTO})\s+desde\s+tu\s+cuenta\s+\*?(\d+)\s+a\s+la\s+cuenta\s+\*?(\d+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )

    # 4. Pago QR:
    # "ESTEBAN BEDOYA MARTINEZ pagaste $12,500.00 por codigo QR desde tu cuenta *8401 a la llave 0092385858 el 09/06/2026 a las 10:46"
    RE_PAGO_QR = re.compile(
        rf"pagaste\s+({_MONTO})\s+por\s+c[oó]digo\s+QR\s+desde\s+tu\s+cuenta\s+\*?(\d+)\s+a\s+la\s+llave\s+(\S+)\s+el\s+({_FECHA})\s+a\s+las\s+({_HORA})",
        re.IGNORECASE,
    )

    # 5. Transferencia enviada con Bre-B a llave:
    # "transferiste $7,882.00 a la llave @ariza929 desde tu cuenta *8401 a Leidy Diana Ariza Chavarría el 09/06/26 a las 17:42"
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
        # Limpiamos el cuerpo: quitamos saltos de línea repetidos para que los regex multi-línea no fallen
        texto = re.sub(r"\s+", " ", cuerpo)

        # Orden importa: probamos los patrones más específicos primero
        # (RE_ENVIADA_LLAVE antes que RE_ENVIADA_CUENTA porque el primero es más restrictivo)

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

        return None  # ningún patrón hizo match — el correo se ignora
