import os
import sqlite3
import logging
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from datetime import datetime
from DatabaseUtils import DatabaseUtils

# Configuração do logger para registrar eventos e erros em 'BibGenerator.log'
logging.basicConfig(filename='BibGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class BibGenerator:
    def __init__(self, db_name: str, output_dir: str = "pdf_output"):
        """
        Inicializa o BibGenerator, garantindo o uso do banco correto.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.bib_database = BibDatabase()

    def fetch_entries_from_db(self) -> list:
        """
        Busca as entradas BibTeX do banco de dados.
        """
        query = "SELECT id, title, author, year, journal, volume, number, pages, doi, url FROM bib_references"
        try:
            with self.db_utils.connect() as conn:
                rows = conn.execute(query).fetchall()
            logging.info(f"Entradas recuperadas do banco de dados: {rows}")  # Log das entradas
            return [
                {
                    "ENTRYTYPE": "article",
                    "ID": f"entry_{row[0]}",
                    "title": row[1] or "Título não informado",
                    "author": row[2] or "Autor não informado",
                    "year": str(row[3]) if row[3] else "Ano não informado",
                    "journal": row[4] or "Publicação não informada",
                    "volume": row[5] or "Volume não informado",
                    "number": row[6] or "Número não informado",
                    "pages": row[7] or "Páginas não informadas",
                    "doi": row[8] or "DOI não informado",
                    "url": row[9] or "Link não informado"
                }
                for row in rows
            ]

        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar entradas do banco de dados: {e}")
            return []

    def verify_bib_integrity(self, bib_content: str) -> bool:
        """
        Verifica a integridade do conteúdo BibTeX para garantir que ele esteja bem-formado.
        """
        try:
            bibtexparser.loads(bib_content)
            return True
        except Exception as e:
            logging.error(f"Erro de integridade no conteúdo BibTeX: {e}")
            return False

    def generate_and_save_bib(self, tex_timestamp: str) -> str:
        """
        Gera e salva o arquivo BibTeX com referências do banco de dados.
        """
        try:
            entries = self.fetch_entries_from_db()
            if not entries:
                logging.warning("Nenhuma entrada encontrada para gerar o arquivo BibTeX.")
                return ""
    
            self.bib_database.entries = entries
            writer = BibTexWriter()
    
            # Gera conteúdo BibTeX
            bib_content = writer.write(self.bib_database)
            logging.info(f"Conteúdo BibTeX gerado: \n{bib_content}")
    
            # Caminho do arquivo BibTeX
            bib_path = os.path.join(self.output_dir, f"{tex_timestamp}.bib")
    
            # Grava conteúdo BibTeX em um arquivo
            with open(bib_path, "w", encoding="utf-8") as bib_file:
                bib_file.write(bib_content)
                logging.info(f"Arquivo BibTeX salvo com sucesso em: {bib_path}")
    
            # Verifica se o arquivo foi corretamente gravado
            if os.path.getsize(bib_path) == 0:
                logging.error(f"Arquivo .bib foi criado, mas está vazio: {bib_path}")
                return ""
    
            return bib_path
        except Exception as e:
            logging.error(f"Erro ao gerar e salvar o arquivo BibTeX: {e}")
            return ""
