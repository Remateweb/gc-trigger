"""
RemateWeb GC Trigger — App principal com UI CustomTkinter.
Monitora vMix e dispara webhooks para a API RemateWeb.
"""
import sys
import threading
import customtkinter as ctk
from datetime import datetime

from config_manager import load_config, save_config
from api_client import login
from vmix_client import fetch_vmix_xml, get_title_inputs
from monitor import VmixMonitor

# ============================================================
# Theme
# ============================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BRAND_COLOR = "#6C5CE7"
BRAND_HOVER = "#8B7AFF"
BG_DARK = "#0D0D12"
BG_CARD = "#16161F"
BG_INPUT = "#1E1E2A"
BORDER_COLOR = "#2A2A3A"
TEXT_PRIMARY = "#F0F0F5"
TEXT_SECONDARY = "#8888A0"
TEXT_MUTED = "#555568"
GREEN = "#00D68F"
RED = "#FF6B6B"
YELLOW = "#FFD93D"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RemateWeb GC Trigger")
        self.geometry("720x640")
        self.minsize(600, 500)
        self.configure(fg_color=BG_DARK)

        self.config = load_config()
        self.monitor: VmixMonitor | None = None
        self.titles_data: list = []
        self.access_token: str = ""

        # Iniciar na tela de login
        self._show_login()

    # ============================================================
    # Módulo 1: Login
    # ============================================================
    def _show_login(self):
        self._clear()

        frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER_COLOR)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Logo / Title
        ctk.CTkLabel(
            frame, text="🎯 GC Trigger", font=("Inter", 28, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(padx=40, pady=(32, 4))

        ctk.CTkLabel(
            frame, text="RemateWeb — Monitoramento vMix",
            font=("Inter", 13), text_color=TEXT_SECONDARY,
        ).pack(padx=40, pady=(0, 24))

        # Email
        ctk.CTkLabel(frame, text="E-MAIL", font=("Inter", 11, "bold"), text_color=TEXT_MUTED, anchor="w").pack(
            padx=40, fill="x")
        self.login_email = ctk.CTkEntry(
            frame, placeholder_text="seu@email.com", height=42,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 13),
        )
        self.login_email.pack(padx=40, fill="x", pady=(4, 12))

        # Password
        ctk.CTkLabel(frame, text="SENHA", font=("Inter", 11, "bold"), text_color=TEXT_MUTED, anchor="w").pack(
            padx=40, fill="x")
        self.login_password = ctk.CTkEntry(
            frame, placeholder_text="Digite sua senha", show="•", height=42,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 13),
        )
        self.login_password.pack(padx=40, fill="x", pady=(4, 8))

        # Error label
        self.login_error = ctk.CTkLabel(
            frame, text="", font=("Inter", 12), text_color=RED, wraplength=280,
        )
        self.login_error.pack(padx=40, pady=(0, 4))

        # Login button
        self.login_btn = ctk.CTkButton(
            frame, text="Entrar", font=("Inter", 14, "bold"), height=44,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
            command=self._do_login,
        )
        self.login_btn.pack(padx=40, fill="x", pady=(4, 32))

        # Bind Enter key
        self.login_password.bind("<Return>", lambda e: self._do_login())
        self.login_email.bind("<Return>", lambda e: self.login_password.focus())

    def _do_login(self):
        email = self.login_email.get().strip()
        password = self.login_password.get().strip()

        if not email or not password:
            self.login_error.configure(text="Preencha e-mail e senha")
            return

        self.login_btn.configure(state="disabled", text="Autenticando...")
        self.login_error.configure(text="")

        def _auth():
            try:
                result = login(email, password)
                self.access_token = result.get("access_token", "")
                self.after(0, self._show_admin)
            except Exception as e:
                self.after(0, lambda: self.login_error.configure(text=str(e)))
                self.after(0, lambda: self.login_btn.configure(state="normal", text="Entrar"))

        threading.Thread(target=_auth, daemon=True).start()

    # ============================================================
    # Módulo 2: Admin (Mapeamento)
    # ============================================================
    def _show_admin(self):
        self._clear()
        self.geometry("780x720")

        # ── Header
        header = ctk.CTkFrame(self, fg_color=BG_CARD, height=56, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🎯 GC Trigger", font=("Inter", 16, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(
            header, text="● Parado", font=("Inter", 12, "bold"), text_color=TEXT_MUTED,
        )
        self.status_label.pack(side="right", padx=20)

        # ── Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ── Card: Conexão vMix
        card_vmix = self._card(scroll, "⚙️ Conexão vMix")

        row1 = ctk.CTkFrame(card_vmix, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(row1, text="URL do vMix:", font=("Inter", 12), text_color=TEXT_SECONDARY).pack(side="left")
        self.vmix_url_entry = ctk.CTkEntry(
            row1, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12, "bold"), width=320,
        )
        self.vmix_url_entry.pack(side="left", padx=(8, 8))
        self.vmix_url_entry.insert(0, self.config.get("vmix_url", "http://127.0.0.1:8088/api"))

        self.vmix_connect_btn = ctk.CTkButton(
            row1, text="Conectar", font=("Inter", 12, "bold"), height=36, width=120,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
            command=self._connect_vmix,
        )
        self.vmix_connect_btn.pack(side="left")

        self.vmix_status = ctk.CTkLabel(card_vmix, text="", font=("Inter", 11), text_color=TEXT_MUTED)
        self.vmix_status.pack(anchor="w")

        # ── Card: API Key
        card_api = self._card(scroll, "🔑 API Key")

        ctk.CTkLabel(card_api, text="Chave de autenticação para a API RemateWeb:",
                      font=("Inter", 11), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.api_key_entry = ctk.CTkEntry(
            card_api, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12), show="•",
        )
        self.api_key_entry.pack(fill="x")
        self.api_key_entry.insert(0, self.config.get("api_key", ""))

        # ── Card: Mapeamento de campos
        card_map = self._card(scroll, "🗺️ Mapeamento de Campos")

        # Title selector
        ctk.CTkLabel(card_map, text="TITLE DO VMIX", font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(
            anchor="w", pady=(0, 4))
        self.title_combo = ctk.CTkComboBox(
            card_map, values=["Conecte ao vMix primeiro..."],
            font=("Inter", 12), fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
            height=36, command=self._on_title_selected,
        )
        self.title_combo.pack(fill="x", pady=(0, 16))

        # Field mappings
        fields_frame = ctk.CTkFrame(card_map, fg_color="transparent")
        fields_frame.pack(fill="x")
        fields_frame.columnconfigure((0, 1, 2), weight=1, uniform="col")

        # Auction ID
        f1 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(f1, text="AUCTION ID", font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.field_auction_combo = ctk.CTkComboBox(
            f1, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_auction_combo.pack(fill="x", pady=(4, 0))

        # Lot Number (Gatilho)
        f2 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f2.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(f2, text="LOT NUMBER (GATILHO)", font=("Inter", 10, "bold"), text_color=YELLOW).pack(anchor="w")
        self.field_lot_combo = ctk.CTkComboBox(
            f2, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_lot_combo.pack(fill="x", pady=(4, 0))

        # Value
        f3 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f3.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(f3, text="VALUE (R$)", font=("Inter", 10, "bold"), text_color=GREEN).pack(anchor="w")
        self.field_value_combo = ctk.CTkComboBox(
            f3, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_value_combo.pack(fill="x", pady=(4, 0))

        # Restore saved field mappings
        if self.config.get("field_auction_id"):
            self.field_auction_combo.set(self.config["field_auction_id"])
        if self.config.get("field_lot_number"):
            self.field_lot_combo.set(self.config["field_lot_number"])
        if self.config.get("field_value"):
            self.field_value_combo.set(self.config["field_value"])

        # ── Botões de ação
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(16, 0))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶ Salvar e Iniciar Monitoramento",
            font=("Inter", 14, "bold"), height=48,
            fg_color=GREEN, hover_color="#00B87A", text_color="#000",
            command=self._start_monitoring,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ Parar",
            font=("Inter", 14, "bold"), height=48,
            fg_color=RED, hover_color="#FF4444", text_color="#FFF",
            state="disabled",
            command=self._stop_monitoring,
        )
        self.stop_btn.pack(side="left", width=120)

        # ── Card: Log
        card_log = self._card(scroll, "📋 Log de Eventos")

        self.log_text = ctk.CTkTextbox(
            card_log, height=180, fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
            font=("Consolas", 11), border_color=BORDER_COLOR, border_width=1,
            corner_radius=8, state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

        # Auto-connect if vmix_url is saved
        if self.config.get("vmix_url") and self.config.get("selected_title"):
            self.after(500, self._connect_vmix)

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        """Cria um card estilizado."""
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text=title, font=("Inter", 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        return inner

    def _connect_vmix(self):
        url = self.vmix_url_entry.get().strip()
        if not url:
            self.vmix_status.configure(text="⚠️ Insira a URL do vMix", text_color=RED)
            return

        self.vmix_connect_btn.configure(state="disabled", text="Conectando...")
        self.vmix_status.configure(text="Buscando Titles...", text_color=TEXT_MUTED)

        def _fetch():
            try:
                root = fetch_vmix_xml(url)
                titles = get_title_inputs(root)

                if not titles:
                    self.after(0, lambda: self.vmix_status.configure(
                        text="⚠️ Nenhum Title encontrado no vMix", text_color=YELLOW))
                else:
                    self.titles_data = titles
                    names = [f"{t['title']} (#{t['number']})" for t in titles]
                    self.after(0, lambda: self._update_title_list(names))
                    self.after(0, lambda: self.vmix_status.configure(
                        text=f"✅ Conectado — {len(titles)} Title(s) encontrado(s)", text_color=GREEN))

                    # Auto-select saved title
                    saved = self.config.get("selected_title", "")
                    if saved:
                        for i, t in enumerate(titles):
                            if t["key"] == saved:
                                self.after(100, lambda n=names[i]: self.title_combo.set(n))
                                self.after(200, lambda n=names[i]: self._on_title_selected(n))
                                break

            except Exception as e:
                self.after(0, lambda: self.vmix_status.configure(text=f"❌ {e}", text_color=RED))
            finally:
                self.after(0, lambda: self.vmix_connect_btn.configure(state="normal", text="Conectar"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_title_list(self, names: list):
        self.title_combo.configure(values=names)
        if names:
            self.title_combo.set(names[0])
            self._on_title_selected(names[0])

    def _on_title_selected(self, selected: str):
        """Quando um Title é selecionado, preenche os ComboBoxes de campos."""
        idx = None
        for i, t in enumerate(self.titles_data):
            display = f"{t['title']} (#{t['number']})"
            if display == selected:
                idx = i
                break

        if idx is None:
            return

        title_data = self.titles_data[idx]
        field_names = [f["name"] for f in title_data["fields"]]

        if not field_names:
            field_names = ["(sem campos)"]

        self.field_auction_combo.configure(values=field_names)
        self.field_lot_combo.configure(values=field_names)
        self.field_value_combo.configure(values=field_names)

        # Auto-select saved values or defaults
        saved_auction = self.config.get("field_auction_id", "")
        saved_lot = self.config.get("field_lot_number", "")
        saved_value = self.config.get("field_value", "")

        if saved_auction in field_names:
            self.field_auction_combo.set(saved_auction)
        elif field_names[0] != "(sem campos)":
            self.field_auction_combo.set(field_names[0])

        if saved_lot in field_names:
            self.field_lot_combo.set(saved_lot)
        elif len(field_names) > 1:
            self.field_lot_combo.set(field_names[1] if len(field_names) > 1 else field_names[0])

        if saved_value in field_names:
            self.field_value_combo.set(saved_value)
        elif len(field_names) > 2:
            self.field_value_combo.set(field_names[2] if len(field_names) > 2 else field_names[-1])

    def _start_monitoring(self):
        # Validar campos
        api_key = self.api_key_entry.get().strip()
        vmix_url = self.vmix_url_entry.get().strip()
        lot_field = self.field_lot_combo.get()
        value_field = self.field_value_combo.get()
        auction_field = self.field_auction_combo.get()

        if not api_key:
            self._log("❌ API Key não preenchida")
            return
        if lot_field in ("—", "(sem campos)"):
            self._log("❌ Selecione o campo de Lote (gatilho)")
            return

        # Determinar title key
        selected_title = self.title_combo.get()
        title_key = ""
        for t in self.titles_data:
            if f"{t['title']} (#{t['number']})" == selected_title:
                title_key = t["key"]
                break

        if not title_key:
            self._log("❌ Selecione um Title do vMix")
            return

        # Salvar config
        self.config.update({
            "vmix_url": vmix_url,
            "api_key": api_key,
            "selected_title": title_key,
            "field_auction_id": auction_field,
            "field_lot_number": lot_field,
            "field_value": value_field,
        })
        save_config(self.config)
        self._log("💾 Configurações salvas")

        # Iniciar monitor
        self.monitor = VmixMonitor(
            config=self.config,
            on_log=lambda msg: self.after(0, lambda m=msg: self._log(m)),
            on_status=lambda s: self.after(0, lambda st=s: self._update_status(st)),
            on_bid_sent=lambda d: self.after(0, lambda data=d: self._on_bid(data)),
        )
        self.monitor.start()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _stop_monitoring(self):
        if self.monitor:
            self.monitor.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _update_status(self, status: str):
        if status == "running":
            self.status_label.configure(text="● Monitorando", text_color=GREEN)
        elif status == "error":
            self.status_label.configure(text="● Erro", text_color=RED)
        else:
            self.status_label.configure(text="● Parado", text_color=TEXT_MUTED)

    def _on_bid(self, data: dict):
        """Callback quando um bid é enviado."""
        pass  # Log já é feito pelo monitor

    def _log(self, message: str):
        """Adiciona mensagem ao log visual."""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{now}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ============================================================
    # Utils
    # ============================================================
    def _clear(self):
        """Remove todos os widgets da janela."""
        for w in self.winfo_children():
            w.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
