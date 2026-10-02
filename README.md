# Matriz Administrativa de Obligaciones

Sistema para controlar las obligaciones regulatorias, contractuales e
internas de **Laarcourier Express S.A.**, **Laar Seguridad Cía. Ltda.** y
**Virtual Create S.A.**: quién es responsable de cada una, cuándo vence, qué
evidencia (PDF) la respalda, quién valida su cierre y qué recordatorios se
envían.

Es la versión funcional del mockup aprobado. Está construida sobre la
plantilla [`skelleton_base`](https://github.com/dpenarreta/skelleton_base)
(autenticación, JWT, usuarios, roles, permisos, auditoría e identidad
visual), cuyo historial se conserva en este repositorio. Los desarrollos
nuevos van solo aquí.

| Documento | Contenido |
| --- | --- |
| [Documento funcional](docs/matriz/documento-funcional.md) | Pantallas, campos, reglas de negocio, defectos del mockup y plan por fases |
| [Estado de implementación](docs/matriz/implementacion.md) | Qué se construyó, decisiones tomadas y qué queda pendiente |
| [API de la matriz](docs/matriz/api.md) | Endpoints, permisos y ejemplos |
| [Despliegue](docs/matriz/despliegue.md) | Desarrollo local, producción con Docker, variables de entorno |
| [Informe del mockup](docs/referencia/Informe_Funcionamiento_Matriz_Administrativa_3.docx) | Informe de funcionamiento original |
| `docs/*.md` (template base) | Arquitectura, autenticación, roles, seguridad y QA de la plantilla |

## Tecnologías

| Componente | Tecnología |
| --- | --- |
| Backend | Python 3.12, Django 5.1, Django REST Framework |
| Base de datos | SQL Server (`mssql-django` + `pyodbc`) |
| Autenticación | JWT + sesiones propias, contraseñas Argon2, bloqueo por intentos (template base) |
| Frontend | React 18, Vite, React Router, Bootstrap 5 |
| Evidencias | Sistema de archivos (volumen Docker) o bucket S3 compatible |
| Correo | SMTP configurable por variables de entorno |
| Reportes | Excel (`openpyxl`) y PDF (`reportlab`) |
| Pruebas | pytest contra SQL Server real (146) y Vitest (21) |

## Módulos

| Pantalla | Qué hace |
| --- | --- |
| Resumen | Incumplidas, en progreso, próximas a vencer (7 días) y finalizadas a tiempo o fuera de plazo; próximos vencimientos y cierres recientes |
| Matriz | Períodos con búsqueda, filtros (área, entidad, responsable, prioridad, estado, etapa), agrupación, orden por urgencia, paginación y exportación a Excel/PDF |
| Detalle del período | Pestañas General, Documentos, Recordatorios e Historial; enviar a validación, validar, devolver, rechazar evidencia, cambiar fecha con justificación, editar seguimiento |
| Calendario | Vencimientos del mes coloreados por estado |
| Documentos | Expedientes con evidencia y pendientes de evidencia |
| Reportes | Cumplimiento a tiempo y tardío, por área y por entidad, con rango de fechas y exportación |
| Configuración | Empresa, recordatorios y escalamiento, usuarios y roles por empresa, auditoría |
| Administración del sistema (`/admin`) | Módulos del template base: usuarios, roles, permisos, identidad visual |

Un **programador** (`python manage.py run_scheduler`) genera los períodos
siguientes, envía recordatorios (15, 7, 3 y 1 día antes y el día del
vencimiento), escala al supervisor a los 2 días de atraso y reintenta los
avisos fallidos, aunque nadie tenga la aplicación abierta.

## Roles por empresa

| Rol | Puede |
| --- | --- |
| Administrador | Todo, incluida la configuración y los usuarios de la empresa |
| Responsable | Ver y gestionar solo los períodos donde es responsable o suplente; crear obligaciones de sus áreas |
| Supervisor/Aprobador | Ver todo, cambiar fechas, validar, devolver y rechazar evidencia, exportar |
| Auditor | Solo lectura y exportación |

Quien carga la evidencia o envía un período no puede validar ese mismo
cierre. Todos los permisos se comprueban en el servidor.

## Puesta en marcha rápida (desarrollo)

Requisitos: Python 3.12, Node 22, Docker y el driver ODBC 17 o 18 para SQL
Server.

```bash
cp .env.example .env                    # completar DB_PASSWORD
cp backend/.env.example backend/.env    # completar SECRET_KEY, JWT_SECRET_KEY, DB_PASSWORD
docker compose up -d mssql

cd backend
python -m venv .venv && .venv/Scripts/activate   # Linux/Mac: source .venv/bin/activate
pip install -r requirements/dev.txt
python scripts/ensure_database.py
python manage.py migrate
python manage.py createsuperuser
DEMO_USERS_PASSWORD='<elegir una>' python manage.py seed_demo   # opcional: datos ficticios
python manage.py runserver

cd ../frontend
npm install
cp .env.example .env
npm run dev
```

Detalles, producción y variables de entorno en
[docs/matriz/despliegue.md](docs/matriz/despliegue.md).

## Comandos

| Comando | Dónde | Qué hace |
| --- | --- | --- |
| `python manage.py seed_catalogs` | `backend/` | Áreas, entidades de control y las 3 empresas (idempotente) |
| `python manage.py seed_demo` | `backend/` | Usuarios, obligaciones y períodos ficticios (exige `DEMO_USERS_PASSWORD`) |
| `python manage.py run_scheduler [--once]` | `backend/` | Programador de períodos, recordatorios, escalamiento y reintentos |
| `pytest` | `backend/` | Pruebas del backend (necesita SQL Server) |
| `ruff check . && black --check .` | `backend/` | Lint y formato |
| `npm test` / `npm run lint` / `npm run build` | `frontend/` | Pruebas, lint y build |
| `docker compose -f docker-compose.prod.yml up -d --build` | raíz | Stack completo: SQL Server, backend, worker y frontend |

## Estructura

```
matriz_admin/
├── backend/
│   ├── apps/
│   │   ├── core, authentication, users, roles, permissions, branding   # template base
│   │   ├── organizations/   # empresas, sucursales, áreas, entidades, roles por empresa
│   │   ├── obligations/     # obligaciones, períodos, evidencias, estados, reportes
│   │   └── reminders/       # recordatorios, escalamiento, programador
│   ├── templates/emails/    # correos (recordatorio, escalamiento)
│   └── scripts/             # ensure_database.py, wait_for_db.py
├── frontend/src/
│   ├── components/matriz/   # AppShell, PeriodDrawer, modales, visor PDF
│   ├── pages/Matriz/        # Resumen, Matriz, Calendario, Documentos, Reportes, Configuración
│   └── pages/Admin/         # panel administrativo del template base
├── docs/matriz/             # documentación de este proyecto
├── docker-compose.yml       # SQL Server para desarrollo
└── docker-compose.prod.yml  # stack completo de producción
```
