"""Pruebas de reglas de negocio y flujos persistentes, sin abrir la interfaz."""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from nexo.storage import Store, SLA_HOURS
from nexo.automation import category_suggestions, apply_categories, sla_scan, daily_report
from nexo.demo import seed_demo


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.store = Store(self.path / "data")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def create(self, **kwargs):
        data = dict(type="Incidente", title="VPN desconectada", description="No hay conectividad VPN", requester="Usuario de prueba", category="Otros", priority="Alta")
        return self.store.create_ticket(data | kwargs, "Analista")

    def test_numbering_per_type_and_persistence(self):
        a = self.create()
        b = self.create(type="Requerimiento")
        c = self.create()
        self.assertTrue(self.store.ticket(a)["number"].endswith("00001"))
        self.assertTrue(self.store.ticket(b)["number"].startswith("REQ-"))
        self.assertTrue(self.store.ticket(b)["number"].endswith("00001"))
        self.assertTrue(self.store.ticket(c)["number"].endswith("00002"))
        other = Store(self.store.directory)
        try:
            new = other.create_ticket(dict(type="Incidente", title="Otro", description="Prueba", requester="Persona", category="Otros", priority="Baja"))
            self.assertTrue(other.ticket(new)["number"].endswith("00003"))
        finally:
            other.close()

    def test_invalid_ticket_leaves_no_record_or_sequence(self):
        with self.assertRaises(ValueError):
            self.create(title=" ")
        self.assertEqual([], self.store.tickets())
        valid = self.create()
        self.assertTrue(self.store.ticket(valid)["number"].endswith("00001"))

    def test_resolution_required_and_reopen(self):
        tid = self.create()
        with self.assertRaises(ValueError):
            self.store.update_ticket(tid, {"status": "Resuelto"})
        self.assertEqual("Nuevo", self.store.ticket(tid)["status"])
        self.store.update_ticket(tid, {"status": "En progreso", "assignee": "Ana"}, "Ana")
        self.store.update_ticket(tid, {"status": "Resuelto", "resolution": "Conectividad verificada"}, "Ana")
        self.assertIsNotNone(self.store.ticket(tid)["resolved_at"])
        self.store.update_ticket(tid, {"status": "Cerrado"}, "Ana")
        self.store.update_ticket(tid, {"status": "En progreso"}, "Ana")
        self.assertIsNone(self.store.ticket(tid)["resolved_at"])
        self.assertEqual(5, len(self.store.events(tid)))

    def test_transition_and_type_immutable(self):
        tid = self.create()
        with self.assertRaises(ValueError):
            self.store.update_ticket(tid, {"status": "Cerrado", "resolution": "Solución"})
        with self.assertRaises(ValueError):
            self.store.update_ticket(tid, {"type": "Requerimiento"})

    def test_stale_form_does_not_overwrite(self):
        tid = self.create()
        old = self.store.ticket(tid)
        self.store.update_ticket(tid, {"assignee": "Ana"}, expected_version=old["version"])
        with self.assertRaises(ValueError):
            self.store.update_ticket(tid, {"assignee": "Luis"}, expected_version=old["version"])
        self.assertEqual("Ana", self.store.ticket(tid)["assignee"])

    def test_priority_recalculates_from_creation(self):
        tid = self.create(priority="Baja")
        self.store.update_ticket(tid, {"priority": "Crítica"})
        row = self.store.ticket(tid)
        elapsed = datetime.fromisoformat(row["due_at"]) - datetime.fromisoformat(row["created_at"])
        self.assertEqual(timedelta(hours=4), elapsed)

    def test_notes_and_document_links(self):
        tid = self.create()
        self.store.add_note(tid, "Validado el alcance", "Ana")
        article = self.store.save_article("VPN", "Redes", "# Diagnóstico\nRevisar conectividad")
        self.store.link_article(tid, article, "Ana")
        self.store.link_article(tid, article, "Ana")
        self.assertEqual(1, len(self.store.linked_articles(tid)))
        self.assertEqual(3, len(self.store.events(tid)))
        with self.assertRaises(ValueError):
            self.store.add_note(tid, " ")

    def test_attachments_are_copied_and_hash_checked(self):
        tid = self.create()
        source = self.path / "evidencia.txt"
        source.write_text("Prueba de evidencia", encoding="utf-8")
        self.store.add_attachment(tid, source, "Ana")
        source.unlink()
        attached = self.store.attachments(tid)[0]
        output = self.path / "copia.txt"
        self.store.save_attachment(attached["id"], output)
        self.assertEqual("Prueba de evidencia", output.read_text(encoding="utf-8"))
        (self.store.attachments_dir / attached["stored_name"]).write_bytes(b"alterado")
        with self.assertRaises(ValueError):
            self.store.save_attachment(attached["id"], output)

    def test_size_limit(self):
        tid = self.create()
        source = self.path / "grande.bin"
        with source.open("wb") as file:
            file.truncate(20*1024*1024+1)
        with self.assertRaises(ValueError):
            self.store.add_attachment(tid, source)
        self.assertFalse(self.store.attachments(tid))

    def test_csv_handles_quotes_unicode_and_formula(self):
        self.create(title='=HYPERLINK("x")', requester='José, "TI"')
        path = self.path / "tickets.csv"
        self.store.export_csv(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            row = list(csv.DictReader(handle))[0]
        self.assertTrue(row["title"].startswith("'="))
        self.assertEqual('José, "TI"', row["requester"])

    def test_backup_can_be_opened_with_docs_and_attachments(self):
        tid = self.create()
        article = self.store.save_article("Guía", "Redes", "Pasos documentados")
        self.store.link_article(tid, article)
        source = self.path / "log.txt"
        source.write_text("evidencia")
        self.store.add_attachment(tid, source)
        path = self.path / "backup.zip"
        self.store.backup(path)
        restored = self.path / "restored"
        with zipfile.ZipFile(path) as archive:
            self.assertIn("manifest.json", archive.namelist())
            archive.extractall(restored)
        copy = Store(restored)
        try:
            self.assertEqual(1, len(copy.tickets()))
            self.assertEqual(1, len(copy.linked_articles(tid)))
            self.assertEqual(1, len(copy.attachments(tid)))
            self.assertEqual("ok", copy.db.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            copy.close()

    def test_sla_scan_detects_expired(self):
        tid = self.create()
        with self.store.db:
            self.store.db.execute("UPDATE tickets SET due_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(), tid))
        self.assertIn("VENCIDO", sla_scan(self.store))
        self.assertEqual(1, self.store.stats()["overdue"])
        self.store.update_ticket(tid, {"status": "Resuelto", "resolution": "Verificado"})
        self.assertNotIn("VENCIDO", sla_scan(self.store))

    def test_category_review_only_changes_eligible_tickets(self):
        a = self.create()
        b = self.create(category="Redes")
        proposed = category_suggestions(self.store)
        self.assertEqual([a], [s["id"] for s in proposed])
        self.assertEqual("Otros", self.store.ticket(a)["category"])
        self.assertEqual(1, apply_categories(self.store, proposed))
        self.assertEqual("Redes", self.store.ticket(a)["category"])
        self.assertEqual(0, apply_categories(self.store, proposed))

    def test_suggestion_skips_ticket_changed_since_preview(self):
        tid = self.create()
        proposed = category_suggestions(self.store)
        self.store.update_ticket(tid, {"assignee": "Otra persona"})
        self.assertEqual(0, apply_categories(self.store, proposed))

    def test_report_creates_real_outputs(self):
        self.create()
        report, csv_path = daily_report(self.store)
        self.assertIn("Tickets totales: 1", report.read_text(encoding="utf-8"))
        self.assertTrue(csv_path.exists())
        self.assertEqual("Reporte operativo", self.store.runs()[0]["name"])

    def test_search_filters(self):
        self.create(title="Error en IIS", priority="Crítica", category="Servidores")
        self.create(title="Acceso nuevo", type="Requerimiento")
        self.assertEqual(1, len(self.store.tickets(query="IIS")))
        self.assertEqual(1, len(self.store.tickets(type_="Requerimiento")))
        self.assertEqual(1, len(self.store.tickets(priority="Crítica")))
        self.assertEqual(0, len(self.store.tickets(status="Cerrado")))

    def test_demo_idempotent(self):
        seed_demo(self.store)
        seed_demo(self.store)
        self.assertEqual(9, self.store.stats()["total"])
        self.assertEqual(3, len(self.store.articles()))
        self.assertEqual(2, self.store.stats()["resolved"])


if __name__ == "__main__":
    unittest.main()
