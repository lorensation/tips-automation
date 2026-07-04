# Runbook: cuadro acumulativo "PRONOS 2026.xlsx" y SharePoint

El cuadro completo de pronósticos vive en un único archivo acumulativo
(`PRONOS 2026.xlsx`) con una hoja por jornada (`PRO_DD_MM`). El archivo
"oficial" está en el SharePoint corporativo de hipodromos.org:

> <https://hipodromos-my.sharepoint.com/:x:/g/personal/lsanz_hipodromos_org/IQBQD8JE9ahuSbMHg4TiwvJ3AaoCAJHOHFEE9E5XJY3hoGU>

En esta iteración la sincronización con SharePoint es **manual** (sin Graph
API). La app trabaja siempre sobre la copia local configurada en
`PRONOS_FILE_PATH` (por defecto `data/PRONOS 2026.xlsx`).

---

## Flujo de trabajo

### 0. Primera vez: coloca el archivo real en `data/`

1. Abre el enlace de SharePoint → `Archivo` → `Guardar como` → `Descargar una copia`.
2. Guarda el archivo como `data/PRONOS 2026.xlsx` dentro del repositorio
   (la carpeta `data/` está en `.gitignore`; no se sube a git).
   - Alternativa: si la copia del repo `templates_excel/PRONOS 2026.xlsx` está
     al día, cópiala: `Copy-Item "templates_excel/PRONOS 2026.xlsx" "data/"`.

Si no colocas nada, la primera generación crea el archivo desde la plantilla
(`Cuadro_Pronosticos_Ejemplo.xlsx`) y lo avisa en los logs — válido para
probar, pero no contiene las jornadas históricas.

### 1. Genera la hoja de la jornada

En la app: jornada → **Outputs** → **"Añadir al cuadro acumulativo"**.

Qué hace exactamente:

1. Crea un backup con timestamp en `data/backups/` (se conservan los últimos 20).
2. Añade la hoja `PRO_DD_MM` copiando el formato de la plantilla, adaptada al
   número real de carreras y a la gama de colores de la sede.
3. Coloca la hoja antes de `ANUAL 2026` y no toca ninguna hoja existente
   (`PRO_*`, `CLA_*`, `ANUAL 2026`).
4. Guarda en un archivo temporal, verifica que las hojas históricas siguen
   intactas y solo entonces reemplaza el archivo. Si algo falla, restaura el
   backup automáticamente.

Si la jornada se regenera, la hoja `PRO_DD_MM` se **reemplaza** (no se duplica).

El patrón del nombre de hoja es configurable con `CUADRO_SHEET_NAME_PATTERN`
(admite `{dd}`, `{mm}`, `{date}`, `{venue}`).

### 2. Sube el archivo actualizado a SharePoint

1. Abre el enlace de SharePoint en el navegador.
2. En la carpeta contenedora (OneDrive de lsanz@hipodromos.org), usa
   **Cargar → Archivos** y selecciona `data/PRONOS 2026.xlsx`.
3. Acepta **Reemplazar** cuando pregunte por el conflicto de nombre.

SharePoint mantiene su propio historial de versiones (clic derecho →
*Historial de versiones*), así que el reemplazo es reversible también en la nube.

> ⚠️ Si otra persona edita el archivo en SharePoint entre tu descarga y tu
> subida, esos cambios se perderían al reemplazar. Con un único operador (tú)
> no hay conflicto; si algún día hay más editores, descarga siempre justo antes
> de generar.

### 3. Restaurar un backup local

```powershell
Copy-Item "data/backups/PRONOS 2026.backup_YYYYMMDD_HHMMSS.xlsx" "data/PRONOS 2026.xlsx" -Force
```

---

## Anexo (futuro): automatizar con Microsoft Graph API

No implementado en esta iteración. Si se quiere automatizar la descarga/subida,
esto es lo que haría falta:

1. **Registro de aplicación en Azure AD** (Entra ID) del tenant hipodromos.org
   (necesita un administrador del tenant):
   - Azure Portal → Microsoft Entra ID → *App registrations* → *New registration*.
   - Tipo: *Accounts in this organizational directory only*.
   - Anotar `Application (client) ID` y `Directory (tenant) ID`.
2. **Credencial**: *Certificates & secrets* → *New client secret* (anotar el valor).
3. **Permisos** (*API permissions* → Microsoft Graph → *Application permissions*):
   - `Files.ReadWrite.All` (o, mejor, `Sites.Selected` + concesión sobre el
     sitio concreto para limitar el alcance) + *Grant admin consent*.
4. **Variables de entorno** que se añadirían: `MS_TENANT_ID`, `MS_CLIENT_ID`,
   `MS_CLIENT_SECRET`, `MS_DRIVE_ID`, `MS_FILE_ID` (nunca en el repo).
5. **Flujo**: client credentials → token → `GET /drives/{drive}/items/{id}/content`
   para descargar y `PUT .../content` para subir.
6. **Prueba**: descargar el archivo, comparar hash con la copia local, subir a
   un archivo de prueba antes de tocar el real.

Mientras tanto, el flujo manual de arriba cubre la operativa con un coste de
~1 minuto por jornada.
