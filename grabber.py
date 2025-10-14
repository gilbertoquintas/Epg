#!/usr/bin/env python3
import os
import sys
import io
import gzip
import yaml
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Tuple, Optional

# ------------- Config helpers ------------- #

def load_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def load_config(config_path: str = 'config.yml') -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return load_yaml(config_path)

def load_channel_mappings(mapping_path: str = 'channel_mappings.yml') -> Dict[str, str]:
    """
    Espera um YAML como:
    mappings:
      - original_id: "id1"
        new_id: "id 1"
      - original_id: "chA"
        new_id: "Channel A"
    Retorna um dict original_id -> new_id
    """
    if not os.path.exists(mapping_path):
        print(f"[WARN] mapping file not found: {mapping_path}. No mappings will be applied.")
        return {}
    data = load_yaml(mapping_path)
    mappings_list = data.get('mappings', [])
    out = {}
    for item in mappings_list:
        orig = item.get('original_id')
        new = item.get('new_id')
        if orig is not None and new is not None:
            out[str(orig)] = str(new)
    return out

# ------------- XML pretty ------------- #

def pretty_xml(elem: ET.Element) -> bytes:
    raw = ET.tostring(elem, encoding='utf-8')
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding='utf-8')

# ------------- Fetch / decompress ------------- #

def fetch_url(url: str, timeout: int = 30) -> bytes:
    print(f"[FETCH] {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content

def is_gzip(content: bytes) -> bool:
    return len(content) >= 2 and content[:2] == b'\x1f\x8b'

def decompress_if_gzip(content: bytes) -> bytes:
    if is_gzip(content):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as gz:
                return gz.read()
        except Exception as e:
            raise RuntimeError(f"Failed to decompress gzip: {e}")
    return content

# ------------- Helpers para mapeamento ------------- #

def map_channel_id(orig_id: str, mappings: Dict[str, str]) -> str:
    # mapeamento exato; se não existir, retorna orig_id
    return mappings.get(orig_id, orig_id)

def ensure_display_name(channel_el: ET.Element, fallback: Optional[str] = None):
    """Garante que exista um elemento <display-name> com algum texto."""
    dn = channel_el.find('display-name')
    if dn is None:
        dn = ET.SubElement(channel_el, 'display-name')
    if (dn.text is None or dn.text.strip() == '') and fallback:
        dn.text = fallback
def save_compressed_gz(filename: str, data: bytes):
    """Salva os dados em um arquivo .gz."""
    with gzip.open(filename, 'wb') as f:
        f.write(data)
    print(f"[INFO] Arquivo salvo e comprimido como {filename}")

xml_data = pretty_xml

# Salvar o arquivo XML comprimido em .gz
save_compressed_gz('output.xml.gz', xml_data)

# -------
