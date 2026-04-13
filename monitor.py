"""
Monitor Engine — Thread de background que monitora o vMix e dispara webhooks.
"""
import time
import threading
from datetime import datetime

from vmix_client import fetch_vmix_xml, get_field_value
from api_client import post_bid, clean_value, clean_auction_id


class VmixMonitor:
    """Motor de monitoramento do vMix em background thread."""

    def __init__(self, config: dict, on_log=None, on_status=None, on_bid_sent=None):
        self.config = config
        self.on_log = on_log or (lambda msg: print(f"[MONITOR] {msg}"))
        self.on_status = on_status or (lambda s: None)
        self.on_bid_sent = on_bid_sent or (lambda d: None)

        self._running = False
        self._thread: threading.Thread | None = None
        self._last_lot: str | None = None
        self._poll_interval = 1.0  # segundos

    @property
    def running(self) -> bool:
        return self._running

    def start(self):
        """Inicia o monitoramento em background."""
        if self._running:
            return
        self._running = True
        self._last_lot = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.on_log("Monitoramento iniciado")
        self.on_status("running")

    def stop(self):
        """Para o monitoramento."""
        self._running = False
        self.on_log("Monitoramento parado")
        self.on_status("stopped")

    def _loop(self):
        """Loop principal de polling do vMix."""
        vmix_url = self.config.get("vmix_url", "")
        title_key = self.config.get("selected_title", "")
        field_lot = self.config.get("field_lot_number", "")
        field_value = self.config.get("field_value", "")
        field_auction = self.config.get("field_auction_id", "")
        api_key = self.config.get("api_key", "")

        if not all([vmix_url, title_key, field_lot]):
            self.on_log("⚠️ Configuração incompleta (URL, Title ou Lote)")
            self._running = False
            self.on_status("error")
            return

        consecutive_errors = 0

        while self._running:
            try:
                root = fetch_vmix_xml(vmix_url)
                if root is None:
                    raise ConnectionError("XML vazio")

                # Ler campo de lote (gatilho)
                current_lot = get_field_value(root, title_key, field_lot) or ""
                current_lot = current_lot.strip()

                # Primeira leitura: salva estado sem disparar
                if self._last_lot is None:
                    self._last_lot = current_lot
                    self.on_log(f"📍 Lote inicial: {current_lot or '(vazio)'}")
                    consecutive_errors = 0
                    time.sleep(self._poll_interval)
                    continue

                # Detectar mudança no lote
                if current_lot != self._last_lot:
                    old_lot = self._last_lot
                    self._last_lot = current_lot

                    now = datetime.now().strftime("%H:%M:%S")
                    self.on_log(f"🔄 [{now}] Lote mudou: {old_lot} → {current_lot}")

                    # Ler valores atuais
                    raw_value = get_field_value(root, title_key, field_value) or "0"
                    raw_auction = get_field_value(root, title_key, field_auction) or "0"

                    value = clean_value(raw_value)
                    auction_id = clean_auction_id(raw_auction)

                    self.on_log(f"📤 Enviando: auction={auction_id} lote={current_lot} valor={value}")

                    # Disparar webhook
                    try:
                        result = post_bid(api_key, auction_id, current_lot, value)
                        status = result.get("status", "?")
                        self.on_log(f"✅ API respondeu: {status}")
                        self.on_bid_sent({
                            "time": now,
                            "lot": current_lot,
                            "value": value,
                            "auction_id": auction_id,
                            "status": status,
                        })
                    except Exception as e:
                        self.on_log(f"❌ Erro ao enviar: {e}")

                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3 or consecutive_errors % 10 == 0:
                    self.on_log(f"⚠️ Erro #{consecutive_errors}: {e}")
                if consecutive_errors == 1:
                    self.on_status("error")

            time.sleep(self._poll_interval)

        self._running = False
