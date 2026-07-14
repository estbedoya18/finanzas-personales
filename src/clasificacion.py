"""Reglas contables para cuentas propias, transferencias y categorías."""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, Optional

from .modelo import Transaccion


@dataclass(frozen=True)
class CuentaPropia:
    identificador: str
    banco: str = ""
    nombre: str = ""
    tipo: str = "cuenta"
    rol: str = "sin_definir"
    alias: str = ""
    llaves: str = ""
    activo: bool = True

    def coincidencias(self) -> set[str]:
        valores = [self.identificador, *self.alias.split("|"), *self.llaves.split("|")]
        return {_normalizar_identificador(valor) for valor in valores if valor.strip()}


@dataclass(frozen=True)
class ReglaCategoria:
    patron: str
    categoria: str
    subcategoria: str = ""
    naturaleza: str = ""
    campo: str = "texto"
    prioridad: int = 100
    activo: bool = True


def _normalizar_identificador(valor: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (valor or "").lower())


def _coincide(valor: str, cuenta: CuentaPropia) -> bool:
    candidato = _normalizar_identificador(valor)
    if not candidato:
        return False

    for conocido in cuenta.coincidencias():
        if conocido == candidato:
            return True
        # Permite comparar una cuenta completa del correo con el último bloque registrado.
        if conocido.isdigit() and len(conocido) >= 4 and candidato.endswith(conocido):
            return True
    return False


class ClasificadorFinanciero:
    """Aplica reglas explicables; no reemplaza categorías ingresadas manualmente."""

    VENTANA_TRANSFERENCIA_HORAS = 48

    def __init__(
        self,
        cuentas: Iterable[CuentaPropia],
        reglas: Iterable[ReglaCategoria],
    ):
        self.cuentas = [cuenta for cuenta in cuentas if cuenta.activo]
        self.reglas = sorted(
            (regla for regla in reglas if regla.activo and regla.patron),
            key=lambda regla: regla.prioridad,
        )

    def clasificar(self, transacciones: Iterable[Transaccion]) -> None:
        transacciones = list(transacciones)
        self._marcar_transferencias_explicitas(transacciones)
        self._emparejar_transferencias(transacciones)

        for transaccion in transacciones:
            if transaccion.naturaleza == "interno":
                continue
            self._respetar_clasificacion_manual(transaccion)
            if transaccion.clasificado_por == "manual":
                continue
            self._aplicar_reglas(transaccion)
            self._aplicar_valores_por_defecto(transaccion)

    def _marcar_transferencias_explicitas(self, transacciones: list[Transaccion]) -> None:
        for transaccion in transacciones:
            if transaccion.tipo != "transferencia_enviada":
                continue

            destino = self._buscar_cuenta_destino(transaccion)
            if destino is None:
                continue

            transaccion.asignar(
                naturaleza="interno",
                categoria="Transferencia interna",
                subcategoria=destino.nombre or destino.identificador,
                cuenta_destino=destino.identificador,
                transferencia_id=f"interna:{transaccion.id_correo}",
                clasificado_por="sistema",
                confianza_clasificacion="alta",
            )

    def _buscar_cuenta_destino(self, transaccion: Transaccion) -> Optional[CuentaPropia]:
        for cuenta in self.cuentas:
            if cuenta.identificador == transaccion.cuenta:
                continue
            if _coincide(transaccion.referencia or "", cuenta):
                return cuenta
            if _coincide(transaccion.contraparte, cuenta):
                return cuenta
        return None

    def _emparejar_transferencias(self, transacciones: list[Transaccion]) -> None:
        salidas = [
            tx for tx in transacciones
            if tx.tipo == "transferencia_enviada" and tx.naturaleza == "interno"
        ]
        entradas = [
            tx for tx in transacciones
            if tx.tipo == "transferencia_recibida" and tx.naturaleza != "interno"
        ]

        for salida in salidas:
            for entrada in entradas:
                if entrada.cuenta != salida.cuenta_destino:
                    continue
                if abs(entrada.monto - salida.monto) > 0.01:
                    continue
                if not self._estan_cerca_en_tiempo(salida.fecha_hora, entrada.fecha_hora):
                    continue

                identificador = f"interna:{salida.id_correo}:{entrada.id_correo}"
                salida.asignar(transferencia_id=identificador)
                entrada.asignar(
                    naturaleza="interno",
                    categoria="Transferencia interna",
                    subcategoria=self._nombre_cuenta(salida.cuenta),
                    cuenta_destino=salida.cuenta,
                    transferencia_id=identificador,
                    clasificado_por="sistema",
                    confianza_clasificacion="alta",
                )
                break

    def _nombre_cuenta(self, identificador: str) -> str:
        for cuenta in self.cuentas:
            if cuenta.identificador == identificador:
                return cuenta.nombre or identificador
        return identificador

    def _estan_cerca_en_tiempo(self, primera: str, segunda: str) -> bool:
        try:
            fecha_primera = datetime.fromisoformat(primera)
            fecha_segunda = datetime.fromisoformat(segunda)
        except (TypeError, ValueError):
            return True
        diferencia_horas = abs((fecha_primera - fecha_segunda).total_seconds()) / 3600
        return diferencia_horas <= self.VENTANA_TRANSFERENCIA_HORAS

    def _respetar_clasificacion_manual(self, transaccion: Transaccion) -> None:
        if transaccion.categoria and not transaccion.clasificado_por:
            transaccion.asignar(clasificado_por="manual", confianza_clasificacion="manual")

    def _aplicar_reglas(self, transaccion: Transaccion) -> None:
        for regla in self.reglas:
            texto = self._valor_regla(regla.campo, transaccion)
            if not texto or not self._patron_coincide(regla.patron, texto):
                continue

            transaccion.asignar(
                categoria=regla.categoria,
                subcategoria=regla.subcategoria,
                naturaleza=regla.naturaleza or transaccion.naturaleza,
                clasificado_por="regla",
                confianza_clasificacion="alta",
            )
            return

    def _valor_regla(self, campo: str, transaccion: Transaccion) -> str:
        valores = {
            "contraparte": transaccion.contraparte,
            "referencia": transaccion.referencia or "",
            "descripcion_raw": transaccion.descripcion_raw,
        }
        if campo in valores:
            return valores[campo]
        return " ".join(valores.values())

    def _patron_coincide(self, patron: str, texto: str) -> bool:
        try:
            return bool(re.search(patron, texto, re.IGNORECASE))
        except re.error:
            return patron.lower() in texto.lower()

    def _aplicar_valores_por_defecto(self, transaccion: Transaccion) -> None:
        naturaleza = transaccion.naturaleza
        if not naturaleza:
            naturaleza = {
                "compra": "gasto",
                "pago_qr": "gasto",
                "pago_pse": "gasto",
                "transferencia_enviada": "gasto",
                "transferencia_recibida": "ingreso",
            }.get(transaccion.tipo, "pendiente")
            transaccion.asignar(naturaleza=naturaleza)

        if transaccion.categoria:
            return

        categoria = {
            "gasto": "Sin clasificar",
            "ingreso": "Otros ingresos",
            "pendiente": "Pendiente de revisar",
        }.get(naturaleza, "Sin clasificar")
        transaccion.asignar(
            categoria=categoria,
            clasificado_por="sistema",
            confianza_clasificacion="pendiente",
        )
