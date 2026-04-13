"""
Config Manager — Gerencia config.json para persistência de configurações.
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "vmix_url": "http://127.0.0.1:8088/api",
    "api_key": "0c18ab41-eb23-4782-8e3f-34582fad10b6",
    "api_url": "https://test.api-net9.remateweb.com/api/ocr/bid",
    "selected_title": "",
    "field_auction_id": "",
    "field_lot_number": "",
    "field_value": "",
    "field_payment_condition": "",
}


def load_config() -> dict:
    """Carrega config.json ou retorna defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge com defaults para garantir que todas as chaves existam
            merged = {**DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, IOError):
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """Salva configurações no config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[CONFIG] Erro ao salvar: {e}")
