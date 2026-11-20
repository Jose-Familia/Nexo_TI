# Nexo TI

**Una mesa de soporte de escritorio, en Python, para registrar, resolver y documentar.**

Versión 1.0.0 · Interfaz en español · Python + Tkinter + SQLite · Sin paquetes externos.

## Iniciar en Windows

1. Instala Python **3.11 o superior** con el componente **Tcl/Tk**. Para comprobarlo, ejecuta `py -3 -m tkinter`: debe abrir una ventana.
2. Extrae **toda** la carpeta del ZIP a una ruta permanente de tu equipo.
3. Abre **`Probar_Demo.bat`** para explorar con nueve tickets y tres artículos ficticios.
4. Abre **`Iniciar_Nexo_TI.bat`** para trabajar en tu espacio vacío.

También puedes iniciar desde una terminal en esta carpeta:

```bash
python main.py --demo
python main.py
```

La demostración y los datos reales usan carpetas independientes. Los datos se conservan al cerrar la aplicación. No es necesario ejecutar `pip install`.

## Qué puedes hacer

| Módulo | Funciones |
| --- | --- |
| Resumen | Activos, críticos, vencidos, finalizados, cola de atención y carga por tipo |
| Tickets | Crear incidentes/requerimientos, asignar responsable, prioridades, estados y activo/servicio |
| Búsqueda | Número, asunto, descripción, solicitante, responsable o activo; filtros por estado/tipo/prioridad |
| Seguimiento | Bitácora de cambios y notas con fecha y operador; solución obligatoria al resolver |
| Adjuntos | Copia local de evidencias, límite de 20 MB por archivo y verificación SHA-256 |
| Documentación | Artículos editables, lectura de Markdown básico, búsqueda y vínculo con tickets |
| Automatizaciones | Revisar SLA, proponer categorías con revisión humana y generar reportes Markdown + CSV |
| Exportación | Vista filtrada a CSV; ficha completa del ticket y artículos a Markdown |
| Respaldo | ZIP con base de datos, documentos, historial y adjuntos |

## Numeración y estados

Los consecutivos son independientes por tipo y año:

- `INC-AAAA-00001`: incidente, una interrupción o degradación de un servicio.
- `REQ-AAAA-00001`: requerimiento de soporte o solicitud de servicio.

El número se asigna de forma atómica al crear el ticket. Su tipo queda fijo para mantener la coherencia de la identificación. No se eliminan tickets ni entradas de la bitácora desde la interfaz.

Flujo: **Nuevo → En progreso / En espera → Resuelto → Cerrado**. También se puede resolver directamente un caso nuevo con su solución documentada. Reabrir un resuelto o cerrado lo lleva a **En progreso**. Consulta la tabla completa en [la guía](docs/GUIA_DE_USO.md).

## Objetivos de resolución

| Prioridad | Objetivo continuo |
| --- | --- |
| Crítica | 4 horas |
| Alta | 8 horas |
| Media | 24 horas |
| Baja | 72 horas |

Se cuentan desde la creación. **En espera no detiene el reloj.** Cambiar la prioridad recalcula la fecha objetivo desde la creación. Estos valores son reglas iniciales de la aplicación; no son los SLA de una empresa concreta. No hay calendario laboral, SLA de primera respuesta ni escalamiento automático. Las fechas se guardan con zona UTC y se muestran en la zona horaria del equipo.

## Dónde están tus datos

- Windows: `%LOCALAPPDATA%\NexoTI`.
- Demo Windows: `%LOCALAPPDATA%\NexoTI-Demo`.
- macOS/Linux: `~/.local/share/NexoTI` y `NexoTI-Demo`.
- Ruta personalizada: `python main.py --data-dir "D:\NexoDatos"`.

La carpeta contiene `nexo.db`, `adjuntos/` y, al generar reportes, `reportes/`. El perfil del operador es una etiqueta para el historial, **no autenticación**.

## Automatización sin abrir la interfaz

Desde la raíz del proyecto:

```bash
python -m nexo.automation --job sla
python -m nexo.automation --job daily-report
python -m nexo.automation --job backup
python -m nexo.automation --job suggest-categories
```

Añade `--demo` para consultar la base demo, o `--data-dir "D:\NexoDatos"` para usar una ruta determinada. La CLI no inserta los ejemplos: inicia la demo una vez primero.

Puedes programar estos comandos con el Programador de tareas de Windows. Elige la ruta **absoluta** de `python.exe`, usa `-m nexo.automation --job daily-report` como argumentos y establece la raíz del proyecto en **Iniciar en**. Usa la misma cuenta de Windows que ejecuta la aplicación, o indica `--data-dir` de forma explícita. El código de salida es 0 si termina correctamente; las excepciones generan una salida distinta de cero.

La clasificación por CLI solo muestra sugerencias. Aplicarlas requiere revisar y seleccionar los casos desde la interfaz. Estas automatizaciones trabajan sobre la base local; no controlan aplicaciones externas, no envían correos ni reinician servicios. La integración con otros sistemas RPA necesita adaptar sus interfaces y credenciales al entorno real.

## Copia y restauración

Crea el ZIP en **Configuración → Crear copia de seguridad**. También puedes usar la tarea `backup`. SQLite realiza una instantánea consistente de los cambios confirmados, incluidos los del registro WAL.

Para restaurar:

1. Cierra todas las instancias de Nexo TI y las tareas programadas.
2. Conserva la carpeta de datos actual como respaldo, **renombrándola**.
3. Extrae tu ZIP de respaldo en una **carpeta nueva**. Debe contener `nexo.db`, `manifest.json` y `adjuntos/` si existen archivos.
4. Inicia con `python main.py --data-dir "RUTA_DE_LA_CARPETA_RESTAURADA"` y verifica los tickets y adjuntos.
5. Para usar esa carpeta siempre, conserva el mismo argumento o modifica tu acceso directo.

No mezcles una base restaurada con archivos `-wal` o `-shm` de otra base. La restauración es manual y no sobrescribe tus datos desde la interfaz.

## Desarrollo y validación

```bash
python -m unittest discover -s tests -v
python -m compileall -q nexo main.py
```

Hay pruebas de numeración persistente, estados, reapertura, solución obligatoria, conflictos de edición, cálculo de objetivos, vínculos, adjuntos, CSV, restauración, reglas de clasificación, reportes y datos demo. Consulta [arquitectura](docs/ARQUITECTURA.md) para la estructura y los puntos de extensión.

La prueba `tests/test_ui.py` abre ventanas y comprueba un flujo de escritorio cuando hay pantalla gráfica; en un servidor sin pantalla se omite. Esta entrega se validó en Linux con Python 3.12 y Tk 9.0. La ejecución nativa en Windows queda pendiente de comprobar en un equipo Windows. Se incluyen capturas de la aplicación funcionando en `docs/vista_*.png`.

## Alcance de esta versión

Es una aplicación local para un operador; puede detectar formularios desactualizados, pero no implementa colaboración empresarial. No incluye autenticación, roles, cifrado propio, sincronización, integraciones con correo/Active Directory/ITSM, ni un instalador `.exe`. No coloques la base activa en una carpeta compartida de red. La bitácora conserva cambios de la aplicación, pero no es un registro inalterable frente a quien tenga acceso al archivo SQLite. Usa permisos y cifrado del sistema operativo para proteger tus datos.

El proyecto incluye código fuente completo y lanzadores para Windows. No requiere acceso a servicios del banco ni utiliza información real de ninguna organización.
# Nexo_TI
