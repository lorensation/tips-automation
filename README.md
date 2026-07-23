# Hipódromo Tips Agent

Aplicación interna para automatizar la creación, validación, generación y envío de Tips y Pronósticos de jornadas de carreras de caballos.

> Historial de la última iteración (auditoría, decisiones, riesgos y próximos
> pasos): [docs/iteracion_2026-07-04.md](docs/iteracion_2026-07-04.md)

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

## Despliegue en VM (Oracle Cloud Free / Hetzner)

Recomendado: una VM pequeña con `docker compose` + Tailscale. Mantiene la
decisión de no exponer nada a Internet (la app solo es accesible dentro del
tailnet, igual que en [docs/runbook_iphone.md](docs/runbook_iphone.md)) y el
disco persistente conserva `data/PRONOS 2026.xlsx`, `uploads/` y `generated/`
sin cambios en el código.

### Opciones de proveedor

- **Oracle Cloud Always Free** ($0/mes): VM Ampere ARM. Desde junio 2026 el
  tier gratuito es 2 OCPU / 12 GB RAM y ~200 GB de disco — de sobra para esta
  app (el render de Chromium necesita ~1 GB). Pegas: según la región puede
  haber falta de capacidad al crear la instancia (ayuda pasar la cuenta a
  Pay-As-You-Go, que sigue costando $0 si solo se usan recursos free) y la
  CPU es ARM64 (ver nota abajo).
- **Hetzner Cloud** (~4 €/mes): CX22 (x86, 2 vCPU / 4 GB / 40 GB NVMe) o
  CAX11 (ARM, algo más barato). Sin sorpresas y con datacenter en la UE.

### Pasos

```bash
# En la VM (Ubuntu/Debian):
curl -fsSL https://get.docker.com | sh
git clone <repo> && cd tips-automation
cp .env.example .env            # APP_SECRET_KEY, ADMIN_*, claves LLM/SMTP/Drive
docker compose up -d --build    # incluye Postgres; restart: unless-stopped

# Acceso privado (mismo esquema que docs/runbook_iphone.md):
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Abrir `http://<nombre-vm>.<tailnet>.ts.net:8080` desde cualquier dispositivo
del tailnet (opcional: `sudo tailscale serve --bg 8080` para HTTPS con
certificado válido). **No abrir el puerto 8080 en el firewall público de la
VM**: en Oracle, no añadir ingress rules a la Security List más allá de SSH;
en Hetzner, crear un Cloud Firewall que solo permita SSH entrante (Tailscale
no necesita puertos abiertos). Ojo: Docker publica puertos saltándose `ufw`,
por eso Postgres va mapeado a `127.0.0.1` en `docker-compose.yml` — no
cambiarlo a `0.0.0.0` en una VM pública.

### Nota ARM64 (Oracle Ampere / Hetzner CAX)

La imagen se construye nativa en la propia VM (`docker compose build`);
`python:3.12-slim-bookworm`, Playwright/Chromium y `psycopg[binary]` publican
binarios arm64. Tras el primer despliegue, generar un cuadro PNG de prueba
para verificar el render de Chromium.

### Por qué no Cloud Run (descartado)

Su filesystem es efímero: el acumulativo `data/PRONOS 2026.xlsx` (escritura
atómica + backups con restauración) necesitaría un mount GCS FUSE que no
tiene file locking ni semántica POSIX de `rename`, y además la URL sería
pública. Para una herramienta de un solo usuario no compensa la
re-arquitectura; una VM con disco reproduce el entorno local tal cual.
