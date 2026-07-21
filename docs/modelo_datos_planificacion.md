# Modelo de datos para planificación y canales

Este documento define las hojas que soportan presupuesto, metas, movimientos manuales, sesiones de Telegram y trazabilidad de notificaciones.

## presupuestos

| Columna | Uso |
|---|---|
| id_presupuesto | Identificador único. |
| periodo | Mes en formato `YYYY-MM`. |
| categoria | Categoría presupuestada. |
| monto_presupuestado | Límite mensual en COP. |
| activo | `SI` o `NO`. |
| creado_en | Fecha de creación. |
| actualizado_en | Última modificación. |

## metas_ahorro

| Columna | Uso |
|---|---|
| id_meta | Identificador único. |
| nombre | Nombre visible de la meta. |
| tipo | Emergencia, inversión, liquidez, hogar, vivienda u otro. |
| monto_objetivo | Valor objetivo. |
| fecha_objetivo | Fecha opcional. |
| cuenta_asociada | Cuenta de referencia opcional. |
| activo | `SI` o `NO`. |
| creado_en | Fecha de creación. |
| actualizado_en | Última modificación. |

## movimientos_metas

| Columna | Uso |
|---|---|
| id_movimiento | Identificador único. |
| fecha_hora | Fecha del aporte, retiro o ajuste. |
| id_meta | Meta relacionada. |
| tipo_movimiento | `aporte`, `retiro` o `ajuste`. |
| monto | Valor absoluto en COP. |
| descripcion | Nota opcional. |
| origen | Dashboard, Telegram o ajuste. |
| creado_en | Fecha de registro. |

## movimientos_manuales

| Columna | Uso |
|---|---|
| id_movimiento | Identificador único. |
| fecha_hora | Fecha real del movimiento. |
| tipo | `gasto_efectivo`, `ingreso_efectivo`, `retiro_efectivo` o `ajuste`. |
| monto | Valor absoluto. |
| direccion | `entrada` o `salida`; aplica principalmente a ajustes. |
| cuenta | Cuenta origen o cuenta afectada. |
| cuenta_destino | Cuenta destino; para retiro debe ser `EFECTIVO`. |
| categoria | Categoría financiera. |
| subcategoria | Detalle opcional de clasificación. |
| contraparte | Comercio, persona o concepto. |
| descripcion | Nota del usuario. |
| origen | Telegram, dashboard, manual o ajuste. |
| estado | Borrador, confirmado, aprobado, procesar, cancelado. |
| creado_en | Fecha de creación. |
| procesado_en | Fecha en que Python lo incorporó a `transacciones`. |

## telegram_sesiones

| Columna | Uso |
|---|---|
| chat_id | Conversación de Telegram. |
| flujo | Registro de efectivo o resolución de pendiente. |
| paso | Paso actual de la plantilla. |
| datos_temporales | JSON con datos aún no confirmados. |
| actualizado_en | Última interacción. |

## notificaciones_log

| Columna | Uso |
|---|---|
| id_notificacion | Identificador único. |
| fecha_hora | Momento del intento. |
| tipo | Recordatorio diario, resumen semanal, ambigüedad, etc. |
| canal | Telegram o correo. |
| estado | Enviado o error. |
| detalle | Respuesta o descripción del fallo. |

## Reglas contables

- El presupuesto se define únicamente por categoría y periodo.
- Las transferencias internas no consumen presupuesto.
- Un retiro hacia efectivo genera una salida bancaria y una entrada a `EFECTIVO`, ambas con naturaleza `interno`.
- Una compra en efectivo es un gasto desde la cuenta `EFECTIVO`.
- Los aportes a metas no alteran por sí mismos el saldo bancario; son asignaciones conceptuales hasta que exista un movimiento financiero real.
