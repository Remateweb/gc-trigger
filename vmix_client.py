"""
vMix Client — Lê e parseia o XML da API do vMix.
"""
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
import requests


def fetch_vmix_xml(vmix_url: str, timeout: int = 5) -> Optional[ET.Element]:
    """Faz GET na API do vMix e retorna o XML root."""
    try:
        resp = requests.get(vmix_url, timeout=timeout)
        resp.raise_for_status()
        return ET.fromstring(resp.text)
    except requests.ConnectionError:
        raise ConnectionError(f"Não foi possível conectar ao vMix em {vmix_url}")
    except requests.Timeout:
        raise TimeoutError(f"Timeout ao conectar ao vMix ({timeout}s)")
    except ET.ParseError:
        raise ValueError("Resposta do vMix não é um XML válido")
    except requests.HTTPError as e:
        raise ConnectionError(f"vMix retornou erro: {e.response.status_code}")


def get_title_inputs(root: ET.Element) -> List[Dict]:
    """Extrai todos os inputs do tipo 'GT' ou 'Title' do XML do vMix.
    Retorna lista de {key, title, number, fields: [{name, value}]}."""
    titles = []
    inputs_el = root.find(".//inputs")
    if inputs_el is None:
        return titles

    for inp in inputs_el.findall("input"):
        inp_type = inp.get("type", "")
        # vMix usa 'GT' e 'Title' para Graphics/Titles
        if inp_type.lower() not in ("gt", "title", "gtitle"):
            continue

        key = inp.get("key", "")
        title = inp.get("title", inp.get("name", f"Input {key}"))
        number = inp.get("number", "")

        fields = []
        for text_el in inp.findall(".//text"):
            name = text_el.get("name", text_el.get("index", ""))
            value = text_el.text or ""
            fields.append({"name": name, "value": value})

        titles.append({
            "key": key,
            "title": title,
            "number": number,
            "fields": fields,
        })

    return titles


def get_field_value(root: ET.Element, title_key: str, field_name: str) -> Optional[str]:
    """Lê o valor atual de um campo específico dentro de um Title."""
    inputs_el = root.find(".//inputs")
    if inputs_el is None:
        return None

    for inp in inputs_el.findall("input"):
        if inp.get("key") == title_key:
            for text_el in inp.findall(".//text"):
                name = text_el.get("name", text_el.get("index", ""))
                if name == field_name:
                    return text_el.text or ""
    return None


def get_input_number(root: ET.Element, title_key: str) -> Optional[str]:
    """Retorna o número do input pelo key."""
    inputs_el = root.find(".//inputs")
    if inputs_el is None:
        return None
    for inp in inputs_el.findall("input"):
        if inp.get("key") == title_key:
            return inp.get("number", "")
    return None


def is_input_on_air(root: ET.Element, title_key: str) -> bool:
    """Verifica se o input está no ar (active, preview ou overlay)."""
    number = get_input_number(root, title_key)
    if not number:
        return False

    # Verificar se é o input ativo (Program)
    active_el = root.find(".//active")
    if active_el is not None and active_el.text and active_el.text.strip() == number:
        return True

    # Verificar overlays (GC normalmente fica em overlay)
    for overlay_el in root.findall(".//overlay"):
        overlay_num = overlay_el.text or overlay_el.get("number", "")
        # Overlay pode ter o número do input como texto
        if overlay_el.text and overlay_el.text.strip() == number:
            return True
        # Ou como atributo input
        if overlay_el.get("input", "") == number:
            return True

    return False
