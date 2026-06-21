"""Parser para correos de notificaciones@lulobank.com.

Maneja:
  - Envío con Bre-B (transferencia enviada)
  - Recibo por Bre-B (transferencia recibida)
  - Pago PSE exitoso

Ignora explícitamente: pagos PSE fallidos, ofertas de crédito, OTPs, marketing.
"""

import re
from typing import Optional

from ..modelo import Transaccion
from ..normalizar import normalizar_monto, normalizar_fecha, normalizar_hora, combinar_fecha_hora
from .base import ParserBase


class LuloParser(ParserBase):
    banco = "Lulo"
    remitente = "notificaciones@lulobank.com"

    # Lista blanca de asuntos: solo estos son transacciones reales que afectan el balance.
    # NOTA: "Pago PSE fallido" se excluye porque no se movió plata.
    ASUNTOS_VALIDOS = (
        "envío con bre-b exitoso",
        "envio con bre-b exitoso",   # por si llega sin tilde
        "recibiste plata por bre-b",
        "pago pse exitoso",
    )

    # Patrones de extracción
    RE_DEST_BRE_B = re.compile(r"Realizaste una transferencia a\s+(.+?)\s+por\s+(\$[\d.,]+)", re.IGNORECASE)
    RE_RECIBO_BRE_B = re.compile(r"Recibiste\s+(\$[\d.,]+)\s+de\s+(.+?)$", re.IGNORECASE | re.MULTILINE)
    RE_PAGO_PSE = re.compile(r"Hiciste un pago a\s+(.+?)\s+por\s+(\$[\d.,]+)", re.IGNORECASE)

    RE_CUENTA_ORIGEN = re.compile(r"Origen\s*cuenta\s*[•·\-]\s*(\d+)", re.IGNORECASE)
    RE_LLAVE = re.compile(r"Llave\s*[•·\-]\s*(\S+)", re.IGNORECASE)
    RE_ID_TRANSACCION = re.compile(r"ID\.?\s*transacci[oó]n\s*[•·\-]\s*(\d+)", re.IGNORECASE)
    RE_COMPROBANTE = re.compile(r"No\.?\s*comprobante\s+(\d+)", re.IGNORECASE)
    RE_FECHA = re.compile(r"Fecha\s+(.+?)(?:\n|Hora)", re.IGNORECASE)
    RE_HORA = re.compile(r"Hora\s+([\d:]+\s*(?:a\.?m\.?|p\.?m\.?)?)", re.IGNORECASE)

    def aplica(self, asunto: str, cuerpo: str, remitente: str) -> bool:
        if self.remitente not in remitente.lower():
            return False
        asunto_l = asunto.lower()
        return any(a in asunto_l for a in self.ASUNTOS_VALIDOS)

    def _extraer_fecha_hora(self, texto: str) -> Optional[str]:
        m_f = self.RE_FECHA.search(texto)
        m_h = self.RE_HORA.search(texto)
        if not (m_f and m_h):
            return None
        try:
            fecha_iso = normalizar_fecha(m_f.group(1).strip())
            hora_hhmm = normalizar_hora(m_h.group(1).strip())
            return combinar_fecha_hora(fecha_iso, hora_hhmm)
        except ValueError:
            return None

    def parsear(self, id_correo: str, asunto: str, cuerpo: str) -> Optional[Transaccion]:
        asunto_l = asunto.lower()
        fecha_hora = self._extraer_fecha_hora(cuerpo)
        cuenta = (self.RE_CUENTA_ORIGEN.search(cuerpo) or [None, ""])[1] if self.RE_CUENTA_ORIGEN.search(cuerpo) else ""
        m_cuenta = self.RE_CUENTA_ORIGEN.search(cuerpo)
        cuenta = m_cuenta.group(1) if m_cuenta else ""

        # --- Envío con Bre-B ---
        if "bre-b exitoso" in asunto_l and "envío" in asunto_l or "envio" in asunto_l:
            if m := self.RE_DEST_BRE_B.search(cuerpo):
                beneficiario, monto_s = m.groups()
                m_llave = self.RE_LLAVE.search(cuerpo)
                m_id = self.RE_ID_TRANSACCION.search(cuerpo)
                return Transaccion(
                    id_correo=id_correo,
                    fecha_hora=fecha_hora or "",
                    banco=self.banco,
                    tipo="transferencia_enviada",
                    monto=normalizar_monto(monto_s),
                    direccion="salida",
                    cuenta=cuenta,
                    contraparte=beneficiario.strip(),
                    referencia=(m_llave.group(1) if m_llave else None) or (m_id.group(1) if m_id else None),
                    descripcion_raw=cuerpo[:500],
                )

        # --- Recibo por Bre-B ---
        if "recibiste plata por bre-b" in asunto_l:
            if m := self.RE_RECIBO_BRE_B.search(cuerpo):
                monto_s, remitente_p = m.groups()
                return Transaccion(
                    id_correo=id_correo,
                    fecha_hora=fecha_hora or "",
                    banco=self.banco,
                    tipo="transferencia_recibida",
                    monto=normalizar_monto(monto_s),
                    direccion="entrada",
                    cuenta=cuenta,
                    contraparte=remitente_p.strip(),
                    descripcion_raw=cuerpo[:500],
                )

        # --- Pago PSE exitoso ---
        if "pago pse exitoso" in asunto_l:
            if m := self.RE_PAGO_PSE.search(cuerpo):
                comercio, monto_s = m.groups()
                m_comp = self.RE_COMPROBANTE.search(cuerpo)
                return Transaccion(
                    id_correo=id_correo,
                    fecha_hora=fecha_hora or "",
                    banco=self.banco,
                    tipo="pago_pse",
                    monto=normalizar_monto(monto_s),
                    direccion="salida",
                    cuenta=cuenta,
                    contraparte=comercio.strip(),
                    referencia=m_comp.group(1) if m_comp else None,
                    descripcion_raw=cuerpo[:500],
                )

        return None
