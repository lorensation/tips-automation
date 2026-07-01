# Hipódromo Tips Agent

Aplicación interna para automatizar la creación, validación, generación y envío de Tips y Pronósticos de jornadas de carreras de caballos.

## Stack

- FastAPI + Jinja2 + HTMX
- SQLAlchemy 2 + Alembic
- Postgres en Docker Compose
- `pdfplumber` + `PyMuPDF` para partants PDF
- Providers LLM intercambiables: `mock`, Groq y OpenRouter
- `openpyxl` para Excel
- HTML/CSS + Playwright para PNG/PDF
- SMTP y Google Drive API para acciones finales

## Desarrollo local

```bash
cp .env.example .env
docker compose up --build
```

Abrir:

```text
http://localhost:8080
```

Con la configuración local de ejemplo, si `ADMIN_PASSWORD_HASH` está vacío, se crea el usuario `ADMIN_EMAIL` con contraseña `admin`.

## Comandos útiles

```bash
pytest
alembic upgrade head
uvicorn app.main:app --reload
```

## Reglas de seguridad del MVP

- El PDF de participantes es la fuente de verdad.
- El LLM solo normaliza texto; no valida ni ejecuta acciones finales.
- La validación determinista bloquea outputs si hay picks inválidos.
- Drive y email requieren outputs revisados.
- Los secretos se configuran por variables de entorno o Secret Manager, nunca en el repo.

## Despliegue Cloud Run

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
