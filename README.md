# Hipódromo Tips Agent

Aplicación interna para automatizar la creación, validación, generación y envío de Tips y Pronósticos de jornadas de carreras de caballos.

## Stack

- FastAPI + Jinja2 (HTMX cargado, UI server-rendered)
- SQLAlchemy 2 + Alembic
- Postgres en Docker Compose (SQLite en dev sin Docker)
- `pdfplumber` + `PyMuPDF` para partants PDF
- Providers LLM intercambiables: `mock`, Groq y OpenRouter (con reintento de reparación y fallback determinista)
- `openpyxl` (+ Pillow) para Excel preservando las plantillas oficiales
- HTML/CSS + Playwright para PNG/PDF del cuadro visual
- SMTP y Google Drive API para acciones finales

## Flujo de una jornada

1. **Crear jornada** (fecha + sede; la sede fija la gama de colores).
2. **Subir PDF** de participantes → parseo automático → revisión/corrección del
   partant (incluye marcar retirados con la casilla "Corre") → confirmar.
3. **Pronósticos**: dos vías, ambas validadas de forma determinista contra el partant:
   - *Entrada masiva*: un único textarea con el bloque completo de los 8
     especialistas → segmentación automática por nombre (acentos/alias/WhatsApp)
     → normalización LLM con fallback → **preview editable** con errores por
     especialista y carrera → se guarda solo lo válido o lo confirmado.
   - *Individual*: textarea por especialista + corrección manual por carrera.
4. **Outputs**:
   - **Excel de Tips**: nuevo archivo por generación, usando la hoja de la sede
     de `templates_excel/Tips _Ejemplo.xlsx` con su formato exacto (solo se
     rellenan valores; agrupa votos de `pick_1` por caballo).
   - **Cuadro visual** (HTML → PNG/PDF vía Playwright).
   - **Cuadro acumulativo**: añade la hoja `PRO_DD_MM` a `data/PRONOS 2026.xlsx`
     con backup automático previo, verificación post-guardado y restauración si
     falla. Ver [docs/runbook_sharepoint.md](docs/runbook_sharepoint.md).
5. **Revisión** → subida a Drive / envío de email (siempre con confirmación).

## Desarrollo local

```bash
cp .env.example .env    # revisa APP_SECRET_KEY y ADMIN_*
docker compose up --build
```

Abrir <http://localhost:8080>. Con la configuración local de ejemplo, si
`ADMIN_PASSWORD_HASH` está vacío, se crea el usuario `ADMIN_EMAIL` con
contraseña `admin` (cámbiala para cualquier uso fuera de tu máquina).

Sin Docker:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload   # usa sqlite dev.db
```

### Acceso desde iPhone

La app se puede usar desde Safari en el iPhone por LAN (misma WiFi) o mediante
Tailscale, sin exponer nada a Internet. Pasos exactos, regla de firewall y
checklist de seguridad en [docs/runbook_iphone.md](docs/runbook_iphone.md).

## Comandos útiles

```bash
pytest                       # suite completa
pytest tests/test_tips_excel_generator.py tests/test_cuadro_generator.py -q
alembic upgrade head
uvicorn app.main:app --reload
```

## Cuadro acumulativo (PRONOS 2026.xlsx)

- Un único archivo acumulativo; cada jornada añade una hoja `PRO_DD_MM`
  (patrón configurable con `CUADRO_SHEET_NAME_PATTERN`; el archivo corporativo
  real usa esa convención, por eso es el default en lugar de
  `YYYY-MM-DD_SEDE`).
- Las hojas históricas (`PRO_*`, `CLA_*`, `ANUAL 2026`) nunca se tocan.
- Antes de cada escritura se crea backup en `data/backups/` (se conservan 20);
  la escritura es atómica (temporal + verificación + replace) y se restaura el
  backup si algo falla.
- La sincronización con SharePoint es manual en esta iteración:
  [docs/runbook_sharepoint.md](docs/runbook_sharepoint.md).

## Seguridad

- Login obligatorio con sesión firmada; rate-limit en `/login` (5 intentos/5 min).
- Token CSRF en todos los formularios POST.
- El PDF de participantes es la fuente de verdad; se valida por magic bytes
  (`%PDF-`), tamaño máximo 15 MB y nombre de archivo saneado.
- El LLM solo normaliza texto; **la validación final siempre es determinista**
  (picks duplicados, picks fuera del partant, carreras inexistentes, retirados,
  especialistas inválidos). Cualquier reparación o fallback marca
  `requires_human_review`.
- Drive y email requieren outputs revisados y confirmación explícita.
- Los secretos se configuran por variables de entorno o Secret Manager, nunca en el repo.

## Despliegue Cloud Run (futuro)

El contenedor escucha en `$PORT`. Configuración recomendada:

```bash
gcloud run deploy hipodromo-tips \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 3 \
  --timeout 300
```

Usar Secret Manager para `APP_SECRET_KEY`, `DATABASE_URL`, claves LLM, SMTP y Google Drive.
