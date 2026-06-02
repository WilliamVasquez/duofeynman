# 🔒 Security — DuoFeynman

Esta app está pensada para ser expuesta a internet. Antes de hacerlo, seguí
este checklist al pie de la letra. Las fallas más comunes en apps personales
son las primeras 4-5 de esta lista.

---

## ✅ Checklist mínimo de producción

### 1. `APP_ENV=production` y validación de config

Cuando ponés `APP_ENV=production` en `.env`, el backend se niega a arrancar si:

- `SECRET_KEY` es el default, está vacío, o tiene menos de 32 caracteres
- `CORS_ORIGINS` contiene `*` (wildcard)
- `DB_PASSWORD` está vacío o es uno conocido (`root`, `password`, el del template)

Si te aborta el arranque con `⛔ ARRANQUE ABORTADO`, **es a propósito**: arreglá el problema antes de seguir.

### 2. SECRET_KEY fuerte

Generá una clave nueva:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegala en `.env` como `SECRET_KEY=...`. **No la compartas, no la subas a Git.**

### 3. Base de datos: usuario dedicado, no root

```sql
CREATE USER 'duofeynman_user'@'localhost' IDENTIFIED BY 'una_password_fuerte';
GRANT SELECT, INSERT, UPDATE, DELETE ON duofeynman.* TO 'duofeynman_user'@'localhost';
FLUSH PRIVILEGES;
```

En `.env`:
```
DB_USER=duofeynman_user
DB_PASSWORD=una_password_fuerte
```

**Nunca uses `root` en producción.** Si te entran al user de la app no pueden tocar nada del sistema.

### 4. HTTPS obligatorio — reverse proxy con certificado

La app NO incluye HTTPS. Andá detrás de un reverse proxy. **Caddy** es lo más fácil:

```caddy
duofeynman.tudominio.com {
    reverse_proxy 127.0.0.1:8000
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}
```

Caddy te saca el certificado de Let's Encrypt automáticamente. Alternativas:
- **Nginx + certbot** (más manual)
- **Traefik** (si vas con Docker)
- **Cloudflare Tunnel** (gratis, expone tu servidor sin abrir puertos)

### 5. Firewall: cerrar TODO menos 80/443

```bash
# UFW (Ubuntu)
ufw default deny incoming
ufw allow ssh
ufw allow 80
ufw allow 443
ufw enable
```

**El puerto 8000 (uvicorn) NO debe ser accesible desde internet** — solo desde localhost. Si exponés uvicorn directo, perdés HTTPS y los rate limits son más fáciles de evadir.

### 6. CORS específico

En `.env`:
```
CORS_ORIGINS=https://duofeynman.tudominio.com
```

Solo los dominios reales. Si tu frontend está en el mismo dominio que tu API, agregalo solo a él.

### 7. Backup de la DB

Cron diario:
```bash
0 3 * * * mysqldump -u duofeynman_user -p'pass' duofeynman | gzip > /backups/duofeynman_$(date +\%Y\%m\%d).sql.gz
```

Y movelos a otro lado (S3, Backblaze B2, otra máquina). Si te hackean y borran la DB, sin backup no recuperás nada.

### 8. Logs y monitoreo

El backend ya logea `audit_log` (intentos de login OK y fallidos). Mandalos a un archivo:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 \
    --log-config logging.yaml \
    >> /var/log/duofeynman/app.log 2>&1
```

Revisá los logs semanal: si ves muchísimos `login_fail` desde una IP, es un ataque.

### 9. Actualizá deps regularmente

```bash
pip list --outdated
pip install --upgrade <paquete>
```

Especialmente `fastapi`, `sqlalchemy`, `bcrypt`, `jose`. Las vulnerabilidades suelen estar en deps, no en tu código.

### 10. NO commitees `.env`

```bash
echo ".env" >> .gitignore
echo "backend/.env" >> .gitignore
echo "*.sqlite" >> .gitignore
echo "models/" >> .gitignore
```

Si subiste un `.env` a Git por error: **rotá TODAS las claves inmediatamente** (SECRET_KEY, DB_PASSWORD). El Git history queda para siempre.

---

## 🛡️ Protecciones ya activas en el código

| Protección | Cómo funciona |
|---|---|
| **Rate limit `/auth/login`** | 5 intentos por minuto por IP |
| **Rate limit `/auth/register`** | 3 cuentas por hora por IP |
| **Rate limit `/tts`** | 60 req/min por IP |
| **Rate limit `/attempts/transcribe`** | 20 req/min por IP |
| **Rate limit global** | 120 req/min por IP |
| **Password policy** | Mín 8 chars, debe mezclar letras + números, blocklist de comunes |
| **Login error genérico** | No leakea si el email existe ("Credenciales inválidas") |
| **Bcrypt rounds=12** | Hash robusto contra rainbow tables |
| **JWT con expiración** | Default 7 días, configurable en `.env` |
| **Security headers** | X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| **HSTS + CSP** (producción) | Solo cuando `APP_ENV=production` |
| **CORS estricto** | Sin wildcard en producción |
| **`/docs` y `/redoc` ocultos** en producción | Reduce superficie de ataque |
| **Stack traces ocultos** en producción | Errores 500 devuelven mensaje genérico |
| **SQLAlchemy ORM** | Protege contra SQL injection (no usamos f-strings con queries) |
| **Audit log** de intentos de login | Loguea OK y FAIL con email + IP |

---

## 🚨 Lo que aún NO tiene protección (limitaciones conscientes)

| Falta | Riesgo | Cuándo importa |
|---|---|---|
| **2FA / MFA** | Si tu password se filtra, te entran | Cuando tengas users reales con datos importantes |
| **Verificación de email** | Cuentas con email falso | Si abrís registro público masivo |
| **Logout server-side / revocación de JWT** | Si te roban un token vale 7 días | Para apps con datos sensibles |
| **CSRF tokens** | Cookies de sesión (no usamos, usamos JWT en Authorization header) | N/A en arquitectura JWT-bearer actual |
| **Captcha en registro** | Bots pueden crear cuentas hasta el rate limit | Si te empiezan a spamear |
| **Storage de tokens revocados** | Sin Redis no podemos hacer revocación instantánea | Cuando crezca la app |

Cuando algún punto te empiece a importar, lo agregamos.

---

## 📋 Antes de exponerlo a internet — quick checklist

- [ ] `APP_ENV=production` en `.env`
- [ ] `SECRET_KEY` nueva (48+ chars random)
- [ ] DB user dedicado (no root) con password fuerte
- [ ] `CORS_ORIGINS` solo con tus dominios reales (sin `*`)
- [ ] HTTPS configurado (Caddy/Nginx/Cloudflare)
- [ ] Firewall cerrado salvo 80, 443, SSH
- [ ] `uvicorn` escuchando solo `127.0.0.1`, no `0.0.0.0`
- [ ] `.env` NO está en Git (`git check-ignore .env` debe imprimir el path)
- [ ] Backup automático de la DB configurado
- [ ] Logs siendo escritos a archivo + rotación con `logrotate`
- [ ] Probaste el rate limit (intentá 6 logins consecutivos, el 6º debe dar 429)
- [ ] Probaste registrar con password "12345678" — debe fallar con mensaje claro

Si todo está ✅, podés exponerlo.

---

## 🔁 Mantenimiento mensual

1. Revisar logs por intentos de login sospechosos
2. `pip list --outdated` y actualizar
3. Verificar que los backups funcionan (restaurá uno en otra DB de prueba)
4. Revisar usuarios activos en MySQL: `SELECT id, username, last_login_at FROM users ORDER BY last_login_at DESC LIMIT 20;`

---

¿Dudas o algo no cierra? Volvé al README o consultame puntualmente.
