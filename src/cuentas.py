"""Utilidades para reconocer cuentas propias, alias y llaves Bre-B."""

import re
import unicodedata
from typing import Iterable


_SEPARADOR = re.compile(r"[|,;\n]+")
_DESCRIPCIONES_GENERICAS = {
    "ahorro",
    "ahorros",
    "cuenta",
    "cuentaahorros",
    "cuentacorriente",
    "corriente",
    "deposito",
    "tarjeta",
}


def normalizar_identificador(valor: str) -> str:
    """Normaliza números, correos, celulares y llaves alfanuméricas."""
    texto = unicodedata.normalize("NFKD", valor or "")
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", texto)


def separar_identificadores(valor: str) -> list[str]:
    """Permite registrar varias llaves o alias con |, coma, punto y coma o salto de línea."""
    return [parte.strip() for parte in _SEPARADOR.split(valor or "") if parte.strip()]


def es_descripcion_generica(valor: str) -> bool:
    return normalizar_identificador(valor) in _DESCRIPCIONES_GENERICAS


def es_identificador_detectable(valor: str) -> bool:
    """Evita crear cuentas automáticas desde textos genéricos como 'Ahorros'."""
    normalizado = normalizar_identificador(valor)
    if not normalizado or es_descripcion_generica(valor):
        return False
    return bool(re.search(r"\d{4,}", normalizado))


def coincide_identificador(valor: str, conocidos: Iterable[str]) -> bool:
    """Busca una cuenta o llave aunque venga incluida dentro del texto bancario."""
    candidato = normalizar_identificador(valor)
    if not candidato:
        return False
    for conocido in conocidos:
        normalizado = normalizar_identificador(conocido)
        if not normalizado:
            continue
        if candidato == normalizado:
            return True
        es_numero = normalizado.isdigit() and len(normalizado) >= 4
        es_llave_explicita = len(normalizado) >= 6 and (
            "@" in conocido or "*" in conocido
        )
        if (es_numero or es_llave_explicita) and normalizado in candidato:
            return True
    return False
