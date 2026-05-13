# Enriquecedor Excel Empresas

Aplicación local en Python para enriquecer archivos Excel de empresas españolas con teléfono corporativo, email, web fuente, estado y nivel de confianza.

## Qué incluye

- Backend Python con FastAPI.
- Frontend web en HTML, CSS y JavaScript, sin tkinter, PyQt ni PySide.
- Subida de Excel por drag & drop.
- Detección automática de columnas aunque cambien los nombres.
- Búsqueda gratuita mediante DuckDuckGo HTML y crawling básico de webs candidatas.
- Extracción y validación de teléfonos españoles fijos y emails corporativos.
- Concurrencia controlada, timeouts, reintentos, caché local y logs.
- Pausa y reanudación cooperativa desde la interfaz.
- Exportación de Excel enriquecido, logs, errores y empresas no encontradas.

## Estructura

```text
company_enricher/
  api/          FastAPI y endpoints
  core/         Excel, detección de columnas, modelos, validación
  search/       Buscadores gratuitos, scraping, caché, scoring
  services/     Orquestación de trabajos
  web/          Frontend HTML/CSS/JS
  utils/        Logging
data/
  uploads/      Excels subidos
  outputs/      Resultados exportados
  logs/         Logs por trabajo
  cache/        Caché JSON de búsquedas y webs
```

## Instalación

Necesitas Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecución

```bash
python -m company_enricher
```

Abre el navegador en:

```text
http://127.0.0.1:8000
```

También puedes usar:

```bash
bash scripts/run_app.sh
```

## Configuración

Edita `.env` si quieres ajustar:

- `MAX_CONCURRENCY`: número de empresas procesadas en paralelo.
- `REQUEST_TIMEOUT_SECONDS`: timeout por petición web.
- `SEARCH_DELAY_SECONDS`: pausa entre búsquedas para ser más prudente.
- `MAX_CRAWL_PAGES_PER_COMPANY`: páginas internas a analizar por empresa.
- `MAX_UPLOAD_MB`: tamaño máximo del Excel.

## Cómo funciona la búsqueda

1. Lee el Excel y detecta cabecera y columnas relevantes.
2. Usa web existente si el Excel trae columna web.
3. Busca candidatos con DuckDuckGo HTML.
4. Prioriza webs oficiales frente a directorios y redes sociales.
5. Rastrea la página inicial y enlaces de contacto/aviso legal/quiénes somos.
6. Extrae emails y teléfonos.
7. Valida teléfonos españoles y descarta móviles personales.
8. Puntúa candidatos por dominio, relevancia del nombre de empresa y tipo de email.

## Limitaciones importantes

No usa APIs de pago. La tasa de acierto depende de que la información esté publicada en webs accesibles. Google Maps y otros sitios pueden bloquear scraping agresivo o impedir automatización; por eso la versión base evita dependencias frágiles y usa crawling prudente. Se puede añadir Playwright como estrategia opcional si hace falta para webs que renderizan contacto con JavaScript.

## Pruebas

```bash
python -m pytest
```

## Siguiente mejora recomendada

Con un Excel real de muestra puedo ajustar los pesos de detección de columnas, el scoring de candidatos y las reglas de exclusión para tu sector concreto.
