"""Pruebas de formatos admitidos en saldos iniciales."""

from src.saldos_sheets import SaldosSheets, ZONA_HORARIA


def test_lee_montos_colombianos():
    assert SaldosSheets._monto("1.234.567") == 1_234_567
    assert SaldosSheets._monto("$ 1.234.567,50") == 1_234_567.50
    assert SaldosSheets._monto(250000) == 250000


def test_lee_fechas_comunes_de_google_sheets():
    assert SaldosSheets._fecha("13/07/2026").isoformat() == "2026-07-13T00:00:00"
    assert SaldosSheets._fecha("2026-07-13 08:30").isoformat() == "2026-07-13T08:30:00"


def test_usa_zona_horaria_de_colombia():
    assert ZONA_HORARIA.key == "America/Bogota"
