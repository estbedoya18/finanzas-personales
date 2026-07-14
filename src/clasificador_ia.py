"""Clasificación de movimientos con OpenAI dentro del catálogo permitido."""

from dataclasses import dataclass
import json
import os
from typing import Optional

from .categorias import catalogo_para_prompt, es_clasificacion_valida
from .modelo import Transaccion

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass(frozen=True)
class ResultadoClasificacionIA:
    categoria: str
    subcategoria: str
    confianza: str
    requiere_revision: bool
    explicacion: str


class ClasificadorIA:
    """Pide una clasificación estructurada; nunca recibe correos completos ni identificadores de cuenta."""

    MODELO_POR_DEFECTO = "gpt-5.6"

    def __init__(self, cliente=None, modelo: Optional[str] = None):
        api_key = os.getenv("OPENAI_API_KEY")
        self.modelo = modelo or os.getenv("OPENAI_MODEL") or self.MODELO_POR_DEFECTO
        self.cliente = cliente
        if self.cliente is None and api_key and OpenAI is not None:
            self.cliente = OpenAI(api_key=api_key)

    @property
    def disponible(self) -> bool:
        return self.cliente is not None

    def clasificar(self, transaccion: Transaccion) -> Optional[ResultadoClasificacionIA]:
        if not self.disponible:
            return None

        respuesta = self.cliente.responses.create(
            model=self.modelo,
            input=[
                {"role": "system", "content": self._instrucciones()},
                {
                    "role": "user",
                    "content": json.dumps(self._movimiento_minimo(transaccion), ensure_ascii=False),
                },
            ],
            text={"format": self._schema_respuesta()},
        )

        try:
            datos = json.loads(respuesta.output_text)
            resultado = ResultadoClasificacionIA(
                categoria=datos["categoria"],
                subcategoria=datos["subcategoria"],
                confianza=datos["confianza"],
                requiere_revision=datos["requiere_revision"],
                explicacion=datos["explicacion"],
            )
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError):
            return None

        if not es_clasificacion_valida(resultado.categoria, resultado.subcategoria):
            return None
        return resultado

    def _instrucciones(self) -> str:
        return f"""Clasificas movimientos de finanzas personales de Colombia.
Elige exclusivamente una categoría y subcategoría del siguiente catálogo:
{catalogo_para_prompt()}

Reglas obligatorias:
- ICETEX es Obligaciones financieras / Crédito educativo.
- ADDI es Obligaciones financieras / Compra financiada.
- Educación se usa para pagos educativos directos, no para cuotas de crédito.
- No inventes categorías ni subcategorías.
- Marca requiere_revision=true si el comercio es ambiguo o no hay evidencia suficiente.
- Explica brevemente la decisión en español.
"""

    @staticmethod
    def _movimiento_minimo(transaccion: Transaccion) -> dict:
        return {
            "tipo": transaccion.tipo,
            "direccion": transaccion.direccion,
            "monto_cop": transaccion.monto,
            "comercio_o_contraparte": transaccion.contraparte,
            "medio_pago": transaccion.referencia or "",
        }

    @staticmethod
    def _schema_respuesta() -> dict:
        return {
            "type": "json_schema",
            "name": "clasificacion_financiera",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "categoria": {"type": "string"},
                    "subcategoria": {"type": "string"},
                    "confianza": {"type": "string", "enum": ["alta", "media", "baja"]},
                    "requiere_revision": {"type": "boolean"},
                    "explicacion": {"type": "string"},
                },
                "required": [
                    "categoria", "subcategoria", "confianza", "requiere_revision", "explicacion",
                ],
                "additionalProperties": False,
            },
        }
