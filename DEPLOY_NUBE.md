# Despliegue en la nube (gratuito)

StockVibe puede usar una **base de datos central** compartida entre escritorio y móvil mediante una API REST.

| Servicio | Rol | Plan gratuito |
|----------|-----|---------------|
| [Neon](https://neon.tech) | PostgreSQL persistente | ~0.5 GB, sin tarjeta |
| [Render](https://render.com) | Hosting de la API FastAPI | 750 h/mes, duerme tras 15 min |

---

## 1. Crear la base de datos en Neon

1. Regístrate en [https://neon.tech](https://neon.tech).
2. Crea un proyecto (por ejemplo `stockvibe`).
3. En **Dashboard → Connection string**, copia la URL **pooled** con formato:
   ```
   postgresql://usuario:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
4. Guárdala: será la variable `DATABASE_URL`.

---

## 2. Desplegar la API en Render

### Opción A: Blueprint (recomendada)

1. Sube este repositorio a GitHub.
2. En [Render](https://render.com) → **New → Blueprint**.
3. Conecta el repo; Render detectará `render.yaml`.
4. Configura las variables de entorno:
   - `DATABASE_URL` → URL de Neon (paso 1).
   - `STOCKVIBE_API_KEY` → una clave larga y secreta (ej. generada con un generador de contraseñas).
5. Despliega. La URL será algo como:
   ```
   https://stockvibe-api.onrender.com
   ```

### Opción B: Manual

1. **New → Web Service** → conecta el repo.
2. **Root Directory:** `backend`
3. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Añade las mismas variables `DATABASE_URL` y `STOCKVIBE_API_KEY`.

### Verificar

Abre en el navegador:
```
https://TU-SERVICIO.onrender.com/health
```
Debe responder: `{"ok": true, "service": "stockvibe-api"}`.

> **Nota:** En el plan gratuito, Render “duerme” el servicio tras ~15 min sin tráfico. La primera petición puede tardar 30–60 segundos en despertar.

---

## 3. Configurar escritorio y móvil

Copia el ejemplo y edítalo:

```bash
copy stockvibe_config.example.json stockvibe_config.json
```

Contenido de `stockvibe_config.json`:

```json
{
  "mode": "remote",
  "api_url": "https://stockvibe-api.onrender.com",
  "api_key": "TU_CLAVE_SECRETA"
}
```

También puedes configurarlo desde **Ajustes → Sincronización en la Nube** en la app de escritorio.

**Reinicia la aplicación** después de cambiar el modo.

### Variables de entorno (alternativa)

```bash
set STOCKVIBE_MODE=remote
set STOCKVIBE_API_URL=https://stockvibe-api.onrender.com
set STOCKVIBE_API_KEY=tu-clave-secreta
```

En Android, coloca `stockvibe_config.json` junto al APK o en la carpeta de datos de la app según el empaquetado.

---

## 4. Probar en local (desarrollo)

Terminal 1 — API con SQLite local:

```bash
cd backend
pip install -r requirements.txt
set STOCKVIBE_API_KEY=dev-key
uvicorn main:app --reload --port 8000
```

Terminal 2 — Cliente en modo remoto:

```bash
set STOCKVIBE_MODE=remote
set STOCKVIBE_API_URL=http://127.0.0.1:8000
set STOCKVIBE_API_KEY=dev-key
python main.py
```

---

## Arquitectura

```
Escritorio (main.py) ──HTTP──┐
                             ├──► FastAPI (Render) ──► PostgreSQL (Neon)
Android (main_android.py) ───┘
```

- **`backend/main.py`**: API REST con autenticación por header `X-API-Key`.
- **`api_client.py`**: cliente HTTP usado cuando `mode` es `remote`.
- **`data_access.py`**: elige automáticamente local o remoto.
- **`database.py`**: lógica de negocio (SQLite local o PostgreSQL en servidor).

---

## Seguridad

- Usa una `STOCKVIBE_API_KEY` fuerte y no la compartas públicamente.
- No subas `stockvibe_config.json` a Git (contiene la clave).
- Neon y Render usan HTTPS en producción.

---

## Volver al modo local

En `stockvibe_config.json`:

```json
{
  "mode": "local"
}
```

Reinicia la app. Volverá a usar `inventory.db` en el equipo.
