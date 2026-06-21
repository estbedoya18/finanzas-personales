"""Registro de parsers activos. El orquestador itera por esta lista."""

from .bancolombia import BancolombiaParser
from .lulo import LuloParser
from .nu import NuParser
from .nequi import NequiParser

PARSERS = [
    BancolombiaParser(),
    LuloParser(),
    NuParser(),
    NequiParser(),
]
