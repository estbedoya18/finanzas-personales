"""Reglas contables, transferencias internas y clasificación con IA."""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, Optional

from .cuentas import coincide_identificador, separar_identificadores
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
    cuenta_asociada: str = ""
    moneda: str = "COP"

    def coincidencias(self) -> set[str]:
        valores = [
            self.identificador,
            *separar_identificadores(self.alias),
            *separar_identificadores(self.llaves),
        ]
        return {valor for valor in valores if valor.strip()}


@dataclass(frozen=True)
class ReglaCategoria:
    patron: str
    categoria: str
    subcategoria: str = ""
    naturaleza: str = ""
    campo: str = "texto"
    prioridad: int = 100
    activo: bool = True


def _coincide(valor: str, cuenta: CuentaPropia) -> bool:
    return coincide_identificador(valor, cuenta.coincidencias())


class ClasificadorFinanciero:
    """Aplica reglas estructurales y usa IA solo para categoría y subcategoría."""

    VENTANA_TRANSFERENCIA_HORAS = 48

    def __init__(
        self,
        cuentas: Iterable[CuentaPropia],
        reglas: Iterable[ReglaCategoria],
        clasificador_ia=None,
    ):
        self.cuentas = [cuenta for cuenta in cuentas if cuenta.activo]
        self.reglas = sorted(
            (regla for regla in reglas if regla.activo and regla.patron),
            key=lambda regla: regla.prioridad,
        )
        self.clasificador_ia = clasificador_ia

    def clasificar(
        self,
        transacciones: Iterable[Transaccion],
        ids_permitidos_ia: Optional[set[str]] = None,
    ) -> None:
        transacciones = list(transacciones)
        self._marcar_transferencias_explicitas(transacciones)
        self._emparejar_transferencias(transacciones)

        for transaccion in transacciones:
            if transaccion.naturaleza == "interno":
                continue

            self._asignar_naturaleza_base(transaccion)
            self._normalizar_clasificacion_heredada(transaccion)
            if self._aplicar_reglas_estructurales(transaccion):
                continue
            if self._es_clasificacion_manual(transaccion):
                continue
            if transaccion.estado_revision == "pendiente" and (
                ids_permitidos_ia is None or transaccion.id_correo not in ids_permitidos_ia
            ):
                continue
            if self._aplicar_reglas(transaccion):
                continue
            if self._puede_usar_ia(transaccion, ids_permitidos_ia) and self._aplicar_ia(transaccion):
                continue
            self._aplicar_valores_por_defecto(transaccion)

    def _marcar_transferencias_explicitas(self, transacciones: list[Transaccion]) -> None:
        for tx in transacciones:
            if tx.tipo not in {"transferencia_enviada", "transferencia_recibida"}:
                continue
            contraparte = self._buscar_cuenta_en_contraparte(tx)
            if contraparte is None:
                continue

            if tx.tipo == "transferencia_enviada":
                cuenta_destino = contraparte.identificador
                subcategoria = contraparte.nombre or contraparte.identificador
            else:
                destino = self._cuenta_del_movimiento(tx)
                cuenta_destino = destino.identificador if destino else tx.cuenta
                subcategoria = f"Desde {contraparte.nombre or contraparte.identificador}"

            tx.asignar(
                naturaleza="interno",
                categoria="Transferencia interna",
                subcategoria=subcategoria,
                cuenta_destino=cuenta_destino,
                transferencia_id=f"interna:{tx.id_correo}",
                clasificado_por="sistema",
                confianza_clasificacion="alta",
                estado_revision="resuelto",
            )

    def _cuenta_del_movimiento(self, tx: Transaccion) -> Optional[CuentaPropia]:
        return next(
            (cuenta for cuenta in self.cuentas if _coincide(tx.cuenta, cuenta)),
            None,
        )

    def _buscar_cuenta_en_contraparte(self, tx: Transaccion) -> Optional[CuentaPropia]:
        cuenta_movimiento = self._cuenta_del_movimiento(tx)
        for cuenta in self.cuentas:
            if cuenta_movimiento and cuenta.identificador == cuenta_movimiento.identificador:
                continue
            if _coincide(tx.referencia or "", cuenta) or _coincide(tx.contraparte, cuenta):
                return cuenta
        return None

    def _emparejar_transferencias(self, transacciones: list[Transaccion]) -> None:
        salidas = [
            tx for tx in transacciones
            if tx.tipo == "transferencia_enviada" and tx.naturaleza == "interno"
        ]
        entradas = [tx for tx in transacciones if tx.tipo == "transferencia_recibida"]

        for salida in salidas:
            for entrada in entradas:
                if entrada.cuenta != salida.cuenta_destino or abs(entrada.monto - salida.monto) > 0.01:
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
                    estado_revision="resuelto",
                )
                break

    def _nombre_cuenta(self, identificador: str) -> str:
        return next(
            (cuenta.nombre or identificador for cuenta in self.cuentas if cuenta.identificador == identificador),
            identificador,
        )

    def _estan_cerca_en_tiempo(self, primera: str, segunda: str) -> bool:
        try:
            diferencia = abs(
                (datetime.fromisoformat(primera) - datetime.fromisoformat(segunda)).total_seconds()
            )
        except (TypeError, ValueError):
            return True
        return diferencia / 3600 <= self.VENTANA_TRANSFERENCIA_HORAS

    @staticmethod
    def _aplicar_reglas_estructurales(tx: Transaccion) -> bool:
        referencia = (tx.referencia or "").strip().lower()
        if tx.naturaleza == "ingreso" and ("nómina" in referencia or "nomina" in referencia):
            tx.asignar(
                categoria="Ingresos",
                subcategoria="Nómina",
                clasificado_por="regla",
                confianza_clasificacion="alta",
                estado_revision="resuelto",
                categoria_sugerida=None,
                subcategoria_sugerida=None,
            )
            return True
        return False

    @staticmethod
    def _normalizar_clasificacion_heredada(tx: Transaccion) -> None:
        if tx.categoria == "Salario":
            tx.asignar(
                categoria="Ingresos",
                subcategoria="Nómina",
                clasificado_por="regla",
                confianza_clasificacion="alta",
                estado_revision="resuelto",
            )

    @staticmethod
    def _es_clasificacion_manual(tx: Transaccion) -> bool:
        if tx.clasificado_por in {"ia", "regla", "sistema"}:
            return False
        if tx.categoria and tx.categoria not in {"Sin clasificar", "Pendiente de revisar"}:
            tx.asignar(
                clasificado_por="manual",
                confianza_clasificacion="manual",
                estado_revision="resuelto",
                categoria_sugerida=None,
                subcategoria_sugerida=None,
            )
            return True
        return tx.clasificado_por == "manual"

    def _aplicar_reglas(self, tx: Transaccion) -> bool:
        for regla in self.reglas:
            texto = self._valor_regla(regla.campo, tx)
            if not texto or not self._patron_coincide(regla.patron, texto):
                continue

            naturaleza = tx.naturaleza or self._naturaleza_base(tx)
            if naturaleza == "pendiente" and regla.naturaleza in {"ingreso", "gasto"}:
                naturaleza = regla.naturaleza

            tx.asignar(
                categoria=regla.categoria,
                subcategoria=regla.subcategoria,
                naturaleza=naturaleza,
                clasificado_por="regla",
                confianza_clasificacion="alta",
                estado_revision="resuelto",
            )
            return True
        return False

    @staticmethod
    def _valor_regla(campo: str, tx: Transaccion) -> str:
        valores = {
            "contraparte": tx.contraparte,
            "referencia": tx.referencia or "",
            "descripcion_raw": tx.descripcion_raw,
        }
        return valores.get(campo, " ".join(valores.values()))

    @staticmethod
    def _patron_coincide(patron: str, texto: str) -> bool:
        try:
            return bool(re.search(patron, texto, re.IGNORECASE))
        except re.error:
            return patron.lower() in texto.lower()

    def _puede_usar_ia(self, tx: Transaccion, ids_permitidos_ia: Optional[set[str]]) -> bool:
        return self.clasificador_ia is not None and (
            ids_permitidos_ia is None or tx.id_correo in ids_permitidos_ia
        )

    def _aplicar_ia(self, tx: Transaccion) -> bool:
        resultado = self.clasificador_ia.clasificar(tx)
        if resultado is None:
            return False

        if resultado.requiere_revision or resultado.confianza != "alta":
            tx.asignar(
                categoria="Pendiente de revisar",
                subcategoria=None,
                clasificado_por="ia",
                confianza_clasificacion=resultado.confianza,
                estado_revision="pendiente",
                categoria_sugerida=resultado.categoria,
                subcategoria_sugerida=resultado.subcategoria,
                explicacion_clasificacion=resultado.explicacion,
            )
            return True

        tx.asignar(
            categoria=resultado.categoria,
            subcategoria=resultado.subcategoria,
            clasificado_por="ia",
            confianza_clasificacion=resultado.confianza,
            estado_revision="resuelto",
            explicacion_clasificacion=resultado.explicacion,
        )
        return True

    def _asignar_naturaleza_base(self, tx: Transaccion) -> None:
        tx.asignar(naturaleza=self._naturaleza_base(tx))

    @staticmethod
    def _naturaleza_base(tx: Transaccion) -> str:
        if tx.direccion == "entrada":
            return "ingreso"
        if tx.direccion == "salida":
            return "gasto"
        return {
            "compra": "gasto",
            "pago_qr": "gasto",
            "pago_pse": "gasto",
            "transferencia_enviada": "gasto",
            "transferencia_recibida": "ingreso",
        }.get(tx.tipo, "pendiente")

    def _aplicar_valores_por_defecto(self, tx: Transaccion) -> None:
        if tx.categoria:
            return
        if tx.naturaleza == "ingreso":
            tx.asignar(
                categoria="Ingresos",
                subcategoria="Otros ingresos",
                clasificado_por="sistema",
                confianza_clasificacion="sin_ia",
                estado_revision="sin_ia",
            )
            return
        tx.asignar(
            categoria="Sin clasificar",
            clasificado_por="sistema",
            confianza_clasificacion="sin_ia",
            estado_revision="sin_ia",
        )
