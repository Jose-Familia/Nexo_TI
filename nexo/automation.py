"""Automatizaciones locales y punto de entrada para el Programador de tareas."""
from datetime import datetime, timezone
from pathlib import Path
import argparse

from nexo.storage import Store, OPEN_STATUSES, default_data_dir

RULES = (
    ("Accesos", ("contraseña", "password", "permisos", "acceso", "bloqueada", "bloqueado")),
    ("Correo", ("outlook", "correo", "buzón", "mail")),
    ("Redes", ("vpn", "wifi", "wi-fi", "conectividad", "dns", "red")),
    ("Servidores", ("iis", "servidor", "disco", "linux", "windows server", "cpu", "memoria")),
    ("Hardware", ("impresora", "teclado", "monitor", "laptop", "pantalla")),
    ("Aplicaciones", ("aplicación", "aplicacion", "error", "api", "sistema")),
)


def category_suggestions(store):
    suggestions = []
    for ticket in store.tickets():
        if ticket["status"] not in OPEN_STATUSES or ticket["category"] != "Otros":
            continue
        text = (ticket["title"] + " " + ticket["description"]).casefold()
        for category, words in RULES:
            matched = next((word for word in words if word in text), None)
            if matched:
                suggestions.append({"id": ticket["id"], "number": ticket["number"], "category": category,
                                    "reason": matched, "version": ticket["version"]})
                break
    return suggestions


def apply_categories(store, suggestions, actor="RPA · Clasificación"):
    count = 0
    for item in suggestions:
        current = store.ticket(item["id"])
        if current["category"] != "Otros" or current["status"] not in OPEN_STATUSES or current["version"] != item["version"]:
            continue
        store.update_ticket(current["id"], {"category": item["category"]}, actor, expected_version=item["version"])
        count += 1
    store.log_run("Clasificación de tickets", "Completado", f"{count} tickets clasificados a partir de una revisión del operador.")
    return count


def sla_scan(store, log=True):
    stamp = datetime.now(timezone.utc)
    lines = []
    for ticket in store.tickets():
        if ticket["status"] not in OPEN_STATUSES:
            continue
        hours = (datetime.fromisoformat(ticket["due_at"]) - stamp).total_seconds() / 3600
        if hours < 0:
            lines.append(f"VENCIDO · {ticket['number']} · {ticket['title']} · {abs(hours):.1f} h de retraso")
        elif hours <= 2:
            lines.append(f"PRÓXIMO · {ticket['number']} · {ticket['title']} · vence en {hours:.1f} h")
    detail = "\n".join(lines) if lines else "Sin tickets vencidos ni vencimientos en las próximas dos horas."
    if log:
        store.log_run("Revisión de SLA", "Completado", detail)
    return detail


def daily_report(store):
    directory = store.directory / "reportes"
    directory.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    report = directory / f"resumen-{stamp}.md"
    csv_path = directory / f"tickets-{stamp}.csv"
    stats = store.stats()
    content = f"""# Nexo TI · Reporte de operaciones

Generado: {datetime.now().astimezone().strftime('%d/%m/%Y %H:%M %Z')}

## Indicadores

- Tickets totales: {stats['total']}
- Activos: {stats['open']}
- Críticos activos: {stats['critical']}
- Vencidos activos: {stats['overdue']}
- Sin asignar: {stats['unassigned']}
- Resueltos o cerrados: {stats['resolved']}

## Atención requerida

{sla_scan(store, log=False)}

## Criterios

Objetivo de resolución continuo: Crítica 4 h; Alta 8 h; Media 24 h; Baja 72 h.
El estado En espera no detiene el reloj. Los objetivos son configuraciones de
esta versión; no representan compromisos contractuales de una organización.

Detalle exportado: {csv_path.name}
"""
    report.write_text(content, encoding="utf-8")
    store.export_csv(csv_path)
    store.log_run("Reporte operativo", "Completado", f"Generados {report.name} y {csv_path.name}")
    return report, csv_path


def main():
    parser = argparse.ArgumentParser(description="Nexo TI · Automatizaciones locales")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--job", required=True, choices=("sla", "daily-report", "backup", "suggest-categories"))
    args = parser.parse_args()
    store = Store(args.data_dir or default_data_dir(args.demo))
    try:
        if args.job == "sla":
            print(sla_scan(store))
        elif args.job == "daily-report":
            for path in daily_report(store):
                print(path)
        elif args.job == "backup":
            directory = store.directory / "copias"
            directory.mkdir(exist_ok=True)
            path = directory / ("nexo-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".zip")
            store.backup(path)
            store.log_run("Copia de seguridad", "Completado", path.name)
            print(path)
        else:
            for item in category_suggestions(store):
                print(f"{item['number']}: {item['category']} (palabra: {item['reason']})")
    finally:
        store.close()


if __name__ == "__main__":
    main()
