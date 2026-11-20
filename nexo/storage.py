"""Persistencia, reglas de tickets, documentación, adjuntos y copias."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
import uuid
import zipfile

TYPES = ("Incidente", "Requerimiento")
PRIORITIES = ("Crítica", "Alta", "Media", "Baja")
STATUSES = ("Nuevo", "En progreso", "En espera", "Resuelto", "Cerrado")
CATEGORIES = ("Aplicaciones", "Servidores", "Redes", "Accesos", "Hardware", "Correo", "Otros")
SLA_HOURS = {"Crítica": 4, "Alta": 8, "Media": 24, "Baja": 72}
TRANSITIONS = {
    "Nuevo": {"En progreso", "En espera", "Resuelto"},
    "En progreso": {"En espera", "Resuelto"},
    "En espera": {"En progreso", "Resuelto"},
    "Resuelto": {"En progreso", "Cerrado"},
    "Cerrado": {"En progreso"},
}
OPEN_STATUSES = ("Nuevo", "En progreso", "En espera")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_date(value):
    return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M") if value else "—"


def default_data_dir(demo=False):
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / ("NexoTI-Demo" if demo else "NexoTI")


def csv_safe(value):
    text = "" if value is None else str(value)
    # Evita fórmulas al abrir exportaciones en una hoja de cálculo.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r")) else text


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.attachments_dir = self.directory / "adjuntos"
        self.attachments_dir.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.directory / "nexo.db", timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              number TEXT NOT NULL UNIQUE,
              type TEXT NOT NULL CHECK(type IN ('Incidente','Requerimiento')),
              title TEXT NOT NULL, description TEXT NOT NULL,
              requester TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
              assignee TEXT NOT NULL DEFAULT '', category TEXT NOT NULL,
              priority TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Nuevo',
              asset TEXT NOT NULL DEFAULT '', resolution TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              due_at TEXT NOT NULL, resolved_at TEXT, version INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS sequences (
              prefix TEXT NOT NULL, year INTEGER NOT NULL, value INTEGER NOT NULL,
              PRIMARY KEY(prefix, year)
            );
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ticket_id INTEGER NOT NULL REFERENCES tickets(id),
              created_at TEXT NOT NULL, actor TEXT NOT NULL,
              kind TEXT NOT NULL, body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS articles (
              id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
              category TEXT NOT NULL, body TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ticket_articles (
              ticket_id INTEGER NOT NULL REFERENCES tickets(id),
              article_id INTEGER NOT NULL REFERENCES articles(id),
              PRIMARY KEY(ticket_id,article_id)
            );
            CREATE TABLE IF NOT EXISTS attachments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ticket_id INTEGER NOT NULL REFERENCES tickets(id),
              name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE,
              size INTEGER NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS automation_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL, name TEXT NOT NULL,
              status TEXT NOT NULL, detail TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_events_ticket ON events(ticket_id,id);
            PRAGMA user_version=1;
        """)

    def close(self):
        self.db.close()

    def setting(self, key, default=""):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def _event(self, ticket_id, actor, kind, body):
        self.db.execute("INSERT INTO events(ticket_id,created_at,actor,kind,body) VALUES(?,?,?,?,?)",
                        (ticket_id, now_iso(), actor.strip() or "Operador", kind, body))

    def _validate(self, data):
        for field in ("title", "description", "requester"):
            if not str(data.get(field, "")).strip():
                raise ValueError({"title": "Escribe un título.", "description": "Escribe la descripción.", "requester": "Indica el solicitante."}[field])
        if len(data["title"]) > 180:
            raise ValueError("El título admite hasta 180 caracteres.")
        for field, values in (("type", TYPES), ("category", CATEGORIES), ("priority", PRIORITIES)):
            if data.get(field) not in values:
                raise ValueError(f"Valor inválido: {field}.")

    def create_ticket(self, data, actor="Operador"):
        self._validate(data)
        stamp = now_iso()
        year = datetime.fromisoformat(stamp).astimezone().year
        prefix = "INC" if data["type"] == "Incidente" else "REQ"
        # Reserva del consecutivo y creación atómicos, también con dos instancias.
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT INTO sequences VALUES(?,?,1) ON CONFLICT(prefix,year) DO UPDATE SET value=value+1", (prefix, year))
            seq = self.db.execute("SELECT value FROM sequences WHERE prefix=? AND year=?", (prefix, year)).fetchone()[0]
            number = f"{prefix}-{year}-{seq:05d}"
            fields = ("type", "title", "description", "requester", "email", "assignee", "category", "priority", "asset", "resolution")
            values = [str(data.get(f, "")).strip() for f in fields]
            due = (datetime.fromisoformat(stamp) + timedelta(hours=SLA_HOURS[data["priority"]])).isoformat(timespec="seconds")
            cur = self.db.execute(f"INSERT INTO tickets(number,{','.join(fields)},created_at,updated_at,due_at) VALUES({','.join('?' for _ in range(len(fields)+4))})",
                                  [number, *values, stamp, stamp, due])
            self._event(cur.lastrowid, actor, "Creación", f"Ticket creado · {data['priority']} · {data['category']}")
            self.db.commit()
            return cur.lastrowid
        except Exception:
            self.db.rollback()
            raise

    def ticket(self, ticket_id):
        row = self.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if not row:
            raise ValueError("No se encontró el ticket.")
        return dict(row)

    def tickets(self, query="", status="Todos", type_="Todos", priority="Todas"):
        sql = "SELECT * FROM tickets WHERE 1=1"
        args = []
        if query.strip():
            sql += " AND (number LIKE ? OR title LIKE ? OR description LIKE ? OR requester LIKE ? OR assignee LIKE ? OR asset LIKE ?)"
            args += [f"%{query.strip()}%"] * 6
        for column, val in (("status", status), ("type", type_), ("priority", priority)):
            if val not in ("Todos", "Todas"):
                sql += f" AND {column}=?"
                args.append(val)
        sql += " ORDER BY CASE WHEN status IN ('Resuelto','Cerrado') THEN 1 ELSE 0 END, CASE priority WHEN 'Crítica' THEN 0 WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END, created_at DESC,id DESC"
        return [dict(r) for r in self.db.execute(sql, args)]

    def update_ticket(self, ticket_id, data, actor="Operador", expected_version=None):
        with self.db:
            old = self.ticket(ticket_id)
            merged = old | data
            self._validate(merged)
            if merged["type"] != old["type"]:
                raise ValueError("El tipo no se modifica después de asignar el número.")
            status = merged["status"]
            if status not in STATUSES:
                raise ValueError("Estado inválido.")
            if status != old["status"] and status not in TRANSITIONS[old["status"]]:
                raise ValueError(f"No se permite pasar de {old['status']} a {status}.")
            if status in ("Resuelto", "Cerrado") and not merged["resolution"].strip():
                raise ValueError("Documenta la solución antes de resolver o cerrar.")
            if expected_version is not None and old["version"] != expected_version:
                raise ValueError("Otro cambio actualizó este ticket. Cierra esta ficha y vuelve a abrirla.")
            fields = ("title", "description", "requester", "email", "assignee", "category", "priority", "asset", "status", "resolution")
            changes = [f"{f}: {old[f]} → {merged[f]}" for f in fields if str(old[f]) != str(merged[f]).strip()]
            if not changes:
                return
            # El objetivo se calcula desde la creación; las esperas no pausan SLA.
            due = (datetime.fromisoformat(old["created_at"]) + timedelta(hours=SLA_HOURS[merged["priority"]])).isoformat(timespec="seconds")
            resolved = old["resolved_at"]
            if status == "Resuelto" and old["status"] != "Resuelto":
                resolved = now_iso()
            elif status in OPEN_STATUSES:
                resolved = None
            version = old["version"] if expected_version is None else expected_version
            cur = self.db.execute(f"UPDATE tickets SET {','.join(f+'=?' for f in fields)},due_at=?,resolved_at=?,updated_at=?,version=version+1 WHERE id=? AND version=?",
                                  [*[str(merged[f]).strip() for f in fields], due, resolved, now_iso(), ticket_id, version])
            if cur.rowcount != 1:
                raise ValueError("El ticket cambió en otra instancia. Vuelve a abrirlo.")
            self._event(ticket_id, actor, "Actualización", "\n".join(changes))

    def add_note(self, ticket_id, body, actor="Operador"):
        if not body.strip():
            raise ValueError("Escribe una nota antes de agregarla.")
        with self.db:
            self.ticket(ticket_id)
            self._event(ticket_id, actor, "Nota", body.strip())

    def events(self, ticket_id):
        return [dict(r) for r in self.db.execute("SELECT * FROM events WHERE ticket_id=? ORDER BY id DESC", (ticket_id,))]

    def stats(self):
        rows = self.tickets()
        stamp = now_iso()
        active = [t for t in rows if t["status"] in OPEN_STATUSES]
        return {"total": len(rows), "open": len(active), "critical": sum(t["priority"] == "Crítica" for t in active),
                "overdue": sum(datetime.fromisoformat(t["due_at"]) < datetime.fromisoformat(stamp) for t in active),
                "resolved": sum(t["status"] in ("Resuelto", "Cerrado") for t in rows),
                "unassigned": sum(not t["assignee"] for t in active)}

    def articles(self, query=""):
        return [dict(r) for r in self.db.execute("SELECT * FROM articles WHERE title LIKE ? OR body LIKE ? OR category LIKE ? ORDER BY updated_at DESC,id DESC", (f"%{query}%",)*3)]

    def save_article(self, title, category, body, article_id=None):
        if not title.strip() or not body.strip():
            raise ValueError("El artículo necesita título y contenido.")
        if category not in CATEGORIES:
            raise ValueError("Categoría inválida.")
        stamp = now_iso()
        with self.db:
            if article_id:
                self.db.execute("UPDATE articles SET title=?,category=?,body=?,updated_at=? WHERE id=?", (title.strip(), category, body.strip(), stamp, article_id))
                return article_id
            return self.db.execute("INSERT INTO articles(title,category,body,created_at,updated_at) VALUES(?,?,?,?,?)", (title.strip(), category, body.strip(), stamp, stamp)).lastrowid

    def linked_articles(self, ticket_id):
        return [dict(r) for r in self.db.execute("SELECT a.* FROM articles a JOIN ticket_articles l ON a.id=l.article_id WHERE l.ticket_id=? ORDER BY a.title", (ticket_id,))]

    def link_article(self, ticket_id, article_id, actor="Operador"):
        with self.db:
            cur = self.db.execute("INSERT OR IGNORE INTO ticket_articles VALUES(?,?)", (ticket_id, article_id))
            if cur.rowcount:
                title = self.db.execute("SELECT title FROM articles WHERE id=?", (article_id,)).fetchone()[0]
                self._event(ticket_id, actor, "Documentación", f"Artículo vinculado: {title}")

    def add_attachment(self, ticket_id, source, actor="Operador"):
        self.ticket(ticket_id)
        source = Path(source)
        if not source.is_file():
            raise ValueError("Selecciona un archivo válido.")
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("El tamaño máximo por adjunto es 20 MB.")
        stored = uuid.uuid4().hex + ".bin"
        dest = self.attachments_dir / stored
        try:
            shutil.copyfile(source, dest)
            if dest.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("El tamaño máximo por adjunto es 20 MB.")
            digest = hashlib.sha256(dest.read_bytes()).hexdigest()
            with self.db:
                self.db.execute("INSERT INTO attachments(ticket_id,name,stored_name,size,sha256,created_at) VALUES(?,?,?,?,?,?)", (ticket_id, source.name, stored, dest.stat().st_size, digest, now_iso()))
                self._event(ticket_id, actor, "Adjunto", f"Archivo agregado: {source.name}")
        except Exception:
            dest.unlink(missing_ok=True)
            raise

    def attachments(self, ticket_id):
        return [dict(r) for r in self.db.execute("SELECT * FROM attachments WHERE ticket_id=? ORDER BY id", (ticket_id,))]

    def save_attachment(self, attachment_id, destination):
        row = self.db.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
        if not row:
            raise ValueError("No se encontró el adjunto.")
        source = self.attachments_dir / row["stored_name"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("El archivo no coincide con su huella de integridad.")
        shutil.copyfile(source, destination)

    def export_csv(self, destination, rows=None):
        fields = ("number", "type", "title", "requester", "assignee", "category", "priority", "status", "asset", "created_at", "due_at", "resolved_at", "resolution")
        with open(destination, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            for row in self.tickets() if rows is None else rows:
                writer.writerow(csv_safe(row[f]) for f in fields)

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination in {self.directory / name for name in ("nexo.db", "nexo.db-wal", "nexo.db-shm")} or self.attachments_dir in destination.parents:
            raise ValueError("Guarda la copia fuera del directorio de adjuntos y de la base activa.")
        # SQLite.backup incluye las transacciones confirmadas en WAL.
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "nexo.db"
            conn = sqlite3.connect(snapshot)
            try:
                self.db.backup(conn)
            finally:
                conn.close()
            manifest = {"application": "Nexo TI", "version": 1, "created_at": now_iso(), "database": "nexo.db"}
            descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent, prefix="nexo-copia-", suffix=".tmp")
            os.close(descriptor)
            temporary_archive = Path(temporary_name)
            try:
                with zipfile.ZipFile(temporary_archive, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.write(snapshot, "nexo.db")
                    for row in self.db.execute("SELECT stored_name FROM attachments"):
                        path = self.attachments_dir / row[0]
                        if not path.is_file():
                            raise ValueError(f"Falta un adjunto: {row[0]}. Copia incompleta.")
                        archive.write(path, "adjuntos/" + path.name)
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                os.replace(temporary_archive, destination)
            finally:
                temporary_archive.unlink(missing_ok=True)

    def log_run(self, name, status, detail):
        with self.db:
            self.db.execute("INSERT INTO automation_runs(created_at,name,status,detail) VALUES(?,?,?,?)", (now_iso(), name, status, detail))

    def runs(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM automation_runs ORDER BY id DESC LIMIT 30")]
