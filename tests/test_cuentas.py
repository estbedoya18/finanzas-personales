"""Pruebas de reconocimiento de cuentas y llaves Bre-B."""

from src.cuentas import (
    coincide_identificador,
    es_identificador_detectable,
    separar_identificadores,
)


def test_no_detecta_descripciones_genericas_como_cuentas():
    assert not es_identificador_detectable("Ahorros")
    assert not es_identificador_detectable("Cuenta corriente")
    assert es_identificador_detectable("Cuenta *8401")


def test_separa_varias_llaves_bre_b():
    llaves = separar_identificadores(
        "usuario@correo.com | +57 300 123 4567; @lulo-abcd"
    )
    assert llaves == [
        "usuario@correo.com",
        "+57 300 123 4567",
        "@lulo-abcd",
    ]


def test_reconoce_llave_dentro_del_texto_bancario():
    conocidos = ["usuario@correo.com", "@lulo-abcd"]
    assert coincide_identificador(
        "Transferencia Bre-B enviada a la llave @lulo-abcd",
        conocidos,
    )
    assert not coincide_identificador(
        "Transferencia recibida desde Lulo Bank",
        ["Lulo"],
    )
