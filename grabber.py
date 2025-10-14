import logging
import requests
import yaml
import gzip
import shutil
import os
import xml.etree.ElementTree as ET

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_config(config_path: str) -> str:
    """Carrega a URL do arquivo config.yml"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            url = config.get('url')
            if not url or not url.startswith(('http://', 'https://')):
                raise ValueError("URL inválida no arquivo de configuração.")
            return url
    except Exception as e:
        logging.error(f"Erro ao carregar config: {e}")
        raise


def download_and_decompress_file(url: str, output_path: str):
    """Faz o download do .gz e descomprime para XML"""
    try:
        logging.info(f"Baixando arquivo de: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open('temp.gz', 'wb') as f:
            f.write(response.content)

        with gzip.open('temp.gz', 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove('temp.gz')
        logging.info(f"Arquivo salvo como: {output_path}")

    except Exception as e:
        logging.error(f"Erro no download ou descompressão: {e}")
        raise


def load_channel_mappings(mapping_path: str) -> dict:
    """Carrega o arquivo de mapeamento YAML e retorna um dicionário {original_id: new_id}"""
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mappings = yaml.safe_load(f)
            return {
                ch['original_id']: ch['new_id']
                for ch in mappings.get('channels', [])
                if 'original_id' in ch and 'new_id' in ch
            }
    except Exception as e:
        logging.error(f"Erro ao carregar mapeamentos: {e}")
        raise


def apply_channel_id_mapping(xml_path: str, mapping: dict):
    """Aplica os mapeamentos ao arquivo XMLTV, sobrescrevendo o epg.xml"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Atualiza <channel id="...">
        for channel in root.findall("channel"):
            orig_id = channel.get("id")
            if orig_id in mapping:
                channel.set("id", mapping[orig_id])
                logging.debug(f"Canal {orig_id} → {mapping[orig_id]}")

        # Atualiza <programme channel="...">
        for programme in root.findall("programme"):
            orig_id = programme.get("channel")
            if orig_id in mapping:
                programme.set("channel", mapping[orig_id])
                logging.debug(f"Programa {orig_id} → {mapping[orig_id]}")

        tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        logging.info(f"Arquivo XMLTV atualizado e sobrescrito: {xml_path}")

    except Exception as e:
        logging.error(f"Erro ao aplicar mapeamentos: {e}")
        raise


def main():
    config_path = 'config.yml'
    mappings_path = 'channel_mappings.yml'
    xml_path = 'epg.xml'

    try:
        url = load_config(config_path)
        download_and_decompress_file(url, xml_path)
        mappings = load_channel_mappings(mappings_path)
        apply_channel_id_mapping(xml_path, mappings)
    except Exception as e:
        logging.error(f"Erro geral: {e}")


if __name__ == "__main__":
    main()
