#!/usr/bin/env python3
import os
import sys
import io
import gzip
import json
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

# ------------- Conversão JSON -> XMLTV ------------- #

def json_channel_to_element(ch: dict, mappings: Dict[str, str]) -> ET.Element:
    """
    Converte um objeto de canal JSON para <channel id="..."><display-name>...</display-name></channel>
    Aplica mapeamento ao id se necessário.
    """
    orig_id = str(ch.get('id') or ch.get('channel') or ch.get('guid') or '')
    new_id = map_channel_id(orig_id, mappings)
    ch_el = ET.Element('channel', id=new_id)
    display_name = ch.get('display-name') or ch.get('name') or ch.get('title') or new_id
    dn = ET.SubElement(ch_el, 'display-name')
    dn.text = display_name
    return ch_el

def json_programme_to_element(p: dict, mappings: Dict[str, str]) -> Optional[ET.Element]:
    """
    Converte um programa JSON num elemento <programme>.
    Mapeia o campo 'channel' se necessário.
    Espera campos: channel, start, stop, title, desc/description
    """
    channel = p.get('channel')
    start = p.get('start')
    stop = p.get('stop')
    if not (channel and start and stop):
        return None
    mapped_channel = map_channel_id(str(channel), mappings)
    prog = ET.Element('programme', {
        'start': str(start),
        'stop': str(stop),
        'channel': mapped_channel
    })
    title = ET.SubElement(prog, 'title')
    title.text = p.get('title') or ''
    desc = ET.SubElement(prog, 'desc')
    desc.text = p.get('desc') or p.get('description') or ''
    return prog

def json_to_xmltv_root(json_obj: dict, mappings: Dict[str, str]) -> ET.Element:
    tv = ET.Element('tv')
    for ch in json_obj.get('channels', []):
        ch_el = json_channel_to_element(ch, mappings)
        tv.append(ch_el)
    for p in json_obj.get('programs', []) + json_obj.get('programmes', []):
        el = json_programme_to_element(p, mappings)
        if el is not None:
            tv.append(el)
    return tv

# ------------- Processamento de XML ------------- #

def copy_and_map_channel_element(ch: ET.Element, mappings: Dict[str, str]) -> ET.Element:
    """
    Retorna uma cópia do elemento <channel> com o id mapeado (se aplicável).
    Não altera o elemento original.
    """
    orig_id = ch.attrib.get('id', '')
    new_id = map_channel_id(orig_id, mappings)
    new_ch = ET.Element('channel', id=new_id)
    # copiar display-name e outros filhos (simples copy)
    for child in ch:
        # cria cópia superficial
        c = ET.SubElement(new_ch, child.tag)
        c.text = child.text
        # copiar atributos do filho, se existirem (raramente)
        if child.attrib:
            for k, v in child.attrib.items():
                c.set(k, v)
    # garantir display-name
    ensure_display_name(new_ch, fallback=new_id)
    return new_ch

def copy_and_map_programme_element(prog: ET.Element, mappings: Dict[str, str]) -> ET.Element:
    """
    Retorna uma cópia do <programme> com o atributo channel mapeado (se aplicável).
    """
    attrs = dict(prog.attrib)
    attrs['channel'] = map_channel_id(attrs.get('channel', ''), mappings)
    new_prog = ET.Element('programme', attrs)
    # copiar filhos (title, desc, etc)
    for child in prog:
        c = ET.SubElement(new_prog, child.tag)
        c.text = child.text
        if child.attrib:
            for k, v in child.attrib.items():
                c.set(k, v)
    return new_prog

# ------------- Merge logic ------------- #

def merge_sources(sources: List[dict], mappings: Dict[str, str], output_file: str = 'epg.xml'):
    """
    Processa cada source (dicionário com chaves 'url' e opcional 'type' e 'name'),
    aplica mapeamentos e escreve um XML consolidado.
    """
    tv_root = ET.Element('tv')
    seen_channels = set()  # baseado em novo_id
    programmes: List[ET.Element] = []

    for src in sources:
        url = src.get('url')
        name = src.get('name') or url
        stype = src.get('type')  # 'xml' | 'json' | None (auto detect)
        if not url:
            print(f"[WARN] source without url, skipping: {src}")
            continue

        try:
            raw = fetch_url(url)
            raw = decompress_if_gzip(raw)
        except Exception as e:
            print(f"[ERROR] failed to fetch {url}: {e}")
            continue

        # Detect type
        content = raw.lstrip()
        is_xml_content = content.startswith(b'<') or stype == 'xml'
        is_json_content = (not is_xml_content) and (stype == 'json' or content.startswith(b'{') or content.startswith(b'['))

        try:
            if is_xml_content:
                # parse XML
                other = ET.fromstring(content)
                # process channels
                for ch in other.findall('channel'):
                    new_ch = copy_and_map_channel_element(ch, mappings)
                    new_id = new_ch.attrib.get('id')
                    if new_id in seen_channels:
                        # se já existe, podemos atualizar display-name se vazio
                        seen = True
                    else:
                        tv_root.append(new_ch)
                        seen_channels.add(new_id)
                # process programmes
                for prog in other.findall('programme'):
                    new_prog = copy_and_map_programme_element(prog, mappings)
                    programmes.append(new_prog)
                print(f"[OK] merged XML source: {name}")
            elif is_json_content:
                j = json.loads(raw.decode('utf-8'))
                other_root = json_to_xmltv_root(j, mappings)
                # channels
                for ch in other_root.findall('channel'):
                    ch_id = ch.attrib.get('id')
                    if ch_id in seen_channels:
                        continue
                    tv_root.append(ch)
                    seen_channels.add(ch_id)
                # programmes
                for prog in other_root.findall('programme'):
                    programmes.append(prog)
                print(f"[OK] merged JSON source: {name}")
            else:
                print(f"[WARN] Unknown content type for {name}, skipping")
        except Exception as e:
            print(f"[ERROR] parsing source {name}: {e}")

    # append programmes after channels (so channels come first)
    for p in programmes:
        tv_root.append(p)

    # write output
    try:
        xml_bytes = pretty_xml(tv_root)
        with open(output_file, 'wb') as f:
            f.write(xml_bytes)
        print(f"[DONE] wrote {output_file}")
    except Exception as e:
        print(f"[ERROR] failed writing output: {e}")

# ------------- Main ------------- #

def main():
    cfg_path = os.environ.get('CONFIG_PATH', 'config.yml')
    mapping_path = os.environ.get('MAPPING_PATH', 'channel_mappings.yml')
    output_file = os.environ.get('OUTPUT_FILE', 'epg.xml')

    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print(f"[FATAL] could not load config: {e}")
        sys.exit(1)

    sources = cfg.get('sources', [])
    if not sources:
        print("[FATAL] no sources defined in config.yml")
        sys.exit(1)

    mappings = load_channel_mappings(mapping_path)
    if mappings:
        print(f"[INFO] loaded {len(mappings)} channel mappings")
    else:
        print("[INFO] no channel mappings loaded")

    merge_sources(sources, mappings, output_file=output_file)

if __name__ == "__main__":
    main()
