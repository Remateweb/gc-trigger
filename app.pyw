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
        self.geometry("780x720")
        self.minsize(600, 500)
        self.configure(fg_color=BG_DARK)

        self.config = load_config()
        self.monitor = None  # type: VmixMonitor | None
        self.titles_data = []
        self.is_authenticated = False

        # Abre direto na tela principal (sem login)
        self._show_admin()

    # ============================================================
    # Tela Principal (Admin)
    # ============================================================
    def _show_admin(self):
        self._clear()

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

        # Botão engrenagem (config API)
        gear_btn = ctk.CTkButton(
            header, text="⚙", font=("Inter", 18), width=40, height=36,
            fg_color="transparent", hover_color=BORDER_COLOR, text_color=TEXT_SECONDARY,
            command=self._open_settings_popup,
        )
        gear_btn.pack(side="right")

        # ── Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_DARK)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ── Card: Conexão vMix (PÚBLICO)
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

        # ── Card: Mapeamento de Campos (PÚBLICO)
        card_map = self._card(scroll, "🗺️ Mapeamento de Campos")

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

        # ── Auction ID (manual — não vem do vMix)
        auction_row = ctk.CTkFrame(card_map, fg_color="transparent")
        auction_row.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(auction_row, text="AUCTION ID (manual):", font=("Inter", 10, "bold"),
                     text_color=TEXT_MUTED).pack(side="left")
        self.auction_id_entry = ctk.CTkEntry(
            auction_row, height=34, width=180, placeholder_text="Ex: 8934",
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 12, "bold"),
        )
        self.auction_id_entry.pack(side="left", padx=(8, 0))
        saved_auction = self.config.get("auction_id", "")
        if saved_auction:
            self.auction_id_entry.insert(0, str(saved_auction))

        # ── Mapeamento de campos do vMix
        fields_frame = ctk.CTkFrame(card_map, fg_color="transparent")
        fields_frame.pack(fill="x")
        fields_frame.columnconfigure((0, 1, 2), weight=1, uniform="col")

        f2 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f2.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(f2, text="LOT NUMBER (GATILHO)", font=("Inter", 10, "bold"), text_color=YELLOW).pack(anchor="w")
        self.field_lot_combo = ctk.CTkComboBox(
            f2, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_lot_combo.pack(fill="x", pady=(4, 0))

        f3 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f3.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(f3, text="VALUE (R$)", font=("Inter", 10, "bold"), text_color=GREEN).pack(anchor="w")
        self.field_value_combo = ctk.CTkComboBox(
            f3, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_value_combo.pack(fill="x", pady=(4, 0))

        f4 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f4.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(f4, text="COND. PAGAMENTO", font=("Inter", 10, "bold"), text_color=TEXT_SECONDARY).pack(anchor="w")
        self.field_payment_combo = ctk.CTkComboBox(
            f4, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_payment_combo.pack(fill="x", pady=(4, 0))

        # Restore saved field mappings
        if self.config.get("field_lot_number"):
            self.field_lot_combo.set(self.config["field_lot_number"])
        if self.config.get("field_value"):
            self.field_value_combo.set(self.config["field_value"])
        if self.config.get("field_payment_condition"):
            self.field_payment_combo.set(self.config["field_payment_condition"])

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
            font=("Inter", 14, "bold"), height=48, width=140,
            fg_color="#CC3333", hover_color="#AA2222", text_color="#FFFFFF",
            state="disabled",
            command=self._stop_monitoring,
        )
        self.stop_btn.pack(side="left")

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

    # ============================================================
    # API Config — Popup protegido por login
    # ============================================================
    def _open_settings_popup(self):
        """Abre popup de configurações da API."""
        popup = ctk.CTkToplevel(self)
        popup.title("⚙ Configurações API")
        popup.geometry("500x420")
        popup.configure(fg_color=BG_DARK)
        popup.resizable(False, False)
        popup.grab_set()  # Modal
        popup.after(100, popup.lift)

        # Guardar referência
        self._settings_popup = popup

        container = ctk.CTkFrame(popup, fg_color=BG_CARD, corner_radius=12,
                                  border_width=1, border_color=BORDER_COLOR)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(container, text="🔒 Configuração API",
                     font=("Inter", 16, "bold"), text_color=TEXT_PRIMARY).pack(padx=20, pady=(16, 12))

        if self.is_authenticated:
            self._build_settings_unlocked(container)
        else:
            self._build_settings_login(container)

    def _build_settings_login(self, container):
        """Formulário de login dentro do popup."""
        ctk.CTkLabel(container, text="Faça login para editar a configuração",
                     font=("Inter", 11), text_color=TEXT_MUTED).pack(padx=20, pady=(0, 12))

        # Email
        ctk.CTkLabel(container, text="E-MAIL", font=("Inter", 10, "bold"),
                     text_color=TEXT_MUTED).pack(padx=20, anchor="w")
        email_entry = ctk.CTkEntry(
            container, height=36, placeholder_text="seu@email.com",
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 12),
        )
        email_entry.pack(fill="x", padx=20, pady=(4, 8))

        # Senha
        ctk.CTkLabel(container, text="SENHA", font=("Inter", 10, "bold"),
                     text_color=TEXT_MUTED).pack(padx=20, anchor="w")
        pass_entry = ctk.CTkEntry(
            container, height=36, placeholder_text="Digite sua senha", show="•",
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 12),
        )
        pass_entry.pack(fill="x", padx=20, pady=(4, 8))

        error_label = ctk.CTkLabel(container, text="", font=("Inter", 10), text_color=RED)
        error_label.pack(padx=20)

        login_btn = ctk.CTkButton(
            container, text="🔓 Desbloquear", font=("Inter", 13, "bold"), height=40,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
        )
        login_btn.pack(fill="x", padx=20, pady=(8, 20))

        def _do_login():
            email = email_entry.get().strip()
            password = pass_entry.get().strip()
            if not email or not password:
                error_label.configure(text="Preencha e-mail e senha")
                return
            login_btn.configure(state="disabled", text="Verificando...")
            error_label.configure(text="")

            def _auth():
                try:
                    login(email, password)
                    self.is_authenticated = True
                    self.after(0, lambda: self._settings_popup.destroy())
                    self.after(100, self._open_settings_popup)
                    self.after(0, lambda: self._log("🔓 Login realizado — config desbloqueada"))
                except Exception as e:
                    self.after(0, lambda: error_label.configure(text=str(e)))
                    self.after(0, lambda: login_btn.configure(state="normal", text="🔓 Desbloquear"))

            threading.Thread(target=_auth, daemon=True).start()

        login_btn.configure(command=_do_login)
        pass_entry.bind("<Return>", lambda e: _do_login())

    def _build_settings_unlocked(self, container):
        """Formulário de API key/URL desbloqueado."""
        ctk.CTkLabel(container, text="✅ Autenticado",
                     font=("Inter", 11, "bold"), text_color=GREEN).pack(padx=20, pady=(0, 12))

        # API Key
        ctk.CTkLabel(container, text="API KEY", font=("Inter", 10, "bold"),
                     text_color=TEXT_MUTED).pack(padx=20, anchor="w")
        api_key_entry = ctk.CTkEntry(
            container, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12),
        )
        api_key_entry.pack(fill="x", padx=20, pady=(4, 12))
        api_key_entry.insert(0, self.config.get("api_key", ""))

        # API URL
        ctk.CTkLabel(container, text="API ENDPOINT", font=("Inter", 10, "bold"),
                     text_color=TEXT_MUTED).pack(padx=20, anchor="w")
        api_url_entry = ctk.CTkEntry(
            container, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12),
        )
        api_url_entry.pack(fill="x", padx=20, pady=(4, 16))
        api_url_entry.insert(0, self.config.get("api_url", "https://test.api-net9.remateweb.com/api/ocr/bid"))

        def _save():
            self.config["api_key"] = api_key_entry.get().strip()
            self.config["api_url"] = api_url_entry.get().strip()
            save_config(self.config)
            self._log("💾 Configuração API salva")
            self._settings_popup.destroy()

        save_btn = ctk.CTkButton(
            container, text="💾 Salvar", font=("Inter", 13, "bold"), height=42,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
            command=_save,
        )
        save_btn.pack(fill="x", padx=20, pady=(0, 20))

    # ============================================================
    # Cards helper
    # ============================================================
    def _card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text=title, font=("Inter", 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        return inner

    # ============================================================
    # vMix Connection
    # ============================================================
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

    def _update_title_list(self, names):
        self.title_combo.configure(values=names)
        if names:
            self.title_combo.set(names[0])
            self._on_title_selected(names[0])

    def _on_title_selected(self, selected):
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

        self.field_lot_combo.configure(values=field_names)
        self.field_value_combo.configure(values=field_names)
        self.field_payment_combo.configure(values=["—"] + field_names)

        saved_lot = self.config.get("field_lot_number", "")
        saved_value = self.config.get("field_value", "")

        if saved_lot in field_names:
            self.field_lot_combo.set(saved_lot)
        elif len(field_names) > 1:
            self.field_lot_combo.set(field_names[1])

        if saved_value in field_names:
            self.field_value_combo.set(saved_value)
        elif len(field_names) > 2:
            self.field_value_combo.set(field_names[2])

        saved_payment = self.config.get("field_payment_condition", "")
        if saved_payment in field_names:
            self.field_payment_combo.set(saved_payment)
        else:
            self.field_payment_combo.set("—")

    # ============================================================
    # Monitoring
    # ============================================================
    def _start_monitoring(self):
        api_key = self.config.get("api_key", "")
        api_url = self.config.get("api_url", "")
        vmix_url = self.vmix_url_entry.get().strip()
        lot_field = self.field_lot_combo.get()
        value_field = self.field_value_combo.get()
        auction_id_str = self.auction_id_entry.get().strip()
        payment_field = self.field_payment_combo.get()
        if payment_field == "—":
            payment_field = ""

        if not api_key:
            self._log("❌ API Key não configurada — faça login e configure a API primeiro")
            return
        if not auction_id_str:
            self._log("❌ Preencha o Auction ID")
            return
        if lot_field in ("—", "(sem campos)"):
            self._log("❌ Selecione o campo de Lote (gatilho)")
            return

        selected_title = self.title_combo.get()
        title_key = ""
        for t in self.titles_data:
            if f"{t['title']} (#{t['number']})" == selected_title:
                title_key = t["key"]
                break

        if not title_key:
            self._log("❌ Selecione um Title do vMix")
            return

        # Salvar config de mapeamento
        self.config.update({
            "vmix_url": vmix_url,
            "selected_title": title_key,
            "auction_id": auction_id_str,
            "field_lot_number": lot_field,
            "field_value": value_field,
            "field_payment_condition": payment_field,
        })
        save_config(self.config)
        self._log("💾 Configurações de mapeamento salvas")

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

    def _update_status(self, status):
        if status == "running":
            self.status_label.configure(text="● Monitorando", text_color=GREEN)
        elif status == "error":
            self.status_label.configure(text="● Erro", text_color=RED)
        else:
            self.status_label.configure(text="● Parado", text_color=TEXT_MUTED)

    def _on_bid(self, data):
        pass

    def _log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{now}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
