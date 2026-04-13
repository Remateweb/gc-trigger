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

        fields_frame = ctk.CTkFrame(card_map, fg_color="transparent")
        fields_frame.pack(fill="x")
        fields_frame.columnconfigure((0, 1), weight=1, uniform="col")

        f1 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f1.grid(row=0, column=0, padx=(0, 6), pady=(0, 8), sticky="nsew")
        ctk.CTkLabel(f1, text="AUCTION ID", font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.field_auction_combo = ctk.CTkComboBox(
            f1, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_auction_combo.pack(fill="x", pady=(4, 0))

        f2 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f2.grid(row=0, column=1, padx=(6, 0), pady=(0, 8), sticky="nsew")
        ctk.CTkLabel(f2, text="LOT NUMBER (GATILHO)", font=("Inter", 10, "bold"), text_color=YELLOW).pack(anchor="w")
        self.field_lot_combo = ctk.CTkComboBox(
            f2, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_lot_combo.pack(fill="x", pady=(4, 0))

        f3 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f3.grid(row=1, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(f3, text="VALUE (R$)", font=("Inter", 10, "bold"), text_color=GREEN).pack(anchor="w")
        self.field_value_combo = ctk.CTkComboBox(
            f3, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_value_combo.pack(fill="x", pady=(4, 0))

        f4 = ctk.CTkFrame(fields_frame, fg_color="transparent")
        f4.grid(row=1, column=1, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(f4, text="COND. PAGAMENTO", font=("Inter", 10, "bold"), text_color=TEXT_SECONDARY).pack(anchor="w")
        self.field_payment_combo = ctk.CTkComboBox(
            f4, values=["—"], font=("Inter", 11), height=34,
            fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            button_color=BRAND_COLOR, button_hover_color=BRAND_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
        )
        self.field_payment_combo.pack(fill="x", pady=(4, 0))

        # Restore saved field mappings
        if self.config.get("field_auction_id"):
            self.field_auction_combo.set(self.config["field_auction_id"])
        if self.config.get("field_lot_number"):
            self.field_lot_combo.set(self.config["field_lot_number"])
        if self.config.get("field_value"):
            self.field_value_combo.set(self.config["field_value"])
        if self.config.get("field_payment_condition"):
            self.field_payment_combo.set(self.config["field_payment_condition"])

        # ── Card: Configuração API (PROTEGIDO — requer login)
        card_api = self._card(scroll, "🔒 Configuração API (requer login)")

        # Container para o conteúdo protegido
        self.api_config_content = ctk.CTkFrame(card_api, fg_color="transparent")
        self.api_config_content.pack(fill="x")

        if self.is_authenticated:
            self._show_api_config_unlocked()
        else:
            self._show_api_config_locked()

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
            font=("Inter", 14, "bold"), height=48, width=120,
            fg_color=RED, hover_color="#FF4444", text_color="#FFF",
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
    # API Config — Protegido por login
    # ============================================================
    def _show_api_config_locked(self):
        """Mostra estado bloqueado do card de API."""
        for w in self.api_config_content.winfo_children():
            w.destroy()

        # Mostrar API Key salva (mascarada) + API URL se existirem
        saved_key = self.config.get("api_key", "")
        saved_url = self.config.get("api_url", "https://test.api-net9.remateweb.com/api/ocr/bid")

        if saved_key:
            info = ctk.CTkFrame(self.api_config_content, fg_color="transparent")
            info.pack(fill="x", pady=(0, 8))
            masked = saved_key[:8] + "•" * (len(saved_key) - 8) if len(saved_key) > 8 else "•" * len(saved_key)
            ctk.CTkLabel(info, text=f"API Key: {masked}", font=("Inter", 11),
                         text_color=TEXT_SECONDARY).pack(anchor="w")
            ctk.CTkLabel(info, text=f"Endpoint: {saved_url}", font=("Inter", 11),
                         text_color=TEXT_MUTED).pack(anchor="w")

        # Inline login
        login_frame = ctk.CTkFrame(self.api_config_content, fg_color=BG_INPUT, corner_radius=8,
                                    border_width=1, border_color=BORDER_COLOR)
        login_frame.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(login_frame, text="Faça login para editar a configuração da API",
                     font=("Inter", 11), text_color=TEXT_MUTED).pack(padx=12, pady=(10, 6))

        row_login = ctk.CTkFrame(login_frame, fg_color="transparent")
        row_login.pack(fill="x", padx=12, pady=(0, 4))

        self.inline_email = ctk.CTkEntry(
            row_login, placeholder_text="E-mail", height=34, width=180,
            fg_color=BG_DARK, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 11),
        )
        self.inline_email.pack(side="left", padx=(0, 6))

        self.inline_password = ctk.CTkEntry(
            row_login, placeholder_text="Senha", show="•", height=34, width=150,
            fg_color=BG_DARK, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=("Inter", 11),
        )
        self.inline_password.pack(side="left", padx=(0, 6))

        self.inline_login_btn = ctk.CTkButton(
            row_login, text="🔓 Desbloquear", font=("Inter", 11, "bold"), height=34, width=130,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
            command=self._do_inline_login,
        )
        self.inline_login_btn.pack(side="left")

        self.inline_error = ctk.CTkLabel(login_frame, text="", font=("Inter", 10), text_color=RED)
        self.inline_error.pack(padx=12, pady=(0, 10))

        # Bind Enter
        self.inline_password.bind("<Return>", lambda e: self._do_inline_login())

    def _do_inline_login(self):
        """Login inline para desbloquear a configuração da API."""
        email = self.inline_email.get().strip()
        password = self.inline_password.get().strip()

        if not email or not password:
            self.inline_error.configure(text="Preencha e-mail e senha")
            return

        self.inline_login_btn.configure(state="disabled", text="Verificando...")
        self.inline_error.configure(text="")

        def _auth():
            try:
                login(email, password)
                self.is_authenticated = True
                self.after(0, self._show_api_config_unlocked)
                self.after(0, lambda: self._log("🔓 Login realizado — API desbloqueada"))
            except Exception as e:
                self.after(0, lambda: self.inline_error.configure(text=str(e)))
                self.after(0, lambda: self.inline_login_btn.configure(state="normal", text="🔓 Desbloquear"))

        threading.Thread(target=_auth, daemon=True).start()

    def _show_api_config_unlocked(self):
        """Mostra o formulário completo de configuração da API."""
        for w in self.api_config_content.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.api_config_content, text="✅ Autenticado — configure a API abaixo",
                     font=("Inter", 11, "bold"), text_color=GREEN).pack(anchor="w", pady=(0, 8))

        # API Key
        ctk.CTkLabel(self.api_config_content, text="API KEY",
                     font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.api_key_entry = ctk.CTkEntry(
            self.api_config_content, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12),
        )
        self.api_key_entry.pack(fill="x", pady=(4, 12))
        self.api_key_entry.insert(0, self.config.get("api_key", ""))

        # API URL (endpoint)
        ctk.CTkLabel(self.api_config_content, text="API ENDPOINT (URL de envio dos lotes)",
                     font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        self.api_url_entry = ctk.CTkEntry(
            self.api_config_content, height=36, fg_color=BG_INPUT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=("Inter", 12),
        )
        self.api_url_entry.pack(fill="x", pady=(4, 8))
        self.api_url_entry.insert(0, self.config.get("api_url", "https://test.api-net9.remateweb.com/api/ocr/bid"))

        # Botão salvar API config
        save_api_btn = ctk.CTkButton(
            self.api_config_content, text="💾 Salvar Configuração API",
            font=("Inter", 12, "bold"), height=36,
            fg_color=BRAND_COLOR, hover_color=BRAND_HOVER,
            command=self._save_api_config,
        )
        save_api_btn.pack(anchor="w", pady=(4, 0))

    def _save_api_config(self):
        """Salva API key e URL no config.json."""
        api_key = self.api_key_entry.get().strip()
        api_url = self.api_url_entry.get().strip()

        self.config["api_key"] = api_key
        self.config["api_url"] = api_url
        save_config(self.config)
        self._log("💾 Configuração da API salva")

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

        self.field_auction_combo.configure(values=field_names)
        self.field_lot_combo.configure(values=field_names)
        self.field_value_combo.configure(values=field_names)
        self.field_payment_combo.configure(values=["—"] + field_names)

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
        auction_field = self.field_auction_combo.get()
        payment_field = self.field_payment_combo.get()
        if payment_field == "—":
            payment_field = ""

        if not api_key:
            self._log("❌ API Key não configurada — faça login e configure a API primeiro")
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
            "field_auction_id": auction_field,
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
