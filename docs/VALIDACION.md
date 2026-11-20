# Validación de la entrega

## Resultado

**18 pruebas superadas:** 17 flujos de negocio/persistencia y 1 prueba integrada de interfaz de escritorio. Las cinco páginas y las cuatro pestañas del ticket se abrieron sin errores durante la comprobación.

Entorno ejecutado: Linux, Python 3.12 y Tk 9.0 con pantalla virtual. La aplicación se diseñó para Python 3.11+ con Tkinter. No se ha ejecutado nativamente en Windows en esta entrega; los lanzadores `.bat` se incluyen como fuente.

## Cobertura comprobada

- Consecutivos por tipo, persistencia y creación con una segunda conexión.
- Datos obligatorios y rechazo de creaciones inválidas.
- Estados, solución obligatoria, cierre y reapertura.
- Protección frente a formularios desactualizados.
- Recálculo del objetivo al cambiar la prioridad.
- Bitácora, notas y vínculos sin duplicar artículos.
- Copia de adjuntos, huella de integridad y límite de tamaño.
- CSV con comillas, Unicode y protección contra interpretación como fórmula.
- Copia ZIP restaurable con tickets, documentación y adjuntos; integridad SQLite.
- Identificación de SLA vencidos y exclusión de casos finalizados.
- Vista previa de categorías sin mutación y aplicación solo a casos elegibles.
- Omisión de sugerencias sobre casos modificados después de la vista previa.
- Generación real del reporte Markdown y CSV.
- Búsqueda/filtros y datos demo idempotentes.
- Flujo gráfico: crear ticket, rechazar resolución vacía, resolver, abrir sus pestañas, buscarlo y crear un artículo.

Las capturas `vista_resumen.png`, `vista_tickets.png`, `vista_ticket.png`, `vista_documentacion.png`, `vista_automatizaciones.png` y `vista_configuracion.png` muestran la aplicación real en modo demo. El aspecto de las fuentes y los controles puede variar con Windows y la escala de pantalla.

## Repetir

Desde la raíz del proyecto:

```bash
python -m unittest discover -s tests -v
```

En un servidor sin pantalla se omite la prueba gráfica. En un escritorio abre ventanas brevemente y las cierra. No usa ni modifica la base de datos personal: cada prueba crea un directorio temporal.
