# Guía de uso · Nexo TI

## Un caso de principio a fin

1. Entra a Configuración y guarda el nombre del operador para identificar el historial.
2. Pulsa Nuevo ticket. Describe el síntoma o la solicitud, el solicitante, la prioridad, el responsable y el activo o servicio involucrado.
3. Guarda. Verás el identificador definitivo; la ficha se vuelve a abrir para agregar seguimiento, adjuntos y documentación.
4. Cambia a En progreso cuando empieces la atención. Si depende de información o aprobación, usa En espera y explica la dependencia en una nota.
5. En Bitácora, registra lo revisado, decisiones y escalamiento. Las notas se guardan al pulsar Agregar nota, sin esperar a Guardar cambios.
6. En Adjuntos, selecciona evidencias. La aplicación conserva una copia; mover el archivo original no afecta el adjunto. Para recuperarlo, selecciónalo y usa Guardar copia.
7. En Documentación, elige un artículo y pulsa Vincular artículo. Haz clic en un artículo vinculado para leer el procedimiento.
8. Escribe la solución con acciones realizadas y cómo validaste el resultado. Selecciona Resuelto y guarda.
9. Tras la aceptación del resultado, cambia a Cerrado. Si el problema reaparece, usa En progreso y agrega una nota con el motivo de la reapertura.
10. Exporta la ficha Markdown si necesitas entregarla. Incluye la información guardada, historial, contenido de los artículos vinculados e inventario de adjuntos. Los archivos adjuntos se guardan por separado o dentro de la copia de seguridad.

## Estados permitidos

| Estado actual | Siguiente estado permitido |
| --- | --- |
| Nuevo | En progreso, En espera, Resuelto |
| En progreso | En espera, Resuelto |
| En espera | En progreso, Resuelto |
| Resuelto | Cerrado, En progreso |
| Cerrado | En progreso |

La solución es obligatoria en Resuelto y Cerrado. No hay borrado de casos. Un ticket abierto puede tener una solución preliminar, pero no cuenta como finalizado hasta cambiar de estado. Reabrir limpia la fecha de resolución anterior y conserva el texto de solución y la bitácora; el SLA continúa desde la creación original.

## Prioridad sugerida

- **Crítica:** interrupción de servicio esencial con impacto amplio.
- **Alta:** afectación importante con atención prioritaria.
- **Media:** afectación acotada o requerimiento normal.
- **Baja:** solicitud planificable o impacto menor.

Son criterios de ejemplo. Ajusta su uso a las reglas de tu operación. La prioridad se selecciona manualmente y no se deriva de impacto/urgencia en esta versión.

## Artículos

Puedes utilizar `# Título`, `## Sección`, listas con `- ` y pasos numerados. El visor da formato a encabezados y viñetas. Conserva el resto como texto; no interpreta HTML, imágenes, tablas ni todo el estándar Markdown.

Estructura útil: Objetivo, Alcance, Comprobaciones, Procedimiento, Validación y Escalamiento. Evita incluir contraseñas. Los tickets vinculados muestran la versión actual del artículo, no una copia histórica inmutable.

## Automatizaciones

**Revisión de SLA:** consulta casos abiertos vencidos y con vencimiento en las próximas dos horas. No cambia su prioridad ni su responsable. Registra cada ejecución en el historial.

**Clasificación:** busca palabras en asunto y descripción de tickets activos clasificados como Otros. Muestra categoría y palabra encontrada. Doble clic o barra espaciadora marca/desmarca una sugerencia. Aplicar seleccionados actualiza solamente esos casos y registra el cambio. Una regla por palabras puede equivocarse: revisa antes de aplicar. Si el ticket cambió después de mostrar la propuesta, se omite para no sobrescribir un trabajo posterior.

**Reporte:** genera Markdown y CSV en la carpeta reportes, y muestra sus rutas. Puedes consultar el detalle de ejecuciones con doble clic o Enter. No se envía información a otros servicios.

El tablero se actualiza cada minuto mientras está abierto sin diálogos. Los trabajos RPA se ejecutan manualmente o mediante el Programador de tareas con la CLI; no hay planificador interno en segundo plano.

## Atajos

| Atajo | Acción |
| --- | --- |
| Ctrl+N | Nuevo ticket |
| Ctrl+F | Búsqueda en tickets/documentación |
| Ctrl+S | Guardar ficha o artículo |
| F5 | Actualizar página principal |
| Enter en una tabla | Abrir ticket o detalle de ejecución |

## Solución de problemas

- **No abre el `.bat`:** ejecuta `py -3 main.py` en una terminal para ver el error. Revisa que el ZIP esté completamente extraído y Python incluya Tcl/Tk.
- **No aparece un ticket:** limpia la búsqueda y los tres filtros. Confirma que no estés usando el espacio demo o una ruta de datos distinta.
- **No permite guardar:** revisa asunto, solicitante, descripción, categoría/prioridad y la solución si estás resolviendo.
- **Formulario desactualizado:** cierra y vuelve a abrir el ticket. La protección de versión evita reemplazar cambios posteriores.
- **Texto pequeño:** usa la escala de pantalla de Windows. La interfaz exige al menos 1120×740 para la ventana principal; los formularios tienen barras de desplazamiento.
- **Error inesperado:** consulta `errores.log` en el directorio de datos. No compartas ese archivo sin revisar si contiene rutas o datos sensibles.
- **Linux sin Tk:** instala el paquete Tkinter que corresponda a tu distribución y versión de Python.

## Migrar a otro equipo

Guarda una copia, copia el proyecto y el ZIP al nuevo equipo, instala Python con Tk, extrae el respaldo a una carpeta nueva y arranca con `--data-dir`. Utiliza el mismo argumento para las tareas programadas. Evita compartir simultáneamente la base activa entre varios equipos.
