"""Interfaz de escritorio Tk/ttk. Sin navegador, servidor ni paquetes externos."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import traceback
import sys

from nexo.storage import (TYPES, PRIORITIES, STATUSES, CATEGORIES, TRANSITIONS,
                          OPEN_STATUSES, SLA_HOURS, local_date)
from nexo.automation import category_suggestions, apply_categories, sla_scan, daily_report

BG = "#F3F5F8"
WHITE = "#FFFFFF"
INK = "#18253A"
MUTED = "#6B778B"
LINE = "#E3E8EF"
NAV = "#142236"
TEAL = "#087F75"
RED = "#C44752"
PURPLE = "#7760BB"
FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def label(parent, text, size=10, color=INK, bold=False, bg=None, **kw):
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=bg or parent.cget("bg"), **kw)


def button(parent, text, command, primary=False, **kw):
    return tk.Button(parent, text=text, command=command, font=(FONT, 10, "bold"),
                     bg=TEAL if primary else WHITE, fg=WHITE if primary else INK,
                     activebackground="#0B6D65" if primary else "#E8EEF3",
                     activeforeground=WHITE if primary else INK,
                     relief="flat", bd=0, highlightthickness=0, cursor="hand2", padx=16, pady=10, **kw)


def text_box(parent, height=7):
    wrap = tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
    text = tk.Text(wrap, height=height, font=(FONT, 10), bg=WHITE, fg=INK,
                   insertbackground=INK, relief="flat", wrap="word", padx=12, pady=10, undo=True)
    scroll = ttk.Scrollbar(wrap, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    return wrap, text


def show_text(text, content, markdown=False):
    text.configure(state="normal")
    text.delete("1.0", "end")
    if markdown:
        text.tag_configure("h1", font=(FONT, 17, "bold"), foreground=INK, spacing1=10, spacing3=10)
        text.tag_configure("h2", font=(FONT, 12, "bold"), foreground=TEAL, spacing1=12, spacing3=6)
        for line in content.splitlines():
            if line.startswith("# "):
                text.insert("end", line[2:] + "\n", "h1")
            elif line.startswith("## "):
                text.insert("end", line[3:] + "\n", "h2")
            elif line.startswith("- "):
                text.insert("end", "•  " + line[2:] + "\n")
            else:
                text.insert("end", line + "\n")
    else:
        text.insert("1.0", content)
    text.configure(state="disabled")


def table(parent, columns, heights=10):
    wrap = tk.Frame(parent, bg=WHITE)
    names = [col[0] for col in columns]
    tree = ttk.Treeview(wrap, columns=names, show="headings", height=heights, selectmode="browse")
    for name, title, width in columns:
        tree.heading(name, text=title, anchor="w")
        minimum = max(65, tkfont.Font(family=FONT, size=9, weight="bold").measure(title) + 24)
        tree.column(name, width=max(width, minimum), minwidth=minimum, anchor="w", stretch=name in ("title", "detail", "body"))
    scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    hscroll = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
    scroll.pack(side="right", fill="y")
    hscroll.pack(side="bottom", fill="x")
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("odd", background="#F8FAFC")
    tree.tag_configure("critical", foreground=RED)
    return wrap, tree


def sla_label(ticket):
    if ticket["status"] in ("Resuelto", "Cerrado"):
        resolved = ticket["resolved_at"]
        if resolved and datetime.fromisoformat(resolved) > datetime.fromisoformat(ticket["due_at"]):
            return "Fuera de objetivo"
        return "Finalizado"
    hours = (datetime.fromisoformat(ticket["due_at"]) - datetime.now(timezone.utc)).total_seconds()/3600
    if hours < 0:
        return f"Vencido {abs(hours):.0f} h"
    if hours < 1:
        return f"{max(0, int(hours*60))} min restantes"
    return f"{hours:.0f} h restantes"


class App(tk.Tk):
    def __init__(self, store, demo=False):
        super().__init__()
        self.store = store
        self.demo = demo
        self.page = "Resumen"
        self.actor = store.setting("operator", "Operador")
        self.title("Nexo TI · Mesa de soporte" + (" · DEMOSTRACIÓN" if demo else ""))
        self.geometry("1440x900")
        self.minsize(1120, 740)
        self.configure(bg=BG)
        self._styles()
        self._shell()
        self.bind("<Control-n>", lambda _: self.new_ticket())
        self.bind("<Control-f>", self.focus_search)
        self.bind("<F5>", lambda _: self.navigate(self.page))
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.navigate("Resumen")
        self.after(60000, self._tick)

    def report_callback_exception(self, exc, value, tb):
        log = self.store.directory / "errores.log"
        with log.open("a", encoding="utf-8") as handle:
            handle.write("".join(traceback.format_exception(exc, value, tb)))
        messagebox.showerror("Nexo TI", f"No se pudo completar la operación.\n\n{value}\n\nRegistro: {log}", parent=self)

    def _styles(self):
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
            tkfont.nametofont(name).configure(family=FONT, size=10)
        self.option_add("*TCombobox*Listbox.font", (FONT, 10))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10), background=BG, foreground=INK)
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=INK,
                        rowheight=47, borderwidth=0, relief="flat", font=(FONT, 10))
        style.configure("Treeview.Heading", background="#F4F7FA", foreground=MUTED,
                        font=(FONT, 9, "bold"), padding=(8, 12), borderwidth=0)
        style.map("Treeview", background=[("selected", "#DCEFEB")], foreground=[("selected", INK)])
        style.map("Treeview.Heading", background=[("active", "#EDF1F5")])
        style.configure("TEntry", fieldbackground=WHITE, padding=8, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("TCombobox", fieldbackground=WHITE, background=WHITE, padding=7, bordercolor=LINE, arrowcolor=MUTED)
        style.map("TCombobox", fieldbackground=[("readonly", WHITE)], selectbackground=[("readonly", WHITE)], selectforeground=[("readonly", INK)])
        style.configure("TNotebook", background=WHITE, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(20, 12), background="#EDF1F5", foreground=MUTED)
        style.map("TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", TEAL)])
        style.configure("TScrollbar", borderwidth=0, arrowsize=12, background="#D4DDE5", troughcolor="#F4F7FA")

    def _shell(self):
        sidebar = tk.Frame(self, bg=NAV, width=216)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=NAV)
        brand.pack(fill="x", padx=24, pady=(32, 28))
        label(brand, "nexo", 28, WHITE, True).pack(anchor="w")
        label(brand, "TI  /  SERVICE DESK", 8, "#8EA3BD", True).pack(anchor="w", pady=(0, 5))
        label(sidebar, "ESPACIO DE TRABAJO", 8, "#7B91AC", True).pack(anchor="w", padx=24, pady=(12, 14))
        self.nav_buttons = {}
        for page, icon in (("Resumen", "◈"), ("Tickets", "▤"), ("Documentación", "▥"), ("Automatizaciones", "↻"), ("Configuración", "⚙")):
            btn = tk.Button(sidebar, text=f"{icon}   {page}", anchor="w", font=(FONT, 11),
                            bg=NAV, fg="#B4C2D4", activebackground="#233D50", activeforeground=WHITE,
                            bd=0, highlightthickness=0, relief="flat", cursor="hand2", padx=17, pady=14,
                            command=lambda p=page: self.navigate(p))
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[page] = btn
        bottom = tk.Frame(sidebar, bg=NAV)
        bottom.pack(side="bottom", fill="x", padx=24, pady=28)
        label(bottom, "●  DATOS LOCALES", 8, "#62C6B2", True).pack(anchor="w")
        label(bottom, "Modo demostración" if self.demo else "Espacio personal", 9, "#95A8C0").pack(anchor="w", pady=(8, 3))
        label(bottom, "Nexo TI  1.0", 8, "#6E839D").pack(anchor="w")

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        header = tk.Frame(right, bg=WHITE, height=78, highlightbackground=LINE, highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.breadcrumb = label(header, "Mesa de soporte  /  Resumen", 10, MUTED)
        self.breadcrumb.pack(side="left", padx=28)
        self.operator_label = label(header, f"{self.actor}  ·  Operaciones TI", 10, INK, True)
        self.operator_label.pack(side="right", padx=28)
        if self.demo:
            label(header, "DEMO · DATOS FICTICIOS", 8, PURPLE, True).pack(side="right", padx=10)
        self.content = tk.Frame(right, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=24)
        self.status_text = tk.StringVar(value="Listo · Ctrl+N: nuevo ticket · Ctrl+F: buscar · F5: actualizar")
        label(right, "", 9, MUTED, textvariable=self.status_text, anchor="w").pack(side="bottom", fill="x", padx=28, pady=(0, 12), before=self.content)

    def _tick(self):
        if self.page == "Resumen" and not any(isinstance(w, tk.Toplevel) for w in self.winfo_children()):
            self.navigate("Resumen")
        self.after(60000, self._tick)

    def navigate(self, page):
        self.page = page
        for name, btn in self.nav_buttons.items():
            btn.configure(bg="#25414F" if name == page else NAV,
                          fg="#A3E3D6" if name == page else "#B4C2D4")
        for child in self.content.winfo_children():
            child.destroy()
        self.breadcrumb.configure(text="Mesa de soporte  /  " + page)
        self.search_entry = None
        {"Resumen": self.dashboard, "Tickets": self.ticket_page, "Documentación": self.docs_page,
         "Automatizaciones": self.automation_page, "Configuración": self.settings_page}[page]()

    def heading(self, title, subtitle, action=None):
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 22))
        copy = tk.Frame(row, bg=BG)
        copy.pack(side="left")
        label(copy, title, 24, INK, True).pack(anchor="w")
        label(copy, subtitle, 10, MUTED).pack(anchor="w", pady=(7, 0))
        if action:
            button(row, action[0], action[1], True).pack(side="right")

    def panel(self, parent, title, subtitle=None):
        panel = tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        head = tk.Frame(panel, bg=WHITE)
        head.pack(fill="x", padx=20, pady=(16, 12))
        label(head, title, 12, INK, True).pack(side="left")
        if subtitle:
            label(head, subtitle, 9, MUTED).pack(side="right")
        return panel

    def dashboard(self):
        self.heading("Todo bajo control.", "Tu operación de soporte, en una sola vista.", ("+  Nuevo ticket", self.new_ticket))
        stats = self.store.stats()
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 22))
        for i, (title, key, foot, color) in enumerate((("Tickets activos", "open", "Incidentes y requerimientos", TEAL),
                ("Prioridad crítica", "critical", "Requieren atención inmediata", RED),
                ("SLA vencidos", "overdue", "Objetivo de resolución superado", "#B07832"),
                ("Finalizados", "resolved", "Resueltos o cerrados", PURPLE))):
            cards.columnconfigure(i, weight=1, uniform="cards")
            card = tk.Frame(cards, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 3 else 7))
            label(card, title, 10, MUTED).pack(anchor="w", padx=20, pady=(17, 2))
            label(card, str(stats[key]).zfill(2), 30, color, True).pack(anchor="w", padx=20)
            label(card, foot, 8, MUTED).pack(anchor="w", padx=20, pady=(4, 18))

        center = tk.Frame(self.content, bg=BG)
        center.pack(fill="both", expand=True)
        center.columnconfigure(0, weight=3)
        center.columnconfigure(1, weight=1, minsize=260)
        center.rowconfigure(0, weight=1)
        left = self.panel(center, "Cola de atención", "Prioridad y antigüedad")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        wrap, tree = table(left, [("number", "TICKET", 150), ("title", "ASUNTO", 330),
                                  ("priority", "PRIORIDAD", 100), ("sla", "OBJETIVO", 138)], 6)
        wrap.pack(fill="both", expand=True, padx=10)
        rows = [r for r in self.store.tickets() if r["status"] in OPEN_STATUSES]
        for i, row in enumerate(rows):
            tree.insert("", "end", iid=str(row["id"]), values=(row["number"], row["title"], row["priority"], sla_label(row)), tags=("odd" if i % 2 else "even", "critical" if row["priority"] == "Crítica" else "normal"))
        if not rows:
            label(left, "No hay tickets activos. Crea el primero para comenzar.", 10, MUTED).pack(pady=24)
        tree.bind("<Double-1>", lambda _: self.open_selection(tree))
        tree.bind("<Return>", lambda _: self.open_selection(tree))
        bottom = tk.Frame(left, bg=WHITE)
        bottom.pack(side="bottom", fill="x", padx=14, pady=10, before=wrap)
        button(bottom, "Abrir seleccionado", lambda: self.open_selection(tree)).pack(side="left")
        button(bottom, "Ver todos los tickets  →", lambda: self.navigate("Tickets")).pack(side="right")

        right = self.panel(center, "Pulso de la operación")
        right.grid(row=0, column=1, sticky="nsew")
        rows_all = self.store.tickets()
        for type_, color in (("Incidente", TEAL), ("Requerimiento", PURPLE)):
            count = sum(r["type"] == type_ and r["status"] in OPEN_STATUSES for r in rows_all)
            frame = tk.Frame(right, bg=WHITE)
            frame.pack(fill="x", padx=20, pady=12)
            label(frame, type_ + "s", 10, MUTED).pack(anchor="w")
            label(frame, f"{count} activos", 16, color, True).pack(anchor="w", pady=4)
            bar = tk.Canvas(frame, height=5, bg="#EDF1F5", bd=0, highlightthickness=0)
            bar.pack(fill="x", pady=6)
            bar.bind("<Configure>", lambda event, b=bar, c=count, color_=color: (b.delete("all"), b.create_rectangle(0, 0, event.width * c / max(stats["open"], 1), 5, fill=color_, outline="")))
        tk.Frame(right, height=1, bg=LINE).pack(fill="x", padx=20, pady=12)
        label(right, f"{stats['unassigned']} sin responsable", 12, INK, True).pack(anchor="w", padx=20, pady=8)
        label(right, "Asigna cada caso para dar\ncontinuidad al seguimiento.", 10, MUTED, justify="left").pack(anchor="w", padx=20)
        button(right, "Preparar reporte", self.run_report).pack(anchor="w", padx=20, pady=22)

        footer = tk.Frame(self.content, bg="#E5EEEB", padx=18, pady=14)
        footer.pack(side="bottom", fill="x", pady=(18, 0), before=center)
        label(footer, "CONOCIMIENTO COMPARTIDO", 8, TEAL, True).pack(side="left")
        label(footer, f"  {len(self.store.articles())} artículos disponibles para documentar y resolver mejor.", 10, INK).pack(side="left")
        button(footer, "Explorar  →", lambda: self.navigate("Documentación")).pack(side="right")

    def focus_search(self, _=None):
        if self.page not in ("Tickets", "Documentación"):
            self.navigate("Tickets")
        if self.search_entry:
            self.search_entry.focus_set()
            self.search_entry.selection_range(0, "end")
        return "break"

    def ticket_page(self):
        self.heading("Tickets", "Cada solicitud, con contexto, responsable y seguimiento.", ("+  Nuevo ticket", self.new_ticket))
        filters = tk.Frame(self.content, bg=BG)
        filters.pack(fill="x", pady=(0, 16))
        self.q = tk.StringVar()
        self.filter_status = tk.StringVar(value="Todos")
        self.filter_type = tk.StringVar(value="Todos")
        self.filter_priority = tk.StringVar(value="Todas")
        search_wrap = tk.Frame(filters, bg=BG)
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 12))
        label(search_wrap, "BUSCAR NÚMERO, ASUNTO, SOLICITANTE O ACTIVO", 8, MUTED, True).pack(anchor="w", pady=(0, 5))
        self.search_entry = ttk.Entry(search_wrap, textvariable=self.q)
        self.search_entry.pack(fill="x")
        for title, var, values in (("ESTADO", self.filter_status, ("Todos",) + STATUSES),
                ("TIPO", self.filter_type, ("Todos",) + TYPES), ("PRIORIDAD", self.filter_priority, ("Todas",) + PRIORITIES)):
            box = tk.Frame(filters, bg=BG)
            box.pack(side="left", padx=(0, 10))
            label(box, title, 8, MUTED, True).pack(anchor="w", pady=(0, 5))
            combo = ttk.Combobox(box, textvariable=var, values=values, state="readonly", width=15)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _: self.refresh_tickets())
        panel = self.panel(self.content, "Mesa de trabajo", "Doble clic o Enter para abrir")
        panel.pack(fill="both", expand=True)
        wrap, self.ticket_tree = table(panel, [("number", "NÚMERO", 148), ("title", "ASUNTO", 290),
                ("type", "TIPO", 125), ("priority", "PRIORIDAD", 90), ("status", "ESTADO", 108),
                ("assignee", "RESPONSABLE", 135), ("sla", "SLA", 140)], 9)
        wrap.pack(fill="both", expand=True, padx=10)
        self.ticket_tree.bind("<Double-1>", lambda _: self.open_selection(self.ticket_tree))
        self.ticket_tree.bind("<Return>", lambda _: self.open_selection(self.ticket_tree))
        bottom = tk.Frame(panel, bg=WHITE)
        bottom.pack(side="bottom", fill="x", padx=12, pady=10, before=wrap)
        self.results_label = label(bottom, "", 9, MUTED)
        self.results_label.pack(side="left", padx=8)
        button(bottom, "Exportar vista CSV", self.export_view).pack(side="right", padx=(8, 0))
        button(bottom, "Abrir ticket", lambda: self.open_selection(self.ticket_tree), True).pack(side="right")
        self.q.trace_add("write", lambda *_: self.refresh_tickets())
        self.refresh_tickets()

    def refresh_tickets(self):
        tree = self.ticket_tree
        selection = tree.selection()
        tree.delete(*tree.get_children())
        self.filtered_rows = self.store.tickets(self.q.get(), self.filter_status.get(), self.filter_type.get(), self.filter_priority.get())
        for i, row in enumerate(self.filtered_rows):
            tree.insert("", "end", iid=str(row["id"]), values=(row["number"], row["title"], row["type"], row["priority"], row["status"], row["assignee"] or "Sin asignar", sla_label(row)), tags=("odd" if i % 2 else "even", "critical" if row["priority"] == "Crítica" and row["status"] in OPEN_STATUSES else "normal"))
        if selection and tree.exists(selection[0]):
            tree.selection_set(selection[0])
        self.results_label.configure(text=f"{len(self.filtered_rows)} tickets" + (" · Ajusta los filtros si no encuentras un caso." if not self.filtered_rows else ""))

    def open_selection(self, tree):
        if tree.selection():
            self.open_ticket(int(tree.selection()[0]))
        else:
            self.status_text.set("Selecciona un ticket para ver su ficha.")

    def new_ticket(self):
        TicketDialog(self)

    def open_ticket(self, ticket_id):
        TicketDialog(self, ticket_id)

    def export_view(self):
        path = filedialog.asksaveasfilename(parent=self, title="Exportar tickets visibles", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="tickets.csv")
        if path:
            self.store.export_csv(path, self.filtered_rows)
            self.status_text.set(f"Exportados {len(self.filtered_rows)} tickets · {path}")

    def docs_page(self):
        self.heading("Documentación", "Procedimientos, soluciones y conocimiento conectado a tus tickets.", ("+  Nuevo artículo", lambda: ArticleDialog(self)))
        self.doc_q = tk.StringVar()
        self.search_entry = ttk.Entry(self.content, textvariable=self.doc_q)
        self.search_entry.pack(fill="x", pady=(0, 16))
        split = tk.PanedWindow(self.content, orient="horizontal", bg=BG, sashwidth=16, bd=0)
        split.pack(fill="both", expand=True)
        left = self.panel(split, "Base de conocimiento")
        wrap, self.doc_tree = table(left, [("title", "ARTÍCULO", 300), ("category", "ÁREA", 110)], 10)
        wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        split.add(left, minsize=310, width=420)
        right = self.panel(split, "Lectura del artículo")
        self.doc_title = label(right, "Selecciona un artículo", 15, INK, True, anchor="w", justify="left", wraplength=480)
        self.doc_title.pack(fill="x", padx=22, pady=(5, 8))
        self.doc_meta = label(right, "", 9, MUTED, anchor="w")
        self.doc_meta.pack(fill="x", padx=22, pady=(0, 12))
        wrap, self.doc_body = text_box(right, 12)
        wrap.pack(fill="both", expand=True, padx=20)
        show_text(self.doc_body, "Selecciona un procedimiento para leerlo, editarlo o vincularlo desde un ticket.")
        actions = tk.Frame(right, bg=WHITE)
        actions.pack(fill="x", padx=20, pady=14)
        button(actions, "Editar artículo", self.edit_selected_article).pack(side="left")
        button(actions, "Exportar Markdown", self.export_article).pack(side="right")
        split.add(right, minsize=400)
        self.doc_tree.bind("<<TreeviewSelect>>", self.read_selected_article)
        self.doc_q.trace_add("write", lambda *_: self.refresh_articles())
        self.refresh_articles()

    def refresh_articles(self):
        self.doc_tree.delete(*self.doc_tree.get_children())
        self.doc_articles = {a["id"]: a for a in self.store.articles(self.doc_q.get())}
        for i, article in enumerate(self.doc_articles.values()):
            self.doc_tree.insert("", "end", iid=str(article["id"]), values=(article["title"], article["category"]), tags=("odd" if i % 2 else "even",))
        children = self.doc_tree.get_children()
        if children:
            self.doc_tree.selection_set(children[0])
            self.read_selected_article()
        else:
            self.doc_title.configure(text="Sin artículos")
            self.doc_meta.configure(text="")
            show_text(self.doc_body, "Crea un artículo o cambia el término de búsqueda.")

    def selected_article(self):
        selected = self.doc_tree.selection()
        return self.doc_articles.get(int(selected[0])) if selected else None

    def read_selected_article(self, _=None):
        article = self.selected_article()
        if article:
            self.doc_title.configure(text=article["title"])
            self.doc_meta.configure(text=article["category"] + "  ·  Actualizado " + local_date(article["updated_at"]))
            show_text(self.doc_body, article["body"], markdown=True)

    def edit_selected_article(self):
        article = self.selected_article()
        if article:
            ArticleDialog(self, article)

    def export_article(self):
        article = self.selected_article()
        if not article:
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".md", filetypes=[("Markdown", "*.md")], initialfile=f"articulo-{article['id']}.md")
        if path:
            Path(path).write_text(f"# {article['title']}\n\n{article['body']}\n", encoding="utf-8")
            self.status_text.set("Artículo exportado · " + path)

    def automation_page(self):
        self.heading("Automatizaciones", "Menos tareas repetitivas. Más tiempo para resolver.")
        intro = tk.Frame(self.content, bg="#E5EEEB", padx=20, pady=16)
        intro.pack(fill="x", pady=(0, 20))
        label(intro, "RPA LOCAL", 9, TEAL, True).pack(anchor="w")
        label(intro, "Ejecuta flujos de soporte y consulta su resultado. La clasificación se revisa antes de aplicar cambios.", 10, INK).pack(anchor="w", pady=(6, 0))
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 20))
        for i, (name, description, cta, command) in enumerate((
            ("01  /  Vigilar vencimientos", "Detecta SLA vencidos y casos\nque vencen en las próximas 2 h.", "Revisar SLA", self.run_sla),
            ("02  /  Clasificar tickets", "Propone una categoría por palabras\nclave para casos en «Otros».", "Revisar sugerencias", self.run_categories),
            ("03  /  Reporte de operación", "Genera un resumen Markdown y\nun CSV de todos los tickets.", "Generar reporte", self.run_report))):
            cards.columnconfigure(i, weight=1, uniform="jobs")
            card = tk.Frame(cards, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 2 else 8))
            label(card, name, 12, INK, True).pack(anchor="w", padx=18, pady=(20, 10))
            label(card, description, 10, MUTED, justify="left").pack(anchor="w", padx=18)
            button(card, cta, command).pack(anchor="w", padx=14, pady=16)
        panel = self.panel(self.content, "Historial de ejecuciones", "Últimas 30 ejecuciones")
        panel.pack(fill="both", expand=True)
        wrap, tree = table(panel, [("time", "FECHA", 160), ("job", "AUTOMATIZACIÓN", 210),
                                   ("status", "RESULTADO", 120), ("detail", "DETALLE", 430)], 5)
        wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        runs = self.store.runs()
        for i, run in enumerate(runs):
            tree.insert("", "end", iid=str(run["id"]), values=(local_date(run["created_at"]), run["name"], run["status"], run["detail"].replace("\n", " · ")), tags=("odd" if i % 2 else "even",))
        mapping = {str(r["id"]): r for r in runs}
        def detail(_=None):
            if tree.selection():
                run = mapping[tree.selection()[0]]
                ReadDialog(self, run["name"], run["detail"])
        tree.bind("<Double-1>", detail)
        tree.bind("<Return>", detail)
        label(self.content, "Programación desatendida: usa los comandos de la guía con el Programador de tareas de Windows.", 9, MUTED).pack(anchor="w", pady=(12, 0))

    def run_sla(self):
        result = sla_scan(self.store)
        if self.page == "Automatizaciones":
            self.navigate(self.page)
        ReadDialog(self, "Revisión de SLA", result)

    def run_report(self):
        paths = daily_report(self.store)
        if self.page == "Automatizaciones":
            self.navigate(self.page)
        messagebox.showinfo("Reporte generado", "Archivos creados:\n\n" + "\n\n".join(str(p) for p in paths), parent=self)
        self.status_text.set("Reporte de operación generado.")

    def run_categories(self):
        suggestions = category_suggestions(self.store)
        if not suggestions:
            messagebox.showinfo("Clasificación", "No hay sugerencias para tickets activos en la categoría Otros.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("Revisar clasificación sugerida")
        win.geometry("900x500")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        label(win, "Revisa las sugerencias", 20, INK, True).pack(anchor="w", padx=24, pady=(24, 8))
        label(win, "Solo se modificará la categoría de los tickets marcados.", 10, MUTED).pack(anchor="w", padx=24, pady=(0, 16))
        wrap, tree = table(win, [("apply", "APLICAR", 80), ("number", "TICKET", 160), ("category", "CATEGORÍA", 150), ("detail", "PALABRA DETECTADA", 300)], 5)
        wrap.pack(fill="both", expand=True, padx=24)
        selected = {s["id"] for s in suggestions}
        for item in suggestions:
            tree.insert("", "end", iid=str(item["id"]), values=("Sí", item["number"], item["category"], item["reason"]))
        def toggle(_=None):
            if tree.selection():
                item_id = int(tree.selection()[0])
                selected.symmetric_difference_update({item_id})
                tree.set(str(item_id), "apply", "Sí" if item_id in selected else "No")
        tree.bind("<Double-1>", toggle)
        tree.bind("<space>", toggle)
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=24, pady=18)
        button(bottom, "Marcar / desmarcar", toggle).pack(side="left")
        def apply():
            count = apply_categories(self.store, [s for s in suggestions if s["id"] in selected], self.actor + " · RPA")
            win.destroy()
            self.navigate(self.page)
            self.status_text.set(f"Clasificación aplicada · {count} tickets actualizados.")
        button(bottom, "Aplicar seleccionados", apply, True).pack(side="right")

    def settings_page(self):
        self.heading("Tu espacio de trabajo", "Preferencias, datos y respaldo de la operación.")
        panel = self.panel(self.content, "Perfil del operador")
        panel.pack(fill="x", pady=(0, 18))
        row = tk.Frame(panel, bg=WHITE)
        row.pack(fill="x", padx=20, pady=(0, 18))
        operator = tk.StringVar(value=self.actor)
        ttk.Entry(row, textvariable=operator, width=34).pack(side="left", padx=(0, 12))
        def save():
            if not operator.get().strip():
                messagebox.showerror("Perfil", "Indica un nombre para la bitácora.", parent=self)
                return
            self.actor = operator.get().strip()
            self.store.set_setting("operator", self.actor)
            self.operator_label.configure(text=f"{self.actor}  ·  Operaciones TI")
            self.status_text.set("Perfil actualizado.")
        button(row, "Guardar nombre", save, True).pack(side="left")
        label(panel, "Este nombre identifica los cambios en la bitácora; no es una cuenta de acceso.", 9, MUTED).pack(anchor="w", padx=20, pady=(0, 18))
        panel = self.panel(self.content, "Objetivos de resolución")
        panel.pack(fill="x", pady=(0, 18))
        label(panel, "Crítica: 4 horas     ·     Alta: 8 horas     ·     Media: 24 horas     ·     Baja: 72 horas", 11, INK).pack(anchor="w", padx=20, pady=8)
        label(panel, "Tiempo continuo desde la creación. En espera no pausa el reloj. Cambiar la prioridad recalcula el objetivo.", 9, MUTED).pack(anchor="w", padx=20, pady=(0, 18))
        panel = self.panel(self.content, "Datos y continuidad")
        panel.pack(fill="x")
        label(panel, "Directorio de datos", 9, MUTED).pack(anchor="w", padx=20)
        label(panel, str(self.store.directory), 10, INK, wraplength=850, justify="left").pack(anchor="w", padx=20, pady=(4, 12))
        actions = tk.Frame(panel, bg=WHITE)
        actions.pack(fill="x", padx=20, pady=(0, 20))
        button(actions, "Crear copia de seguridad", self.backup, True).pack(side="left", padx=(0, 12))
        button(actions, "Guía de uso", lambda: ReadDialog(self, "Nexo TI · Guía rápida", QUICK_HELP, markdown=True)).pack(side="left")
        label(self.content, "Versión local para un operador. SQLite y adjuntos sin cifrado propio; utiliza los permisos y el cifrado del equipo.", 9, MUTED).pack(anchor="w", pady=16)

    def backup(self):
        path = filedialog.asksaveasfilename(parent=self, title="Crear copia de seguridad", defaultextension=".zip", initialfile="nexo-respaldo-" + datetime.now().strftime("%Y%m%d-%H%M") + ".zip", filetypes=[("Copia Nexo TI", "*.zip")])
        if path:
            self.store.backup(path)
            self.store.log_run("Copia de seguridad", "Completado", Path(path).name)
            messagebox.showinfo("Copia creada", "Base de datos y adjuntos guardados en:\n" + path, parent=self)


class ReadDialog(tk.Toplevel):
    def __init__(self, app, title, content, markdown=False):
        super().__init__(app)
        self.title(title)
        self.geometry("800x570")
        self.configure(bg=BG)
        self.transient(app)
        label(self, title, 18, INK, True).pack(anchor="w", padx=24, pady=20)
        wrap, text = text_box(self)
        wrap.pack(fill="both", expand=True, padx=24)
        show_text(text, content, markdown)
        button(self, "Cerrar", self.destroy).pack(anchor="e", padx=24, pady=16)


class ArticleDialog(tk.Toplevel):
    def __init__(self, app, article=None):
        super().__init__(app)
        self.app = app
        self.article = article
        self.title("Editar artículo" if article else "Nuevo artículo")
        self.geometry("900x720")
        self.minsize(700, 550)
        self.configure(bg=BG)
        self.transient(app)
        self.grab_set()
        label(self, "Conocimiento que se comparte.", 21, INK, True).pack(anchor="w", padx=24, pady=(22, 6))
        label(self, "Escribe pasos claros, validación y criterios de escalamiento.", 10, MUTED).pack(anchor="w", padx=24, pady=(0, 18))
        self.title_var = tk.StringVar(value=article["title"] if article else "")
        self.category_var = tk.StringVar(value=article["category"] if article else "Otros")
        label(self, "TÍTULO", 8, MUTED, True).pack(anchor="w", padx=24, pady=(0, 5))
        ttk.Entry(self, textvariable=self.title_var).pack(fill="x", padx=24)
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=24, pady=14)
        label(row, "Categoría", 10, MUTED).pack(side="left", padx=(0, 12))
        ttk.Combobox(row, textvariable=self.category_var, values=CATEGORIES, state="readonly").pack(side="left")
        label(row, "Texto / Markdown básico: #, ## y listas", 9, MUTED).pack(side="right")
        wrap, self.body = text_box(self, 14)
        wrap.pack(fill="both", expand=True, padx=24)
        if article:
            self.body.insert("1.0", article["body"])
        else:
            self.body.insert("1.0", "# Objetivo\n\n## Procedimiento\n1. \n\n## Validación\n\n## Escalamiento\n")
        self.error = label(self, "", 10, RED, anchor="w")
        self.error.pack(fill="x", padx=24, pady=(10, 0))
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=24, pady=(8, 18))
        button(row, "Cancelar", self.destroy).pack(side="left")
        button(row, "Guardar artículo", self.save, True).pack(side="right")
        self.bind("<Control-s>", lambda _: self.save())

    def save(self):
        try:
            self.app.store.save_article(self.title_var.get(), self.category_var.get(), self.body.get("1.0", "end-1c"), self.article["id"] if self.article else None)
        except ValueError as error:
            self.error.configure(text=str(error))
            return
        self.destroy()
        if self.app.page == "Documentación":
            self.app.navigate("Documentación")
        self.app.status_text.set("Artículo guardado.")


class TicketDialog(tk.Toplevel):
    def __init__(self, app, ticket_id=None):
        super().__init__(app)
        self.app = app
        self.store = app.store
        self.ticket_id = ticket_id
        self.record = self.store.ticket(ticket_id) if ticket_id else None
        self.title(self.record["number"] if self.record else "Nuevo ticket · Nexo TI")
        self.geometry("1080x850")
        self.minsize(920, 700)
        self.configure(bg=BG)
        self.transient(app)
        self.grab_set()
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=24, pady=(20, 14))
        copy = tk.Frame(head, bg=BG)
        copy.pack(side="left")
        label(copy, self.record["number"] if self.record else "Nuevo ticket", 24, INK, True).pack(anchor="w")
        label(copy, (f"Creado {local_date(self.record['created_at'])}  ·  {sla_label(self.record)}" if self.record else "El número se asigna al guardar. Los campos con * son obligatorios."), 10, MUTED).pack(anchor="w", pady=5)
        if self.record:
            label(head, self.record["status"].upper(), 10, TEAL, True).pack(side="right")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24)
        details = tk.Frame(self.notebook, bg=WHITE)
        self.notebook.add(details, text="Ficha del ticket")
        self._form(details)
        if self.record:
            history = tk.Frame(self.notebook, bg=WHITE)
            attachments = tk.Frame(self.notebook, bg=WHITE)
            docs = tk.Frame(self.notebook, bg=WHITE)
            self.notebook.add(history, text="Bitácora")
            self.notebook.add(attachments, text="Adjuntos")
            self.notebook.add(docs, text="Documentación")
            self._history(history)
            self._attachments(attachments)
            self._docs(docs)
        self.error = label(self, "", 10, RED, anchor="w")
        self.error.pack(fill="x", padx=24, pady=(8, 0))
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=24, pady=(8, 18))
        button(actions, "Cerrar" if self.record else "Cancelar", self.request_close).pack(side="left")
        if self.record:
            button(actions, "Exportar ficha", self.export_ticket).pack(side="left", padx=10)
        button(actions, "Guardar cambios" if self.record else "Crear ticket", self.save, True).pack(side="right")
        self.bind("<Control-s>", lambda _: self.save())
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.initial_form = self.data()

    def _form(self, parent):
        # Formulario desplazable para pantallas de menor altura.
        canvas = tk.Canvas(parent, bg=WHITE, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        form = tk.Frame(canvas, bg=WHITE, padx=20, pady=16)
        window = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        self.vars = {}
        defaults = {"type": "Incidente", "title": "", "requester": "", "email": "", "assignee": "", "category": "Otros", "priority": "Media", "asset": "", "status": "Nuevo"}
        source = defaults | (self.record or {})
        def field(row, column, name, title, values=None, span=1, disabled=False):
            wrap = tk.Frame(form, bg=WHITE)
            wrap.grid(row=row, column=column, columnspan=span, sticky="ew", padx=(0, 12 if column == 0 and span == 1 else 0), pady=(0, 12))
            label(wrap, title, 8, MUTED, True).pack(anchor="w", pady=(0, 5))
            var = tk.StringVar(value=source[name])
            self.vars[name] = var
            if values:
                widget = ttk.Combobox(wrap, textvariable=var, values=values, state="disabled" if disabled else "readonly")
            else:
                widget = ttk.Entry(wrap, textvariable=var)
            widget.pack(fill="x")
            return widget
        self.title_entry = field(0, 0, "title", "ASUNTO *", span=2)
        field(1, 0, "type", "TIPO *", TYPES, disabled=bool(self.record))
        field(1, 1, "priority", "PRIORIDAD *", PRIORITIES)
        field(2, 0, "requester", "SOLICITANTE *")
        field(2, 1, "email", "CORREO DEL SOLICITANTE")
        field(3, 0, "assignee", "RESPONSABLE")
        field(3, 1, "category", "CATEGORÍA *", CATEGORIES)
        field(4, 0, "asset", "ACTIVO / SERVICIO")
        allowed = [source["status"]] + [s for s in STATUSES if self.record and s in TRANSITIONS[source["status"]]]
        field(4, 1, "status", "ESTADO", allowed, disabled=not self.record)
        label(form, "DESCRIPCIÓN / EVIDENCIA INICIAL *", 8, MUTED, True).grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 5))
        wrap, self.description = text_box(form, 5)
        wrap.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.description.insert("1.0", self.record["description"] if self.record else "")
        label(form, "SOLUCIÓN / RESULTADO · OBLIGATORIO AL RESOLVER", 8, MUTED, True).grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 5))
        wrap, self.resolution = text_box(form, 4)
        wrap.grid(row=8, column=0, columnspan=2, sticky="ew")
        self.resolution.insert("1.0", self.record["resolution"] if self.record else "")
        if self.record:
            label(form, "Objetivo: " + local_date(self.record["due_at"]) + " · Las esperas no pausan el SLA.", 9, MUTED).grid(row=9, column=0, columnspan=2, sticky="w", pady=12)
        self.title_entry.focus_set()

    def data(self):
        return {name: var.get() for name, var in self.vars.items()} | {"description": self.description.get("1.0", "end-1c"), "resolution": self.resolution.get("1.0", "end-1c")}

    def request_close(self):
        if self.data() != self.initial_form:
            if not messagebox.askyesno("Cambios sin guardar", "¿Cerrar y descartar los cambios de la ficha?", parent=self):
                return
        self.destroy()

    def save(self):
        try:
            if self.ticket_id:
                self.store.update_ticket(self.ticket_id, self.data(), self.app.actor, self.record["version"])
            else:
                self.ticket_id = self.store.create_ticket(self.data(), self.app.actor)
        except ValueError as error:
            self.error.configure(text=str(error))
            self.notebook.select(0)
            return
        ticket_id = self.ticket_id
        self.destroy()
        self.app.navigate(self.app.page)
        self.app.status_text.set("Ticket guardado · " + self.store.ticket(ticket_id)["number"])
        self.app.open_ticket(ticket_id)

    def _history(self, parent):
        label(parent, "Actividad y decisiones", 15, INK, True).pack(anchor="w", padx=20, pady=(20, 10))
        wrap, self.history_text = text_box(parent, 10)
        wrap.pack(fill="both", expand=True, padx=20)
        self.refresh_history()
        label(parent, "NUEVA NOTA", 8, MUTED, True).pack(anchor="w", padx=20, pady=(16, 5))
        wrap, self.note = text_box(parent, 3)
        wrap.pack(fill="x", padx=20)
        button(parent, "Agregar nota", self.add_note, True).pack(anchor="e", padx=20, pady=14)

    def refresh_history(self):
        content = "\n\n".join(f"{local_date(e['created_at'])}  ·  {e['actor']}  /  {e['kind']}\n{e['body']}" for e in self.store.events(self.ticket_id))
        show_text(self.history_text, content)

    def add_note(self):
        try:
            self.store.add_note(self.ticket_id, self.note.get("1.0", "end-1c"), self.app.actor)
        except ValueError as error:
            self.error.configure(text=str(error))
            return
        self.note.delete("1.0", "end")
        self.refresh_history()
        self.error.configure(text="Nota agregada.")

    def _attachments(self, parent):
        label(parent, "Evidencias y archivos", 15, INK, True).pack(anchor="w", padx=20, pady=(20, 8))
        label(parent, "Máximo 20 MB por archivo. Los adjuntos se copian al espacio de datos del proyecto.", 10, MUTED).pack(anchor="w", padx=20, pady=(0, 16))
        wrap, self.attachment_tree = table(parent, [("title", "ARCHIVO", 380), ("size", "TAMAÑO", 110), ("date", "AGREGADO", 180)], 6)
        wrap.pack(fill="both", expand=True, padx=20)
        self.refresh_attachments()
        actions = tk.Frame(parent, bg=WHITE)
        actions.pack(fill="x", padx=20, pady=18)
        button(actions, "+  Agregar archivo", self.attach, True).pack(side="left")
        button(actions, "Guardar copia del seleccionado", self.download_attachment).pack(side="right")

    def refresh_attachments(self):
        self.attachment_tree.delete(*self.attachment_tree.get_children())
        for row in self.store.attachments(self.ticket_id):
            self.attachment_tree.insert("", "end", iid=str(row["id"]), values=(row["name"], f"{row['size']/1024:.1f} KB", local_date(row["created_at"])))

    def attach(self):
        path = filedialog.askopenfilename(parent=self, title="Adjuntar evidencia")
        if path:
            try:
                self.store.add_attachment(self.ticket_id, path, self.app.actor)
            except ValueError as error:
                self.error.configure(text=str(error))
                return
            self.refresh_attachments()
            self.refresh_history()

    def download_attachment(self):
        selection = self.attachment_tree.selection()
        if not selection:
            self.error.configure(text="Selecciona un archivo.")
            return
        row = next(r for r in self.store.attachments(self.ticket_id) if str(r["id"]) == selection[0])
        path = filedialog.asksaveasfilename(parent=self, initialfile=row["name"])
        if path:
            self.store.save_attachment(row["id"], path)
            self.error.configure(text="Copia del adjunto guardada.")

    def _docs(self, parent):
        label(parent, "Soluciones vinculadas", 15, INK, True).pack(anchor="w", padx=20, pady=(20, 8))
        label(parent, "Relaciona procedimientos con el contexto del caso. Selecciona un artículo para leerlo.", 10, MUTED).pack(anchor="w", padx=20, pady=(0, 16))
        self.linked_wrap, self.linked_tree = table(parent, [("title", "ARTÍCULO", 550), ("category", "CATEGORÍA", 160)], 3)
        self.linked_wrap.pack(fill="x", padx=20)
        self.linked_tree.bind("<<TreeviewSelect>>", self.read_linked)
        row = tk.Frame(parent, bg=WHITE)
        row.pack(fill="x", padx=20, pady=14)
        self.article_choices = {f"KB-{a['id']:04d} · {a['title']}": a for a in self.store.articles()}
        self.article_var = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.article_var, values=list(self.article_choices), state="readonly")
        combo.pack(side="left", fill="x", expand=True, padx=(0, 12))
        button(row, "Vincular artículo", self.link_doc, True).pack(side="right")
        wrap, self.linked_body = text_box(parent, 7)
        wrap.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.refresh_linked()

    def refresh_linked(self):
        self.linked_tree.delete(*self.linked_tree.get_children())
        self.linked_articles = {a["id"]: a for a in self.store.linked_articles(self.ticket_id)}
        for article in self.linked_articles.values():
            self.linked_tree.insert("", "end", iid=str(article["id"]), values=(article["title"], article["category"]))
        children = self.linked_tree.get_children()
        if children:
            self.linked_tree.selection_set(children[0])
            self.read_linked()
        else:
            show_text(self.linked_body, "Este ticket aún no tiene documentación vinculada.")

    def read_linked(self, _=None):
        selected = self.linked_tree.selection()
        if selected:
            article = self.linked_articles[int(selected[0])]
            show_text(self.linked_body, article["body"], markdown=True)

    def link_doc(self):
        article = self.article_choices.get(self.article_var.get())
        if article:
            self.store.link_article(self.ticket_id, article["id"], self.app.actor)
            self.refresh_linked()
            self.refresh_history()

    def export_ticket(self):
        row = self.store.ticket(self.ticket_id)
        path = filedialog.asksaveasfilename(parent=self, initialfile=row["number"] + ".md", defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            content = f"# {row['number']} · {row['title']}\n\n"
            for key, name in (("type", "Tipo"), ("status", "Estado"), ("priority", "Prioridad"), ("requester", "Solicitante"), ("email", "Correo"), ("assignee", "Responsable"), ("category", "Categoría"), ("asset", "Activo / Servicio")):
                content += f"- {name}: {row[key] or '—'}\n"
            content += f"- Creado: {local_date(row['created_at'])}\n- Objetivo: {local_date(row['due_at'])}\n\n## Descripción\n\n{row['description']}\n\n## Solución\n\n{row['resolution'] or 'Pendiente'}\n\n## Bitácora\n"
            for event in self.store.events(self.ticket_id):
                content += f"\n### {local_date(event['created_at'])} · {event['actor']} · {event['kind']}\n\n{event['body']}\n"
            content += "\n## Documentación vinculada\n"
            for article in self.store.linked_articles(self.ticket_id):
                content += f"\n### KB-{article['id']:04d} · {article['title']}\n\n{article['body']}\n"
            content += "\n## Adjuntos (inventario)\n"
            for attachment in self.store.attachments(self.ticket_id):
                content += f"\n- {attachment['name']} · {attachment['size']} bytes · SHA-256: {attachment['sha256']}\n"
            Path(path).write_text(content, encoding="utf-8")
            self.error.configure(text="Ficha guardada en Markdown.")


QUICK_HELP = """# Primeros pasos

## 1. Crea un ticket
Usa Nuevo ticket o Ctrl+N. Elige Incidente para una interrupción o degradación, y Requerimiento para una solicitud de soporte o servicio. El número INC/REQ se asigna al guardar.

## 2. Da seguimiento
Abre el ticket, asigna responsable y cambia su estado. Documenta las decisiones en Bitácora y adjunta evidencias. Al resolver, escribe la solución; luego puedes cerrar el caso. Para reabrir, selecciona En progreso.

## 3. Comparte conocimiento
Crea artículos en Documentación. Desde la pestaña Documentación de un ticket, vincula los procedimientos relacionados.

## 4. Automatiza tareas
Revisa los vencimientos, valida sugerencias de clasificación y genera reportes. Las automatizaciones operan sobre los datos locales. No envían correos ni ejecutan acciones sobre servidores.

## 5. Conserva tus datos
Crea copias de seguridad desde Configuración. El ZIP incluye SQLite y adjuntos. La guía del proyecto explica cómo restaurarlo con la aplicación cerrada.

## Atajos
- Ctrl+N: nuevo ticket.
- Ctrl+F: buscar tickets o artículos.
- Ctrl+S: guardar ficha o artículo.
- F5: actualizar la vista principal.

## Objetivos de resolución
Crítica 4 h, Alta 8 h, Media 24 h, Baja 72 h. El reloj es continuo y no se detiene en espera. Se muestran las fechas en la zona horaria del equipo.
"""
