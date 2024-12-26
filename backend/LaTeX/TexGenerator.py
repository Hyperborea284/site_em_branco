import os
import logging
import sqlite3
from datetime import datetime
from pylatex import Document, Section, Command, NoEscape
from pylatexenc.latexencode import unicode_to_latex
import subprocess

# Configuração do logger
logging.basicConfig(filename='TexGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class TexGenerator:
    """
    Classe TexGenerator para gerar, revisar e compilar documentos LaTeX a partir de dados do banco de dados.
    """
    base_dir = 'pdf_output/'

    def __init__(self, db_name: str):
        """
        Inicializa o TexGenerator, definindo o caminho do banco e o diretório de saída.
        """
        self.db_name = os.path.join(os.getcwd(), "databases", os.path.basename(db_name))
        os.makedirs(self.base_dir, exist_ok=True)

    @staticmethod
    def generate_timestamp() -> str:
        """
        Gera um timestamp formatado para nomear arquivos.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def fetch_summaries_and_sources(self) -> tuple:
        """
        Busca os resumos de cada seção do banco de dados.

        Retorna:
        tuple: Um dicionário de resumos e o conteúdo BibTeX vazio (compatibilidade futura).
        """
        sections = ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao"]
        summaries = {}

        try:
            if not os.path.exists(self.db_name):
                logging.error(f"Banco de dados não encontrado: {self.db_name}")
                return summaries, ""

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            for section in sections:
                query = f"SELECT summary_gpt3 FROM {section}"
                cursor.execute(query)
                rows = cursor.fetchall()
                summaries[section] = [row[0] for row in rows if row[0]]

            conn.close()
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar resumos: {e}")
        except Exception as e:
            logging.error(f"Erro geral: {e}")

        return summaries, ""

    def create_tex_document(self, summaries: dict, bib_path: str) -> Document:
        """
        Cria um documento LaTeX com os resumos e referências bibliográficas.

        Parâmetros:
        summaries (dict): Dicionário contendo resumos categorizados por seção.
        bib_path (str): Caminho do arquivo BibTeX.

        Retorna:
        Document: Objeto LaTeX gerado.
        """
        doc = Document(
            documentclass="abntex2",
            document_options=["article", "11pt", "oneside", "a4paper", "brazil", "sumario=tradicional"]
        )

        # Configuração do preâmbulo
        preamble = [
            r'\usepackage[T1]{fontenc}',
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage{lmodern}',
            r'\usepackage{indentfirst}',
            r'\usepackage{graphicx}',
            r'\usepackage{color}',
            r'\usepackage{microtype}',
            r'\usepackage[brazilian,hyperpageref]{backref}',
            r'\usepackage[alf]{abntex2cite}',
            r'''
            \definecolor{blue}{RGB}{41,5,195}
            \hypersetup{
                pdftitle={Relatório Gerado},
                pdfauthor={Sistema de Gerenciamento},
                pdfsubject={Relatório gerado automaticamente},
                pdfkeywords={abnt, latex, abntex2, artigo científico},
                colorlinks=true,
                linkcolor=blue,
                citecolor=blue,
                urlcolor=blue
            }
            ''',
            # Definindo o subtítulo genérico diretamente
            r'\newcommand{\theforeigntitle}{Generic Subtitle in a Foreign Language}'
        ]
        for command in preamble:
            doc.preamble.append(NoEscape(command))

        # Título, subtítulo genérico e autor
        doc.preamble.append(Command("title", "Relatório Gerado"))
        doc.preamble.append(Command("author", "Sistema de Gerenciamento"))
        doc.preamble.append(Command("date", datetime.now().strftime("%Y-%m-%d")))

        # Layout e espaçamento
        doc.preamble.append(NoEscape(r'\setlength{\parindent}{1.3cm}'))
        doc.preamble.append(NoEscape(r'\setlength{\parskip}{0.2cm}'))
        doc.preamble.append(NoEscape(r'\SingleSpacing'))

        # Adicionando capa
        doc.append(NoEscape(r'\maketitle'))
        doc.append(NoEscape(r'\selectlanguage{brazil}'))
        doc.append(NoEscape(r'\frenchspacing'))

        # Adicionando conteúdo das seções
        for section, texts in summaries.items():
            with doc.create(Section(section.capitalize())):
                for text in texts:
                    if text.strip():
                        doc.append(NoEscape(unicode_to_latex(text)))

        # Adicionando bibliografia
        if bib_path and os.path.exists(bib_path):
            doc.append(NoEscape(r'\bibliography{' + os.path.splitext(os.path.basename(bib_path))[0] + '}'))

        return doc

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo LaTeX para PDF.
        """
        try:
            base_name = os.path.splitext(tex_file_path)[0]

            for _ in range(2):  # Compilação dupla para resolver referências
                subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)

            subprocess.run(['bibtex', base_name], check=True)  # Processa referências
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)

            pdf_path = f"{base_name}.pdf"
            if os.path.exists(pdf_path):
                logging.info(f"PDF gerado com sucesso: {pdf_path}")
                return pdf_path
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao compilar LaTeX: {e}")
        return ""

    def generate_and_compile_document(self, summaries=None, bib_path=None) -> str:
        """
        Gera e compila o documento LaTeX para PDF.

        Parâmetros:
        summaries (dict): Resumos organizados em seções.
        bib_path (str): Caminho do arquivo BibTeX.

        Retorna:
        str: Caminho do arquivo PDF gerado.
        """
        timestamp = self.generate_timestamp()
        tex_file_path = os.path.join(self.base_dir, f"{timestamp}.tex")

        if summaries is None:
            summaries, _ = self.fetch_summaries_and_sources()

        # Gerando o conteúdo LaTeX
        doc = self.create_tex_document(summaries, bib_path)
        with open(tex_file_path, "w", encoding="utf-8") as tex_file:
            tex_file.write(doc.dumps())

        # Compilando o LaTeX para PDF
        return self.compile_tex_to_pdf(tex_file_path)
