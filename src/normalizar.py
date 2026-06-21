"""Utilidades para normalizar montos, fechas y horas que vienen de los correos."""

import re
from datetime import datetime

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def normalizar_monto(s: str) -> float:
    """Convierte montos en distintos formatos a float.

    Maneja todos los formatos vistos en correos colombianos:
      '$49,000.00'   -> 49000.00   (formato US con coma de miles)
      '$7.500,00'    -> 7500.00    (formato CO con punto de miles)
      'COP43.700,00' -> 43700.00
      '$28,000'      -> 28000.00   (sin decimales, coma de miles)
      '$ 161.042'    -> 161042.00  (sin decimales, punto de miles)
      '$112'         -> 112.00
    """
    s = re.sub(r"[\$\s]|COP", "", s, flags=re.IGNORECASE)
    if not s:
        raise ValueError("Monto vacío")

    if "," not in s and "." not in s:
        return float(s)

    last_comma = s.rfind(",")
    last_dot = s.rfind(".")

    if last_comma == -1:
        # solo puntos: decide por cuántos dígitos van después del último punto
        if len(s) - last_dot - 1 == 2:
            return float(s)  # decimal US
        return float(s.replace(".", ""))  # miles CO

    if last_dot == -1:
        if len(s) - last_comma - 1 == 2:
            return float(s.replace(",", "."))  # decimal CO
        return float(s.replace(",", ""))  # miles US

    # Ambos presentes: el último es el decimal
    if last_comma > last_dot:
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(",", ""))


def normalizar_fecha(s: str) -> str:
    """Devuelve fecha ISO YYYY-MM-DD a partir de varios formatos."""
    s = s.strip()

    # DD/MM/YY o DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # "DD de mes de YYYY"  (formato Lulo)
    m = re.match(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", s, re.IGNORECASE)
    if m:
        d, mo_name, y = m.groups()
        mo = MESES.get(mo_name.lower())
        if mo:
            return f"{y}-{mo:02d}-{int(d):02d}"

    raise ValueError(f"Fecha no reconocida: {s!r}")


def normalizar_hora(s: str) -> str:
    """Devuelve hora HH:MM (24h) a partir de '17:09' o '3:44 a.m.'."""
    s = s.strip().lower().replace(".", "")

    m = re.match(r"(\d{1,2}):(\d{2})\s*(am|pm)", s)
    if m:
        h, mi, period = m.groups()
        h = int(h)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return f"{h:02d}:{int(mi):02d}"

    m = re.match(r"(\d{1,2}):(\d{2})", s)
    if m:
        h, mi = m.groups()
        return f"{int(h):02d}:{int(mi):02d}"

    raise ValueError(f"Hora no reconocida: {s!r}")


def combinar_fecha_hora(fecha_iso: str, hora_hhmm: str) -> str:
    """Devuelve un timestamp ISO 8601 a partir de YYYY-MM-DD y HH:MM."""
    dt = datetime.strptime(f"{fecha_iso} {hora_hhmm}", "%Y-%m-%d %H:%M")
    return dt.isoformat()
