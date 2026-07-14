# Base contable

El proceso conserva la hoja `transacciones` e incorpora seis columnas nuevas:

```
naturaleza | subcategoria | cuenta_destino | transferencia_id |
clasificado_por | confianza_clasificacion
```

Al ejecutar el flujo se crean automáticamente estas hojas:

- **cuentas_propias**: instrumentos detectados en `transacciones`. Completa `alias` o `llaves` con valores separados por `|` para reconocer destinos propios que el correo no identifica por terminación de cuenta.
- **reglas_categorias**: reglas de clasificación. Cada regla usa un patrón de texto (admite expresiones regulares), el campo donde debe buscarlo, categoría, subcategoría, naturaleza, prioridad y si está activa.

## Naturalezas

- `ingreso`: dinero que entra desde una contraparte externa.
- `gasto`: consumo o pago hacia una contraparte externa.
- `interno`: movimiento entre instrumentos propios. No participa en los totales de ingreso o gasto.
- `pendiente`: movimiento aún no clasificable.

## Transferencias internas

Una salida se marca como interna cuando la referencia o contraparte coincide con una cuenta, alias o llave de `cuentas_propias`. Si existe una entrada del mismo valor en la cuenta destino hasta 48 horas después, ambas filas reciben el mismo `transferencia_id`.

Las filas con una categoría existente antes de esta actualización se preservan como `clasificado_por = manual`; las reglas automáticas no las sobrescriben.
