import requests
import gzip
import io
import xml.etree.ElementTree as ET
import yaml
from typing import Dict

# Função para carregar mapeamento de IDs de um arquivo YAML
def load_channel_mappings(mapping_path: str) -> Dict[str, str]:
    """
    Carrega o mapeamento de IDs de um arquivo YAML. O YAML deve ter a seguinte estrutura:
    mappings:
      - original_id: "id1"
        new_id: "new_id1"
      - original_id: "id2"
        new_id: "new_id2"
    Retorna um dicionário no formato {original_id: new_id}.
    """
    with open(mapping_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
        mappings = data.get('mappings', [])
        
        return {item['original_id']: item['new_id'] for item in mappings if 'original_id' in item and 'new_id' in item}

# Função para carregar a URL de um arquivo de configuração YAML
def load_config(config_path: str) -> dict:
    """
    Carrega o arquivo config.yml que contém a URL para o arquivo .gz.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
        return config_data

# Função para verificar se o conteúdo é GZIP
def is_gzip(content: bytes) -> bool:
    return content[:2] == b'\x1f\x8b'

# Função para descomprimir o conteúdo GZIP
def decompress_gzip(content: bytes) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as gz:
        return gz.read()

# Função para obter e descomprimir o conteúdo da URL
def fetch_and_decompress_url(url: str) -> bytes:
    print(f"[FETCHING] {url}")
    response = requests.get(url)
    response.raise_for_status()
    
    content = response.content
    
    # Verifica se é GZIP e descomprime
    if is_gzip(content):
        print("[INFO] Content is GZIP, decompressing...")
        content = decompress_gzip(content)
    return content

# Função para mapear os IDs no XML de acordo com o arquivo de mapeamento
def map_channel_ids(xml_data: bytes, mappings: Dict[str, str]) -> bytes:
    # Parse o XML
    root = ET.fromstring(xml_data)
    
    # Itera sobre todos os elementos com o atributo 'id'
    for channel in root.findall('.//channel'):  # Ajuste o caminho conforme o seu XML
        channel_id = channel.get('id')
        if channel_id and channel_id in mappings:
            new_id = mappings[channel_id]
            print(f"[INFO] Mapping id {channel_id} to {new_id}")
            channel.set('id', new_id)  # Atualiza o ID com o novo valor

    # Retorna o XML modificado em formato de bytes
    return ET.tostring(root, encoding='utf-8')

# Função principal para executar o processo
def main(config_path: str, mapping_path: str):
    # Carrega os dados de configuração (URL)
    config = load_config(config_path)
    url = config.get('url')
    
    if not url:
        raise ValueError("URL not found in the configuration file.")
    
    # Carrega os mapeamentos de IDs
    mappings = load_channel_mappings(mapping_path)

    # Obtém e descomprime o conteúdo da URL
    xml_data = fetch_and_decompress_url(url)
    
    # Mapeia os IDs no XML
    mapped_xml_data = map_channel_ids(xml_data, mappings)
    
    # Aqui você pode salvar o arquivo ou retornar o XML modificado
    with open('output.xml', 'wb') as f:
        f.write(mapped_xml_data)
    print("[INFO] Arquivo XML com IDs mapeados salvo como output.xml.")

# Exemplo de uso
if __name__ == "__main__":
    config_path = 'config.yml'  # Caminho para o arquivo de configuração
    mapping_path = 'channel_mappings.yml'  # Caminho para o arquivo de mapeamento
    main(config_path, mapping_path)
