# Estado de implementación

Este documento relaciona el [documento funcional](documento-funcional.md)
con lo construido. Fecha de corte: 2 de octubre de 2026.

## Resumen

Están implementadas las fases de construcción F3 a F6 del plan (sección 10
del documento funcional) y la parte técnica de F7 (pruebas automáticas y
validación del stack en Docker). Quedan pendientes las fases que dependen
del negocio: levantamiento de datos reales (F1), pruebas de aceptación con
usuarios (UAT) y puesta en marcha (F8).

| Fase | Estado |
| --- | --- |
| F0 Inicio y gobierno | Pendiente del negocio. **Acción inmediata:** cambiar la clave de la cuenta escrita en el mockup y quitarla del mockup y del informe |
| F1 Levantamiento | Pendiente: los datos actuales son ilustrativos (`seed_demo`) |
| F2 Diseño | Hecho sobre el template base (secciones de este documento) |
| F3 Base, acceso y matriz | Hecho |
| F4 Evidencias y cierre | Hecho |
| F5 Recordatorios y escalamiento | Hecho (falta configurar el SMTP real) |
| F6 Reportes, calendario y auditoría | Hecho |
| F7 Pruebas | Automáticas hechas (162 backend + 26 frontend + prueba manual en navegador); UAT pendiente |
| F8 Puesta en marcha | Pendiente |

## Defectos del mockup (sección 8)

| # | Defecto | Cómo se resolvió |
| --- | --- | --- |
| 1 | Contraseña real en el código | No hay contraseñas en el código. Las cuentas demo toman la clave de `DEMO_USERS_PASSWORD`. **El mockup y el informe siguen publicando la clave: hay que cambiarla.** |
| 2 | Permisos solo en el navegador | Todo se comprueba en el servidor (`apps/organizations/access.py`, `apps/obligations/policies.py`) |
| 3 | El Responsable veía todo | `visible_periods` filtra por responsable o suplente; los demás períodos devuelven 404 |
| 4 | Cambio de empresa sin restricción | `/companies/mine/` lista solo las empresas con rol; sin membresía, 404 |
| 5 | "Vence hoy" ocultaba "Validar y finalizar" | "Vence hoy" es una marca (`is_due_today`), no una etapa (`apps/obligations/status.py`) |
| 6 | Sin separación de funciones | Quien cargó la evidencia o envió el período no puede validarlo |
| 7 | "Cargar" de la Matriz sin permisos | La carga solo existe en el detalle y se valida en el servidor |
| 8 | Borrado de rechazados sin control | Solo quien puede cargar en ese período (responsable, suplente o Administrador), solo documentos rechazados, y como borrado lógico |
| 9 | Regla de cambio de fecha incoherente | Administrador y Supervisor; mensaje alineado |
| 10 | Escalamiento no se ejecutaba | `run_escalations` en el programador |
| 11 | PDF validado solo por extensión | Extensión + firma `%PDF-` del contenido + tamaño, en el servidor |
| 12 | Sin rechazar ni devolver | `POST /documents/{id}/reject/` y `POST /periods/{id}/return/`, con motivo |
| 13 | Edición sin botón y con duplicados | "Editar seguimiento" del período; `PATCH /obligations/{id}/` para la plantilla |
| 14 | Una obligación nueva generaba un solo período | `GenerationService` crea los siguientes según la periodicidad |
| 15 | Responsables como texto libre | Referencias a usuarios con rol en la empresa |
| 16 | Configuración de recordatorios global y con errores | Una por empresa, sin anticipaciones repetidas, una hora de envío |
| 17 | Zona horaria solo decorativa | Estado, recordatorios y "hoy" se calculan en la zona de la empresa |
| 18 | Nombre y color de empresa no persistían | Se guardan en la base y se muestran en el menú |
| 19 | Solo rechazados contaba como "con evidencia" | Se cuentan solo documentos válidos |
| 20 | Códigos repetidos y etapa sin transición | `CodeSequence` con bloqueo de fila; la primera evidencia pasa a "En preparación" |

## Decisiones tomadas (sección 9.4)

Se eligió un valor por defecto para cada decisión pendiente y, cuando fue
posible, se dejó configurable. Hay que confirmarlas con el negocio.

| Decisión | Valor implementado | Dónde se cambia |
| --- | --- | --- |
| Quién cambia la fecha de vencimiento | Administrador y Supervisor/Aprobador | Configuración → Roles: permiso `matriz.cambiar_fecha` |
| Qué fecha cuenta como cumplimiento | La de validación (como el mockup) | Configuración → Empresa ("Fecha que cuenta como cumplimiento") |
| Escalamiento | Al supervisor (o al aprobador si no hay), a los 2 días, una sola vez | Configuración → Recordatorios (días y repetición) |
| Copia al suplente | Sí | Configuración → Recordatorios |
| Reglas de vencimiento | Día fijo del mes (mensual) o día y mes (anual) por plantilla; las de `seed_demo` son ilustrativas | Campos `due_day` y `due_month` de la obligación |
| Conservación de documentos | Sin borrado físico; el plazo de retención no está automatizado | Pendiente de legal |
| SSO | Usuario y clave propios (template base) | Pendiente |
| Inicio de sesión y empresa | Se elige la empresa después de iniciar sesión, para no revelar qué empresas existen | — |

## Roles y permisos configurables

Los roles del mockup ya no están en el código: son roles editables del
template base con permisos `matriz.*` del catálogo, y se asignan por empresa.
Ver [roles-y-permisos.md](roles-y-permisos.md). Los módulos del template base se integraron en la interfaz de la matriz
como pestañas de Configuración, sin repetidos: Empresas, Recordatorios,
Usuarios, Roles, Permisos, Catálogos, Identidad visual y Auditoría (rutas
`/configuracion/...`; las rutas antiguas `/admin/...` y `/sistema/...`
redirigen). Se suman las pantallas Empresas (con
sucursales), Catálogos (áreas y entidades) y Auditoría del sistema,
y el formulario de usuario asigna los roles del sistema, los permisos directos
y los roles por empresa. Antes, el formulario del template base no tenía esas
secciones, aunque la API las admitía.

## Diferencias con el mockup

- El login ya no lista usuarios de demostración ni acepta cualquier clave.
- El visor muestra el PDF real con el visor del navegador (páginas, zoom e
  impresión nativos), en lugar de un simulador.
- El recorrido guiado del mockup no se incluyó: modificaba datos. Queda
  como mejora: una ayuda que no toque datos reales.
- Todo envío de correo es real. Con `EMAIL_BACKEND` de consola, que es el
  valor por defecto en desarrollo, los correos se imprimen en el log.

## Validación realizada

- `pytest`: 146 pruebas contra SQL Server 2022 (83 del template base y 63 de
  la matriz: estados, permisos por rol, flujo de cierre, evidencias, cambio
  de fecha, recordatorios, escalamiento, reintentos, generación, reportes y
  exportaciones).
- `vitest`: 21 pruebas (formato por zona horaria, estados, Resumen por
  capacidad y cierre de ventanas con Escape).
- Prueba manual en Chrome: Responsable carga un PDF real (el falso es
  rechazado) y envía a validación; Supervisor revisa el PDF en el visor y
  valida, incluido un período que vence el mismo día.
- Stack de producción en Docker: SQL Server, backend con gunicorn y worker.
  La base se crea y migra sola, el volumen de evidencias es escribible y el
  programador ejecuta sus ciclos. La imagen del frontend no se pudo
  construir en la red corporativa: npm rechaza el certificado de la
  inspección TLS. La configuración de nginx se validó sirviendo el build
  local.

## Correcciones al template base

Encontradas al integrar; se dejaron corregidas aquí:

1. `roles/0001_initial` fallaba en una base nueva (el `ContentType` aún no existía).
2. Auditar un error de validación con archivo adjunto rompía la transacción.
3. `docker-compose.prod.yml` construía un frontend sin `Dockerfile`.
4. `python:3.12-slim` pasó a Debian 13 y el driver ODBC de Debian 12 ya no instalaba.
5. `entrypoint.sh` con CRLF (clon en Windows) impedía arrancar el contenedor.
6. El primer arranque fallaba porque SQL Server no crea la base.

7. El rol "Superusuario" no se resincronizaba con permisos nuevos:
   `post_migrate` no se emite para apps sin modelos (`roles`).
8. Un token vencido en el navegador impedía volver a iniciar sesión.

Conviene llevar las correcciones 1 a 8 también a `skelleton_base`.

## Pendiente

- [ ] Cambiar la clave publicada en el mockup y el informe (F0).
- [ ] Cargar obligaciones, responsables y correos reales (F1).
- [ ] Configurar SMTP corporativo con SPF y DKIM, y probar con buzones reales.
- [ ] Antivirus en la carga de documentos (hoy se valida tipo y tamaño).
- [ ] Reglas de vencimiento del SRI por noveno dígito del RUC y feriados.
- [ ] Ayuda guiada que no modifique datos.
- [ ] Pruebas de aceptación con usuarios de cada rol (F7) y piloto en Laarcourier (F8).
