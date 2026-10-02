# API de la matriz

Todas las rutas cuelgan de `/api/v1/` y exigen `Authorization: Bearer <access>`
(ver `docs/authentication.md` del template base). Los errores siguen el
contrato uniforme `{"error": {"code", "message", "details"}}`. La
documentación interactiva está en `/api/v1/schema/swagger-ui/`.

## Reglas de acceso

- El acceso depende de la **membresía** del usuario en la empresa del recurso.
  Sin membresía, la empresa o el período responden **404**, para no revelar
  que existen.
- Cada acción exige una **capacidad** del rol (tabla abajo). Si falta,
  responde **403** y queda registrado en la auditoría (`access_denied`).
- El **Responsable** solo ve y modifica los períodos donde es responsable o
  suplente.
- Un superusuario de Django actúa como Administrador en todas las empresas.

| Capacidad | Administrador | Responsable | Supervisor | Auditor |
| --- | --- | --- | --- | --- |
| `ver_todas` | ✓ | — | ✓ | ✓ |
| `crear` | ✓ | ✓ (sus áreas) | — | — |
| `editar` | ✓ | ✓ (lo propio) | — | — |
| `cambiar_fecha` | ✓ | — | ✓ | — |
| `cargar`, `enviar` | ✓ | ✓ (lo propio) | — | — |
| `validar` | ✓ | — | ✓ | — |
| `recordar` | ✓ | ✓ (lo propio) | ✓ | — |
| `configurar`, `gestionar_miembros` | ✓ | — | — | — |
| `exportar`, `ver_auditoria` | ✓ | — | ✓ | ✓ |

## Empresas y personas

| Método y ruta | Capacidad | Descripción |
| --- | --- | --- |
| `GET companies/mine/` | — | Empresas con rol, con `role`, `role_label` y `capabilities` |
| `GET companies/{id}/` | membresía | Datos de la empresa y del rol del usuario |
| `PATCH companies/{id}/` | `configurar` | Razón social, nombre corto, país, actividad, `timezone` (IANA), `color`, `compliance_date_basis` (`validation`/`submission`), `general_manager_id` |
| `GET companies/{id}/people/` | membresía | Personas con rol (para elegir responsable, suplente, etc.) |
| `GET/POST companies/{id}/members/` | `gestionar_miembros` | Listar o agregar rol: `{"identifier": "usuario o correo", "role": "responsable", "area_ids": [1]}` |
| `PATCH/DELETE companies/{id}/members/{mid}/` | `gestionar_miembros` | Cambiar rol o áreas, o quitar. No permite dejar la empresa sin Administrador |
| `GET companies/{id}/catalogs/` | membresía | Áreas, entidades, sucursales, tipos, periodicidades, prioridades, etapas y roles |

## Vistas

| Método y ruta | Capacidad | Descripción |
| --- | --- | --- |
| `GET companies/{id}/dashboard/` | membresía | `counts` (overdue, in_progress, due_soon, done, done_on_time, done_late, attention), `upcoming`, `recent_closures` |
| `GET companies/{id}/periods/` | membresía | Matriz paginada. Filtros: `q`, `area`, `entity`, `responsible`, `obligation`, `priority`, `stage`, `status` (`incumplido`/`en_progreso`/`finalizado`), `due_today=true`, `due_from`, `due_to`. Orden `sort`: `urgency` (por defecto), `due`, `name`, `area`, `entity`, `responsible`, `code`, `priority`; con `-` delante, descendente. `page`, `page_size` (máx. 100) |
| `GET companies/{id}/periods/?export=xlsx\|pdf` | `exportar` | La misma matriz como archivo, con los mismos filtros |
| `GET companies/{id}/calendar/?year=&month=` | membresía | Períodos que vencen en el mes |
| `GET companies/{id}/documents-overview/` | membresía | `with_evidence` y `pending` (un período con solo rechazados es pendiente) |
| `GET companies/{id}/reports/?due_from=&due_to=` | membresía | `kpis`, `by_area`, `by_entity`. Con `export=xlsx\|pdf` exige `exportar` |
| `GET companies/{id}/audit/` | `ver_auditoria` | Historial de períodos de la empresa, más reciente primero. Filtros `actor`, `action`, `from`, `to` |

Cada fila de período trae `status`, calculado en el servidor con la zona
horaria de la empresa:

```json
{
  "group": "en_progreso",
  "group_label": "En progreso",
  "label": "Vence hoy",
  "stage": "pendiente_validacion",
  "is_due_today": true,
  "is_late": false,
  "days_overdue": 0,
  "days_remaining": 0
}
```

## Obligaciones y períodos

| Método y ruta | Capacidad | Descripción |
| --- | --- | --- |
| `POST companies/{id}/obligations/` | `crear` | Crea la obligación y su primer período. Obligatorios: `name`, `area_id`, `control_entity_id`, `type`, `periodicity`, `expected_evidence`, `due_date`, `responsible_id`. Opcionales: `description`, `legal_basis`, `legal_basis_url`, `due_day`, `due_month`, `due_time`, `default_priority`, `branch_id`, `label`, `start_date`, `preparation_date`, `backup_id`, `supervisor_id`, `approver_id`, `priority`, `notes` |
| `GET/PATCH obligations/{id}/` | membresía / `editar` | Plantilla de la obligación |
| `GET periods/{id}/` | visibilidad | Detalle con `actions` (qué botones puede usar el usuario) |
| `PATCH periods/{id}/` | `editar` | `responsible_id`, `backup_id`, `supervisor_id`, `approver_id`, `priority`, `progress`, `notes`, `branch_id` |
| `POST periods/{id}/due-date/` | `cambiar_fecha` | `{"due_date": "2026-10-20", "due_time": "17:00", "reason": "mínimo 10 caracteres"}` |
| `POST periods/{id}/submit/` | `enviar` | Exige al menos un documento válido |
| `POST periods/{id}/validate/` | `validar` | Exige estar pendiente de validación, evidencia válida y que quien valida no haya cargado ni enviado |
| `POST periods/{id}/return/` | `validar` | `{"reason": "…"}`; vuelve a En preparación |
| `GET periods/{id}/history/` | visibilidad | Historial (solo lectura) |

## Evidencias

| Método y ruta | Capacidad | Descripción |
| --- | --- | --- |
| `GET periods/{id}/documents/` | visibilidad | Documentos válidos y rechazados |
| `POST periods/{id}/documents/` | `cargar` | `multipart/form-data` con `file`. Solo PDF real (firma `%PDF-`) de hasta `DOCUMENT_MAX_UPLOAD_MB` |
| `GET documents/{id}/file/[?download=1]` | visibilidad | El PDF, en línea o como adjunto. Cada acceso queda auditado |
| `POST documents/{id}/reject/` | `validar` | `{"reason": "…"}` |
| `DELETE documents/{id}/` | `cargar` | Solo documentos rechazados; borrado lógico |

## Recordatorios

| Método y ruta | Capacidad | Descripción |
| --- | --- | --- |
| `GET/PUT companies/{id}/reminder-config/` | membresía / `configurar` | `offsets` (0–90, sin repetir; el 0 siempre se incluye), `send_time`, `copy_backup`, `escalation_enabled`, `escalation_days` (1–30), `escalation_repeat_days` (0–30) |
| `GET companies/{id}/notifications/` | `ver_auditoria` | Notificaciones de la empresa; filtro `status` |
| `GET periods/{id}/reminders/` | visibilidad | `schedule` (programado, enviado, fallido, no_enviado, suspendido) y `notifications` |
| `POST periods/{id}/reminders/send/` | `recordar` | Reenvío manual al responsable (y suplente) |
| `GET periods/{id}/reminders/preview/?kind=` | visibilidad | `subject`, `to`, `text` y `html` del correo |
| `POST notifications/{id}/retry/` | `recordar` | Reintenta un aviso fallido; la original queda "Reintentado" |
