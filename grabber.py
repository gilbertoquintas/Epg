import logging
import requests
import yaml

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
            return url
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo de configuração {config_path}: {e}")
        raise

# Função para fazer o download do arquivo a partir da URL
def download_file(url: str, output_path: str):
    try:
        logging.info(f"Iniciando o download do arquivo de {url}")
        response = requests.get(url)
        response.raise_for_status()  # Garante que a requisição foi bem-sucedida
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Arquivo salvo como {output_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao baixar o arquivo: {e}")
        raise

# Função principal que carrega a URL e faz o download
def main(config_path: str, output_path: str = 'epg.xml'):
    try:
        # Carrega a URL do arquivo de configuração
        url = load_config(config_path)
        
        # Faz o download do arquivo e salva como epg.xml
        download_file(url, output_path)
    except Exception as e:
        logging.error(f"Erro no processo: {e}")

# Exemplo de uso
if __name__ == "__main__":
    config_path = 'config.yml'  # Caminho para o arquivo de configuração
    main(config_path)
