import sys
from datetime import datetime
import sqlite3
import re
import random
import string
import unicodedata
from latex import escape
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

class Main:
    def __init__(self, nome_banco, nome_arquivo_saida):
        self.nome_banco = nome_banco
        self.nome_arquivo_saida = nome_arquivo_saida

    def resumo(self):
        conn = sqlite3.connect(self.nome_banco)
        cursor = conn.cursor()
        cursor.execute('SELECT plataform, analised_link, authors, publish_date, title, data_registro, tags FROM links')
        links_data = cursor.fetchall()
        conn.close()

        bib_database = BibDatabase()
        for link_data in links_data:
            bibtex_entry = self.create_bibtex_entry(link_data)
            bib_database.entries.append(bibtex_entry)

        with open(self.nome_arquivo_saida, 'w', encoding='utf-8') as file:
            writer = BibTexWriter()
            file.write(writer.write(bib_database))

    def create_bibtex_entry(self, link_data):
        platform = link_data[0]
        authors = platform if platform != "Sem Plataforma" else link_data[2] if link_data[2] else "Autor não identificado"
        if isinstance(authors, str):
            author_list = [author.strip() for author in authors.split(",")]  # Convertendo para lista, se for uma string
        else:
            author_list = authors
     
        author_string = ", ".join(author_list) if author_list else "Autor não identificado"
     
        publish_date = self.format_publish_date(link_data[3])
        data_registro = link_data[5] if link_data[5] else 'Sem Data de Registro'
        tags = eval(link_data[6]) if link_data[6] else []

        website_title = self.process_website_title(link_data[4])

        title = link_data[4]
        author = ', '.join(author_list)
        meta_description = link_data[0]

        year, month = self.deduce_year_month(publish_date, data_registro)
        online_url = link_data[1]
        data_registro_formatted = f'Acessado em {data_registro}'

        bibtex_entry_sing = {
            'ENTRYTYPE': 'online',
            'ID': website_title,
            'title': escape(f'{title}') if title else 'Sem título',
            'author': escape(f'{author_string}') if author_string else 'Autor não identificado',
            'year': escape(f'{year}') if year else 'Sem Ano',
            'month': escape(f'{month}') if month else 'Sem Mês',
            'url': f'{online_url}' if online_url else 'Sem URL',
            'note': escape(f'{data_registro_formatted}') if data_registro_formatted else 'Sem data',
            'abstract': escape(f'{meta_description}') if meta_description else 'Sem mais informações',
            'keywords': escape(f'{", ".join(tags)}') if tags else 'Sem palavras-chave'
        }

        return bibtex_entry_sing

    def format_publish_date(self, raw_date):
        if raw_date:
            try:
                date_object = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                formatted_date = date_object.strftime("%Y-%m-%d %H:%M:%S")
                return formatted_date
            except ValueError:
                return 'Sem Data'
        else:
            return 'Sem Data'

    def deduce_year_month(self, publish_date, data_registro):
        if publish_date:
            try:
                date_object = datetime.strptime(publish_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None, None
        elif data_registro:
            try:
                date_object = datetime.strptime(data_registro, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None, None
        else:
            return None, None

        year = date_object.strftime("%Y")
        month = date_object.strftime("%B")
        return year, month

    def process_website_title(self, title):
        if title:
            processed_title = re.sub(r'[^a-zA-Z0-9\s]', '', self.format_special_characters(title))
            processed_title = processed_title.replace(' ', '_')
            if len(processed_title) > 45:
                processed_title = processed_title[:45]
            elif len(processed_title) < 45:
                processed_title += self.generate_random_string(45 - len(processed_title))
            return processed_title.replace(' ', '_')
        else:
            return 'Sem_titulo'

    def format_special_characters(self, text):
        if text:
            normalized_text = unicodedata.normalize('NFKD', text)
            return ''.join([c for c in normalized_text if not unicodedata.combining(c)])
        else:
            return ''

    def generate_random_string(self, length=10):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for _ in range(length))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 bib_generator.py <nome_do_banco_de_dados> <nome_do_arquivo_de_saida>")
        sys.exit(1)

    nome_banco = sys.argv[1]
    nome_arquivo_saida = sys.argv[2]

    bib = Main(nome_banco, nome_arquivo_saida)
    bib.resumo()
