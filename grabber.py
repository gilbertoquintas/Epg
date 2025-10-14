import logging
import requests
import gzip
import io
import xml.etree.ElementTree as ET
import yaml
from typing import Dict

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para carregar mapeamento de IDs de um arquivo YAML
def load_channel_mappings(mapping_path: str) -> Dict[str, str]:
    try:
        with open(mapping_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            mappings = data.get('mappings', [])
            return {item['original_id']: item['new_id'] for item in mappings if 'original_id' in item and 'new_id' in item}
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo de mapeamento {mapping_path}: {e}")
        raise

# Função para carregar a URL de um arquivo de configuração YAML
def load_config(config_path: str) -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo de configuração {config_path}: {e}")
        raise

# Função para verificar se o conteúdo é GZIP
def is_gzip(content: bytes) -> bool:
    return content[:2] == b'\x1f\x8b'

# Função para descomprimir o conteúdo GZIP
def decompress_gzip(content: bytes) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as gz:
        return gz.read()

# Função para obter e descomprimir o conteúdo da URL
def fetch_and_decompress_url(url: str) -> bytes:
    try:
        logging.info(f"[FETCHING] {url}")
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
        
        # Verifica se é GZIP e descomprime
        if is_gzip(content):
            logging.info("[INFO] Content is GZIP, decompressing...")
            content = decompress_gzip(content)
        return content
    except requests.exceptions.RequestException as e:
        logging.error(f"[ERROR] Request failed: {e}")
        raise

# Função para mapear os IDs no XML de acordo com o arquivo de mapeamento
def map_channel_ids(xml_data: bytes, mappings: Dict[str, str]) -> bytes:
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logging.error(f"[ERROR] Failed to parse XML: {e}")
        raise

    # Itera sobre todos os elementos com o atributo 'id'
    for channel in root.findall('.//channel'):
        channel_id = channel.get('id')
        if channel_id and channel_id in mappings:
            new_id = mappings[channel_id]
            logging.info(f"[INFO] Mapping id {channel_id} to {new_id}")
            channel.set('id', new_id)  # Atualiza o ID com o novo valor

    # Retorna o XML modificado em formato de bytes
    return ET.tostring(root, encoding='utf-8')

# Função para salvar o XML como um arquivo GZIP
def save_as_gzip(content: bytes, output_path: str):
    try:
        with gzip.open(output_path, 'wb') as f:
            f.write(content)
        logging.info(f"[INFO] Arquivo comprimido salvo como {output_path}.")
    except Exception as e:
        logging.error(f"[ERROR] Falha ao salvar arquivo GZIP: {e}")
        raise

# Função principal para executar o processo
def main(config_path: str, mapping_path: str):
    try:
        # Carrega os dados de configuração (URL)
        config = load_config(config_path)
        url = config.get('url')
        
        if not url:
            logging.error("URL não encontrada no arquivo de configuração.")
            raise ValueError("URL not found in the configuration file.")
        
        # Carrega os mapeamentos de IDs
        mappings = load_channel_mappings(mapping_path)

        # Obtém e descomprime o conteúdo da URL
        xml_data = fetch_and_decompress_url(url)
        
        # Mapeia os IDs no XML
        mapped_xml_data = map_channel_ids(xml_data, mappings)
        
        # Salva o arquivo XML modificado como epg.xml.gz
        save_as_gzip(mapped_xml_data, 'epg.xml.gz')
    except Exception as e:
        logging.error(f"Erro no processo principal: {e}")

# Exemplo de uso
if __name__ == "__main__":
    config_path = 'config.yml'  # Caminho para o arquivo de configuração
    mapping_path = 'channel_mappings.yml'  # Caminho para o arquivo de mapeamento
    main(config_path, mapping_path)
