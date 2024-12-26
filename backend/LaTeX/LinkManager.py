import requests
from goose3 import Goose
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from database_utils import DatabaseUtils
import logging

# Configuração do logger para registrar eventos e erros no arquivo 'LinkManager.log'
logging.basicConfig(filename='LinkManager.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class LinkManager:
    def __init__(self, db_name: str = "database.db"):
        """
        Inicializa a classe LinkManager e configura o banco de dados e o extrator Goose.

        Parâmetros:
        db_name (str): O nome do banco de dados onde os links e suas informações serão armazenados.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.goose = Goose()

    def fetch_and_store_link(self, url: str) -> bool:
        """
        Faz o download e armazena as informações extraídas de um link. Utiliza o Goose para 
        realizar a extração dos dados principais do artigo, e insere esses dados no banco de dados.

        Parâmetros:
        url (str): A URL do link que será extraído e armazenado.

        Retorna:
        bool: `True` se o link for armazenado com sucesso, `False` em caso de falha.
        """
        try:
            response = requests.get(url, timeout=10)  # Realiza a requisição HTTP para o link
            response.raise_for_status()  # Levanta exceções para códigos de status de erro

            # Extrai as informações do link
            article = self.extract_info(url)
            if article:
                # Cria um dicionário com as informações extraídas
                link_data = {
                    "link": url,
                    "cleaned_text": article.cleaned_text,
                    "authors": ', '.join(article.authors) if article.authors else None,
                    "domain": article.domain,
                    "publish_date": article.publish_date,
                    "meta_description": article.meta_description,
                    "title": article.title,
                    "tags": ', '.join(article.tags) if article.tags else None,
                    "schema": article.schema,
                    "opengraph": article.opengraph
                }
                # Insere o link no banco de dados e retorna o resultado
                return self.db_utils.insert_link(link_data)
            return False
        except requests.RequestException as e:
            print(f"Erro ao acessar o link {url}: {e}")
            return False

    def extract_info(self, url: str) -> Optional[Any]:
        """
        Extrai informações detalhadas de um link utilizando o Goose, incluindo conteúdo limpo,
        autores, data de publicação, meta descrição e outros metadados.

        Parâmetros:
        url (str): A URL do link que será extraído.

        Retorna:
        Optional[Any]: Um objeto de artigo do Goose contendo o texto e metadados, ou `None` se falhar.
        """
        try:
            article = self.goose.extract(url)
            return article if article.cleaned_text else None
        except Exception as e:
            print(f"Erro ao extrair informações do link {url}: {e}")
            return None

    def register_multiple_links(self, urls: List[str]) -> Dict[str, bool]:
        """
        Registra múltiplos links em sequência, retornando um dicionário com o status 
        (sucesso/falha) para cada link.

        Parâmetros:
        urls (List[str]): Uma lista de URLs que serão registradas.

        Retorna:
        Dict[str, bool]: Um dicionário onde cada chave é um URL e cada valor é `True` para sucesso ou `False` para falha.
        """
        status = {}
        for url in urls:
            status[url] = self.fetch_and_store_link(url)
        return status

    def fetch_link_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Busca os dados de um link específico no banco de dados.

        Parâmetros:
        url (str): A URL do link a ser buscado.

        Retorna:
        Optional[Dict[str, Any]]: Um dicionário contendo os dados do link, ou `None` se não for encontrado.
        """
        query = "SELECT * FROM links WHERE link = ?"
        result = self.db_utils.execute_query(query, (url,))
        if result:
            # Obter os nomes das colunas e mapear os resultados para um dicionário
            columns = [desc[0] for desc in self.db_utils.connect().cursor().description]
            return dict(zip(columns, result[0]))
        return None

    def delete_link(self, url: str) -> bool:
        """
        Remove um link específico da base de dados.

        Parâmetros:
        url (str): A URL do link a ser removido.

        Retorna:
        bool: `True` se o link foi removido com sucesso, `False` caso contrário.
        """
        query = "DELETE FROM links WHERE link = ?"
        result = self.db_utils.execute_query(query, (url,))
        return result is not None

    def update_link_data(self, url: str, updated_data: Dict[str, Any]) -> bool:
        """
        Atualiza os dados de um link específico com base nos campos fornecidos no dicionário `updated_data`.

        Parâmetros:
        url (str): A URL do link a ser atualizado.
        updated_data (Dict[str, Any]): Um dicionário contendo os campos e valores a serem atualizados.

        Retorna:
        bool: `True` se a atualização foi bem-sucedida, `False` caso contrário.
        """
        set_clause = ', '.join([f"{key} = ?" for key in updated_data.keys()])
        query = f"UPDATE links SET {set_clause} WHERE link = ?"
        params = tuple(updated_data.values()) + (url,)
        result = self.db_utils.execute_query(query, params)
        return result is not None

    def fetch_all_links(self) -> List[Dict[str, Any]]:
        """
        Busca e retorna todos os links armazenados no banco de dados.

        Retorna:
        List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa um link e suas informações associadas.
        """
        rows = self.db_utils.fetch_all_links()
        # Obter os nomes das colunas e mapear os resultados para uma lista de dicionários
        columns = [desc[0] for desc in self.db_utils.connect().cursor().description]
        return [dict(zip(columns, row)) for row in rows]

    def fetch_links_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Busca e retorna todos os links de um domínio específico.

        Parâmetros:
        domain (str): O domínio a ser filtrado.

        Retorna:
        List[Dict[str, Any]]: Uma lista de dicionários com os links do domínio especificado.
        """
        query = "SELECT * FROM links WHERE domain = ?"
        rows = self.db_utils.execute_query(query, (domain,))
        if rows:
            columns = [desc[0] for desc in self.db_utils.connect().cursor().description]
            return [dict(zip(columns, row)) for row in rows]
        return []

    def clean_old_links(self, days: int = 30) -> int:
        """
        Remove links que foram armazenados há mais de um determinado número de dias.

        Parâmetros:
        days (int): O número de dias após os quais os links antigos serão removidos (padrão é 30 dias).

        Retorna:
        int: O número de links que foram removidos.
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = "DELETE FROM links WHERE publish_date < ?"
        conn = self.db_utils.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (cutoff_date,))
            deleted_count = cursor.rowcount  # Obtém o número de links removidos
            conn.commit()
            return deleted_count
        except sqlite3.Error as e:
            print(f"Erro ao limpar links antigos: {e}")
            return 0
        finally:
            self.db_utils.disconnect(conn)
