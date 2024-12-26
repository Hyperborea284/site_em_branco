import os
import logging
from sqlalchemy import create_engine
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

# Configuração do logger para registrar eventos e mensagens de erro
logging.basicConfig(filename='LlamaDatabaseQuery.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class LlamaDatabaseQuery:
    def __init__(self):
        """
        Inicializa a classe, configurando o diretório de bancos de dados e preparando a conexão para consulta.
        """
        self.databases_folder = os.path.join(os.path.dirname(__file__), 'databases')
        self.db_uri = None
        self.query_engine = None

    def select_database(self) -> str:
        """
        Lista e seleciona um banco de dados disponível no diretório de bancos.

        Retorna:
        str: URI do banco de dados selecionado, caso seja encontrado e selecionado.
        """
        # Lista os bancos de dados disponíveis
        available_databases = [f for f in os.listdir(self.databases_folder) if os.path.isfile(os.path.join(self.databases_folder, f))]

        if not available_databases:
            logging.error("Nenhum banco de dados encontrado na pasta 'databases'.")
            raise FileNotFoundError("Nenhum banco de dados encontrado na pasta 'databases'.")

        # Exibe os bancos de dados disponíveis para seleção
        print("Bancos de dados disponíveis para análise:")
        for i, db in enumerate(available_databases):
            print(f"{i + 1}. {db}")

        # Recebe a escolha do usuário e valida
        while True:
            try:
                selected_db_index = int(input("\nDigite o número correspondente ao banco de dados que deseja analisar: "))
                if 1 <= selected_db_index <= len(available_databases):
                    selected_db = available_databases[selected_db_index - 1]
                    break
                else:
                    print("Seleção inválida. Digite um número válido.")
            except ValueError:
                print("Entrada inválida. Digite um número.")

        # Define a URI do banco de dados selecionado
        db_path = os.path.join(self.databases_folder, selected_db)
        self.db_uri = f'sqlite:///{db_path}'
        logging.info(f"Banco de dados selecionado: {db_path}")
        return self.db_uri

    def initialize_query_engine(self):
        """
        Configura o SQLDatabase e o NLSQLTableQueryEngine para o banco de dados selecionado.
        """
        if not self.db_uri:
            raise ValueError("Banco de dados não selecionado. Chame select_database() antes.")

        # Conecta ao banco de dados e configura o SQLDatabase para a tabela 'links'
        engine = create_engine(self.db_uri)
        sql_database = SQLDatabase(engine, include_tables=["links"])

        # Inicializa o NLSQLTableQueryEngine para consulta na tabela 'links'
        self.query_engine = NLSQLTableQueryEngine(sql_database, tables=["links"])
        logging.info("NLSQLTableQueryEngine configurado com sucesso para a tabela 'links'.")

    def process_user_query(self, user_query: str) -> str:
        """
        Processa uma consulta de linguagem natural no banco de dados selecionado.

        Parâmetros:
        user_query (str): A consulta do usuário em linguagem natural.

        Retorna:
        str: Resposta processada da consulta.
        """
        if not self.query_engine:
            raise ValueError("Query engine não inicializado. Chame initialize_query_engine() primeiro.")

        try:
            response = self.query_engine.query(user_query)
            logging.info(f"Consulta processada: {user_query}")
            return response
        except Exception as e:
            logging.error(f"Erro ao processar a consulta '{user_query}': {e}")
            return f"Erro ao processar a consulta: {e}"

    def run_interactive_session(self):
        """
        Inicia uma sessão interativa onde o usuário pode fazer perguntas sobre o banco de dados selecionado.
        """
        if not self.db_uri or not self.query_engine:
            raise ValueError("Banco de dados ou query engine não inicializados.")

        print("Sessão interativa iniciada. Digite sua pergunta sobre o banco de dados (ou 'sair' para encerrar):\n")
        while True:
            user_query = input("> ")
            if user_query.lower() == 'sair':
                print("Encerrando a sessão interativa.")
                logging.info("Sessão interativa encerrada pelo usuário.")
                break

            # Processa a consulta do usuário e exibe a resposta
            response = self.process_user_query(user_query)
            print(response)

