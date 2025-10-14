import logging
import requests
import yaml
import gzip
import shutil
import os
import xml.etree.ElementTree as ET

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para carregar a URL a partir do arquivo config.yml
def load_config(config_path: str) -> str:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            url = config.get('url')
            if not url:
                logging.error("URL não encontrada no arquivo de configuração.")
                raise ValueError("URL não encontrada no arquivo de configuração.")
            # Verifica se a URL é válida (pelo menos começa com http:// ou https://)
            if not (url.startswith('http://') or url.startswith('https://')):
                logging.error(f"URL inválida encontrada: {url}")
                raise ValueError(f"URL inválida encontrada: {url}")
            return url
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo de configuração {config_path}: {e}")
        raise

# Função para fazer o download do arquivo a partir da URL
def download_and_decompress_file(url: str, output_path: str):
    try:
        logging.info(f"Iniciando o download do arquivo de {url}")
        response = requests.get(url, timeout=10)  # Timeout de 10 segundos
        response.raise_for_status()  # Garante que a requisição foi bem-sucedida

        # Salva o arquivo comprimido temporariamente
        temp_gz_path = 'temp_file.gz'
        with open(temp_gz_path, 'wb') as f:
            f.write(response.content)

        # Descomprime o arquivo .gz para o caminho de saída
        with gzip.open(temp_gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)  # Copia o conteúdo descomprimido para o arquivo final

        logging.info(f"Arquivo descomprimido e salvo como {output_path}")
        
        # Remove o arquivo temporário
        os.remove(temp_gz_path)
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao baixar o arquivo: {e}")
        raise
    except IOError as e:
        logging.error(f"Erro ao salvar o arquivo no disco: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro desconhecido: {e}")
        raise

def apply_channel_id_mapping(xmltv_path: str, channel_mappings_path: str, output_path: str = None):
    try:
        # Carregar o mapeamento
        with open(channel_mappings_path, 'r', encoding='utf-8') as f:
            mappings = yaml.safe_load(f)
        
        mapping_dict = {
            channel['original_id']: channel['new_id']
            for channel in mappings.get('channels', [])
            if channel.get('original_id') and channel.get('new_id')
        }

        if not mapping_dict:
            raise ValueError("Nenhum mapeamento válido encontrado no arquivo YAML.")

        # Parse do XML
        tree = ET.parse(xmltv_path)
        root = tree.getroot()

        # Atualizar <channel id="...">
        for channel in root.findall("channel"):
            orig_id = channel.get("id")
            if orig_id in mapping_dict:
                new_id = mapping_dict[orig_id]
                logging.info(f"Atualizando canal: {orig_id} → {new_id}")
                channel.set("id", new_id)

        # Atualizar <programme channel="...">
        for programme in root.findall("programme"):
            orig_id = programme.get("channel")
            if orig_id in mapping_dict:
                new_id = mapping_dict[orig_id]
                logging.info(f"Atualizando programa: {orig_id} → {new_id}")
                programme.set("channel", new_id)

        # Salvar novo arquivo
        output_file = output_path if output_path else xmltv_path
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        logging.info(f"Arquivo XML atualizado salvo em: {output_file}")

    except Exception as e:
        logging.error(f"Erro ao aplicar mapeamento de canais no XML: {e}")
        raise

# Função principal que carrega a URL e faz o download
def main(config_path: str, output_path: str = 'epg.xml', channel_mappings_path: str = 'channel_mappings.yml'):
    try:
        # Carrega a URL do arquivo de configuração
        url = load_config(config_path)
        
        # Faz o download e descomprime o arquivo XMLTV
        download_and_decompress_file(url, output_path)
        
        # Exemplo de atualização do ID do canal
        apply_channel_id_mapping('epg.xml', 'channel_mappings.yml')
    
    except Exception as e:
        logging.error(f"Erro no processo: {e}")

# Exemplo de uso
if __name__ == "__main__":
    config_path = 'config.yml'  # Caminho para o arquivo de configuração
    channel_mappings_path = 'channel_mappings.yml'  # Caminho para o arquivo de mapeamento dos canais
    main(config_path, channel_mappings_path=channel_mappings_path)
