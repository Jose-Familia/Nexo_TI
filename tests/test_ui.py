"""Prueba opcional de escritorio: se omite cuando no existe pantalla gráfica."""
import os
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform in ("win32", "darwin") or os.environ.get("DISPLAY"), "Se requiere pantalla gráfica")
class DesktopFlow(unittest.TestCase):
    def test_create_resolve_document_and_filter(self):
        from nexo.storage import Store
        from nexo.demo import seed_demo
        from nexo.ui import App, TicketDialog, ArticleDialog
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            seed_demo(store)
            app = App(store, demo=True)
            try:
                for page in ("Resumen", "Tickets", "Documentación", "Automatizaciones", "Configuración"):
                    app.navigate(page)
                    app.update()
                app.navigate("Tickets")
                form = TicketDialog(app)
                form.vars["title"].set("Validación de escritorio")
                form.vars["requester"].set("Persona de prueba")
                form.description.insert("1.0", "Contexto para el flujo visual")
                form.save()
                app.update()
                self.assertEqual(10, store.stats()["total"])
                form = next(w for w in app.winfo_children() if isinstance(w, TicketDialog))
                tid = form.ticket_id
                form.vars["status"].set("Resuelto")
                form.save()
                self.assertIn("solución", form.error.cget("text"))
                form.resolution.insert("1.0", "Validado con el solicitante")
                form.save()
                app.update()
                self.assertEqual("Resuelto", store.ticket(tid)["status"])
                form = next(w for w in app.winfo_children() if isinstance(w, TicketDialog))
                for index in range(4):
                    form.notebook.select(index)
                    app.update()
                form.destroy()
                app.q.set("Validación de escritorio")
                self.assertEqual(1, len(app.ticket_tree.get_children()))
                app.navigate("Documentación")
                editor = ArticleDialog(app)
                editor.title_var.set("Procedimiento de prueba gráfica")
                editor.body.delete("1.0", "end")
                editor.body.insert("1.0", "# Objetivo\nProcedimiento verificado")
                editor.save()
                app.update()
                self.assertEqual(4, len(store.articles()))
            finally:
                app.destroy()
                store.close()


if __name__ == "__main__":
    unittest.main()
