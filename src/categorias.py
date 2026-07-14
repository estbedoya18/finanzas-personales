"""Catálogo cerrado de categorías disponibles para la clasificación automática."""

import json


CATALOGO_CATEGORIAS = {
    "Alimentación": ["Mercado", "Restaurantes", "Domicilios", "Café"],
    "Transporte": ["Movilidad por app", "Combustible", "Transporte público", "Parqueadero y peajes"],
    "Vivienda y servicios": ["Arriendo", "Servicios públicos", "Internet y telefonía", "Mantenimiento"],
    "Salud": ["Farmacia", "Consultas", "Seguros de salud"],
    "Educación": ["Matrícula", "Cursos", "Materiales educativos"],
    "Suscripciones": ["Streaming", "Software", "Membresías"],
    "Ocio": ["Entretenimiento", "Salidas", "Viajes"],
    "Compras personales": ["Vestuario", "Tecnología", "Hogar", "Cuidado personal"],
    "Mascotas": ["Alimento", "Veterinaria", "Accesorios"],
    "Obligaciones financieras": [
        "Tarjeta de crédito", "Crédito educativo", "Compra financiada", "Otros créditos",
    ],
    "Comisiones e impuestos": ["Comisiones bancarias", "GMF", "Impuestos"],
    "Otros gastos": ["Donaciones", "Otros"],
    "Ingresos": ["Nómina", "Reembolso", "Rendimientos", "Otros ingresos"],
}


def subcategorias_validas(categoria: str) -> list[str]:
    return CATALOGO_CATEGORIAS.get(categoria, [])


def es_clasificacion_valida(categoria: str, subcategoria: str) -> bool:
    return subcategoria in subcategorias_validas(categoria)


def filas_catalogo() -> list[list[str]]:
    filas = []
    for categoria, subcategorias in CATALOGO_CATEGORIAS.items():
        naturaleza = "ingreso" if categoria == "Ingresos" else "gasto"
        for subcategoria in subcategorias:
            filas.append([categoria, subcategoria, naturaleza, "SI"])
    return filas


def catalogo_para_prompt() -> str:
    return json.dumps(CATALOGO_CATEGORIAS, ensure_ascii=False)
