"""Cálculo de saldos estimados para cuentas de depósito activas."""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, Optional

from .clasificacion import CuentaPropia
from .cuentas import coincide_identificador, es_descripcion_generica
from .modelo import Transaccion


TIPOS_CON_SALDO = {
    "cuenta",
    "cuenta_ahorros",
    "cuenta_corriente",
    "deposito",
    "deposito_electronico",
    "billetera",
    "efectivo",
}


@dataclass(frozen=True)
class SaldoInicial:
    cuenta: str
    fecha_corte: datetime
    saldo: float


@dataclass
class SaldoCalculado:
    cuenta: str
    nombre: str
    fecha_corte: str
    saldo_inicial: float
    entradas: float = 0.0
    salidas: float = 0.0
    movimientos: int = 0
    ultima_transaccion: str = ""

    @property
    def saldo_actual(self) -> float:
        return self.saldo_inicial + self.entradas - self.salidas


def es_cuenta_con_saldo(cuenta: CuentaPropia) -> bool:
    return (
        cuenta.activo
        and cuenta.tipo.strip().lower() in TIPOS_CON_SALDO
        and not es_descripcion_generica(cuenta.identificador)
    )


class CalculadorSaldos:
    """Calcula saldos desde un corte confirmado; excluye crédito y préstamos."""

    def __init__(
        self,
        cuentas: Iterable[CuentaPropia],
        saldos_iniciales: Iterable[SaldoInicial],
    ):
        self.cuentas = [cuenta for cuenta in cuentas if cuenta.activo]
        self.saldos_iniciales = {
            saldo.cuenta: saldo for saldo in saldos_iniciales
        }

    def calcular(
        self,
        transacciones: Iterable[Transaccion],
    ) -> tuple[list[SaldoCalculado], int]:
        resultados = self._crear_resultados()
        no_mapeados = 0

        for tx in transacciones:
            cuenta = self._cuenta_contable(tx.cuenta)
            if cuenta is None:
                if not self._es_credito(tx.cuenta):
                    no_mapeados += 1
                continue

            resultado = resultados.get(cuenta.identificador)
            if resultado is None:
                continue
            fecha = self._fecha(tx.fecha_hora)
            corte = self.saldos_iniciales[cuenta.identificador].fecha_corte
            if fecha is None or fecha < corte:
                continue

            monto = abs(float(tx.monto or 0))
            if self._es_entrada(tx):
                resultado.entradas += monto
            elif self._es_salida(tx):
                resultado.salidas += monto
            else:
                no_mapeados += 1
                continue

            resultado.movimientos += 1
            ultima_fecha = self._fecha(resultado.ultima_transaccion)
            if ultima_fecha is None or fecha > ultima_fecha:
                resultado.ultima_transaccion = tx.fecha_hora

        return list(resultados.values()), no_mapeados

    def cuentas_sin_saldo_inicial(self) -> list[CuentaPropia]:
        return [
            cuenta for cuenta in self.cuentas
            if es_cuenta_con_saldo(cuenta)
            and cuenta.identificador not in self.saldos_iniciales
        ]

    def _crear_resultados(self) -> dict[str, SaldoCalculado]:
        resultados = {}
        for cuenta in self.cuentas:
            inicial = self.saldos_iniciales.get(cuenta.identificador)
            if not es_cuenta_con_saldo(cuenta) or inicial is None:
                continue
            resultados[cuenta.identificador] = SaldoCalculado(
                cuenta=cuenta.identificador,
                nombre=cuenta.nombre or cuenta.identificador,
                fecha_corte=inicial.fecha_corte.isoformat(sep=" "),
                saldo_inicial=inicial.saldo,
            )
        return resultados

    def _cuenta_contable(self, identificador: str) -> Optional[CuentaPropia]:
        instrumento = next(
            (
                cuenta for cuenta in self.cuentas
                if coincide_identificador(identificador, cuenta.coincidencias())
            ),
            None,
        )
        if instrumento is None:
            return None
        if es_cuenta_con_saldo(instrumento):
            return instrumento
        if instrumento.tipo.lower() == "tarjeta_debito" and instrumento.cuenta_asociada:
            return next(
                (
                    cuenta for cuenta in self.cuentas
                    if cuenta.identificador == instrumento.cuenta_asociada
                    and es_cuenta_con_saldo(cuenta)
                ),
                None,
            )
        return None

    def _es_credito(self, identificador: str) -> bool:
        return any(
            cuenta.tipo.lower() == "tarjeta_credito"
            and coincide_identificador(identificador, cuenta.coincidencias())
            for cuenta in self.cuentas
        )

    @staticmethod
    def _fecha(valor: str) -> Optional[datetime]:
        texto = str(valor or "").strip().replace("Z", "+00:00")
        texto = re.sub(
            r"^(\d{4}-\d{2}-\d{2}[ T])(\d):",
            r"\g<1>0\2:",
            texto,
        )
        try:
            fecha = datetime.fromisoformat(texto)
        except (TypeError, ValueError):
            return None
        return fecha.replace(tzinfo=None)

    @staticmethod
    def _es_entrada(tx: Transaccion) -> bool:
        return tx.direccion == "entrada" or tx.tipo == "transferencia_recibida"

    @staticmethod
    def _es_salida(tx: Transaccion) -> bool:
        return tx.direccion == "salida" or tx.tipo in {
            "compra", "pago_qr", "pago_pse", "transferencia_enviada",
        }
