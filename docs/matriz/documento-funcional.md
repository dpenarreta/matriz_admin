# Documento Funcional — Matriz Administrativa de Obligaciones

Oct 2, 2026 · @Daniel

## 1. Introducción

Para pasar el mockup a producción hay que construir 6 módulos, un motor de estados, 4 roles con permisos validados en el servidor y 5 servicios externos (base de datos, identidad, almacenamiento de PDF, correo y tareas programadas). Este documento detalla cada pantalla, botón, campo, entrada, salida y regla de negocio necesarios, y señala qué hay que corregir respecto al mockup.

### Alcance

- **Incluye:** login multiempresa, Resumen, Matriz de obligaciones, detalle del período, alta y edición de obligaciones, carga y visor de evidencias, Calendario, Documentos, Reportes, Configuración (empresa, recordatorios, usuarios, auditoría) y recorrido guiado.
- **Empresas iniciales:** Laarcourier Express S.A. (LC), Laar Seguridad Cía. Ltda. (LS) y Virtual Create S.A. (VC), todas en Ecuador, zona America/Guayaquil (UTC-5).
- **Excluye:** la integración contable o tributaria con el SRI o el IESS, y la firma electrónica de documentos. Si se necesitan, se cotizan aparte.

### Fuentes

| Fuente | Qué aporta |
| --- | --- |
| Mockup "Matriz Administrativa de Obligaciones" (artefacto HTML, unas 2.240 líneas de código) | Pantallas, campos, botones, catálogos, motor de estados, permisos y comportamiento real |
| Informe de Funcionamiento de la Matriz Administrativa, versión 3 (1 de septiembre de 2026) | Objetivo, flujo de 7 pasos, reglas de estado, matriz de permisos esperada y alcance simulado frente a producción |
| Prueba manual en Chrome (2 de octubre de 2026, usuario Responsable de LC) | Confirmación de comportamientos y defectos |

Cuando el mockup y el informe no coinciden, el documento lo indica y propone la regla para producción (sección 8).

### Glosario

| Término | Significado |
| --- | --- |
| Obligación (plantilla) | Deber recurrente, como la "Declaración de IVA". Define el área, la entidad, el tipo, la periodicidad, la fuente y la evidencia esperada. |
| Período (ocurrencia) | Cada vencimiento concreto de una obligación, con código `OBL-0001`. Tiene su propia fecha, responsables, evidencia, estado e historial. |
| Tablero | Vista de una empresa. Todo el contenido se filtra por la empresa activa. |
| Evidencia | PDF que respalda el cumplimiento de un período. |
| Cierre validado | Finalización de un período por un usuario con permiso de validar, con evidencia válida. |
| Escalamiento | Aviso a la jefatura cuando un período lleva N días vencido sin cerrar. |

## 2. Arquitectura objetivo y componentes

El mockup es una sola página HTML que guarda todo en el navegador. La versión de producción necesita separar la interfaz de un servidor que decide permisos, estados y cierres, con 5 servicios detrás.

&#91;embedded content: arquitectura objetivo · 7 componentes\]

El navegador conserva el diseño del mockup (6 módulos, modo claro y oscuro, tarjetas en móvil), pero toda regla se comprueba en la API. El programador ejecuta los procesos diarios aunque nadie tenga la aplicación abierta.

| Componente | Qué se desarrolla | Reemplaza en el mockup |
| --- | --- | --- |
| Aplicación web | Las 15 pantallas de la sección 5, conectadas a la API | `localStorage` y datos generados en el navegador |
| API de la aplicación | Las llamadas de la sección 7, el control de acceso (sección 4) y el motor de estados (sección 6) | Las funciones `can`, `isMine` y `occStatus` del navegador |
| Base de datos | El modelo de la sección 3 | El objeto `STATE` |
| Identidad | Inicio de sesión verificado | Cualquier contraseña válida |
| Almacenamiento de PDF | Archivos reales con versiones | Solo el nombre y el tamaño del archivo |
| Servicio de correo | Envío y registro de entrega | Avisos en pantalla "Correo simulado" |
| Programador | Generar períodos, recordatorios, escalamiento y reintentos | No existe |

La tecnología concreta (lenguaje, base de datos, nube) queda abierta para la cotización. Ningún requisito de este documento depende de un proveedor específico.

## 3. Modelo de datos

La base de datos necesita 15 entidades. La clave del diseño es separar la **obligación** (plantilla recurrente) de sus **períodos** (cada vencimiento con su propio estado y evidencia). En el mockup, las fechas se guardan como días de diferencia con "hoy" (`dueOffsetDays`). En producción deben ser fechas reales con zona horaria.

### 3.1 Catálogos

| Entidad | Campos | Validaciones y notas |
| --- | --- | --- |
| Empresa | id (LC, LS, VC), razón social, nombre corto, país, actividad económica, zona horaria, color institucional, gerente general (aprobador por defecto) | Razón social y nombre corto obligatorios. Zona horaria de una lista IANA (el mockup ofrece 5 de América). Color en hexadecimal. |
| Sucursal | id, empresa, nombre | El mockup usa una fija por empresa: "Matriz Quito" (LC), "Oficina Central Guayaquil" (LS), "Oficina Cuenca" (VC). Producción: CRUD por empresa. |
| Área | id, nombre | 8 iniciales: CONT Contabilidad y Tributario, TH Talento Humano y Nómina, SST Seguridad y Salud en el Trabajo, AMB Ambiental, LEG Legal y Permisos, SEG Seguros y Pólizas, INF Arriendos e Infraestructura, RSE Responsabilidad Social. |
| Entidad de control | id, nombre | 8 iniciales: SRI, IESS, MDT (Ministerio del Trabajo), BOMB (Cuerpo de Bomberos), GAD Municipal, ASEG (Aseguradora), ARR (Arrendador), MINAM (Ministerio del Ambiente). |
| Tipo de obligación | regulatoria, contractual, interna | Lista cerrada. |
| Periodicidad | mensual, trimestral, semestral, anual, única | Lista cerrada. El mockup solo genera períodos para mensual y anual. |
| Prioridad | Alta, Media, Baja | Lista cerrada. También sirve para ordenar la matriz. |

### 3.2 Entidades operativas

| Entidad | Campos | Validaciones y notas |
| --- | --- | --- |
| Obligación (plantilla) | id, nombre, descripción, área, entidad de control, tipo, periodicidad, fuente o fundamento legal (texto o enlace), evidencia esperada (texto, p. ej. "Formulario 104 y comprobante de pago"), empresas a las que aplica, día y hora de vencimiento por defecto, activa (sí/no) | Nombre y área obligatorios. El mockup trae 14 plantillas (M01–M14). Las altas desde el formulario quedan con evidencia genérica "Documento de respaldo": producción debe pedir este campo. |
| Período | código `OBL-NNNN` (secuencial por empresa o global), obligación, empresa, sucursal, etiqueta de período ("Octubre 2026", "Período 2026"), fecha de inicio, fecha interna de preparación, fecha y hora de vencimiento, responsable, suplente, supervisor, aprobador, prioridad, avance (0–100 %), etapa (sin\_iniciar, en\_preparacion, pendiente\_validacion), cerrado (sí/no), fecha de cumplimiento, fecha de validación, validado por, observaciones, recordatorios suspendidos (sí/no) | Vencimiento obligatorio. Inicio ≤ preparación ≤ vencimiento. Responsable obligatorio. Si no se indica, el aprobador por defecto es el gerente de la empresa. Por defecto, inicio = vencimiento − 30 días y preparación = vencimiento − 5 días. Hora por defecto 17:00. |
| Documento (evidencia) | id, período, nombre de archivo, versión (v1, v2…), tamaño, tipo MIME, hash, ruta en el almacenamiento, fecha de carga, usuario que carga, estado (válido o rechazado), motivo de rechazo | Solo PDF de hasta 10 MB, verificando el contenido y no solo la extensión. Varios por período. Nunca se borra físicamente: se marca. |
| Evento de historial | id, período, fecha y hora, usuario (o "Sistema"), acción, motivo, valor anterior, valor nuevo | Solo inserción: no se edita ni se borra. Incluye los cambios de fecha, que en el mockup van en una lista aparte (`cambiosFecha`). |
| Notificación | id, período, tipo de aviso (−15, −7, −3, −1 días, día del vencimiento, escalamiento, bajo demanda, reintento), destinatario, fecha programada, fecha de envío, estado (Programado, Enviado, Fallido, Reintentado), número de reintentos, id del mensaje en el proveedor de correo | Una fila por aviso y destinatario. Un reintento crea una fila nueva y marca la original como "Reintentado". |
| Configuración de recordatorios | empresa, anticipaciones en días (por defecto 15, 7, 3, 1 y 0), hora de envío (08:00), escalamiento activo (sí), días de atraso antes de escalar (2), destinatario del escalamiento | Anticipaciones de 1 a 90 días, sin repetir. Días de escalamiento de 1 a 30. El mockup la guarda como una sola configuración global: producción debe tenerla por empresa. |

### 3.3 Usuarios y acceso

| Entidad | Campos | Validaciones y notas |
| --- | --- | --- |
| Usuario | id, usuario (nombre.apellido), nombre completo, correo corporativo, estado (activo o bloqueado), identificador en el proveedor de identidad | Usuario y correo únicos. Sin contraseñas en el código ni en la base: las gestiona el proveedor de identidad. |
| Asignación de rol | usuario, empresa, rol (Administrador, Responsable, Supervisor/Aprobador, Auditor), áreas (opcional, para el Responsable) | Un usuario puede tener roles distintos en cada empresa. El Auditor externo puede asignarse a varias. |

Los campos de responsable, suplente, supervisor y aprobador del período deben apuntar a un **Usuario**, no a un nombre en texto libre como en el mockup. Así "es mío" se decide por identificador y los correos salen de la ficha del usuario.

## 4. Roles, permisos y reglas de acceso

Hay 4 roles, y cada permiso debe comprobarse en el servidor en cada petición. El mockup solo bloquea en el navegador y deja huecos: el Responsable ve todo y cualquier usuario puede cambiar de empresa. La tabla muestra la regla propuesta para producción, que sigue al Informe donde el código y el Informe no coinciden.

| Acción | Administrador | Responsable | Supervisor/Aprobador | Auditor | Diferencia con el mockup |
| --- | --- | --- | --- | --- | --- |
| Ver obligaciones de su empresa | Todas | Solo donde es responsable o suplente | Todas | Todas | En el mockup, el Responsable ve todas (`verTodas:false` no se aplica). |
| Crear obligaciones | Sí | Sí, de su área | No | No | El mockup deja crear al Responsable en cualquier área. |
| Editar el período (responsables, prioridad, avance, observaciones) | Sí | Solo los suyos | No | No | El mockup no tiene edición: el formulario existe, pero ningún botón lo abre. |
| Cambiar la fecha de vencimiento | Sí | Por definir | Por definir | No | El mockup permite al Responsable, aunque el aviso de error dice "Administrador o Supervisor". |
| Cargar evidencia | Sí | Solo en los suyos | No | No | Coincide. |
| Eliminar un documento rechazado | Sí | Solo en los suyos | No | No | El mockup no comprueba de quién es el período. |
| Enviar a validación | Sí | Solo los suyos | No | No | Coincide. |
| Validar y finalizar | Sí, si no cargó la evidencia | No | Sí | No | Falta separación de funciones: en el mockup, el Administrador valida lo que él mismo cargó. |
| Simular o reenviar un recordatorio, reintentar un envío fallido | Sí | Solo los suyos | Sí | No | En el mockup, cualquier rol, incluido el Auditor. |
| Configurar empresa y recordatorios | Sí | No | No | No | Coincide. |
| Gestionar usuarios y roles | Sí | No | No | No | No existe en el mockup: solo hay una lista de usuarios de demostración. |
| Ver auditoría y reportes | Sí | Solo de lo suyo | Sí | Sí | El mockup muestra todo a todos. |
| Exportar reportes | Sí | No | Sí | Sí | El mockup lo permite a cualquier rol. |

### Reglas de acceso por empresa

1. Al iniciar sesión, el usuario elige una empresa donde tenga un rol asignado. Si elige otra, el acceso se rechaza.
2. El selector de empresa de la barra superior lista solo las empresas donde el usuario tiene rol. Al cambiar, se aplica el rol de esa empresa. En el mockup, el selector deja ver cualquier empresa conservando el rol de la sesión.
3. Todas las consultas del servidor filtran por la empresa activa y por el alcance del rol: el Responsable solo ve donde es responsable o suplente.
4. Un intento no permitido devuelve un error 403 y muestra el aviso "Acción no disponible", como hace hoy el mockup con `denied()`.
5. El Auditor es de solo lectura en todo el sistema: los botones de acción aparecen deshabilitados con el motivo.

## 5. Análisis pantalla por pantalla

Son 15 pantallas o ventanas. Para cada una se indica cada elemento, lo que recibe, la regla que aplica y lo que produce. **\[Mockup\]** marca un comportamiento simulado que en producción necesita servidor.

### 5.1 Inicio de sesión

Objetivo: identificar al usuario y fijar la empresa (tablero) de la sesión.

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Panel informativo | Texto | — | Muestra 3 indicadores: empresas activas (3), períodos vigentes y entidades de control (8). Producción: contarlos en la base. | Indicadores |
| Selector de empresa | 3 tarjetas | Clic | Marca la empresa elegida (por defecto LC) y recarga la lista de usuarios de demostración. | Empresa elegida |
| Usuario | Texto obligatorio | nombre.apellido | Se compara sin distinguir mayúsculas. | — |
| Contraseña | Contraseña obligatoria | Texto | **\[Mockup\]** Cualquier contraseña no vacía es válida, salvo en la cuenta con clave fija. Producción: el proveedor de identidad la verifica, con política de contraseñas y bloqueo tras intentos fallidos. | — |
| Ingresar | Botón | Formulario | Busca un usuario con ese nombre y esa empresa. Si no existe o la clave falla, muestra "Usuario o contraseña incorrectos para la empresa seleccionada". Si es correcto, crea la sesión (usuario, nombre, rol, empresa, correo) y abre el Resumen. | Sesión o mensaje de error |
| Usuarios de demostración | Lista con clic | Clic en una fila | **\[Mockup\]** Autocompleta el usuario y la clave `demo1234`. Producción: se elimina y se agrega "Olvidé mi contraseña" o el botón de SSO. | Campos llenos |
| Aviso de simulación | Texto | — | Explica que la autenticación es simulada. Producción: se elimina. | — |

### 5.2 Estructura general (menú lateral y barra superior)

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Tablero activo | Texto | Sesión | Muestra el nombre corto de la empresa. | — |
| Menú | 6 opciones | Clic | Resumen, Matriz de obligaciones, Calendario, Documentos, Reportes, Configuración. La Matriz lleva un contador de períodos de la empresa incumplidos o que vencen hoy. | Cambio de vista |
| Pie del menú | Texto | Sesión | Rol, iniciales, nombre y correo del usuario. | — |
| Cerrar sesión | Botón | Clic | Borra la sesión, guarda el estado y vuelve al login con los campos vacíos. Producción: invalida el token en el servidor. | Login |
| Menú en móvil | Botón (pantallas de 880 px o menos) | Clic | Abre o cierra el menú lateral. | — |
| Buscador global | Texto | Texto libre | Tras 150 ms sin escribir, guarda el texto como filtro de la Matriz y la abre. Busca en el nombre de la obligación, el código, el responsable, la entidad y el área. | Matriz filtrada |
| Recorrido guiado | Botón | Clic | Inicia el recorrido de 7 pasos (5.15). | Tour |
| Notificaciones | Botón con punto rojo | Clic | Abre Configuración en la pestaña Recordatorios. **\[Mockup\]** El punto rojo nunca se enciende. Producción: bandeja de avisos del usuario con un contador de no leídos. | Vista Configuración |
| Selector de empresa | Lista desplegable | Clic | Cambia la empresa activa y vuelve a dibujar la vista. Producción: solo empresas donde el usuario tiene rol (sección 4). | Tablero cambiado |

### 5.3 Resumen

Objetivo: ver de un vistazo el estado de cumplimiento de la empresa activa.

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Encabezado | Texto | Empresa | Nombre corto, actividad, país y zona horaria (si se editó en Configuración, se usa la editada). | — |
| Incumplidas | Indicador | Períodos | Cuenta los que están en estado Incumplido. | Número |
| En progreso | Indicador | Períodos | Cuenta los que están en estado En progreso. | Número |
| Próximas a vencer | Indicador | Períodos | En progreso con 7 días restantes o menos. | Número |
| Finalizadas | Indicador | Períodos | Cerrados, con el desglose "X a tiempo · Y fuera de plazo". | Número y desglose |
| Próximos vencimientos | Lista | Períodos | Los 6 no finalizados con vencimiento más cercano (incluye los vencidos). Cada fila muestra obligación, período, responsable, estado y fecha. Al hacer clic, abre el detalle. | Detalle |
| Cierres recientes | Lista | Períodos | Los 5 cerrados con la validación más reciente. | Detalle |
| Ver matriz completa | Botón | Clic | Abre la Matriz. | — |
| Nueva obligación | Botón | Clic | Abre el formulario (5.6) si el usuario tiene permiso `crear`. | Formulario |
| Recorrido guiado | Botón | Clic | Igual que en la barra superior. | Tour |

Los indicadores se recalculan cada vez que se dibuja la vista, con la hora actual. Producción: el servidor los calcula con la zona horaria de la empresa (sección 6).

### 5.4 Matriz de obligaciones

Objetivo: lista operativa de todos los períodos. Cada fila es un vencimiento independiente.

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Buscar | Texto | Texto libre | Coincidencia parcial, sin distinguir mayúsculas, en nombre, código, responsable, entidad y área. Producción: ignorar también los acentos. | Tabla filtrada |
| Área, Entidad, Responsable | Listas | Valor | Muestran solo los valores presentes en la empresa activa. | Tabla filtrada |
| Prioridad | Lista | Alta, Media o Baja | Igualdad exacta. | Tabla filtrada |
| Estado | Lista | Incumplido, En progreso o Finalizado | Filtra por el grupo de estado. Producción: añadir las etapas (Sin iniciar, En preparación, Pendiente de validación, Vence hoy). | Tabla filtrada |
| Sin agrupar / Por área / Por entidad | Botones excluyentes | Clic | Agrupa las filas con un encabezado por grupo y su cantidad. Los grupos van en orden alfabético de su código. | Tabla agrupada |
| Limpiar filtros | Botón (solo si hay filtros) | Clic | Vacía todos los filtros y deja la agrupación. | Tabla completa |
| Encabezados que ordenan | Columnas | Clic | Obligación, Área, Entidad, Responsable, Vencimiento y Estado. Un segundo clic invierte el orden. El orden por defecto es por urgencia: primero los incumplidos (los más atrasados arriba), luego en progreso (menos días restantes primero) y al final los finalizados. | Tabla ordenada |
| Columna Días | Calculado | Período | "+N d atraso" en rojo, "Vence hoy", "N d restantes" en azul, "N d atraso (cerrado)" o "—". | Texto |
| Columna Estado | Etiqueta | Período | Color según el estado (sección 6). | Etiqueta |
| Ver documentos | Icono por fila | Clic | Abre el visor (5.9). | Visor |
| Cargar evidencia | Icono por fila | Clic | **\[Mockup\]** Abre la ventana de carga sin comprobar permisos. Producción: aplicar `cargar` y que el período sea del usuario, como en el detalle. | Ventana de carga |
| Clic en la fila | Fila | Clic | Abre el detalle (5.5). | Detalle |
| Exportar reporte | Botón | Clic | **\[Mockup\]** Solo muestra un aviso. Producción: genera un PDF o Excel con los filtros aplicados. | Archivo |
| Nueva obligación | Botón | Clic | Formulario (5.6). | Formulario |
| Vista móvil | Tarjetas (880 px o menos) | — | Mismo contenido que la tabla, con los botones "Documentos" y "Cargar". | — |

Producción: paginar en el servidor (el mockup dibuja todas las filas) y recordar los filtros por usuario.

### 5.5 Detalle del período (panel lateral)

Objetivo: expediente completo de un período. La cabecera muestra el código, el período, el nombre, la etiqueta de estado, el tipo y la empresa. Tiene 4 pestañas y un botón para cerrar (también con la tecla Esc o con clic fuera del panel).

**Pestaña General**

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Identificación | Solo lectura | Período y plantilla | Código, empresa y sucursal, área, entidad, tipo, periodicidad, descripción, fuente. **\[Mockup\]** El enlace "ver documento de referencia" no lleva a ninguna parte. Producción: abrir la URL o el archivo de la norma. | — |
| Fechas del período | Solo lectura | Período | Inicio, preparación interna, vencimiento con fecha y hora. Si está cerrado, también el cumplimiento y la validación (con fecha y quién validó). | — |
| Editar fecha (lápiz) | Botón | Clic | Solo visible con permiso `editar` o `configurar`. Abre la ventana de cambio de fecha (5.7). | Ventana |
| Responsables | Solo lectura | Período | Responsable principal con su correo, suplente, supervisor y aprobador. | — |
| Seguimiento | Solo lectura | Período | Prioridad con color, avance con barra, observaciones. Producción: el avance y las observaciones deben poder editarse. | — |
| Enviar a validación | Botón (abierto y no pendiente de validación) | Clic | Requiere permiso `cargar`, que el período sea del usuario y al menos un documento válido. Si falta la evidencia, muestra "Debe cargar la evidencia requerida (...) antes de enviar a validación". Cambia la etapa a pendiente\_validacion, pone el avance en 95 % y registra "Enviado a validación" en el historial. | Etapa actualizada |
| Validar y finalizar | Botón (abierto y pendiente de validación) | Clic | Requiere permiso `validar` y evidencia válida. Cierra el período, suspende los recordatorios, registra el cumplimiento y la validación con la fecha de hoy y quién valida. Si ya pasó el vencimiento, lo marca "fuera de plazo". | Período finalizado |
| Cargar evidencia | Botón (abierto) | Clic | Requiere `cargar` y que el período sea del usuario. Abre la ventana de carga (5.8). | Ventana |
| Simular recordatorio ahora | Botón | Clic | Si los recordatorios están suspendidos, muestra "Sin envío". Si no, registra un aviso "Enviado" al responsable. **\[Mockup\]** No sale ningún correo. Producción: "Reenviar recordatorio" llama al servicio de correo. | Notificación |
| Aviso de suspendidos | Mensaje | Período cerrado | "Los recordatorios de este período están suspendidos..." | — |

**Pestaña Documentos**

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Cargar PDF | Botón | Clic | Deshabilitado si el usuario no tiene `cargar` o el período no es suyo. | Ventana de carga |
| Fila de documento válido | Lista | Documentos | Nombre, versión, tamaño, fecha y quién lo cargó. Botones Ver (visor), Descargar e Imprimir. **\[Mockup\]** Descargar e Imprimir solo muestran un aviso. | Visor o archivo |
| Fila de documento rechazado | Lista | Documentos | Fondo rojo, con el motivo del rechazo (p. ej. "Formato no permitido (.docx)"). Botón Eliminar, que lo quita y registra "Documento rechazado eliminado". Producción: marcar como eliminado en lugar de borrar, y comprobar que el período sea del usuario. | Lista actualizada |
| Sin documentos | Mensaje | Lista vacía | "Sin documentos. Aún no se ha cargado evidencia para este período." | — |
| Aviso de permisos | Mensaje | Rol | Sin `cargar`: "Su rol (...) tiene acceso de solo lectura". Responsable de otro período: "Sin permisos: esta obligación no está asignada a su usuario". | — |

Falta definir quién rechaza un documento válido y con qué motivo. El mockup solo genera rechazos de ejemplo, y producción necesita un botón "Rechazar evidencia" para el validador.

**Pestaña Recordatorios**

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Avisos programados | Lista calculada | Vencimiento y configuración | Por cada anticipación N: fecha = vencimiento − N días, a la hora configurada. Muestra "Enviado" si esa fecha ya pasó y "Programado" si no. Si el período está cerrado: "Suspendidos". **\[Mockup\]** "Enviado" solo significa que la fecha ya pasó. Producción: se lee el estado real de la notificación. | Lista |
| Historial de notificaciones | Lista | Notificaciones del período | Tipo de aviso, destinatario, fecha y estado (Enviado o Fallido). | Lista |
| Vista previa del correo | Botón | Clic | Abre la vista previa (5.10). | Ventana |
| Simular envío ahora | Botón | Clic | Igual que en la pestaña General. | Notificación |

**Pestaña Historial**

Línea de tiempo ordenada por fecha. Cada evento muestra cuándo, la acción, el usuario y el motivo, y en los cambios de fecha, "Valor anterior → Nuevo". Es de solo lectura. **\[Mockup\]** Los cambios de fecha se agregan al final sin ordenar.

### 5.6 Nueva obligación

Objetivo: dar de alta una obligación y su primer período. Solo para quien tiene permiso `crear`.

| Campo | Tipo | Obligatorio | Valor por defecto o regla |
| --- | --- | --- | --- |
| Nombre de la obligación | Texto | Sí | — |
| Descripción | Texto | No | "Sin descripción registrada." |
| Empresa / sucursal | Lista de empresas | Sí | La empresa activa. **\[Mockup\]** La sucursal queda fija en "Matriz". Producción: lista de sucursales de la empresa. |
| Área responsable | Lista (8) | Sí | La primera de la lista. |
| Entidad de control | Lista (8) | Sí | La primera de la lista. |
| Tipo | Lista | Sí | Regulatoria. |
| Fuente o fundamento | Texto o enlace | No | "Registro interno de la empresa." |
| Periodicidad | Lista (5) | Sí | Anual. |
| Período que corresponde | Texto | No | "Período único". Producción: generarlo a partir de la periodicidad y la fecha. |
| Fecha de inicio | Fecha | No | **\[Mockup\]** 5 días antes de hoy si se deja vacía. Producción: vencimiento − 30 días. |
| Fecha interna de preparación | Fecha | No | **\[Mockup\]** 2 días antes de hoy si se deja vacía. Producción: vencimiento − 5 días. |
| Fecha de vencimiento | Fecha | Sí | — |
| Hora de vencimiento | Hora | Sí | 17:00. |
| Responsable principal | Texto | No en el mockup, sí en producción | Si se deja vacío, el mockup inventa un nombre. Producción: elegir entre los usuarios de la empresa. |
| Correo del responsable | Correo | — | Producción: se toma de la ficha del usuario. |
| Suplente, Supervisor | Texto | No | "Por asignar". Producción: elegir entre los usuarios. |
| Aprobador | Texto | No | El gerente general de la empresa. |
| Prioridad | Lista | Sí | Alta. |
| Observaciones | Texto | No | — |
| Evidencia esperada | No existe en el mockup | Sí en producción | Hoy queda "Documento de respaldo". |

**Botón Crear obligación:** comprueba el nombre y la fecha de vencimiento ("Ingrese al menos el nombre y la fecha de vencimiento"). Crea la plantilla y un período con código nuevo, etapa sin\_iniciar y avance 0 %, registra "Obligación creada", abre la Matriz y luego el detalle del período nuevo.

**Producción:**

- Si la periodicidad es recurrente, generar los períodos siguientes automáticamente (sección 6.5).
- Validar el orden de las fechas.
- Avisar si ya existe una obligación con el mismo nombre en esa empresa.
- Agregar la opción de editar la plantilla y el período. El código de edición existe en el mockup, pero ningún botón lo usa, y al guardar crearía un duplicado.

### 5.7 Cambio de fecha de vencimiento

| Campo o botón | Regla |
| --- | --- |
| Aviso | "Este cambio queda registrado en el historial junto con la fecha anterior y no puede eliminarse." |
| Fecha y hora actual | Solo lectura. |
| Nueva fecha | Obligatoria. Producción: no puede ser anterior a la fecha de inicio. |
| Nueva hora | Opcional, 17:00 por defecto. |
| Justificación | Obligatoria. Producción: mínimo 10 caracteres. |
| Guardar cambio | Comprueba la fecha y la justificación. Guarda la nueva fecha y registra el cambio (usuario, motivo, valor anterior, valor nuevo). Producción: recalcular los recordatorios pendientes y, en un período cerrado, conservar el atraso original. |
| Cancelar / X | Cierra sin cambios. |

### 5.8 Cargar evidencia

| Elemento | Tipo | Entrada | Proceso o regla | Salida |
| --- | --- | --- | --- | --- |
| Texto guía | Texto | Plantilla | Obligación, período, documento esperado, "Solo se aceptan archivos PDF de hasta 10 MB. Puede cargar varios documentos." | — |
| Zona de arrastre | Arrastrar y soltar | Archivos | Se resalta al pasar un archivo por encima. Procesa cada archivo por separado. | Lista de carga |
| Elegir archivo | Selector de archivos (varios) | Archivos | Igual que arrastrar. | Lista de carga |
| Validación de formato | Regla | Nombre | Si no termina en .pdf: "formato no permitido. Solo se aceptan archivos PDF." **\[Mockup\]** Solo revisa la extensión. Producción: revisar también el tipo MIME y la firma `%PDF` en el servidor, y pasar un antivirus. | Alerta |
| Validación de tamaño | Regla | Tamaño | Más de 10 MB: "supera el tamaño máximo permitido (10 MB)." Producción: repetir el límite en el servidor. | Alerta |
| Barra de progreso | Por archivo | — | **\[Mockup\]** Avanza con un temporizador. Producción: progreso real de la subida. | Porcentaje |
| Carga fallida | Regla | — | **\[Mockup\]** Falla a propósito si el nombre contiene "fall" o "error". Producción: error real de red o del servidor, con opción de reintentar. | Alerta roja |
| Guardar en el expediente | Botón (activo cuando hay al menos 1 archivo correcto) | Clic | Agrega los documentos (versión v1, tamaño, fecha, usuario, estado válido) y registra "Evidencia cargada (N documento(s))". Producción: guardar el archivo en el almacenamiento, calcular el hash y numerar la versión si el nombre se repite. | Documentos guardados |
| Cerrar / X | Botón | Clic | Cierra la ventana. Los archivos ya subidos que no se guardaron se pierden. | — |

### 5.9 Visor de documentos

| Elemento | Proceso o regla |
| --- | --- |
| Lista lateral | Documentos válidos del período. Al hacer clic, se cambia el documento activo y se vuelve a la página 1. Si no hay ninguno: "Sin documentos: aún no hay evidencia cargada para este período." |
| Página anterior / siguiente | Navega entre páginas. **\[Mockup\]** Siempre son 3 páginas ficticias. Producción: el PDF real, por ejemplo con PDF.js, y el número real de páginas. |
| Zoom + / − | Escala la página mostrando el porcentaje. Producción: límites del 50 % al 300 %. |
| Imprimir | Imprime siempre el documento activo. **\[Mockup\]** Solo muestra un aviso. |
| Descargar | **\[Mockup\]** Solo muestra un aviso. Producción: enlace temporal firmado y registro de quién descargó. |

### 5.10 Vista previa del correo

Muestra el correo que recibiría el responsable:

- **Para:** el correo del responsable.
- **Asunto:** "Recordatorio de vencimiento — \[Obligación\] (\[Período\])".
- **Saludo:** "Estimado(a) \[Responsable\]".
- **Tabla:** obligación, período, empresa, entidad de control, responsable, vencimiento con fecha y hora, estado actual.
- **Enlace:** "Consultar el detalle y cargar el PDF de evidencia". **\[Mockup\]** No funciona.

Producción: plantilla HTML en el servicio de correo, con un enlace directo al detalle del período que exija iniciar sesión. Hacen falta variantes para el escalamiento (al supervisor, con los días de atraso) y para el aviso del día del vencimiento.

### 5.11 Calendario

| Elemento | Proceso o regla |
| --- | --- |
| Mes anterior, mes siguiente, Hoy | Cambian el mes que se muestra. Pasan de diciembre a enero y viceversa. |
| Cuadrícula | 7 columnas, la semana empieza en domingo. El día de hoy aparece con borde azul. |
| Etiquetas por día | Hasta 3 períodos por día, coloreados por estado (rojo incumplido, tomate en progreso, verde finalizado), y "+N más" si hay más. Al hacer clic, abre el detalle. Producción: "+N más" debe abrir la lista del día. |
| Leyenda | Los 3 colores de estado. |

### 5.12 Documentos

Dos tarjetas: "Expedientes con evidencia (N)" y "Pendientes de evidencia (N)". Cada fila muestra obligación, período, cantidad de documentos, responsable y estado, y al hacer clic abre el detalle. Producción: filtros (área, entidad, período), búsqueda por nombre de archivo y paginación. Además, un período que solo tiene documentos rechazados debe contar como pendiente; hoy cuenta como "con evidencia".

### 5.13 Reportes

| Elemento | Regla de cálculo |
| --- | --- |
| Cumplimiento a tiempo | Cerrados a tiempo ÷ total de cerrados × 100, redondeado. Subtítulo: "X de N cierres". |
| Cumplimiento tardío | Cerrados fuera de plazo ÷ total de cerrados × 100. |
| Incumplidas actuales | Cantidad de períodos incumplidos. |
| En progreso | Cantidad de períodos en progreso. |
| Estado por área | Barra apilada por área (finalizado, en progreso, incumplido), con el total al lado. |
| Estado por entidad | Lo mismo, agrupado por entidad de control. |
| Exportar PDF / Excel | **\[Mockup\]** Solo muestran un aviso. Producción: archivos reales con la empresa, la fecha de corte y el usuario que exportó. |

Producción: filtro de rango de fechas o de año (hoy se usan todos los períodos, de cualquier año), comparación entre empresas para el Administrador del grupo y evolución mensual del cumplimiento.

### 5.14 Configuración

Tiene 5 pestañas. Los que no son Administrador las ven en modo lectura, con un aviso.

| Pestaña | Campos y botones | Reglas |
| --- | --- | --- |
| Empresa | Nombre, país, actividad, zona horaria (5 opciones), color institucional, Guardar cambios | Solo Administrador. **\[Mockup\]** El nombre editado no aparece en el menú ni en el encabezado, y el color se pierde al recargar. Producción: guardar en la base y usar la zona horaria en todos los cálculos de vencimiento. |
| Recordatorios | Lista de anticipaciones (1 a 90 días) con hora; el aviso del día del vencimiento no se puede quitar; botones Eliminar, Añadir anticipación, Escalar a la jefatura (sí o no), Días de atraso antes de escalar (1 a 30), Guardar configuración | **\[Mockup\]** "Añadir" siempre agrega 2 días, aunque ya exista; hay un campo de hora por fila, pero solo se guarda la primera. Producción: una sola hora por empresa, anticipaciones sin repetir y recalcular los avisos pendientes. |
| Recordatorios: historial global | Últimas 25 notificaciones de la empresa: obligación, tipo, destinatario, fecha, estado. Botón Reintentar en las fallidas. | El reintento marca la original como "Reintentado" y crea un envío nuevo, sin duplicar. Producción: reintento automático con espera creciente (por ejemplo 3 intentos) y después solo manual. |
| Usuarios y roles | Lista de usuarios de la empresa (nombre, correo, rol) y matriz de permisos | Producción: crear, editar, bloquear y asignar roles por empresa y por área; invitar por correo. |
| Auditoría | Hasta 120 eventos de la empresa: acción, obligación, período, usuario, fecha, motivo | **\[Mockup\]** Sin orden por fecha y sin filtros. Producción: orden de más reciente a más antiguo, filtros por usuario, acción y fechas, paginación y exportación. Incluir los inicios de sesión y los cambios de configuración. |
| Qué está simulado | Texto informativo | Se elimina en producción. |

### 5.15 Recorrido guiado

Tiene 7 pasos con tarjeta flotante, resaltado del elemento, botones Atrás, Siguiente ("Finalizar recorrido" en el último paso) y X para salir, puntos de avance y la barra "paso N de 7". Trabaja sobre el período de LC "Demostración — mes en curso" (IVA, prioridad Alta).

1. **Crear** → botón Nueva obligación.
2. **Asignar** → campo Responsable.
3. **Consultar** → fecha de vencimiento en el detalle.
4. **Recordar** → Simular envío.
5. **Cargar** → zona de arrastre.
6. **Revisar** → visor. Si el período no tiene documentos, el tour agrega uno de ejemplo.
7. **Finalizar** → Validar y finalizar. El tour fuerza la etapa "pendiente de validación".

Al terminar muestra "Recorrido finalizado". **\[Mockup\]** El tour cambia datos (agrega un documento y cambia la etapa) y fuerza la empresa LC. Producción: convertirlo en una ayuda que no modifique datos reales, o quitarlo.

## 6. Motor de estados y lógica de negocio

El estado de un período **no se guarda: se calcula** en cada consulta a partir de 3 datos: si está cerrado, la fecha y hora de vencimiento y la hora actual. Solo la **etapa** (sin iniciar, en preparación, pendiente de validación) la cambian las personas. Producción debe calcularlo en el servidor con la zona horaria de la empresa, no con la hora del navegador.

### 6.1 Cálculo del estado (`occStatus`)

Se evalúa en este orden:

| # | Condición | Estado | Etiqueta | Color | Dato calculado |
| --- | --- | --- | --- | --- | --- |
| 1 | Cerrado y cumplimiento ≤ vencimiento | Finalizado | Finalizado | Verde | — |
| 2 | Cerrado y cumplimiento > vencimiento | Finalizado | Finalizada fuera de plazo | Verde | Días de atraso = cumplimiento − vencimiento |
| 3 | Abierto y ahora > vencimiento | Incumplido | Incumplido | Rojo | Días de atraso = ahora − vencimiento, redondeado |
| 4 | Abierto y vence hoy (mismo día calendario) | En progreso | Vence hoy | Tomate #FF6347 | Días restantes = 0 |
| 5 | Abierto, dentro del plazo | En progreso | Sin iniciar, En preparación o Pendiente de validación, según la etapa | Tomate | Días restantes = vencimiento − ahora, redondeado |

La fecha de vencimiento efectiva es la fecha cambiada, si existe. Si no, la fecha del período con su hora (17:00 por defecto).

**Defecto que hay que corregir:** la regla 4 devuelve la etapa `vence_hoy` y descarta la etapa real. Por eso, el día del vencimiento, un período que ya está pendiente de validación muestra "Enviar a validación" y no "Validar y finalizar", y se puede enviar varias veces (confirmado en la prueba con OBL-0055). Producción: "Vence hoy" es una marca aparte, no una etapa.

### 6.2 Flujo de cierre

&#91;embedded content: flujo de cierre · 4 etapas y el estado Incumplido\]

Las líneas rojas punteadas indican que cualquier etapa abierta pasa a Incumplido al vencer. "Devolver" y el paso automático a En preparación son nuevos: no existen en el mockup.

1. **Sin iniciar.** Avance 0 %. Es la etapa al crear o generar el período.
2. **En preparación.** **\[Mockup\]** Solo existe en los datos de ejemplo: ningún botón lleva a esta etapa. Producción: pasar a En preparación automáticamente al cargar la primera evidencia, o con un botón "Iniciar".
3. **Pendiente de validación.** Se llega con "Enviar a validación". Requisitos: rol con `cargar`, ser responsable o suplente, y al menos un documento válido. Avance 95 %.
4. **Finalizado.** Se llega con "Validar y finalizar". Requisitos: rol con `validar` y evidencia válida. Efectos: cerrado, recordatorios suspendidos, fecha de cumplimiento y de validación = hoy, se registra quién validó, evento en el historial y "fuera de plazo" si ya había vencido.
5. **Rechazo (nuevo en producción).** Desde Pendiente de validación, el validador puede devolver el período a En preparación con un motivo obligatorio, y marcar documentos como rechazados.

En todo momento, aunque esté en progreso, si se supera el vencimiento sin cierre, el período pasa a Incumplido. Desde Incumplido se puede seguir cargando evidencia, enviar a validación y finalizar: el resultado es "Finalizada fuera de plazo".

**Producción:** guardar el avance también en los demás cambios (hoy solo cambia al enviar a validación). Decidir si la fecha de cumplimiento es la del envío a validación o la de la validación. El mockup usa el día de la validación, así que una demora del supervisor cuenta como atraso del responsable.

### 6.3 Cambio de fecha de vencimiento

- Requiere permiso `editar` o `configurar` y una justificación obligatoria.
- Guarda la nueva fecha y hora, y conserva la fecha anterior y el motivo en un historial que no se puede borrar.
- El estado se recalcula al momento: un período incumplido puede volver a "En progreso" si la nueva fecha es futura.
- **Producción:** definir si se permite en un período cerrado y si un período que ya estaba incumplido conserva ese atraso en los reportes. Hoy el atraso desaparece.

### 6.4 Recordatorios y escalamiento

| Regla | Valor por defecto | Detalle |
| --- | --- | --- |
| Anticipaciones | 15, 7, 3 y 1 días antes, y el día del vencimiento | Configurables de 1 a 90 días. El aviso del día del vencimiento siempre existe. |
| Hora de envío | 08:00 | Hora local de la empresa. |
| Destinatario | Responsable | Producción: copia al suplente. |
| Escalamiento | Activo, a los 2 días de atraso | Aviso a la jefatura (supervisor). **\[Mockup\]** Está configurado pero nunca se ejecuta. Producción: un proceso diario lo dispara. Hay que definir si se repite y a quién va después del supervisor (informe, próximo paso 4). |
| Suspensión | Al validar el cierre | No se envía nada más para ese período. |
| Fallos | Estado "Fallido" con contador de reintentos | Reintento manual que no duplica el aviso original. Producción: reintento automático. |
| Sin duplicados | — | Producción: un mismo aviso (período, tipo, destinatario) se envía una sola vez, aunque el proceso se ejecute dos veces. |

### 6.5 Generación de períodos

El mockup genera los períodos de ejemplo con "recetas" fijas, para que siempre haya casos de cada estado. Las mensuales tienen 4 períodos (dos meses atrás, el mes pasado, el actual y el siguiente), y las anuales 2 (este año y el anterior). Producción necesita reglas reales:

- Un proceso programado crea el período siguiente de cada obligación activa N días antes de su inicio (propuesta: 30 días) y registra "Registro del período generado — Sistema".
- El vencimiento se calcula con una regla por plantilla: día fijo del mes, fecha fija anual o, para el SRI, según el noveno dígito del RUC. Estas reglas las debe confirmar el área contable (informe, próximo paso 1).
- El período hereda de la plantilla o del período anterior: responsables, prioridad y evidencia esperada.
- Etiqueta: mensual "Octubre 2026", trimestral "T4 2026", semestral "S2 2026", anual "Período 2026", única "Período único".

### 6.6 Otras reglas

- **Código:** `OBL-` + 4 dígitos, secuencial, generado en el servidor. **\[Mockup\]** Al recargar la página, el contador vuelve al número que sigue a los datos de ejemplo, así que repite códigos de obligaciones creadas antes.
- **"Es mío":** el usuario es el responsable o el suplente del período. Los roles Administrador, Supervisor y Auditor se consideran dueños de todo.
- **Contador del menú:** períodos de la empresa incumplidos o que vencen hoy.
- **Próximas a vencer:** en progreso con 7 días restantes o menos.
- **Formato:** fecha "2 oct. 2026", hora en 12 horas "5:00 p. m.", moneda en dólares con formato es-EC (la función existe, pero ninguna pantalla la usa).

## 7. Integraciones y procesos de servidor

Todo lo que el mockup simula pasa a 5 servicios y 4 procesos programados. El mockup guarda todo en el `localStorage` de cada navegador (clave `matriz_admin_demo_v1`), así que ningún usuario ve los cambios de otro.

| Servicio | Función | Requisitos |
| --- | --- | --- |
| Base de datos relacional | Guardar el modelo de la sección 3 | Transacciones en el cierre y en el cambio de fecha. Copia de seguridad diaria. Historial de solo inserción. |
| Proveedor de identidad | Inicio de sesión | SSO corporativo o usuario y contraseña con política, bloqueo tras intentos fallidos, recuperación de contraseña y cierre de sesión por inactividad. Ninguna contraseña en el código. |
| Almacenamiento de documentos | Guardar los PDF | Privado, con versiones, cifrado, enlaces de descarga temporales y antivirus al subir. Ruta propuesta: empresa/año/código de período/versión. |
| Servicio de correo | Recordatorios y escalamientos | Plantillas HTML, registro de entrega y rebote, dominio corporativo verificado (SPF y DKIM). |
| Generador de reportes | Exportar PDF y Excel | Respeta los filtros y el rol. Incluye la fecha de corte. |

### Procesos programados

| Proceso | Frecuencia | Qué hace |
| --- | --- | --- |
| Generar períodos | Diario | Crea los períodos siguientes según la periodicidad (6.5). |
| Enviar recordatorios | Diario, a la hora configurada por empresa | Por cada período abierto con aviso pendiente para hoy, envía el correo y registra la notificación, sin duplicar. |
| Escalar atrasos | Diario | Períodos incumplidos con N o más días de atraso: aviso al supervisor. |
| Reintentar fallidos | Cada hora | Reintenta las notificaciones fallidas hasta el límite de intentos. |

### Servicios de la aplicación (API)

Cada acción de la interfaz se convierte en una llamada al servidor, que comprueba el rol, la empresa y si el período es del usuario:

| Acción | Llamada propuesta |
| --- | --- |
| Iniciar y cerrar sesión, cambiar de empresa | `POST /auth/login`, `POST /auth/logout`, `POST /session/company` |
| Indicadores del Resumen y Reportes | `GET /companies/{id}/dashboard`, `GET /companies/{id}/reports` |
| Matriz con filtros, orden y página | `GET /companies/{id}/periods?q=&area=&entidad=&responsable=&prioridad=&estado=&sort=&page=` |
| Detalle del período | `GET /periods/{id}` |
| Crear o editar una obligación | `POST /obligations`, `PATCH /obligations/{id}`, `PATCH /periods/{id}` |
| Cambiar la fecha | `POST /periods/{id}/due-date` (con la justificación) |
| Subir, ver o descargar evidencia, rechazar o eliminar un documento | `POST /periods/{id}/documents`, `GET /documents/{id}/url`, `POST /documents/{id}/reject`, `DELETE /documents/{id}` (marca, no borra) |
| Enviar a validación, validar, devolver | `POST /periods/{id}/submit`, `POST /periods/{id}/validate`, `POST /periods/{id}/return` |
| Recordatorios | `GET /periods/{id}/reminders`, `POST /periods/{id}/reminders/send`, `POST /notifications/{id}/retry` |
| Configuración | `GET/PUT /companies/{id}/settings`, `GET/PUT /companies/{id}/reminder-config` |
| Usuarios y roles | `GET/POST/PATCH /users`, `PUT /users/{id}/roles` |
| Auditoría | `GET /companies/{id}/audit?user=&action=&from=&to=` |
| Calendario | `GET /companies/{id}/periods?from=&to=` |

## 8. Defectos y brechas del mockup

Hay 20 puntos que no deben pasar a producción tal como están. Los dos críticos son la contraseña real escrita en el código de un artefacto público y que las reglas solo se validan en el navegador. La severidad es editable.

| # | Severidad | Hallazgo | Dónde | Corrección en producción |
| --- | --- | --- | --- | --- |
| 1 | Crítica | La cuenta "Christian Coque" tiene la clave `Financiero1234` escrita en el código de un artefacto público. El informe también la publica. | `buildUsers`; Informe, sección 7 | Cambiar la clave si se usa en otro sistema, quitarla del mockup y del informe, y usar el proveedor de identidad. |
| 2 | Crítica | Todos los permisos se aplican solo en el navegador: cualquiera puede saltarlos desde la consola. | `can()`, `isMine()` | Validar cada acción en el servidor (sección 4). |
| 3 | Alta | El Responsable ve todos los períodos de la empresa. | `companyOccs` | Filtrar por responsable o suplente. |
| 4 | Alta | Cualquier usuario cambia a otra empresa conservando su rol. | Selector de empresa | Mostrar solo las empresas donde tiene rol, cada una con su propio rol. |
| 5 | Alta | El día del vencimiento no aparece "Validar y finalizar" y se puede reenviar a validación varias veces. | `occStatus`, regla 4 | Separar la marca "Vence hoy" de la etapa (6.1). |
| 6 | Alta | No hay separación de funciones: el Administrador valida evidencia que él mismo cargó. | Validar y finalizar | Impedir que quien carga o envía valide el mismo período. |
| 7 | Alta | El icono "Cargar" de la Matriz abre la carga sin comprobar permisos. | `renderMatrixTable` | Aplicar la misma regla que en el detalle. |
| 8 | Media | Eliminar un documento rechazado no comprueba de quién es el período, y lo borra del todo. | `data-remove-doc` | Comprobar el dueño y marcar como eliminado. |
| 9 | Media | La regla de cambio de fecha no coincide con su aviso: el Responsable sí puede cambiarla y el Supervisor no. | `bindDetailActions` | Definir la regla (sección 4) y alinear el mensaje. |
| 10 | Alta | El escalamiento está configurado, pero nunca se ejecuta. | Recordatorios | Proceso programado de escalamiento (sección 7). |
| 11 | Alta | La validación de PDF solo revisa la extensión. | `handleFiles` | Revisar el tipo MIME y la firma en el servidor, y pasar antivirus. |
| 12 | Media | No existe la acción de rechazar evidencia ni de devolver un período. | Detalle | Agregar "Rechazar" y "Devolver" con motivo (6.2). |
| 13 | Media | El formulario de edición no tiene botón, y al guardar crearía un duplicado. | `openObligationForm` | Editar la plantilla y el período por separado. |
| 14 | Alta | Una obligación creada genera un solo período, aunque sea mensual. | Nueva obligación | Generar los períodos automáticamente (6.5). |
| 15 | Media | Los responsables son texto libre, comparados por nombre. | Modelo del período | Guardarlos como referencias a usuarios. |
| 16 | Media | La configuración de recordatorios es una sola para todo el grupo; "Añadir" duplica los 2 días y solo se guarda la primera hora. | Configuración de recordatorios | Configuración por empresa, sin anticipaciones repetidas y con una sola hora. |
| 17 | Media | La zona horaria de la empresa solo se muestra en pantalla: los cálculos usan la hora del navegador. | `occStatus`, Configuración de empresa | Calcular con la zona horaria de la empresa. |
| 18 | Baja | El nombre editado de la empresa no se ve en ninguna parte, y el color se pierde al recargar. | Configuración de empresa | Guardar en la base y mostrarlo en el menú y los encabezados. |
| 19 | Baja | Un período con solo documentos rechazados aparece "con evidencia". | Vista Documentos | Contar solo documentos válidos. |
| 20 | Media | El código `OBL-` puede repetirse después de recargar, y la etapa "En preparación" no tiene botón que lleve a ella. | `nextCode`, flujo | Código secuencial en el servidor y transición a En preparación (6.2). |

### Diferencias entre el informe y el mockup

| Tema | Informe | Mockup | Propuesta |
| --- | --- | --- | --- |
| El Responsable ve | "Solo las propias" | Todas | Lo que dice el informe |
| El Responsable crea y edita | "Sí (propias)" | Crea en cualquier área; no puede editar | Crear en su área y editar lo suyo |
| El Auditor | Solo consulta | Puede simular recordatorios y exportar | Solo consulta y exportar |
| Escalamiento | "Contempla escalar al supervisor" | No se ejecuta | Implementarlo (sección 7) |

## 9. Requisitos no funcionales, criterios de aceptación y fases

Se propone construir en 4 fases. Siguiendo al informe, se empieza por la base de datos y el almacenamiento de documentos, y el correo automático queda para la segunda etapa.

### 9.1 Requisitos no funcionales

| Tema | Requisito |
| --- | --- |
| Seguridad | HTTPS; sesión con vencimiento por inactividad (propuesta: 30 minutos); permisos comprobados en el servidor; nada sensible en el código del navegador; protección CSRF y XSS (el mockup ya escapa el texto con `esc()`, y debe mantenerse). |
| Trazabilidad | Todo cambio queda en un historial que no se puede borrar: usuario, fecha y hora, acción, motivo, valor anterior y nuevo. |
| Documentos | PDF de hasta 10 MB, con versiones y sin borrado físico. El plazo de conservación lo define legal. |
| Zona horaria | Todos los cálculos con la zona de la empresa; fechas guardadas en UTC. |
| Interfaz | Mantener el diseño del mockup: modo claro y oscuro, tarjetas en pantallas de 880 px o menos, navegación con teclado y Esc para cerrar ventanas. |
| Rendimiento | La Matriz paginada responde en menos de 2 segundos con 5.000 períodos por empresa (cifra propuesta). |
| Disponibilidad | Copia de seguridad diaria, y los procesos programados se pueden ejecutar dos veces sin duplicar nada. |
| Idioma y formato | Español; fechas "2 oct. 2026"; hora "5:00 p. m."; dólares en formato es-EC. |

### 9.2 Criterios de aceptación

- [ ] Un Responsable solo ve y modifica los períodos donde es responsable o suplente. Una llamada directa a la API sobre otro período devuelve 403.
- [ ] Un usuario sin rol en una empresa no puede entrar a ella, ni desde el login ni desde el selector.
- [ ] Sin un documento válido no se puede enviar a validación ni finalizar, ni desde la interfaz ni desde la API.
- [ ] El día del vencimiento, un período pendiente de validación muestra "Validar y finalizar" a quien tiene permiso de validar.
- [ ] Quien cargó la evidencia no puede validar ese mismo período.
- [ ] Un período abierto pasa a Incumplido justo después de la hora de vencimiento en la zona horaria de la empresa.
- [ ] Un cierre después del vencimiento queda como "Finalizada fuera de plazo", con sus días de atraso en Reportes.
- [ ] Un cambio de fecha sin justificación se rechaza; con justificación, queda en el historial con el valor anterior.
- [ ] Un archivo que no es PDF, aunque tenga extensión .pdf, se rechaza en el servidor.
- [ ] Los recordatorios llegan 15, 7, 3 y 1 día antes y el día del vencimiento a la hora configurada, una sola vez cada uno, y dejan de enviarse al validar.
- [ ] Con 2 días de atraso se envía el escalamiento al supervisor.
- [ ] Un envío fallido se puede reintentar sin duplicar el aviso original.
- [ ] Las exportaciones a PDF y Excel coinciden con lo que se ve en pantalla con los mismos filtros.
- [ ] Ninguna contraseña aparece en el código, la base de datos ni la documentación.

### 9.3 Fases de desarrollo

1. **Fase 1. Base, acceso y matriz.** Base de datos y catálogos; proveedor de identidad; usuarios y roles por empresa; Resumen, Matriz, Detalle, Nueva y editar obligación; motor de estados en el servidor; historial. Requisito previo: lista real de obligaciones, responsables y correos (informe, próximos pasos 1 y 2).
2. **Fase 2. Evidencias y cierre.** Almacenamiento de documentos, carga, visor PDF, descarga e impresión; enviar a validación, validar, rechazar y devolver; cambio de fecha; vista Documentos.
3. **Fase 3. Recordatorios y escalamiento.** Servicio de correo y plantillas; procesos programados de recordatorios, escalamiento y reintentos; configuración por empresa; historial de notificaciones. Requisito previo: política de escalamiento aprobada por legal y gerencia (informe, próximo paso 4).
4. **Fase 4. Reportes, calendario y auditoría.** Calendario; Reportes con filtros de fecha y exportación real; Auditoría con filtros; generación automática de períodos; ayuda guiada sin modificar datos.

### 9.4 Decisiones pendientes

- ¿Quién puede cambiar la fecha de vencimiento: Responsable, Supervisor o solo el Administrador?
- ¿La fecha de cumplimiento es la del envío a validación o la de la validación?
- ¿A quién se escala después del supervisor, y cada cuántos días se repite el escalamiento?
- Reglas de vencimiento por obligación: días fijos, calendario del SRI por RUC y feriados.
- Plazo de conservación de los documentos.
- ¿SSO corporativo o usuario y contraseña propios?

## 10. Plan de ejecución por fases

El proyecto completo tiene 9 fases en 3 etapas, desde el acta de inicio hasta la estabilización en las 3 empresas. La estimación referencial es de 22 a 33 semanas. Cada etapa termina en una aprobación (G1, G2, G3) sin la cual no empieza la siguiente.

&#91;embedded content: hoja de ruta · 9 fases, 3 etapas, 3 aprobaciones\]

Las fases de construcción F3 a F6 corresponden a las fases de desarrollo de la sección 9.3. Este plan agrega la preparación, las pruebas integrales y la puesta en marcha. F1 y F2 pueden solaparse unas 2 semanas: el diseño técnico avanza mientras se cierran las reglas de vencimiento.

### 10.1 Resumen de fases

Las duraciones son estimaciones referenciales para un equipo de unas 4 personas (líder técnico, 2 desarrolladores y QA, con apoyo de diseño). Hay que validarlas con el proveedor en la cotización.

| Fase | Etapa | Duración estimada (semanas) | Entregable principal | Criterio de salida |
| --- | --- | --- | --- | --- |
| F0 Inicio y gobierno | Preparar | 1–2 | Acta de inicio, alcance y contrato | Patrocinador, presupuesto y equipo aprobados |
| F1 Levantamiento | Preparar | 2–3 | Catálogo real de obligaciones, reglas y responsables por empresa | Decisiones de la sección 9.4 firmadas |
| F2 Diseño | Preparar | 2–3 | Arquitectura, modelo de datos, API y pantallas finales | Diseño aprobado (G1) |
| F3 Base y matriz | Construir | 4–6 | Inicio de sesión real, roles, Resumen, Matriz y Detalle | Demo aceptada con datos reales de LC |
| F4 Evidencias y cierre | Construir | 3–4 | Carga, visor, validación, rechazo y cambio de fecha | Demo del flujo de cierre completo aceptada |
| F5 Recordatorios | Construir | 3–4 | Correos automáticos, escalamiento y reintentos | Avisos reales recibidos en buzones de prueba |
| F6 Reportes y auditoría | Construir | 3–4 | Reportes con exportación, Calendario, Auditoría y generación de períodos | Demo aceptada (G2) |
| F7 Pruebas y UAT | Entregar | 2–3 | Informe de pruebas funcionales, de seguridad y de rendimiento | Pruebas de aceptación firmadas (G3) |
| F8 Puesta en marcha | Entregar | 2–4 | Producción en LC, luego en LS y VC; usuarios capacitados | 2 semanas estables y traspaso a soporte |

### 10.2 Actividades por fase

**F0 Inicio y gobierno**

- Nombrar al patrocinador (gerencia), al dueño funcional (área administrativa) y al líder técnico.
- Cotizar con este documento y el informe como base (informe, próximo paso 5), y firmar el contrato.
- Definir el comité de seguimiento, la frecuencia de reuniones y la herramienta de gestión.
- Acción inmediata: cambiar la clave de la cuenta escrita en el mockup y quitarla del mockup y del informe (sección 8, punto 1).

**F1 Levantamiento y decisiones**

- Confirmar con cada área las obligaciones, periodicidades, fundamentos y evidencia esperada de cada empresa (informe, próximo paso 1).
- Levantar la lista de responsables, suplentes, supervisores y aprobadores con sus correos corporativos (informe, próximo paso 2).
- Definir las reglas de vencimiento por obligación (días fijos, calendario del SRI, feriados).
- Cerrar las decisiones de la sección 9.4 con legal y gerencia: escalamiento, fecha de cumplimiento, cambio de fecha, conservación de documentos, SSO.
- Validar la matriz de permisos de la sección 4.

**F2 Diseño técnico y funcional**

- Elegir la tecnología y la nube (sección 2) y preparar los ambientes de desarrollo, pruebas y producción.
- Detallar el modelo de datos (sección 3) y la API (sección 7).
- Ajustar las pantallas del mockup con los cambios de las secciones 5 y 8 (rechazar, devolver, editar, usuarios).
- Definir el plan de pruebas a partir de los criterios de aceptación (9.2) y la arquitectura de seguridad.

**F3 Construcción: base, acceso y matriz**

- Base de datos, catálogos y carga inicial de LC.
- Integración con el proveedor de identidad, usuarios y roles por empresa, y el selector de empresa con permisos.
- Motor de estados en el servidor, con la corrección de "Vence hoy" (6.1).
- Resumen, Matriz (filtros, orden, paginación), Detalle, Nueva y editar obligación, e historial.

**F4 Construcción: evidencias y cierre**

- Almacenamiento de PDF con versiones, validación en el servidor y antivirus.
- Carga, visor PDF, descarga e impresión.
- Enviar a validación, validar con separación de funciones, rechazar y devolver.
- Cambio de fecha con justificación y vista Documentos.

**F5 Construcción: recordatorios y escalamiento**

- Servicio de correo con dominio verificado y plantillas (recordatorio, día del vencimiento, escalamiento).
- Procesos programados de recordatorios, escalamiento y reintentos, sin envíos duplicados.
- Configuración de recordatorios por empresa e historial de notificaciones.

**F6 Construcción: reportes, calendario y auditoría**

- Reportes con filtro de fechas y exportación real a PDF y Excel.
- Calendario, Auditoría con filtros y Configuración de empresa.
- Generación automática de períodos (6.5) y ayuda guiada que no modifique datos.

**F7 Pruebas integrales y aceptación**

- Pruebas funcionales de los criterios de la sección 9.2, por rol y por empresa.
- Prueba de seguridad (permisos por API, carga de archivos, sesión) y prueba de rendimiento con el volumen de 9.1.
- Pruebas de aceptación con usuarios reales de cada rol, y corrección de defectos.

**F8 Puesta en marcha y estabilización**

- Cargar las obligaciones, los períodos abiertos y los usuarios reales. Las evidencias históricas se cargan solo si F1 lo decide.
- Capacitar por rol: Administrador, Responsable, Supervisor y Auditor, con manual corto por rol.
- Piloto en Laarcourier durante 2 semanas; luego Laar Seguridad y Virtual Create.
- Soporte reforzado durante la estabilización, y traspaso a soporte con un acuerdo de nivel de servicio.

### 10.3 Actividades transversales

| Actividad | Durante | Responsable |
| --- | --- | --- |
| Gestión del proyecto: plan, riesgos, avance quincenal al comité | F0–F8 | Jefe de proyecto |
| Control de calidad continuo: pruebas automáticas y revisión de código | F3–F7 | Líder técnico y QA |
| Gestión del cambio: comunicación a las áreas y adopción | F1–F8 | Dueño funcional |
| Seguridad y protección de datos | F2–F8 | Líder técnico |

### 10.4 Riesgos principales

| Riesgo | Efecto | Mitigación |
| --- | --- | --- |
| Las reglas de vencimiento o el escalamiento no se deciden a tiempo | F1 se alarga y retrasa todo | Fechas límite para cada decisión en F0; el dueño funcional decide si no hay consenso |
| La lista de responsables y correos está incompleta | Avisos sin destinatario | Validarla por área en F1 y bloquear la carga de períodos sin responsable |
| Los correos caen en spam | Recordatorios que no llegan | Dominio verificado y pruebas con buzones reales en F5 |
| Baja adopción; se sigue usando hojas de cálculo | El sistema queda sin datos | Piloto en LC, capacitación por rol y reportes a gerencia desde el primer mes |
