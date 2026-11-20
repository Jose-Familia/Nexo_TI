"""Datos ficticios. Solo se cargan al elegir --demo."""
from datetime import datetime, timedelta, timezone
from nexo.storage import SLA_HOURS


def seed_demo(store):
    if store.setting("demo_seeded"):
        return
    articles = [
        ("Diagnóstico inicial de una aplicación en IIS", "Servidores", "# Objetivo\nRegistrar evidencia antes de intervenir en una aplicación.\n\n## Comprobaciones\n1. Confirma el alcance y la hora del evento.\n2. Revisa el estado del sitio y del pool en IIS.\n3. Consulta los eventos y los registros autorizados.\n4. Correlaciona con las alertas de monitoreo.\n5. Documenta los resultados en el ticket.\n\n## Escalamiento\nSi es necesario reiniciar, solicita la autorización definida por el área.\n\n## Validación\nConfirma la recuperación con el solicitante y guarda evidencia."),
        ("Solicitud de acceso: información necesaria", "Accesos", "# Antes de asignar acceso\n\n- Nombre y área del solicitante.\n- Aplicación o recurso solicitado.\n- Perfil requerido y justificación.\n- Aprobación del responsable correspondiente.\n- Fecha de expiración cuando aplique.\n\n## Cierre\nRegistra la aprobación y la verificación del usuario. No incluyas contraseñas en el ticket."),
        ("Alerta de espacio en disco", "Servidores", "# Diagnóstico\n\n1. Identifica servidor, volumen y porcentaje de ocupación.\n2. Registra el crecimiento y las rutas involucradas.\n3. Verifica la política de retención y al responsable de los archivos.\n4. Escala con evidencia y una propuesta.\n\n## Precaución operativa\nNo elimines registros ni archivos de aplicación sin validación.\n\n## Evidencias\nAntes/después, ruta evaluada y decisión del responsable."),
    ]
    article_ids = [store.save_article(*a) for a in articles]
    rows = [
        ("Incidente", "Portal de autoservicio sin respuesta", "Los usuarios reciben un error 503 al consultar el portal. Se solicita revisar IIS y correlacionar con monitoreo.", "Laura Méndez", "José René", "Aplicaciones", "Crítica", "WEB-DEMO-01", "En progreso", 6),
        ("Incidente", "Alerta de capacidad en volumen de logs", "El volumen D: alcanzó el 92 %. Validar rutas y crecimiento antes de proponer una limpieza.", "Monitoreo TI", "José René", "Servidores", "Alta", "SRV-DEMO-02", "En progreso", 3),
        ("Requerimiento", "Habilitar acceso a la herramienta de reportes", "Se requiere acceso de consulta. Pendiente aprobación del responsable del área.", "Carlos Peña", "Ana Torres", "Accesos", "Media", "Reportes", "En espera", 5),
        ("Incidente", "VPN se desconecta al iniciar sesión", "El usuario reporta desconexiones de VPN. Confirmar alcance y revisar registros de conectividad.", "María Santos", "", "Otros", "Alta", "LT-DEMO-17", "Nuevo", 9),
        ("Requerimiento", "Instalar monitor adicional en estación", "Solicitud de un monitor adicional para el área de operaciones.", "Pedro Ruiz", "Luis García", "Hardware", "Baja", "PC-DEMO-08", "Nuevo", 2),
        ("Incidente", "Outlook no sincroniza el buzón", "El correo no se actualiza desde esta mañana. El envío de mensajes también está afectado.", "Elena Díaz", "Ana Torres", "Otros", "Media", "LT-DEMO-23", "Nuevo", 4),
        ("Requerimiento", "Documentar revisión de servicios Linux", "Preparar un procedimiento de consulta para el equipo de soporte.", "Operaciones TI", "José René", "Servidores", "Baja", "Linux", "En progreso", 12),
        ("Incidente", "Impresora de recepción fuera de línea", "La cola de impresión se encuentra detenida.", "Recepción", "Luis García", "Hardware", "Media", "PRN-DEMO-01", "Resuelto", 20),
        ("Requerimiento", "Actualizar inventario de equipos", "Revisión y documentación del inventario del laboratorio.", "Soporte TI", "Ana Torres", "Hardware", "Baja", "Laboratorio", "Cerrado", 30),
    ]
    for idx, (type_, title, description, requester, assignee, category, priority, asset, status, age) in enumerate(rows):
        ticket_id = store.create_ticket(dict(type=type_, title=title, description=description, requester=requester,
                                           assignee=assignee, category=category, priority=priority, asset=asset), "Demo")
        if status != "Nuevo":
            target = "Resuelto" if status == "Cerrado" else status
            store.update_ticket(ticket_id, {"status": target, "resolution": "Se validó la corrección con el solicitante y se documentaron las evidencias." if target == "Resuelto" else ""}, "Demo")
            if status == "Cerrado":
                store.update_ticket(ticket_id, {"status": "Cerrado"}, "Demo")
        created = datetime.now(timezone.utc) - timedelta(hours=age)
        with store.db:
            store.db.execute("UPDATE tickets SET created_at=?,due_at=? WHERE id=?", (created.isoformat(timespec="seconds"), (created + timedelta(hours=SLA_HOURS[priority])).isoformat(timespec="seconds"), ticket_id))
        if idx == 0:
            store.add_note(ticket_id, "Se confirmó el alcance. El equipo de aplicaciones está revisando el pool del portal.", "José René")
            store.link_article(ticket_id, article_ids[0], "Demo")
        elif idx == 1:
            store.link_article(ticket_id, article_ids[2], "Demo")
        elif idx == 2:
            store.link_article(ticket_id, article_ids[1], "Demo")
    store.set_setting("demo_seeded", "1")
