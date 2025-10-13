import sys
import os
import yaml
import requests
import gzip
import io
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List

# Funções auxiliares

def pretty_xml(elem):
    """Converte um Elemento XML para uma string formatada com indentação"""
    raw = ET.tostring(elem, encoding='utf-8')
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding='utf-8')

def parse_config(path='config.yml'):
    """Carrega as configurações do arquivo YAML"""
    with open(path, 'rb') as f:
        return yaml.safe_load(f)

def fetch_url(url, timeout=30):
    """Baixa o conteúdo de uma URL com timeout"""
    print(f"Fetching: {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content

def is_xml(content_bytes):
    """Verifica se o conteúdo é XML (baseado nos bytes iniciais)"""
    s = content_bytes.lstrip()
    return s.startswith(b'<')

def is_gzip(content_bytes):
    """Verifica se o conteúdo é comprimido em GZIP"""
    return content_bytes[:2] == b'\x1f\x8b'

def decompress_gzip(content_bytes):
    """Descomprime conteúdo GZIP"""
    with gzip.GzipFile(fileobj=io.BytesIO(content_bytes), mode='rb') as f:
        return f.read()

def load_channel_id_mappings(mapping_file='channel_mappings.yml'):
    """Carrega o mapeamento de IDs do arquivo YAML"""
    with open(mapping_file, 'r') as f:
        mappings = yaml.safe_load(f)
    return mappings.get('mappings', [])

def json_to_xmltv(json_obj, mappings):
    """
    Converte um JSON simples para um elemento <tv>, aplicando mapeamentos de IDs de canais.
    """
    tv = ET.Element('tv')
    
    # Itera sobre os canais no JSON
    for ch in json_obj.get('channels', []):
        ch_id = str(ch.get('id', 'unknown'))  # ID do canal (por padrão "unknown" se não encontrado)
        
        # Substituir o ID conforme o mapeamento
        for mapping in mappings:
            if mapping['original_id'] == ch_id:
                ch_id = mapping['new_id']  # Substitui pelo novo ID mapeado
                break  # Interrompe o loop depois de fazer a substituição

        ch_el = ET.Element('channel', id=ch_id)  # Substitui o ID do canal
        
        # Usa o nome do canal (display-name)
        name = ET.SubElement(ch_el, 'display-name')
        name.text = ch.get('display-name') or ch.get('name') or ch.get('title') or ch_el.attrib['id']
        tv.append(ch_el)
    
    # Processa os programas
    for p in json_obj.get('programs', []) + json_obj.get('programmes', []):
        channel = p.get('channel')
        start = p.get('start')
        stop = p.get('stop')
        if not (channel and start and stop):
            continue
        prog = ET.Element('programme', {
            'start': start,
            'stop': stop,
            'channel': str(channel)  # Aqui, 'channel' já deve estar com o ID atualizado
        })
        t = ET.SubElement(prog, 'title')
        t.text = p.get('title') or ''
        d = ET.SubElement(prog, 'desc')
        d.text = p.get('desc') or p.get('description') or ''
        tv.append(prog)
    
    return tv

def merge_sources(sources: List[dict], output_file='epg.xml', mapping_file='channel_mappings.yml'):
    """
    Mescla várias fontes de dados (XML ou JSON) em um único arquivo EPG.
    """
    # Carregar os mapeamentos de IDs do arquivo YAML
    mappings = load_channel_id_mappings(mapping_file)
    
    # Criar o elemento raiz do XML
    tv_root = ET.Element('tv')
    seen_channels = set()
    
    for src in sources:
        try:
            content = fetch_url(src['url'])
            if is_gzip(content):
                content = decompress_gzip(content)  # Descomprime se for GZIP
        except Exception as e:
            print(f"[WARN] failed to fetch {src.get('url')}: {e}")
            continue

        if src.get('type') == 'xml' or is_xml(content):
            try:
                other = ET.fromstring(content)
                for ch in other.findall('channel'):
                    ch_id = ch.attrib.get('id', 'unknown')  # ID do canal no XML
                    
                    # Substituir o ID conforme o mapeamento
                    for mapping in mappings:
                        if mapping['original_id'] == ch_id:
                            ch_id = mapping['new_id']  # Substitui pelo novo ID mapeado
                            break
                    
                    if ch_id in seen_channels:
                        continue
                    seen_channels.add(ch_id)
                    tv_root.append(ch)
                for prog in other.findall('programme'):
                    tv_root.append(prog)
                print(f"[OK] merged XML from {src.get('name')}")
            except Exception as e:
                print(f"[ERROR] parsing XML from {src.get('url')}: {e}")
        elif src.get('type') == 'json':
            try:
                import json
                j = json.loads(content.decode('utf-8'))
                other = json_to_xmltv(j, mappings)  # Passa os mapeamentos de IDs
                # Merge dos canais e programas
                for ch in other.findall('channel'):
                    ch_id = ch.attrib.get('id')
                    if ch_id in seen_channels:
                        continue
                    seen_channels.add(ch_id)
                    tv_root.append(ch)
                for prog in other.findall('programme'):
                    tv_root.append(prog)
                print(f"[OK] merged JSON from {src.get('name')}")
            except Exception as e:
                print(f"[ERROR] parsing JSON from {src.get('url')}: {e}")
        else:
            print(f"[WARN] unknown type for {src.get('name')}, trying XML parse")
            try:
                other = ET.fromstring(content)
                for ch in other.findall('channel'):
                    ch_id = ch.attrib.get('id', 'unknown')  # ID do canal
                    # Substituir o ID conforme o mapeamento
                    for mapping in mappings:
                        if mapping['original_id'] == ch_id:
                            ch_id = mapping['new_id']  # Substitui pelo novo ID mapeado
                            break
                    
                    if ch_id in seen_channels:
                        continue
                    seen_channels.add(ch_id)
                    tv_root.append(ch)
                for prog in other.findall('programme'):
                    tv_root.append(prog)
                print(f"[OK] merged (fallback XML) from {src.get('name')}")
            except Exception as e:
                print(f"[ERROR] fallback parse failed for {src.get('url')}: {e}")

    # Escrever o arquivo de saída
    xml_bytes = pretty_xml(tv_root)
    with open(output_file, 'wb') as f:
        f.write(xml_bytes)
    print(f"Wrote {output_file} ({len(tv_root)} child elements)")

def main():
    """Função principal que carrega a configuração e mescla as fontes"""
    cfg_path = os.environ.get('CONFIG_PATH', 'config.yml')
    out = os.environ.get('OUTPUT_FILE', 'epg.xml')
    cfg = parse_config(cfg_path)
    sources = cfg.get('sources', [])
    if not sources:
        print("No sources configured in config.yml")
        sys.exit(1)
    merge_sources(sources, output_file=out)

if __name__ == "__main__":
    main()
