# EmpresaScout 🔍

Agente de scraping empresarial por sector con interfaz web. Busca empresas en directorios públicos, extrae sus datos de contacto y los exporta a Excel o CSV. Incluye modo de enriquecimiento para rellenar automáticamente los huecos en ficheros existentes.

---

## Índice

- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
  - [Búsqueda nueva](#búsqueda-nueva)
  - [Enriquecer fichero](#enriquecer-fichero)
  - [Exportar resultados](#exportar-resultados)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [API](#api)
- [Formato de datos](#formato-de-datos)
- [Reglas del agente](#reglas-del-agente)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Preguntas frecuentes](#preguntas-frecuentes)

---

## Características

- **11 sectores** predefinidos: Tecnología, Marketing, Diseño, Construcción, Salud, Legal, Educación, Restauración, Inmobiliaria, Industria y Otros
- **Campo de palabras clave** para afinar la búsqueda (ciudad, tipo de empresa, etc.)
- **Progreso en tiempo real** vía Server-Sent Events — contadores de fuentes, empresas, emails y teléfonos actualizándose en directo
- **Filtros de calidad** — lista negra de 70+ dominios (LinkedIn, Twitter, YouTube, Flickr, App Store, Europages…) para devolver solo empresas reales
- **Enriquecimiento de ficheros** — sube un CSV o Excel con datos incompletos y el agente rellena los huecos
- **Detección automática de columnas** en el fichero subido (soporta nombres en español e inglés)
- **Exportación** a Excel `.xlsx` (con hipervínculos y celdas nuevas resaltadas en verde) y `.csv`
- **Botón de parada** — detiene el agente limpiamente en cualquier momento conservando los datos ya recogidos
- **Modo Demo** — prueba la interfaz sin hacer peticiones reales a internet

---

## Requisitos

| Requisito | Versión mínima |
|-----------|---------------|
| Python    | 3.10          |
| pip       | cualquiera    |

Dependencias Python (se instalan automáticamente):

```
flask>=3.0.0
requests>=2.31.0
beautifulsoup4>=4.12.3
lxml>=5.1.0
openpyxl>=3.1.2
```

---

## Instalación

### 1. Descarga o clona el proyecto

```bash
# Si tienes git
git clone <url-del-repo> empresascout
cd empresascout

# O descomprime el ZIP y entra en la carpeta
cd scraper_app
```

### 2. Instala las dependencias

```bash
# Windows
python -m pip install -r requirements.txt

# macOS / Linux
pip install -r requirements.txt
```

### 3. Arranca el servidor

```bash
python app.py
```

Verás esto en la consola:

```
🚀  EmpresaScout  →  http://localhost:5000
```

### 4. Abre la aplicación

Abre tu navegador y ve a **http://localhost:5000**

---

## Uso

### Búsqueda nueva

1. Selecciona un **sector** en el desplegable
2. (Opcional) Añade **palabras clave** para afinar: ciudad, tipo de empresa, tamaño, etc.
   - Ejemplos: `Barcelona`, `Madrid B2B`, `pyme reformas`, `empresa familiar`
3. Haz clic en **Iniciar**
4. Observa el progreso en tiempo real:
   - El log muestra cada paso del agente
   - Los contadores se actualizan según llegan resultados
5. Cuando termine, usa los botones **Excel** o **CSV** para descargar

> **Modo Demo** — haz clic en el botón naranja `Demo` para ver la interfaz en acción con datos de ejemplo, sin conexión a internet.

> **Parar** — el botón rojo `Parar` detiene el agente entre peticiones. Los resultados ya recogidos quedan disponibles para exportar.

---

### Enriquecer fichero

Usa esta opción cuando ya tienes un listado de empresas pero le faltan emails, teléfonos u otros datos.

#### Formato del fichero

El agente detecta las columnas automáticamente. Los nombres de cabecera pueden estar en español o inglés, en mayúsculas o minúsculas:

| Campo interno | Nombres de cabecera aceptados |
|---------------|-------------------------------|
| `empresa`     | empresa, company, nombre, name, razon social |
| `sector`      | sector, industria, industry, categoria |
| `web`         | web, url, website, pagina, sitio, dominio, link |
| `email`       | email, e-mail, mail, correo, contacto email |
| `telefono`    | telefono, teléfono, phone, tel, tlf, móvil |
| `fuente`      | fuente, source, origen |

**Ejemplo de CSV válido:**

```csv
empresa,web,email,telefono
Constructora García,https://constructoragarcia.es,,
TechCorp,https://techcorp.es,info@techcorp.es,
Reformas Norte,,,
```

#### Pasos

1. Ve a la pestaña **Enriquecer fichero**
2. Arrastra tu fichero a la zona de carga, o haz clic para buscarlo
3. Verifica las columnas detectadas (se muestran antes de iniciar)
4. Haz clic en **Enriquecer**
5. Las filas van apareciendo en la tabla según se procesan
6. Las celdas con datos **nuevos** aparecen resaltadas en verde
7. Descarga el resultado con los botones Excel o CSV

#### Qué hace el agente por cada fila

```
1. Si tiene web → visita la web y busca email y teléfono
2. Si no encuentra en la portada → busca la página de contacto
3. Si no tiene web → hace una búsqueda en DuckDuckGo para encontrarla
4. Si sigue sin datos → la fila se guarda tal cual, sin inventar nada
```

#### Fichero de salida

- **Excel** — las celdas nuevas aparecen en verde claro con texto en negrita
- **CSV** — incluye dos columnas extra: `email_nuevo` y `telefono_nuevo` (`True`/`False`)

---

### Exportar resultados

Los ficheros se guardan en la carpeta `output/` del proyecto y también se pueden descargar directamente desde la interfaz:

| Botón | Fichero generado | Notas |
|-------|-----------------|-------|
| Excel (búsqueda) | `output/resultados.xlsx` | Hipervínculos en columna Web, cabecera oscura |
| CSV (búsqueda)   | `output/resultados.csv`  | UTF-8 con BOM para compatibilidad con Excel |
| Excel (enriquecido) | `output/enriquecido.xlsx` | Celdas nuevas en verde, leyenda al pie |
| CSV (enriquecido)   | `output/enriquecido.csv`  | Incluye columnas `email_nuevo` y `telefono_nuevo` |

---

## Arquitectura

```
Navegador
   │  HTTP / SSE
   ▼
app.py  (Flask)
   ├── /api/scrape    → lanza ScraperAgent en hilo separado
   ├── /api/enrich    → lanza EnricherAgent en hilo separado
   ├── /api/stream    → Server-Sent Events (progreso en tiempo real)
   ├── /api/stop      → señal de parada al agente activo
   └── /api/export    → devuelve xlsx o csv como descarga
         │
         ├── scraper.py   — agente de búsqueda y extracción
         │     ├── DuckDuckGo HTML (sin API key)
         │     ├── Lista negra de 70+ dominios bloqueados
         │     ├── Extracción de email con regex validado
         │     ├── Extracción de teléfonos españoles
         │     └── Deduplicación por dominio
         │
         └── enricher.py  — agente de enriquecimiento
               ├── Lectura de CSV / Excel
               ├── Detección automática de columnas
               ├── Visita web + página de contacto
               ├── Búsqueda de web si la fila no la tiene
               └── Exportación con celdas resaltadas
```

### Flujo del agente de búsqueda

```
Sector seleccionado
       │
       ▼
Genera 5 queries específicas para ese sector
       │
       ▼
Busca cada query en DuckDuckGo HTML
       │
       ▼
Filtra URLs (descarta dominios bloqueados)
       │
       ▼
Visita cada directorio encontrado
       │
       ▼
Extrae links a empresas individuales
(1 link por dominio, descarta paths de login/legal/etc.)
       │
       ▼
Visita cada web de empresa
       │
       ├── Extrae nombre (og:site_name → title → h1 → dominio)
       ├── Extrae emails con regex
       ├── Extrae teléfonos españoles con regex
       └── Si faltan datos → busca página de contacto
       │
       ▼
Deduplica por dominio
       │
       ▼
Emite evento SSE al navegador
       │
       ▼
Exporta a xlsx + csv
```

---

## Estructura del proyecto

```
scraper_app/
│
├── app.py              # Servidor Flask — rutas, sesiones, SSE
├── scraper.py          # Agente de scraping por sector
├── enricher.py         # Agente de enriquecimiento de ficheros
├── requirements.txt    # Dependencias Python
├── README.md           # Este fichero
│
├── templates/
│   └── index.html      # Interfaz web completa (HTML + CSS + JS)
│
├── output/             # Ficheros exportados (se crea automáticamente)
│   ├── resultados.xlsx
│   ├── resultados.csv
│   ├── enriquecido.xlsx
│   └── enriquecido.csv
│
└── uploads/            # Ficheros subidos temporalmente (se borran tras procesar)
```

---

## API

Todos los endpoints devuelven JSON salvo los de exportación y el stream SSE.

### `POST /api/scrape`

Inicia una sesión de scraping.

**Body:**
```json
{
  "sector":   "Construcción",
  "keywords": "Madrid",
  "demo":     false
}
```

**Respuesta:**
```json
{ "session_id": "uuid" }
```

---

### `POST /api/enrich`

Inicia una sesión de enriquecimiento. Se envía como `multipart/form-data`.

**Campo:** `file` — fichero CSV o Excel

**Respuesta:**
```json
{ "session_id": "uuid" }
```

---

### `GET /api/stream/{session_id}`

Stream de eventos SSE. Cada evento es un objeto JSON en el campo `data`.

**Tipos de evento:**

| `type`     | Cuándo se emite | Campos extra |
|------------|----------------|--------------|
| `status`   | Cambio de fase | `phase`, `stats` |
| `company`  | Nueva empresa encontrada | `company`, `stats` |
| `row`      | Fila enriquecida procesada | `row`, `new_fields`, `stats` |
| `summary`  | Resumen inicial del fichero | `summary` |
| `done`     | Proceso completado | `stats` |
| `stopped`  | Detenido por el usuario | `stats` |
| `error`    | Error fatal | `message` |
| `ping`     | Keep-alive cada segundo | — |

---

### `POST /api/stop/{session_id}`

Detiene el agente activo. Los datos ya recogidos se conservan.

---

### `GET /api/export/{session_id}/{fmt}`

Descarga los resultados. `fmt` puede ser `xlsx` o `csv`.

---

## Formato de datos

### Búsqueda nueva

```json
{
  "empresa":   "Constructora Ibérica S.L.",
  "sector":    "Construcción",
  "web":       "https://constructoraiberica.es",
  "email":     "info@constructoraiberica.es",
  "telefono":  "+34914567890",
  "fuente":    "https://directorio-construccion.es"
}
```

### Enriquecimiento

```json
{
  "empresa":        "Constructora Ibérica S.L.",
  "sector":         "Construcción",
  "web":            "https://constructoraiberica.es",
  "email":          "info@constructoraiberica.es",
  "telefono":       "+34914567890",
  "fuente":         "https://directorio-construccion.es",
  "email_nuevo":    true,
  "telefono_nuevo": false
}
```

Los campos `null` se guardan como cadena vacía en el CSV y como celda vacía en el Excel. Nunca se inventan datos.

---

## Reglas del agente

| Regla | Descripción |
|-------|-------------|
| ✅ Solo datos públicos | No accede a páginas con login ni a APIs de pago |
| ✅ Sin inventar datos | Si no encuentra un dato, guarda `null` |
| ✅ Deduplicación | Una empresa = un dominio. No se repite aunque aparezca en varias fuentes |
| ✅ Lista negra | 70+ dominios bloqueados: LinkedIn, Twitter, YouTube, Google, App Store, Europages, etc. |
| ✅ Validación de emails | Descarta extensiones de fichero (`.png`, `.js`…) y dominios de plataformas conocidas |
| ✅ Teléfonos normalizados | Formato `+34XXXXXXXXX`. Descarta números con menos de 9 dígitos |
| ✅ Errores no fatales | Un fallo en una URL no detiene el proceso |
| ✅ Delays entre peticiones | Entre 1.2 y 2.8 segundos aleatorios para no sobrecargar servidores |
| ❌ Sin datos privados | No usa bases de datos de pago ni ficheros internos de empresas |

---

## Limitaciones conocidas

- **DuckDuckGo puede bloquear** la IP tras muchas búsquedas seguidas. Si el log muestra que no se encuentran fuentes, espera unos minutos o usa el campo de palabras clave para variar las queries.
- **Algunos directorios requieren JavaScript** para mostrar el listado de empresas. El scraper solo procesa HTML estático, por lo que esos directorios devuelven pocas o ninguna empresa.
- **La calidad depende de los directorios públicos** disponibles en el momento de la búsqueda. Para sectores muy locales o nichos pequeños puede haber menos resultados.
- **Solo extrae el primer email y teléfono** encontrado en la página. Si una empresa tiene varios, solo se guarda uno.
- **El enriquecimiento es lento** por diseño — respeta delays entre peticiones. Un fichero de 50 empresas puede tardar entre 5 y 15 minutos.

---

## Tecnologías utilizadas

| Capa | Tecnología |
|------|-----------|
| Servidor web | Flask 3.x |
| Scraping HTTP | requests + BeautifulSoup4 + lxml |
| Concurrencia | threading + Queue (SSE) |
| Excel | openpyxl |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Fuente de búsqueda | DuckDuckGo HTML (sin API key) |

---

## Licencia

Proyecto de uso interno. Solo datos públicos y verificables. No usar para scraping masivo ni automatizado sin respetar los términos de uso de cada sitio web.
