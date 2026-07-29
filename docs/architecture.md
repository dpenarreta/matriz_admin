# Arquitectura

## Origen

`skelleton_base` es el resultado de particionar el repositorio `skelleton`
(un proyecto Django + React con módulos de negocio completos: biblioteca de
medios, formularios, avisos, páginas, footer, menús dinámicos) para extraer
únicamente la infraestructura transversal reutilizable: identidad
institucional, autenticación, JWT, usuarios, roles y permisos. Ver
`docs/migration-report.md` para el detalle de qué se conservó, qué se
excluyó y por qué.

## Visión general

```
skelleton_base/
├── backend/    Django 5.1 + DRF, patrón Modelo-Vista-Template, SQL Server
├── frontend/   React 18 + Vite + Bootstrap 5
├── tests/qa/   Criterios de aceptación en Gherkin + step definitions
└── docs/       Esta documentación
```

Backend y frontend son proyectos independientes (AC-008): el backend expone
una API JSON versionada bajo `/api/v1/`, y el frontend la consume vía
`axios`. No hay acoplamiento de build ni de despliegue entre ambos.

## Apps del backend

| App | Responsabilidad |
| --- | --- |
| `apps.core` | Infraestructura transversal: `BaseModel`, `AuditLog`, manejo uniforme de errores, middleware de correlación/logging, paginación genérica, health checks |
| `apps.authentication` | JWT, modelo `Session`, login/logout/refresh, recuperación de contraseña autoservicio, protección contra fuerza bruta |
| `apps.users` | Modelo `User`, CRUD administrativo, filtros/búsqueda, restablecimiento administrativo de contraseña, protección del último administrador activo (AC-038) |
| `apps.roles` | CRUD de roles sobre `django.contrib.auth.models.Group` |
| `apps.permissions` | Catálogo de permisos (código, no editable en runtime), resolución de autorización, clases DRF base |
| `apps.branding` | Identidad institucional / tema visual editable (ver "Decisiones de alcance" abajo) |

Esta separación en 5 apps (más `core`) fue una decisión explícita: el
proyecto original mezclaba auth/roles dentro de `apps.users` y `apps.core`.
Se solicitó y se implementó la separación literal en apps independientes
para que este template sea más fácil de entender y de extender.

## Decisiones de alcance

Estas decisiones se tomaron junto con el responsable del proyecto antes de
implementar, y quedan documentadas aquí para que un mantenedor futuro
entienda el porqué:

1. **`apps.branding` (Configuración) es una adición deliberada más allá del
   mínimo estricto del prompt de partición.** El prompt original solo exige
   identidad institucional *estática*. Se decidió mantenerla completamente
   editable (colores, tipografía, logo, favicon, nombre del sitio) a pedido
   explícito, sin depender de ninguna biblioteca de medios (el logo/favicon
   son URLs de texto). Tiene su propio `.feature` (`branding.feature`) y sus
   propios criterios `AC-BR-xxx`, documentados con el mismo rigor que el
   resto.
2. **SQL Server se valida con Docker.** El proyecto original usaba
   PostgreSQL. La migración a SQL Server (`mssql-django` + `pyodbc`) se
   validó ejecutando migraciones reales contra
   `mcr.microsoft.com/mssql/server:2022-latest` en un contenedor Docker, no
   solo mediante inspección de código.
3. **"Último administrador activo" (AC-038) se definió como
   `is_superuser=True`.** El proyecto original no implementaba este
   criterio en absoluto. Se decidió no crear un concepto nuevo de "rol
   administrador" (que hubiera requerido tocar el modelo de permisos) sino
   reutilizar `is_superuser`, que Django ya trata como bypass total de
   autorización (ver `docs/roles-and-permissions.md`).
4. **El menú administrativo del frontend es estático, no dinámico.** El
   proyecto original resolvía el menú lateral contra un sistema de menús
   configurable en backend (excluido de este template, es un módulo de
   negocio). Aquí es un array fijo en
   `frontend/src/components/admin/AdminSidebar/staticAdminMenu.js`,
   filtrado en el cliente por los permisos del usuario — la autorización
   real sigue viviendo exclusivamente en el backend.
5. **Componentes de UI compartidos simplificados.** El proyecto original
   tenía un sistema de modal compuesto (`ResponsiveModal` + contexto) y un
   componente de vista previa responsiva reutilizable. Se simplificaron a
   `ConfirmDialog` (autocontenido, sobre `useModalA11y`) y
   `DevicePreviewFrame` (selector de dispositivo + marco), preservando el
   mismo comportamiento observable con menos superficie de código.

## Flujo de una request administrativa

```
Cliente (React)
  → apiClient (axios, interceptor agrega Bearer token)
  → Django REST Framework
      → SessionAuthentication (valida JWT + Session activa)
      → HasModulePermission (valida el permiso del catálogo)
      → ViewSet (controlador delgado)
          → *Service (lógica de negocio, nunca en la vista)
              → ORM (modelos)
      ← record_audit_event() para toda mutación relevante
  ← api_exception_handler uniforma cualquier error: {"error": {"code","message","details"}}
```

## Auditoría

`apps.core.models.AuditLog` es de solo lectura desde la API (append-only) y
es transversal: cualquier app puede llamar a
`apps.core.audit.record_audit_event(...)`, que aplica automáticamente
`apps.core.sensitive_data.mask_sensitive_fields` — ningún valor cuyo nombre
de campo sugiera contraseña/token/secreto se persiste en texto plano, sin
importar el llamador.

## Qué no incluye este template

Deliberadamente, `skelleton_base` **no** incluye: biblioteca de medios,
constructor de páginas, formularios dinámicos, avisos, footer configurable,
ni un sistema de menús editable. Un proyecto concreto que necesite alguno de
estos módulos debe construirlo aparte, sin reintroducir el acoplamiento que
esta partición buscó eliminar.
