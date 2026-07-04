# Iteración técnica — 4 de julio de 2026

Registro completo de la iteración de mejora del MVP: auditoría, decisiones,
cambios implementados, verificación, riesgos pendientes y próximos pasos.

Commits de la iteración (rama `main`):

| Commit | Contenido |
|---|---|
| `ea7c417` | Seguridad: CSRF, rate limit de login, MIME real de PDF, logging, utcnow tz-aware |
| `b91638d` | Excel: Tips con formato exacto de plantilla + cuadro acumulativo PRONOS con backup |
| `a9cc36a` | Validación: reintento de reparación LLM, retirados en partant, `validate_picks` puro |
| `f96ae1e` | Entrada masiva con preview editable + frontend responsive iPhone/Safari |
| `17ccb6f` | Runbooks (iPhone, SharePoint) + README |

---

## 1. Auditoría inicial (qué estaba roto o faltaba)

1. **El Excel de Tips destruía la plantilla**: `tips_excel_generator.py` hacía
   `ws.delete_rows(1, max_row)` y escribía una tabla plana; además el router
   pasaba `templates_excel/Tips_base.xlsx`, que **no existía** (la real es
   `Tips _Ejemplo.xlsx`), así que siempre caía a un workbook sin formato.
2. **No existía generador del cuadro acumulativo de pronósticos** — solo la
   plantilla `Cuadro_Pronosticos_Ejemplo.xlsx`.
3. **No había entrada masiva** de pronósticos: solo textarea por especialista.
4. **CSS sin una sola media query** → inutilizable en iPhone/Safari; tablas sin
   scroll horizontal; HTMX cargado pero sin usar.
5. Endurecimiento pendiente: sin CSRF, sin rate limit en `/login`, PDF validado
   solo por extensión, `datetime.utcnow()` deprecado, sin logging, errores de
   validación en lista plana sin agrupar.

Inspección verificada de plantillas (openpyxl):

- **Tips**: 6 hojas por sede (HZ azul/8 carreras, SS verde/7, DH/5, SL/7,
  PIN magenta/5, NOCTURNAS negro/5); cabeceras merged en fila 2, datos en
  filas 3–8 con fills alternos, pie merged B10:E12
  (FAVORITO/ENTRENADOR/JOCKEY DE LA JORNADA).
- **Cuadro**: 1 hoja = 1 jornada; título B13, cabeceras fila 17 (2 columnas
  por carrera, pares D/E..N/O), 8 bloques de especialista de 3 filas (19–42),
  consenso fila 43, logo JPEG anclado F5→H12.
- **Archivo real `PRONOS 2026.xlsx`**: hojas `PRO_27_06`, `CLA_27_06`,
  `PRO_02_07`, `ANUAL 2026`. Convención real de hoja: **`PRO_DD_MM`**.
  Estructura idéntica a la plantilla; la hoja de 5 carreras omite el par N/O.

## 2. Decisiones tomadas (con el usuario)

1. **Acceso iPhone**: LAN (misma WiFi + regla de firewall) como vía principal
   probada, y Tailscale documentado para acceso fuera de casa. Sin exposición
   pública. → `docs/runbook_iphone.md`.
2. **Tips, filas FAVORITO/ENTRENADOR/JOCKEY**: quedan con la etiqueta y valor
   vacío; se rellenan a mano en Excel. Sin campos nuevos en la UI.
3. **Acumulativo**: el archivo real es `PRONOS 2026.xlsx` (SharePoint
   corporativo hipodromos.org). Localmente vive en `data/PRONOS 2026.xlsx`
   (configurable); si falta, bootstrap desde plantilla con aviso.
4. **SharePoint**: sincronización manual documentada en esta iteración; nada
   de Graph API (solo tutorial informativo para el futuro).
5. **Nombre de hoja del cuadro**: el requisito original pedía
   `2026-07-02_HZ_NOCTURNAS`, pero el archivo corporativo usa `PRO_DD_MM` →
   default `PRO_{dd}_{mm}` con patrón configurable
   (`CUADRO_SHEET_NAME_PATTERN`, admite `{date}`, `{venue}`, `{dd}`, `{mm}`).
6. **HTMX**: no se introduce; POST+redirect funciona bien en Safari y evita
   complejidad. Queda cargado por si se quiere en el futuro.
7. **Sin migración Alembic**: no hicieron falta columnas nuevas. Trazabilidad
   del bulk = `prediction.raw_text` (bloque por especialista) +
   `audit_events.payload` (texto completo). `OutputType.CUADRO_EXCEL` entra en
   la columna String existente.

## 3. Cambios implementados

### Seguridad (`app/security.py`, `app/templating.py`, `app/logging_config.py`, `app/utils.py`)
- Token CSRF en sesión + hidden input en todos los formularios POST,
  verificado como dependencia de router.
- Rate limit in-memory en `/login` (5 intentos/5 min, configurable).
- PDF: validación por magic bytes `%PDF-`, límite 15 MB, filename saneado.
- Logging estructurado básico sin secretos; `utcnow()` tz-aware en modelos.
- Instancia Jinja2Templates única con global `csrf_input`.

### Excel de Tips (`app/services/tips_excel_generator.py`, reescrito)
- Carga la plantilla completa y conserva solo la hoja de la sede
  (`VENUE_TIPS_SHEETS` en `app/enums.py`); solo escribe valores en celdas
  existentes (nunca `insert/delete_rows`).
- Adapta el nº real de carreras (limpia grupos sobrantes o extiende copiando
  estilos/anchos); si hay >6 caballos con votos desplaza el pie manteniendo
  merges y alternancia de fills.
- Solo `pick_1`, votos agrupados por caballo, nombre oficial resuelto del
  partant por número; si un pick no cruza → `TipsGenerationError` y **no se
  genera archivo**. Sin fallback a Excel plano.
- Descarga desde la UI: `GET /journeys/{id}/outputs/{output_id}/download`.

### Cuadro acumulativo (`app/services/cuadro_excel_generator.py`, nuevo)
- Flujo por jornada: backup con timestamp (retención 20) → hoja `PRO_DD_MM`
  copiada de la hoja oculta `_PLANTILLA` (creada una vez desde la plantilla,
  estilos copiados **por componentes**, nunca `_style` entre workbooks) →
  adaptación 5–8 carreras → relleno (8 especialistas por display_order,
  consenso 3-2-1 en fila 43, subtítulo sede·fecha) → recolor por sede con
  paleta RGB explícita → logo re-insertado (openpyxl no copia imágenes) →
  guardado atómico (tmp + verificación de hojas históricas + replace) →
  restore desde backup si algo falla.
- Regenerar una jornada reemplaza su hoja (idempotente). Las hojas históricas
  (`PRO_*`, `CLA_*`, `ANUAL 2026`) nunca se tocan — verificado con tests
  contra copia del archivo real.
- Endpoint `POST /journeys/{id}/outputs/cuadro` + botón propio en Outputs.

### Validación y pipeline LLM
- `validate_picks(journey, especialista, picks_por_carrera)`: regla
  determinista única (picks duplicados, fuera de partant o retirados, carreras
  faltantes/inexistentes, especialista inválido), compartida por el flujo
  individual y el masivo.
- Partant: checkbox "Corre" por participante (`is_active`) + regla de mínimo
  3 activos por carrera.
- `normalize_prediction`: LLM → coerción local → **1 reintento con prompt de
  reparación** → fallback determinista. Toda salida reparada o de fallback
  fuerza `requires_human_review=true`.
- Parser PDF: regex de cabecera más estricta, distancias con separador de
  miles, deduplicación de carreras (mejoras que estaban sin commitear en el
  árbol de trabajo y se integraron en `a9cc36a`).

### Entrada masiva (`app/services/bulk_segmenter.py` + rutas `/predictions/bulk*`)
- Segmentación determinista por nombre de especialista: acentos, mayúsculas,
  alias (p. ej. "Romera", "fdez cuesta"), autor de WhatsApp; alias largos
  primero para no confundir FERNANDEZ-CUESTA con JOSE MANUEL FERNÁNDEZ.
  Reporta faltantes, duplicados (bloques unidos) y preámbulo sin asignar.
- Preview editable: checkbox por especialista (marcado solo si sin errores),
  picks editables, errores por carrera resaltados, texto original en
  desplegable. Un fallo LLM en un bloque no tumba el preview.
- Confirm stateless (hidden inputs) con **revalidación siempre en backend**;
  se guarda solo lo incluido; trazabilidad en `raw_text` + `audit_events`.

### Frontend responsive
- Inputs 16px (sin auto-zoom iOS), botones min-height 44px, `.table-scroll`
  en todas las tablas, grid `minmax(min(280px,100%),1fr)`, media query ≤640px
  (padding compacto, topbar wrap, acciones en columna, grid 1 columna).
- Errores agrupados por carrera (`predictions/_errors_grouped.html`).

### Infraestructura
- `docker-compose.yml`: volumen `./data:/app/data`. `.gitignore`: `data/`.
- `requirements.txt`: `Pillow==11.0.0` pinneado (logo del cuadro).
- `.env.example`: `TIPS_TEMPLATE_FILENAME`, `CUADRO_TEMPLATE_FILENAME`,
  `PRONOS_FILE_PATH`, `PRONOS_BACKUP_DIR`, `CUADRO_SHEET_NAME_PATTERN`,
  `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_SECONDS`.

## 4. Verificación realizada

- `python -m pytest -q` → **62 tests pasan** (antes: 16). Nuevos:
  `test_tips_excel_generator.py` (formato por sede, blanking, extensión,
  overflow, errores), `test_cuadro_generator.py` (bootstrap, histórico
  intacto sobre el PRONOS real, regeneración idempotente, restore ante fallo),
  `test_bulk_segmenter.py`, `test_prediction_normalizer_repair.py`,
  `test_routers_basic.py` (CSRF, rate limit, PDF falso, bulk end-to-end,
  descarga), y ampliación de `test_validation_engine.py`.
- Verificación manual de los generadores con scripts (todas las sedes, 5–8
  carreras, overflow, colores) y contra copia del `PRONOS 2026.xlsx` real.
- Pendiente de verificación por el usuario: flujo completo en Docker + prueba
  desde iPhone (pasos exactos en los runbooks) y apertura visual de los .xlsx
  en Excel.

## 5. Riesgos pendientes

| Riesgo | Impacto | Mitigación | ¿Acción del usuario? |
|---|---|---|---|
| `APP_SECRET_KEY=change_me` en `.env` local | Sesiones falsificables en LAN | Generar clave (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) | **Sí** |
| Primera generación sin el PRONOS real en `data/` | Acumulativo sin histórico | Copiar `templates_excel/PRONOS 2026.xlsx` → `data/` | **Sí (1 min)** |
| Ediciones concurrentes en SharePoint | Pisar cambios ajenos al reemplazar | Descargar justo antes de generar; historial de versiones de SharePoint | Solo si hay más editores |
| Columna B "1º/2º/3º" del cuadro es estática | No refleja la clasificación anual real | Documentado; fuera de alcance de esta iteración | No |
| PDFs reales con formatos nuevos | Parseo incompleto | La pantalla de revisión permite corregirlo todo a mano | No |
| Rate limiter in-memory | Se resetea al reiniciar; por-proceso | Suficiente con 1 proceso uvicorn local | No |
| `SECONDARY_LLM_*` en config sin implementar | Falsa expectativa de fallback a 2º proveedor | El fallback actual es el parser determinista | No |

## 6. Próximos pasos recomendados

1. Copiar el PRONOS real a `data/` y probar "Añadir al cuadro acumulativo"
   con una jornada real; abrir el resultado en Excel y compararlo.
2. Cambiar `APP_SECRET_KEY` y la contraseña del admin.
3. Probar el flujo completo desde el iPhone por LAN (runbook, ~5 min).
4. Configurar un proveedor LLM real (Groq/OpenRouter) y probar la entrada
   masiva con mensajes reales de los especialistas.
5. Instalar Tailscale para acceso fuera de casa.
6. Cuando se quiera automatizar SharePoint: registro de app en Azure AD
   (anexo de `docs/runbook_sharepoint.md`) e implementar descarga/subida vía
   Graph API detrás de variables de entorno.
7. Migrar `@app.on_event("startup")` a lifespan handlers (warning de FastAPI).
8. Añadir un test end-to-end con un PDF real de participantes como fixture, y
   valorar implementar (o retirar) el proveedor LLM secundario.
