# MVP — Hipódromo Tips Agent

## 1. Objetivo del MVP

Construir una aplicación web interna donde el administrador pueda:

```text
1. Crear una jornada.
2. Subir el PDF de participantes definitivos.
3. Extraer carreras y caballos.
4. Revisar/corregir el partant extraído.
5. Pegar los pronósticos de cada especialista.
6. Normalizar esos textos mediante un agente LLM.
7. Validar los picks contra el partant oficial.
8. Generar:
   - Tips para televisión.
   - Cuadro completo de pronósticos para redes.
9. Previsualizar los archivos.
10. Subirlos a Google Drive.
11. Enviarlos por email a los destinatarios definidos.
```

La clasificación anual queda fuera del MVP, pero el modelo de datos quedará preparado para añadirla después.

---

# 2. Stack recomendado

```text
Backend/UI:
FastAPI + Jinja2 + HTMX

Base de datos:
Postgres

Local:
Docker Compose + Postgres container

Online:
Google Cloud Run + Postgres externo, por ejemplo Supabase/Neon

Parsing PDF:
pdfplumber + PyMuPDF

Agente LLM:
Provider intercambiable: Groq / OpenRouter / mock/local

Validación:
Pydantic + reglas deterministas

Excel:
openpyxl sobre plantilla base

Cuadro visual:
HTML/CSS + Playwright screenshot/export

Email:
SMTP administracion@hipodromos.org

Drive:
Google Drive API con service account
```

La app debe ejecutarse como contenedor. Cloud Run permite desplegar servicios desde código con `gcloud run deploy --source`, y también ejecuta contenedores directamente. ([Google Cloud Documentation][1])

---

# 3. Arquitectura general

```text
                 ┌────────────────────────┐
                 │  Admin / Compañero      │
                 │  tips.hipodromos.org    │
                 └───────────┬────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │  FastAPI Web Portal     │
                 │  Jinja + HTMX           │
                 └───────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐     ┌────────────────┐    ┌─────────────────┐
│ PDF Parser   │     │ LLM Agent       │    │ Validation      │
│ Partant      │     │ Groq/OpenRouter │    │ Engine          │
└──────┬───────┘     └───────┬────────┘    └────────┬────────┘
       │                     │                      │
       ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Postgres Database                          │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Output Generator                                             │
│ - Tips Excel                                                 │
│ - Pronósticos PNG/PDF                                        │
└──────────────┬──────────────────────────────┬───────────────┘
               ▼                              ▼
        Google Drive                       SMTP Email
```

---

# 4. Entidades principales

## 4.1 Especialistas fijos

```text
EMILIO VILLAVERDE
ESTEBAN ROMERA
ANDER GALDONA
PEDRO MERCADO
JAVIER FERNANDEZ-CUESTA
JOSÉ SOTO
JOSE MANUEL FERNÁNDEZ
HIPOTOUR
```

---

## 4.2 Jornada

```sql
journeys
--------
id
date
venue
theme
status
pdf_filename
partant_confirmed
created_at
updated_at
sent_at
```

Valores de `venue/theme`:

```python
VENUE_THEMES = {
    "HZ_MADRID": "blue",
    "HZ_NOCTURNAS": "black",
    "SAN_SEBASTIAN": "green",
    "DOS_HERMANAS": "orange",
    "SANLUCAR": "yellow",
    "PINEDA": "purple",
}
```

---

## 4.3 Carreras

```sql
races
-----
id
journey_id
race_number
race_name
distance
time
```

---

## 4.4 Participantes

```sql
participants
------------
id
race_id
number
horse_name
raw_name
jockey
trainer
stall
```

---

## 4.5 Pronósticos

```sql
predictions
-----------
id
journey_id
specialist_id
race_number
pick_1
pick_2
pick_3
raw_text
parsed_ok
requires_human_review
validation_errors
created_at
updated_at
```

---

## 4.6 Outputs generados

```sql
generated_outputs
-----------------
id
journey_id
type
local_path
drive_url
created_at
sent_at
```

Tipos:

```text
tips_excel
pronosticos_png
pronosticos_pdf
```

---

# 5. Flujo funcional del MVP

## 5.1 Crear jornada

Pantalla:

```text
Nueva jornada

Fecha: 02/07/2026
Sede: HZ Nocturnas
Color: negro
PDF: participantes.pdf

[Crear jornada]
```

Resultado:

```text
Jornada creada en estado borrador.
```

---

## 5.2 Subir y parsear PDF

Pipeline:

```text
PDF participantes
    ↓
pdfplumber / PyMuPDF
    ↓
Extracción de carreras
    ↓
Extracción de participantes
    ↓
Vista editable
    ↓
Confirmar partant
```

El sistema debe mostrar algo así:

```text
1ª Carrera - Premio Victoriano Jiménez
Hora: 22:10
Distancia: 1.200 metros

Nº | Caballo             | Jockey    | Entrenador
1  | DUKES OF HAATHER    | R.SOUSA   | O.ANAYA
2  | SKY HAWK            | V.JANACEK | C.BUESA
3  | SUMMERCAKE          | J.GELABERT| R.MARTIN A.
4  | AÑOVER              | R.N.VALLE | O.ANAYA
```

Validaciones:

```text
- Cada carrera tiene número.
- Cada participante tiene número.
- No hay números duplicados dentro de una carrera.
- No hay nombres vacíos.
- La jornada tiene al menos una carrera.
```

---

## 5.3 Introducir pronósticos

Pantalla:

```text
Especialista:
[ANDER GALDONA ▼]

Texto:
[ pegar aquí mensaje de WhatsApp ]

[Parsear pronóstico]
```

El agente recibirá:

```text
- Especialista seleccionado.
- Número de carreras.
- Participantes válidos por carrera.
- Texto bruto pegado.
```

Y devolverá JSON normalizado:

```json
{
  "specialist": "ANDER GALDONA",
  "races": [
    {
      "race_number": 1,
      "pick_1": 2,
      "pick_2": 1,
      "pick_3": 3,
      "confidence": 0.98,
      "notes": null
    }
  ],
  "requires_human_review": false
}
```

---

## 5.4 Validar pronósticos

Después del LLM, el backend valida de forma determinista:

```text
- Especialista válido.
- Carrera existente.
- 3 picks por carrera.
- Picks enteros.
- Picks existentes en el partant.
- Sin duplicados en una misma carrera.
- Todas las carreras cubiertas.
```

Ejemplo de error:

```text
JOSE MANUEL FERNÁNDEZ - Carrera 4:
el caballo nº 11 no existe.
Participantes válidos: 1,2,3,4,5,6,7,8,9,10.
```

Nada se guarda como definitivo hasta que pase validación o el admin lo corrija manualmente.

---

## 5.5 Estado de jornada

Pantalla principal:

```text
Jornada: HZ Nocturnas - 02/07/2026

Partant: Confirmado
Carreras: 5
Especialistas completos: 6/8
Errores pendientes: 1
Archivos generados: No
Email enviado: No

[Ver partant]
[Introducir pronóstico]
[Generar archivos]
[Subir a Drive]
[Enviar email]
```

Tabla:

```text
Especialista                  Estado
EMILIO VILLAVERDE             Completo
ESTEBAN ROMERA                Pendiente
ANDER GALDONA                 Completo
PEDRO MERCADO                 Completo
JAVIER FERNANDEZ-CUESTA       Completo
JOSÉ SOTO                     Error
JOSE MANUEL FERNÁNDEZ         Completo
HIPOTOUR                      Pendiente
```

---

# 6. Rol del agente LLM

El agente será clave para **normalizar inputs**, pero no tendrá control directo sobre acciones finales.

## 6.1 Providers soportados

```text
Groq
OpenRouter
MockProvider para tests
```

Configuración:

```env
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=...

SECONDARY_LLM_PROVIDER=openrouter
SECONDARY_LLM_MODEL=...
SECONDARY_LLM_BASE_URL=https://openrouter.ai/api/v1
SECONDARY_LLM_API_KEY=...
```

Interfaz:

```python
class LLMProvider:
    def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.0,
    ) -> dict:
        ...
```

---

## 6.2 Guardarraíles

```text
El agente puede:
- Normalizar texto libre.
- Proponer JSON estructurado.
- Marcar dudas.
- Ayudar a reparar parsing del PDF si falla.

El agente no puede:
- Enviar emails.
- Subir archivos a Drive.
- Saltarse validaciones.
- Inventar caballos.
- Confirmar jornadas.
- Modificar el partant confirmado sin revisión.
```

---

# 7. Generación de outputs

## 7.1 Tips para televisión

Usa solo `pick_1`.

Proceso:

```text
1. Para cada carrera, tomar el primer pick de los 8 especialistas.
2. Agrupar por caballo.
3. Contar votos.
4. Resolver nombre oficial desde el partant.
5. Rellenar plantilla Excel.
```

Ejemplo conceptual:

```text
1ª CARRERA

SKY HAWK (2)          3 votos
SUMMERCAKE (3)        2 votos
DUKES OF HAATHER (1)  2 votos
AÑOVER (4)            1 voto
```

Output:

```text
tips_HZ_NOCTURNAS_2026-07-02.xlsx
```

---

## 7.2 Cuadro completo de pronósticos

Usa `pick_1`, `pick_2`, `pick_3`.

Output:

```text
pronosticos_HZ_NOCTURNAS_2026-07-02.png
pronosticos_HZ_NOCTURNAS_2026-07-02.pdf
```

Render recomendado:

```text
HTML/CSS fijo
    ↓
Playwright Chromium
    ↓
PNG/PDF crisp
```

El color del cuadro se determina por sede:

```text
Madrid: azul
Madrid nocturnas: negro
San Sebastián: verde
Dos Hermanas: naranja
Sanlúcar: amarillo
Pineda: morado
```

---

## 7.3 Consenso inferior X-Y-Z

Regla MVP propuesta:

```text
pick_1 = 3 puntos
pick_2 = 2 puntos
pick_3 = 1 punto
```

Por carrera:

```text
1. Sumar puntos por caballo.
2. Ordenar de mayor a menor.
3. Tomar top 3.
4. Mostrar X-Y-Z.
```

La regla se dejará configurable para poder cambiarla si el criterio interno actual es otro.

---

# 8. Estructura del repositorio

```text
hipodromo-tips-agent/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   │
│   ├── models/
│   │   ├── journey.py
│   │   ├── race.py
│   │   ├── participant.py
│   │   ├── specialist.py
│   │   ├── prediction.py
│   │   └── generated_output.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── journeys.py
│   │   ├── partant.py
│   │   ├── predictions.py
│   │   ├── outputs.py
│   │   └── send.py
│   │
│   ├── services/
│   │   ├── pdf_parser.py
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── groq_provider.py
│   │   │   ├── openrouter_provider.py
│   │   │   └── mock_provider.py
│   │   ├── prediction_normalizer.py
│   │   ├── validator.py
│   │   ├── consensus.py
│   │   ├── tips_excel_generator.py
│   │   ├── board_renderer.py
│   │   ├── drive_uploader.py
│   │   └── email_sender.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── journeys.html
│   │   ├── journey_detail.html
│   │   ├── partant_review.html
│   │   ├── prediction_form.html
│   │   └── pronosticos_board.html
│   │
│   └── static/
│       ├── logo.png
│       └── styles.css
│
├── templates_excel/
│   └── Tips_base.xlsx
│
├── generated/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

# 9. Variables de entorno

## 9.1 `.env.example`

```env
APP_ENV=local
APP_SECRET_KEY=change_me
APP_BASE_URL=http://localhost:8080

DATABASE_URL=postgresql+psycopg://hipodromo:hipodromo@db:5432/hipodromo_tips

ADMIN_EMAIL=lsanz@hipodromos.org
ADMIN_PASSWORD_HASH=

LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=

SECONDARY_LLM_PROVIDER=openrouter
SECONDARY_LLM_MODEL=
SECONDARY_LLM_BASE_URL=https://openrouter.ai/api/v1
SECONDARY_LLM_API_KEY=

SMTP_HOST=smtp.hipodromos.org
SMTP_PORT=587
SMTP_USER=administracion@hipodromos.org
SMTP_PASSWORD=
SMTP_FROM=administracion@hipodromos.org

EMAIL_RECIPIENTS=lsanz@hipodromos.org,jsoto@hipodromos.org,agaldona@hipodromos.org

GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=

OUTPUT_STORAGE_MODE=local
```

En local, puedes usar:

```env
LLM_PROVIDER=mock
OUTPUT_STORAGE_MODE=local
```

para probar sin gastar tokens ni enviar nada.

---

# 10. Despliegue local con Docker

## 10.1 `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install --with-deps chromium

COPY . .

ENV PORT=8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

Cloud Run inyecta la variable `PORT`, y el contenedor debe escuchar en ese puerto en vez de hardcodear uno fijo. ([Google Cloud Documentation][2])

---

## 10.2 `docker-compose.yml`

```yaml
services:
  app:
    build: .
    container_name: hipodromo-tips-app
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./generated:/app/generated
      - ./templates_excel:/app/templates_excel
    depends_on:
      - db

  db:
    image: postgres:16
    container_name: hipodromo-tips-db
    environment:
      POSTGRES_USER: hipodromo
      POSTGRES_PASSWORD: hipodromo
      POSTGRES_DB: hipodromo_tips
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 10.3 Comandos locales

```bash
cp .env.example .env
docker compose up --build
```

Abrir:

```text
http://localhost:8080
```

Migraciones, si se usa Alembic:

```bash
docker compose exec app alembic upgrade head
```

Logs:

```bash
docker compose logs -f app
```

Parar:

```bash
docker compose down
```

Reset completo de base de datos local:

```bash
docker compose down -v
docker compose up --build
```

---

# 11. Despliegue online con Cloud Run

## 11.1 Arquitectura Cloud Run

```text
tips.hipodromos.org
        ↓
Cloud Run service
        ↓
FastAPI container
        ↓
Supabase/Neon Postgres
        ↓
Google Drive
        ↓
SMTP
        ↓
Groq/OpenRouter
```

Cloud Run tiene free tier mensual para servicios, basado en precios de `us-central1`, con límites de CPU/RAM gratuitos mensuales según modalidad de billing. Conviene configurar `max-instances=1` y alertas de presupuesto para evitar sorpresas. ([Google Cloud][3])

---

## 11.2 Configurar proyecto GCP

```bash
gcloud auth login
gcloud config set project TU_PROJECT_ID
gcloud config set run/region europe-west1
```

Habilitar servicios:

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

---

## 11.3 Crear secretos en Secret Manager

Recomendado para claves:

```bash
printf "super-secret-value" | gcloud secrets create APP_SECRET_KEY --data-file=-
printf "..." | gcloud secrets create LLM_API_KEY --data-file=-
printf "..." | gcloud secrets create SMTP_PASSWORD --data-file=-
printf "..." | gcloud secrets create GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 --data-file=-
```

Cloud Run puede acceder a secretos de Secret Manager como variables de entorno o archivos montados. ([Google Cloud Documentation][4])

---

## 11.4 Deploy inicial

Desde la raíz del repo:

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
  --timeout 300 \
  --set-env-vars APP_ENV=production,APP_BASE_URL=https://tips.hipodromos.org,OUTPUT_STORAGE_MODE=drive
```

`--allow-unauthenticated` permite que el servicio sea accesible por navegador, pero la seguridad real se gestiona dentro de la aplicación mediante login propio.

Para variables no secretas, Cloud Run permite configurarlas con consola o `gcloud`. ([Google Cloud Documentation][5])

---

## 11.5 Conectar secretos al servicio

Ejemplo:

```bash
gcloud run services update hipodromo-tips \
  --region europe-west1 \
  --set-secrets APP_SECRET_KEY=APP_SECRET_KEY:latest,LLM_API_KEY=LLM_API_KEY:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest,GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=GOOGLE_SERVICE_ACCOUNT_JSON_BASE64:latest
```

---

## 11.6 Variables de producción

Además de los secretos, configurar:

```bash
gcloud run services update hipodromo-tips \
  --region europe-west1 \
  --set-env-vars DATABASE_URL="postgresql+psycopg://...",LLM_PROVIDER=groq,LLM_MODEL="...",LLM_BASE_URL="https://api.groq.com/openai/v1",SMTP_HOST="smtp.hipodromos.org",SMTP_PORT=587,SMTP_USER="administracion@hipodromos.org",SMTP_FROM="administracion@hipodromos.org",EMAIL_RECIPIENTS="lsanz@hipodromos.org,jsoto@hipodromos.org,agaldona@hipodromos.org",GOOGLE_DRIVE_FOLDER_ID="..."
```

---

## 11.7 Dominio personalizado

Dominio recomendado:

```text
tips.hipodromos.org
```

Crear mapping:

```bash
gcloud beta run domain-mappings create \
  --service hipodromo-tips \
  --domain tips.hipodromos.org \
  --region europe-west1
```

Cloud Run permite mapear dominios personalizados a servicios y proporciona los registros DNS que hay que crear. ([Google Cloud Documentation][6])

Después, en el DNS de `hipodromos.org`, añadir el registro que indique Google. Normalmente será un `CNAME` para subdominios.

Ejemplo conceptual:

```text
Type: CNAME
Name: tips
Value: destino-proporcionado-por-google
```

---

# 12. Seguridad mínima del MVP

```text
- Login obligatorio.
- Usuarios iniciales: Lorenzo + compañero.
- Password hasheada.
- Sesión segura.
- HTTPS en Cloud Run.
- Límite de tamaño de PDF.
- Validación de MIME type.
- No guardar API keys en el repo.
- No permitir envío si hay errores de validación.
- No permitir subida a Drive sin revisión previa.
```

Roles MVP:

```text
admin:
  - crear jornadas
  - corregir partant
  - generar archivos
  - enviar email

editor:
  - pegar pronósticos
  - revisar estado
  - generar borrador
```

---

# 13. Pantallas del MVP

```text
/login
/jornadas
/jornadas/nueva
/jornadas/{id}
/jornadas/{id}/partant
/jornadas/{id}/pronosticos
/jornadas/{id}/outputs
/jornadas/{id}/enviar
```

---

## 13.1 `/jornadas/{id}`

```text
Jornada: HZ Nocturnas - 02/07/2026

Estado:
Partant confirmado: Sí
Pronósticos completos: 8/8
Errores: 0
Outputs generados: Sí
Drive: Pendiente
Email: Pendiente

Acciones:
[Ver partant]
[Introducir pronóstico]
[Generar archivos]
[Subir a Drive]
[Enviar email]
```

---

## 13.2 `/jornadas/{id}/pronosticos`

```text
Especialista              C1       C2       C3       C4       C5       Estado
EMILIO VILLAVERDE         1-2-5    3-1-4    ...      ...      ...      OK
ESTEBAN ROMERA            2-1-5    3-1-4    ...      ...      ...      OK
ANDER GALDONA             1-2-4    3-1-5    ...      ...      ...      Error
```

---

# 14. Generación y envío

## 14.1 Botón “Generar archivos”

Solo disponible cuando:

```text
- Partant confirmado.
- 8/8 especialistas completos.
- 0 errores de validación.
```

Genera:

```text
generated/
  2026-07-02_HZ_NOCTURNAS/
    tips_HZ_NOCTURNAS_2026-07-02.xlsx
    pronosticos_HZ_NOCTURNAS_2026-07-02.png
    pronosticos_HZ_NOCTURNAS_2026-07-02.pdf
```

---

## 14.2 Botón “Subir a Drive”

Crea estructura:

```text
Pronosticos/
  2026-07-02_HZ_NOCTURNAS/
    tips_HZ_NOCTURNAS_2026-07-02.xlsx
    pronosticos_HZ_NOCTURNAS_2026-07-02.png
    pronosticos_HZ_NOCTURNAS_2026-07-02.pdf
```

Guarda links en DB.

---

## 14.3 Botón “Enviar email”

Destinatarios:

```text
lsanz@hipodromos.org
jsoto@hipodromos.org
agaldona@hipodromos.org
```

Asunto:

```text
Tips y pronósticos - HZ Nocturnas 02/07/2026
```

Cuerpo:

```text
Buenos días,

Adjunto los Tips para televisión y el cuadro de pronósticos de la jornada.

También están disponibles en Google Drive:
{drive_url}

Un saludo.
```

Adjuntos:

```text
tips.xlsx
pronosticos.png
pronosticos.pdf
```

---

# 15. Tests mínimos

```text
test_pdf_parser.py
- Extrae carreras.
- Extrae participantes.
- No duplica números.
- Detecta horarios/distancias si están disponibles.

test_prediction_normalizer.py
- Javier WhatsApp con sección "Tríos".
- Ander con nombres de caballos.
- Jose Manuel solo números por línea.
- Texto con "1 carrera" en línea separada.

test_validator.py
- Pick inexistente.
- Pick duplicado.
- Carrera inexistente.
- Especialista inválido.

test_outputs.py
- Genera Tips Excel.
- Genera PNG.
- Genera PDF.
- Respeta theme de jornada.
```

---

# 16. Roadmap de construcción

## Fase 1 — Base deployable

```text
- Crear repo.
- FastAPI mínimo.
- Login.
- Postgres.
- Docker local.
- Deploy Cloud Run.
- Healthcheck.
```

Criterio de aceptación:

```text
La app abre en local y en Cloud Run.
```

---

## Fase 2 — Partant

```text
- Subida de PDF.
- Parser de participantes.
- Vista editable.
- Confirmación de partant.
```

Criterio de aceptación:

```text
El PDF de ejemplo se convierte en carreras + participantes válidos.
```

---

## Fase 3 — Agente LLM

```text
- Adapter Groq/OpenRouter.
- Mock provider para tests.
- Prompt normalizador.
- JSON schema.
- Validación posterior.
```

Criterio de aceptación:

```text
Los ejemplos de WhatsApp se convierten en picks por carrera.
```

---

## Fase 4 — Outputs

```text
- Tips Excel.
- Cuadro PNG/PDF.
- Previsualización.
- Regeneración.
```

Criterio de aceptación:

```text
Los archivos salen con formato utilizable para televisión y redes.
```

---

## Fase 5 — Drive + Email

```text
- Google Drive API.
- SMTP.
- Registro de envío.
- Control de errores.
```

Criterio de aceptación:

```text
El admin puede generar, revisar, subir y enviar desde la app.
```

---

# 17. Definición final del MVP

El MVP está terminado cuando puedas hacer esto de principio a fin:

```text
1. Entrar en la app.
2. Crear jornada.
3. Subir PDF de participantes.
4. Confirmar carreras y caballos.
5. Pegar pronósticos de los 8 especialistas.
6. Ver todos los pronósticos normalizados.
7. Corregir errores manualmente si hace falta.
8. Generar Tips Excel.
9. Generar cuadro PNG/PDF.
10. Subir archivos a Google Drive.
11. Enviar email con adjuntos y enlace.
12. Consultar el histórico de jornadas.
```

---

# 18. Recomendación final de despliegue

Para desarrollo:

```text
Docker Compose local
Postgres local
LLM mock o Groq/OpenRouter real
Outputs en carpeta generated/
```

Para uso real con compañero:

```text
Cloud Run
Postgres externo
Google Drive
SMTP real
Dominio tips.hipodromos.org
Secret Manager
max-instances=1
```

La decisión técnica queda cerrada así:

```text
Local = reproducible, barato y rápido para iterar.
Cloud Run = accesible online, sin mantener servidor, con dominio propio y coste muy bajo si se limita bien.
```

Este diseño evita depender ciegamente del LLM: el agente normaliza, pero el sistema valida, renderiza y envía de forma controlada.

[1]: https://docs.cloud.google.com/run/docs/deploying-source-code?utm_source=chatgpt.com "Deploy services from source code | Cloud Run"
[2]: https://docs.cloud.google.com/run/docs/configuring/services/containers?utm_source=chatgpt.com "Configure containers for services | Cloud Run"
[3]: https://cloud.google.com/run/pricing?utm_source=chatgpt.com "Cloud Run pricing"
[4]: https://docs.cloud.google.com/run/docs/configuring/services/secrets?utm_source=chatgpt.com "Configure secrets for services | Cloud Run"
[5]: https://docs.cloud.google.com/run/docs/configuring/services/environment-variables?utm_source=chatgpt.com "Configure environment variables for services | Cloud Run"
[6]: https://docs.cloud.google.com/run/docs/mapping-custom-domains?utm_source=chatgpt.com "Mapping custom domains | Cloud Run"
