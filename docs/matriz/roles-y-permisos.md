# Roles y permisos

La matriz usa el mismo sistema de roles y permisos del template base
(`docs/roles-and-permissions.md`). No hay listas fijas en el código: todo
se configura en la pantalla **Configuración** de la matriz, que tiene una pestaña (ventana
independiente) por cada módulo del template base: usuarios, roles, permisos,
empresas, catálogos, identidad visual y auditoría del sistema.
Cada pestaña aparece solo para quien tiene su permiso.

## Tres niveles de acceso

| Nivel | Dónde se asigna | Qué controla |
| --- | --- | --- |
| Roles del sistema (`user.groups`) | Configuración → Usuarios → usuario → "Roles del sistema" | Las pestañas del sistema en Configuración: usuarios, roles, permisos, empresas, catálogos, identidad visual, auditoría técnica |
| Permisos directos (`user.user_permissions`) | Configuración → Usuarios → usuario → "Permisos directos" | Lo mismo que el nivel anterior, sin pasar por un rol |
| Roles por empresa (membresía) | Configuración → Usuarios → usuario → "Roles por empresa", o Matriz → Configuración → Usuarios y roles | Qué puede hacer en la matriz **de esa empresa**: los permisos `matriz.*` del rol |

Un mismo rol puede usarse en los dos sentidos. Por ejemplo, "Administrador"
asignado como rol por empresa da los permisos `matriz.*` solo en esa empresa.
Los permisos de la matriz que una persona tenga en el nivel del sistema no
le dan acceso a ninguna empresa: hace falta la membresía. El superusuario
de Django es la excepción y tiene todo en todas las empresas.

## Permisos del catálogo

| Módulo | Permiso | Permite |
| --- | --- | --- |
| `matriz` | `matriz.ver_todas` | Ver todos los períodos de la empresa. **Sin él, solo los propios** (responsable o suplente), y todas las acciones sobre períodos se limitan a esos |
| | `matriz.crear` | Crear obligaciones (limitado a sus áreas si no tiene `ver_todas` y la membresía tiene áreas) |
| | `matriz.editar` | Editar obligaciones y el seguimiento de los períodos |
| | `matriz.cambiar_fecha` | Cambiar la fecha de vencimiento, con justificación |
| | `matriz.cargar` | Cargar evidencias y eliminar las rechazadas |
| | `matriz.enviar` | Enviar períodos a validación |
| | `matriz.validar` | Validar cierres, devolver períodos, rechazar evidencias |
| | `matriz.recordar` | Reenviar recordatorios y reintentar avisos fallidos |
| | `matriz.exportar` | Exportar la matriz y los reportes |
| | `matriz.ver_auditoria` | Ver la auditoría y las notificaciones de la empresa |
| | `matriz.configurar` | Configurar la empresa y sus recordatorios |
| | `matriz.gestionar_miembros` | Asignar y quitar roles en la empresa |
| `empresas` | `empresas.ver`, `empresas.editar` | Configuración → Empresas y sus sucursales |
| `catalogos` | `catalogos.ver`, `catalogos.editar` | Configuración → Catálogos (áreas y entidades de control) |

Los módulos del template base (`usuarios`, `roles`, `permisos`,
`configuracion`, `auditoria`) se mantienen igual.

## Roles sembrados

La migración `organizations/0003` crea estos 4 roles (los del mockup).
Después se pueden editar, renombrar o eliminar, y crear otros:

| Permiso | Administrador | Responsable | Supervisor/Aprobador | Auditor |
| --- | --- | --- | --- | --- |
| `ver_todas` | ✓ | — | ✓ | ✓ |
| `crear`, `editar` | ✓ | ✓ | — | — |
| `cambiar_fecha` | ✓ | — | ✓ | — |
| `cargar`, `enviar` | ✓ | ✓ | — | — |
| `validar` | ✓ | — | ✓ | — |
| `recordar` | ✓ | ✓ | ✓ | — |
| `exportar`, `ver_auditoria` | ✓ | — | ✓ | ✓ |
| `configurar`, `gestionar_miembros` | ✓ | — | — | — |

El rol "Superusuario" del template base se mantiene sincronizado con el
catálogo completo cada vez que se migra.

## Reglas que no dependen del rol

- **Separación de funciones:** quien cargó la evidencia o envió el período no
  puede validar ese mismo cierre, aunque su rol tenga `matriz.validar`.
- **Último gestor:** una empresa no puede quedar sin nadie con
  `matriz.gestionar_miembros`.
- **Visibilidad:** sin membresía en una empresa, la API responde 404, no 403.
- **Auditoría:** cada intento denegado queda en la bitácora (`access_denied`,
  con el permiso que faltó).

## Agregar un permiso nuevo

1. Agregarlo a `apps/permissions/catalog.py` (módulo `matriz`).
2. Si es una acción de la matriz, sumar su constante en `Cap`
   (`apps/organizations/access.py`) y usarla en la vista con
   `require_capability` o `require_period_capability`.
3. `python manage.py makemigrations permissions && python manage.py migrate`.
   El permiso aparece solo en el formulario de roles y el rol "Superusuario"
   lo recibe automáticamente.
