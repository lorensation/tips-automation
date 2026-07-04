# Runbook: acceder a la app desde el iPhone

La app corre en local con Docker en tu PC. Hay dos vías recomendadas para usarla
desde el iPhone, ninguna expone la app a Internet.

---

## Opción A — Misma WiFi (LAN)

Requisitos: el PC y el iPhone conectados a la misma red WiFi.

### 1. Levanta la app

```powershell
docker compose up --build
```

La app escucha en `0.0.0.0:8080`, así que ya acepta conexiones de la LAN.

### 2. Averigua la IP local del PC (Windows)

```powershell
ipconfig
```

Busca el adaptador WiFi/Ethernet activo y apunta la `Dirección IPv4`
(p. ej. `192.168.1.34`).

### 3. Abre el puerto 8080 en el firewall de Windows (una sola vez)

PowerShell **como administrador**:

```powershell
New-NetFirewallRule -DisplayName "Hipodromo Tips 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Private
```

`-Profile Private` limita la regla a redes marcadas como privadas (tu casa).
No la apliques al perfil público.

Para eliminarla más adelante:

```powershell
Remove-NetFirewallRule -DisplayName "Hipodromo Tips 8080"
```

### 4. Desde el iPhone (Safari)

Abre:

```text
http://192.168.1.34:8080
```

(sustituye por tu IP). Inicia sesión con tu usuario admin.

### Notas

- La sesión usa cookies sin flag `Secure` en local (`APP_ENV=local`), por eso
  funciona sobre `http://`. No uses esta configuración fuera de tu red.
- Si la IP del PC cambia (DHCP), repite el paso 2 o fija IP estática en el router.
- Si no carga: comprueba que el PC no esté en "red pública" en Windows
  (Configuración → Red e Internet → propiedades de la WiFi → perfil Privado).

---

## Opción B — Tailscale (acceso desde cualquier lugar, recomendado fuera de casa)

Tailscale crea una VPN privada punto a punto (WireGuard). Nada queda expuesto a
Internet: solo tus dispositivos dentro de tu "tailnet" se ven entre sí.

### 1. En el PC (Windows)

1. Descarga e instala Tailscale: <https://tailscale.com/download/windows>
2. Inicia sesión (cuenta Google/Microsoft/GitHub).
3. Anota la IP Tailscale del PC (icono de bandeja → aparece como `100.x.y.z`),
   o ejecútalo en PowerShell:

   ```powershell
   tailscale ip -4
   ```

### 2. En el iPhone

1. Instala la app **Tailscale** desde el App Store.
2. Inicia sesión con **la misma cuenta**.
3. Activa la conexión (toggle).

### 3. Acceso

Con la app levantada en el PC (`docker compose up`), abre en Safari:

```text
http://100.x.y.z:8080
```

### Notas

- No hace falta regla de firewall para el perfil público: Tailscale crea una
  interfaz propia y Windows la trata como red privada. Si no conecta, aplica la
  misma regla del paso A.3.
- No actives Tailscale Funnel (eso sí publicaría el servicio en Internet).
- Puedes compartir el acceso con otro dispositivo invitándolo a tu tailnet.

---

## Checklist de seguridad mínima

- [ ] `APP_SECRET_KEY` cambiado (no `change_me`) — genera uno: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- [ ] Contraseña de admin propia (`ADMIN_PASSWORD_HASH`), no la de defecto `admin`.
- [ ] Regla de firewall solo en perfil **privado** (opción A).
- [ ] Sin port-forwarding en el router hacia el PC.
- [ ] Tailscale sin Funnel ni nodos compartidos con terceros (opción B).
- [ ] El login tiene rate-limit (5 intentos / 5 min) y todos los formularios llevan token CSRF.
