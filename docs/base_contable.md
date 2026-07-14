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
