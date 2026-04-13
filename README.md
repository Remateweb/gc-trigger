# RemateWeb GC Trigger

Aplicativo Desktop (Windows) para monitoramento do vMix e disparo automático de webhooks para a API RemateWeb.

## Funcionalidades

- **Login seguro** via API RemateWeb (somente admins)
- **Conexão ao vMix** via XML API
- **Mapeamento dinâmico** dos campos de Title (Auction ID, Lot Number, Value)
- **Monitoramento em tempo real** com detecção de mudança de lote
- **Disparo automático** de webhook (`POST /api/ocr/bid`)
- **Persistência** de configurações em `config.json`

## Instalação (Windows)

```bash
# 1. Instalar dependências
setup.bat

# 2. Iniciar
start.bat
```

## Uso Manual

```bash
pip install -r requirements.txt
python app.py
```

## Arquitetura

| Arquivo | Função |
|---------|--------|
| `app.py` | UI principal (CustomTkinter) |
| `config_manager.py` | Persistência de config.json |
| `vmix_client.py` | Leitura do XML do vMix |
| `api_client.py` | Auth + webhook RemateWeb |
| `monitor.py` | Engine de monitoramento em background |

## API Endpoint

```
POST https://test.api-net9.remateweb.com/api/ocr/bid
{
  "apiKey": "...",
  "auctionId": 8934,
  "lotNumber": "15",
  "value": 25000.0
}
```
