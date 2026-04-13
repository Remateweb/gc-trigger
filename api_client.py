"""
API Client — Autenticação e disparo de webhook para a API RemateWeb.
"""
import re
import requests

TOKEN_URL = "https://test.api-net9.remateweb.com/token"
BID_URL = "https://test.api-net9.remateweb.com/api/ocr/bid"


def login(email: str, password: str, timeout: int = 15) -> dict:
    """Autentica na API RemateWeb via OAuth (password grant).
    Retorna dict com access_token e user info em caso de sucesso.
    Raise Exception em caso de falha."""
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "username": email,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )

        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get("error_description") or err.get("error") or "Credenciais inválidas"
            except Exception:
                msg = "Credenciais inválidas"
            raise ValueError(msg)

        data = resp.json()
        token = data.get("access_token", "")
        if not token:
            raise ValueError("Token não retornado pela API")

        return {"access_token": token, "userName": data.get("userName", email)}

    except requests.ConnectionError:
        raise ConnectionError("Sem conexão com a API RemateWeb")
    except requests.Timeout:
        raise TimeoutError("Timeout ao conectar na API")


def clean_value(raw: str) -> float:
    """Limpa valor monetário: remove R$, pontos, espaços, troca vírgula por ponto.
    Ex: 'R$ 25.000,00' → 25000.0"""
    if not raw:
        return 0.0
    cleaned = raw.strip()
    # Remover prefixo R$ e espaços
    cleaned = re.sub(r"[Rr]\$\s*", "", cleaned)
    # Remover espaços restantes
    cleaned = cleaned.replace(" ", "")
    # Remover pontos de milhar
    cleaned = cleaned.replace(".", "")
    # Trocar vírgula decimal por ponto
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_auction_id(raw: str) -> int:
    """Converte auctionId para int."""
    if not raw:
        return 0
    # Extrair apenas dígitos
    digits = re.sub(r"\D", "", raw.strip())
    try:
        return int(digits)
    except ValueError:
        return 0


def post_bid(api_key: str, auction_id: int, lot_number: str, value: float, api_url: str = "", timeout: int = 10) -> dict:
    """Envia dados do lance para a API RemateWeb.
    Retorna response dict em caso de sucesso."""
    url = api_url or BID_URL
    payload = {
        "apiKey": api_key,
        "auctionId": auction_id,
        "lotNumber": lot_number if lot_number and lot_number != "0" else None,
        "value": value,
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        status = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return {"status": status, "payload": payload, "response": body}
    except requests.ConnectionError:
        raise ConnectionError("Sem conexão com a API RemateWeb")
    except requests.Timeout:
        raise TimeoutError("Timeout ao enviar bid")
