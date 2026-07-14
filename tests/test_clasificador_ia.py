"""Pruebas de clasificación con IA sin realizar llamadas externas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clasificacion import ClasificadorFinanciero
from src.clasificador_ia import ResultadoClasificacionIA
from src.modelo import Transaccion


class IADePrueba:
    def __init__(self, resultado):
        self.resultado = resultado
        self.llamadas = 0

    def clasificar(self, transaccion):
        self.llamadas += 1
        return self.resultado


def _compra(comercio="COMERCIO") -> Transaccion:
    return Transaccion(
        id_correo="correo-ia",
        fecha_hora="2026-07-01T12:00:00",
        banco="Bancolombia",
        tipo="compra",
        monto=30000.0,
        direccion="salida",
        cuenta="2913",
        contraparte=comercio,
        descripcion_raw=f"Compra en {comercio}",
    )


def test_ia_aplica_clasificacion_de_alta_confianza():
    ia = IADePrueba(ResultadoClasificacionIA(
        categoria="Suscripciones",
        subcategoria="Streaming",
        confianza="alta",
        requiere_revision=False,
        explicacion="Comercio de streaming.",
    ))
    compra = _compra("NETFLIX")

    ClasificadorFinanciero([], [], clasificador_ia=ia).clasificar([compra], {"correo-ia"})

    assert compra.categoria == "Suscripciones"
    assert compra.subcategoria == "Streaming"
    assert compra.estado_revision == "resuelto"
    assert compra.clasificado_por == "ia"
    assert ia.llamadas == 1
    print("✓ clasificación IA de alta confianza")


def test_ia_ambigua_va_a_revision():
    ia = IADePrueba(ResultadoClasificacionIA(
        categoria="Compras personales",
        subcategoria="Hogar",
        confianza="baja",
        requiere_revision=True,
        explicacion="El comercio no permite saber qué se compró.",
    ))
    compra = _compra("TIENDA ABC")

    ClasificadorFinanciero([], [], clasificador_ia=ia).clasificar([compra], {"correo-ia"})

    assert compra.categoria == "Pendiente de revisar"
    assert compra.categoria_sugerida == "Compras personales"
    assert compra.estado_revision == "pendiente"
    assert compra.explicacion_clasificacion
    print("✓ clasificación IA pendiente de revisión")


if __name__ == "__main__":
    test_ia_aplica_clasificacion_de_alta_confianza()
    test_ia_ambigua_va_a_revision()
    print("\n✅ Todos los tests de IA pasaron")
