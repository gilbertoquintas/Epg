import logging
import requests
import yaml
import gzip
import shutil
import os

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

# Função principal que carrega a URL e faz o download
def main(config_path: str, output_path: str = 'epg.xml'):
    try:
        # Carrega a URL do arquivo de configuração
        url = load_config(config_path)
        
        # Faz o download e descomprime o arquivo XMLTV
        download_and_decompress_file(url, output_path)
    except Exception as e:
        logging.error(f"Erro no processo: {e}")

# Exemplo de uso
if __name__ == "__main__":
    config_path = 'config.yml'  # Caminho para o arquivo de configuração
    main(config_path)
