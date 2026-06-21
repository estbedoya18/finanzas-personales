"""Tests del normalizador de montos, fechas y horas."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.normalizar import normalizar_monto, normalizar_fecha, normalizar_hora


def test_montos():
    casos = [
        ("$49,000.00", 49000.0),     # formato US
        ("$7.500,00", 7500.0),       # formato CO
        ("$25,000.00", 25000.0),
        ("COP43.700,00", 43700.0),
        ("$28,000", 28000.0),        # coma de miles, sin decimales
        ("$ 161.042", 161042.0),     # punto de miles, sin decimales
        ("$112", 112.0),
        ("$1.234.567,89", 1234567.89),  # múltiples puntos de miles + decimal
        ("$1,234,567.89", 1234567.89),  # múltiples comas de miles + decimal US
    ]
    for entrada, esperado in casos:
        resultado = normalizar_monto(entrada)
        assert resultado == esperado, f"normalizar_monto({entrada!r}) = {resultado}, esperaba {esperado}"
    print(f"✓ {len(casos)} montos normalizados")


def test_fechas():
    casos = [
        ("09/06/2026", "2026-06-09"),
        ("09/06/26", "2026-06-09"),
        ("1/1/2026", "2026-01-01"),
        ("20 de junio de 2026", "2026-06-20"),
    ]
    for entrada, esperado in casos:
        resultado = normalizar_fecha(entrada)
        assert resultado == esperado, f"normalizar_fecha({entrada!r}) = {resultado}, esperaba {esperado}"
    print(f"✓ {len(casos)} fechas normalizadas")


def test_horas():
    casos = [
        ("17:09", "17:09"),
        ("08:33", "08:33"),
        ("3:44 a.m.", "03:44"),
        ("3:44 p.m.", "15:44"),
        ("12:00 a.m.", "00:00"),
        ("12:00 p.m.", "12:00"),
    ]
    for entrada, esperado in casos:
        resultado = normalizar_hora(entrada)
        assert resultado == esperado, f"normalizar_hora({entrada!r}) = {resultado}, esperaba {esperado}"
    print(f"✓ {len(casos)} horas normalizadas")


if __name__ == "__main__":
    test_montos()
    test_fechas()
    test_horas()
    print("\n✅ Todos los tests de normalizar pasaron")
