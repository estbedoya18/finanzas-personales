# Finanzas personales — captura automática de transacciones

Lee correos de notificación de bancos (Bancolombia, Lulo, Nu, Nequi), extrae
las transacciones y las escribe en Google Sheets. Corre en GitHub Actions
cada 15 minutos, sin servidor.

## Arquitectura

```
Bancos -> Gmail (filtros + etiquetas) -> GitHub Actions (Python) -> Google Sheets -> Looker Studio
```

## Parsers implementados

| Banco        | Estado       | Tipos de transacción                                                |
|--------------|--------------|---------------------------------------------------------------------|
| Bancolombia  | ✅ completo  | compra, transferencia recibida/enviada, pago QR, Bre-B a llave      |
| Lulo         | ✅ completo  | envío Bre-B, recibo Bre-B, pago PSE                                 |
| Nu           | 🟡 stub      | pendiente de correos de muestra                                     |
| Nequi        | ⚪ deshabilitado | Nequi no notifica por correo de fábrica (ver `parsers/nequi.py`) |

## Esquema del Sheet

Una hoja `transacciones` con estas columnas (el script las crea automáticamente):

```
id_correo | fecha_hora | banco | tipo | monto | direccion | cuenta |
contraparte | referencia | categoria | descripcion_raw | procesado_en
```

`id_correo` es la clave de deduplicación: si un correo ya está en el sheet, se ignora.

---

## Configuración

### 1. Configurar Gmail (filtros y etiquetas)

En Gmail crea estas etiquetas (Settings > Labels > Create new label):

- `Transacciones` (padre)
  - `Transacciones/Bancolombia`
  - `Transacciones/Lulo`
- `Procesado/Finanzas`

Luego crea estos filtros (Settings > Filters > Create new filter):

**Filtro Bancolombia:**
- `From: alertasynotificaciones@an.notificacionesbancolombia.com`
- Aplicar etiqueta `Transacciones/Bancolombia`

**Filtro Lulo:**
- `From: notificaciones@lulobank.com`
- Aplicar etiqueta `Transacciones/Lulo`

### 2. Obtener credenciales de Gmail

En [Google Cloud Console](https://console.cloud.google.com):

1. Crea un proyecto nuevo (o usa uno existente)
2. Habilita la **Gmail API**
3. Configura OAuth consent screen (External, tu correo, no necesitas verificación si solo te lo das a ti mismo)
4. Crea credenciales: **OAuth Client ID > Desktop app**
5. Descarga el JSON, guárdalo como `credentials.json` en la raíz del proyecto

Luego corre localmente:

```bash
pip install -r requirements.txt
python obtener_refresh_token.py
```

Esto abre el navegador, te pide autorizar el acceso a Gmail, y al final imprime tus 3 valores (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN). Guárdalos para el paso 4.

### 3. Crear el Google Sheet y la Service Account

1. Crea un Sheet vacío en Drive y copia su ID de la URL (lo que va entre `/d/` y `/edit`)
2. En Google Cloud Console (mismo proyecto): habilita la **Google Sheets API**
3. Crea una **Service Account**: IAM & Admin > Service Accounts > Create
4. Una vez creada, abre la service account, ve a la pestaña Keys y crea una key tipo JSON. Se descarga un archivo.
5. Abre el JSON y copia el campo `client_email` (algo como `xxx@xxx.iam.gserviceaccount.com`)
6. Vuelve al Sheet y compártelo con ese correo dándole permiso de **Editor**

### 4. Configurar los Secrets de GitHub

En tu repo de GitHub: Settings > Secrets and variables > Actions > New repository secret.

Crea estos 5 secrets:

| Nombre                              | Valor                                                       |
|-------------------------------------|-------------------------------------------------------------|
| `GMAIL_CLIENT_ID`                   | del paso 2                                                  |
| `GMAIL_CLIENT_SECRET`               | del paso 2                                                  |
| `GMAIL_REFRESH_TOKEN`               | del paso 2                                                  |
| `GOOGLE_SHEETS_CREDENTIALS_JSON`    | el contenido completo del JSON descargado en el paso 3.4    |
| `SHEET_ID`                          | del paso 3.1                                                |

### 5. Activar el workflow

El workflow corre solo cada 15 minutos. Para probarlo manualmente la primera vez:

1. Ve a la pestaña **Actions** del repo
2. Click en `Procesar correos de transacciones`
3. Click en **Run workflow**

Revisa los logs. Si todo está bien, deberías ver:
```
INFO Sheet ya tiene 0 transacciones registradas
INFO OK: Bancolombia compra salida -> 7500.00 (BUNUELO SAN FERNANDO)
...
INFO Insertadas N transacciones nuevas en el Sheet
```

Y al abrir tu Sheet, las transacciones recientes estarán ahí.

---

## Pruebas locales

```bash
python tests/test_normalizar.py
python tests/test_bancolombia.py
python tests/test_lulo.py
```

Los tests usan los correos reales como fixtures, así que pasan sin necesidad de credenciales.

## Estructura del repositorio

```
.
├── .github/workflows/
│   └── procesar_correos.yml     # cron de GitHub Actions
├── src/
│   ├── main.py                  # orquestador
│   ├── gmail_client.py          # lectura de Gmail
│   ├── sheets_client.py         # escritura a Sheets
│   ├── modelo.py                # dataclass Transaccion
│   ├── normalizar.py            # utilidades de montos/fechas/horas
│   └── parsers/
│       ├── base.py              # clase base
│       ├── bancolombia.py       # 5 patrones de Bancolombia
│       ├── lulo.py              # 3 patrones de Lulo
│       ├── nu.py                # stub
│       └── nequi.py             # stub
├── tests/
│   ├── test_normalizar.py
│   ├── test_bancolombia.py
│   └── test_lulo.py
├── obtener_refresh_token.py     # se corre 1 vez localmente
├── requirements.txt
└── README.md
```

## Próximos pasos

- **Migrar correos**: cambiar el correo registrado en Bancolombia, Lulo y Nu al correo de finanzas.
- **Conseguir muestras de Nu**: con uno o dos correos reales se implementa el parser.
- **Nequi**: definir estrategia (SMS forwarder, extracto mensual, o bot de Telegram).
- **Dashboard**: conectar Looker Studio al Sheet para visualizar gastos por categoría/mes.
- **Categorización**: agregar una hoja `categorias` con mapeo comercio→categoría y enriquecer el orquestador para llenar la columna automáticamente.
