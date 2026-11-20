# Arquitectura · Nexo TI 1.0

## Capas

| Archivo | Responsabilidad |
| --- | --- |
| `main.py` | Argumentos, espacio de datos, carga demo y arranque gráfico |
| `nexo/ui.py` | Ventanas Tk/ttk, filtros, lectura de artículos y diálogos |
| `nexo/storage.py` | Persistencia SQLite, validación, estados, numeración, bitácora, archivos y respaldo |
| `nexo/automation.py` | Reglas de categoría, consulta de objetivos, reportes y CLI |
| `nexo/demo.py` | Ejemplos ficticios idempotentes en el espacio demo |
| `tests/test_workflows.py` | Flujos integrados con una base temporal por prueba |

Biblioteca estándar exclusivamente. La GUI y la CLI utilizan las mismas reglas de persistencia. Las tareas no controlan pantallas externas ni ejecutan comandos arbitrarios.

## Datos

| Tabla | Relación / propósito |
| --- | --- |
| `tickets` | Entidad principal, identidad, clasificación, contexto, fechas y versión optimista |
| `sequences` | Consecutivo por prefijo y año local |
| `events` | N eventos por ticket, con operador, fecha, clase y contenido |
| `articles` | Procedimientos editables |
| `ticket_articles` | Relación N:M entre tickets y artículos |
| `attachments` | N evidencias por ticket; nombre original, nombre interno, tamaño y SHA-256 |
| `automation_runs` | Historial de tareas, resultado y detalle |
| `settings` | Perfil del operador y marca de inicialización demo |

Los archivos se copian con nombre interno UUID, sin usar la ruta original como destino. No se ejecutan ni abren automáticamente. Guardar copia verifica la huella SHA-256.

SQLite usa claves foráneas, WAL y un timeout de diez segundos. La numeración se reserva con `BEGIN IMMEDIATE`, dentro de la misma transacción del ticket y el primer evento. Los cambios validan el estado y se actualizan con `WHERE id=? AND version=?`. El historial se escribe en la misma transacción que el cambio del ticket.

La copia usa `Connection.backup` a una base temporal, luego reúne los adjuntos registrados. Evita cambios simultáneos mientras haces copias para conservar coherencia entre la instantánea SQL y los archivos, especialmente si amplías el proyecto con borrado de adjuntos. El ZIP no cifra la información.

## Extensión

1. **Integraciones:** añade adaptadores fuera de `ui.py`; deben consumir las reglas de Store y registrar el origen del cambio.
2. **Reglas:** edita `RULES` en automation.py y añade casos representativos de tu vocabulario. El orden importa: gana la primera coincidencia. La regla actual usa subcadenas.
3. **Objetivos:** los valores iniciales están en `SLA_HOURS`. Si los cambias, actualiza también las ayudas y decide cómo migrar fechas de casos existentes; cambiar la constante por sí solo no recalcula todos los registros.
4. **Roles y colaboración:** requiere un diseño nuevo de identidad y permisos y preferiblemente servicio backend + PostgreSQL. El perfil actual no autoriza acciones y la base no debe exponerse como servicio.
5. **Migraciones:** `PRAGMA user_version=1` documenta el esquema actual. Una versión futura debe añadir migraciones explícitas antes de cambiar tablas existentes.
6. **Distribución:** el proyecto se ejecuta como fuente. Un ejecutable Windows se debe generar y comprobar en Windows con una herramienta de empaquetado elegida por el equipo. No se incluye un binario generado en otro sistema.

## Límites conocidos

Sin calendario laboral, alertas del sistema, primera respuesta, integraciones externas ni búsquedas a escala de millones de tickets. El cálculo estadístico y las consultas de búsqueda cargan conjuntos pequeños y están pensados para una mesa local. Las operaciones de archivos se ejecutan en el hilo de la GUI; los adjuntos están limitados a 20 MB y las copias grandes pueden demorar. Los artículos no tienen versionado histórico. La bitácora es una evidencia funcional y no un mecanismo antifraude.
