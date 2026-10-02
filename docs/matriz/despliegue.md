# Despliegue

## Componentes

| Servicio | Imagen | Función |
| --- | --- | --- |
| `mssql` | `mcr.microsoft.com/mssql/server:2022-latest` | Base de datos |
| `backend` | `backend/Dockerfile` | API (gunicorn). Al arrancar crea la base si falta, migra y recolecta estáticos |
| `worker` | La misma imagen del backend | `run_scheduler`: períodos, recordatorios, escalamiento y reintentos |
| `frontend` | `frontend/Dockerfile` | Build de Vite servido por nginx, con las rutas del cliente apuntando a `index.html` |

Las evidencias PDF se guardan en el volumen `evidencias` (`/app/media`). No
se publican: solo salen por `GET /api/v1/documents/{id}/file/`, que comprueba
permisos.

## Desarrollo local

1. Variables de entorno:
   - `.env` (raíz): `DB_NAME`, `DB_PASSWORD`, `DB_PORT` del contenedor de SQL Server.
   - `backend/.env`: ver `backend/.env.example`. En Windows con ODBC 17, `DB_DRIVER=ODBC Driver 17 for SQL Server`.
   - `frontend/.env`: `VITE_API_BASE_URL` apuntando al backend.
2. `docker compose up -d mssql`.
3. Backend:
   ```bash
   cd backend
   pip install -r requirements/dev.txt
   python scripts/ensure_database.py
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py seed_catalogs
   DEMO_USERS_PASSWORD='<clave demo>' python manage.py seed_demo   # opcional
   python manage.py runserver
   python manage.py run_scheduler --once    # un ciclo del programador
   ```
4. Frontend: `cd frontend && npm install && npm run dev`.

Si el puerto 8000 o el 5173 ya están ocupados por otro proyecto, levante
el backend en otro puerto (`runserver 127.0.0.1:8765`) y el frontend con
`npx vite --port 5180`. Ajuste también `VITE_API_BASE_URL`,
`CORS_ALLOWED_ORIGINS` y `FRONTEND_URL`.

### Usuarios de demostración (`seed_demo`)

Son personas ficticias y todas usan la clave de `DEMO_USERS_PASSWORD`.
El comando se niega a correr con `DEBUG=False`, salvo con `--allow-production`.

| Empresa | Administrador | Responsable TH/SST/RSE | Responsable CONT/LEG/SEG/INF/AMB | Supervisor |
| --- | --- | --- | --- | --- |
| Laarcourier | `rodrigo.salcedo` | `priscila.maldonado` | `gabriela.vega` | `daniela.freire` |
| Laar Seguridad | `veronica.idrovo` | `andrea.andrade` | `byron.cevallos` | `paola.salcedo` |
| Virtual Create | `andres.buestan` | `camila.vega` | `andrea.cevallos` | `fernando.moreno` |

`auditoria.externa` es Auditor en las 3 empresas. `rodrigo.salcedo` tiene además el rol del sistema "Superusuario", para entrar a Administración del sistema.

## Producción con Docker

```bash
cp .env.example .env               # DB_NAME, DB_PASSWORD, VITE_API_BASE_URL (URL pública de la API)
cp backend/.env.example backend/.env
# En backend/.env: SECRET_KEY y JWT_SECRET_KEY largos y aleatorios,
# ALLOWED_HOSTS, FRONTEND_URL, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS y el correo.
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_catalogs
```

Variables del `.env` de la raíz usadas por el compose:

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `DB_PASSWORD` | obligatoria | Contraseña `sa` de SQL Server |
| `DB_NAME` | `matriz_admin` | Base de datos (se crea si no existe) |
| `MSSQL_PID` | `Developer` | Edición de SQL Server; en producción, la licenciada (`Standard`, `Enterprise`) |
| `BACKEND_PUBLISHED_PORT` / `FRONTEND_PUBLISHED_PORT` | `8000` / `80` | Puertos publicados |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | URL de la API incluida en el build del frontend |
| `BACKEND_ENV_FILE` | `./backend/.env` | Archivo `.env` del backend y del worker |

En producción, ponga un proxy con HTTPS delante (nginx, Traefik, el
balanceador de la nube). `config/settings/production.py` activa
`SECURE_SSL_REDIRECT`, cookies seguras y HSTS. Para probar sin HTTPS,
defina `SECURE_SSL_REDIRECT=false`.

### Red corporativa con inspección TLS

Si `npm ci` o `pip install` fallan dentro del build con
`self-signed certificate in certificate chain`, la red reemplaza los
certificados. No desactive la verificación: agregue el certificado raíz
corporativo a la imagen (por ejemplo, `COPY ca.crt` +
`NODE_EXTRA_CA_CERTS` en el frontend, y `update-ca-certificates` +
`PIP_CERT` en el backend), o construya las imágenes en un entorno de CI
fuera de esa red.

## Variables de la matriz (`backend/.env`)

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `TIME_ZONE` | `America/Guayaquil` | Zona del servidor. Cada empresa tiene además su propia zona |
| `DOCUMENT_STORAGE_BACKEND` | `filesystem` | `s3` para un bucket S3 compatible (instale `requirements/prod.txt`) |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME` | — | Solo con `s3`. Las credenciales se toman de `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` |
| `MEDIA_ROOT` | `backend/media` | Carpeta de evidencias con `filesystem` |
| `DOCUMENT_MAX_UPLOAD_MB` | `10` | Tamaño máximo por PDF |
| `PERIOD_CODE_PREFIX` | `OBL` | Prefijo del código de período |
| `PERIOD_GENERATION_LEAD_DAYS` | `30` | Anticipación con que se genera el período siguiente |
| `NOTIFICATION_MAX_ATTEMPTS` | `3` | Reintentos automáticos de un aviso fallido |
| `SCHEDULER_INTERVAL_SECONDS` | `300` | Segundos entre ciclos del programador (mínimo 30) |
| `FRONTEND_URL` | `http://localhost:5173` | Base del enlace "Consultar el detalle" de los correos |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | consola | Correo saliente. En producción: `django.core.mail.backends.smtp.EmailBackend` y el SMTP corporativo con SPF y DKIM |

## Programador sin Docker

Si el backend corre fuera de Docker, ejecute el programador como servicio
del sistema operativo (systemd, Programador de tareas de Windows):

- En bucle: `python manage.py run_scheduler`.
- Un ciclo cada 5 minutos: `python manage.py run_scheduler --once` desde cron.

Los procesos son idempotentes: dos ejecuciones simultáneas o repetidas no
duplican períodos ni avisos.

## Copias de seguridad

- Base de datos: respaldo diario de SQL Server (`BACKUP DATABASE`) del volumen `mssql_data`.
- Evidencias: respaldo del volumen `evidencias` o versionado del bucket S3.
