# Base contable y clasificación con IA

El proceso conserva la hoja `transacciones` y agrega columnas de trazabilidad:

```
naturaleza | subcategoria | cuenta_destino | transferencia_id |
clasificado_por | confianza_clasificacion | estado_revision |
categoria_sugerida | subcategoria_sugerida | explicacion_clasificacion
```

Al ejecutar el workflow se crean automáticamente, dentro del mismo Google Sheets:

- **cuentas_propias**: instrumentos detectados en el historial.
- **catalogo_categorias**: categorías y subcategorías permitidas por la IA.
- **reglas_categorias**: memoria de correcciones manuales; no necesitas llenarla comercio por comercio.
- **pendientes_revision**: movimientos cuya clasificación requiere confirmación.


## Cuentas propias y llaves Bre-B

La hoja `cuentas_propias` usa una fila por cuenta o producto financiero real. Una misma cuenta puede tener varias llaves Bre-B: se escriben en la columna `llaves` separadas por `|`. También pueden usarse coma, punto y coma o salto de línea.

Ejemplo conceptual:

```
7353 | Lulo Bank | Lulo ahorro | cuenta | ahorro | Lulo | llave-1|llave-2 | SI
```

Las llaves pueden ser celular, correo, documento o identificador alfanumérico. El motor las reconoce incluso cuando aparecen dentro de una frase del correo. Las transferencias enviadas o recibidas que relacionen dos cuentas propias se clasifican como `interno`.

La detección automática solo crea instrumentos cuando encuentra un identificador con al menos cuatro dígitos. Descripciones genéricas como `Ahorros`, `Cuenta` o `Corriente` no se consideran cuentas. Las filas genéricas creadas por versiones anteriores deben eliminarse o marcarse con `activo = NO`.

## Clasificación

La IA recibe solo tipo, monto, comercio o contraparte y medio de pago; nunca recibe el correo completo, credenciales ni números de cuenta.

El catálogo inicial incluye Alimentación, Transporte, Vivienda y servicios, Salud, Educación, Suscripciones, Ocio, Compras personales, Mascotas, Obligaciones financieras, Comisiones e impuestos, Otros gastos e Ingresos.

Reglas relevantes:

- ICETEX → **Obligaciones financieras / Crédito educativo**.
- ADDI → **Obligaciones financieras / Compra financiada**.
- Una tarjeta de crédito se trata como obligación; las compras ya registradas no se duplican al pagarla.
- Las transferencias entre cuentas propias se marcan como `interno` y no entran en ingresos o gastos.

La IA devuelve una respuesta estructurada. Si la confianza no es alta o el comercio es ambiguo, la transacción queda como `Pendiente de revisar`, conservando la categoría sugerida.

## Configuración opcional

Agrega estos secretos en GitHub Actions cuando quieras activar IA y avisos:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Sin `OPENAI_API_KEY`, el flujo sigue funcionando y marca las clasificaciones como `sin_ia`.

Para reprocesar el histórico con IA, ejecuta manualmente el workflow y activa el parámetro **reclasificar_historico**. Esto debe hacerse de forma consciente porque realiza llamadas adicionales a la API.
