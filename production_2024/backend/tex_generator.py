import sqlite3
import subprocess
from datetime import datetime
import os
import logging
import shutil
import sys
import re
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from latex import escape as latex_escape
from pylatexenc.latexencode import UnicodeToLatexEncoder

# Configurar o logger
logging.basicConfig(filename='tex_generator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseHandler:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.db_name = db_name

    def get_all_elements_from_db(self, table_name, column_name):
        query = f"SELECT {column_name} FROM {table_name}"
        self.cursor.execute(query)
        elements = self.cursor.fetchall()
        all_elements = [element[0] for element in elements] if elements else []
        return all_elements

class TexFileGenerator:
    base_dir = 'pdf_output/'

    def __init__(self, db_name):
        self.db_name = db_name
        _, db_file_name = os.path.split(db_name)
        db_name_without_extension, _ = os.path.splitext(db_file_name)

        self.caminho_bib = f"{db_name_without_extension}"

    @staticmethod
    def generate_timestamp():
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def generate_tex_file(self, db_data):
        dt_string = TexFileGenerator.generate_timestamp()
        file_name = os.path.join(TexFileGenerator.base_dir, f'{dt_string}.tex')

        with open(os.path.join(TexFileGenerator.base_dir, 'ini_latex.txt'), 'r') as arquivo_01:
            ini = arquivo_01.read()

        title = db_data[0]
        ini = ini.replace(r'\titulo{{Correntes da Antropologia}}', f'\\titulo{{{title}}}')

        encoder = UnicodeToLatexEncoder(unknown_char_policy='replace')

        dynamic_entries_section = self.generate_dynamic_entries_section()

        with open(os.path.join(TexFileGenerator.base_dir, 'end_latex.txt'), 'r') as arquivo_02:
            end = arquivo_02.read()
            end = end.replace(r'\bibliography{abntex2-modelo-artigo.bib}', f'\\bibliography{{{self.caminho_bib}}}')

        unique_paragraphs, total_paragraphs, preserved_paragraphs, duplicate_paragraphs, similarity_percent = self.get_unique_paragraphs(db_data[1:])

        # Registrar informações no arquivo de log
        logging.info(f"Total paragraphs: {total_paragraphs}")
        logging.info(f"Preserved paragraphs: {preserved_paragraphs}")
        logging.info(f"Duplicate paragraphs: {duplicate_paragraphs}")
        logging.info(f"Similarity percentage: {similarity_percent:.2f}%")

        with open(file_name, 'w', encoding='utf-8') as tex_file:
            tex_file.write(ini)
            tex_file.write(dynamic_entries_section)

            for paragraph in unique_paragraphs:
                tex_file.write(paragraph + '\n')

            tex_file.write(end)

        return file_name

    def get_unique_paragraphs(self, paragraphs):
        unique_paragraphs = []
        seen_paragraphs = set()
        total_paragraphs = len(paragraphs)
        duplicate_paragraphs = 0
    
        for paragraph in paragraphs:
            # Tokenize paragraph into sentences
            sentences = sent_tokenize(paragraph)
    
            # Preprocess sentences
            preprocessed_sentences = []
            for sentence in sentences:
                # Tokenize sentence into words
                words = word_tokenize(sentence)
    
                # Remove stopwords
                filtered_words = [word for word in words if word.lower() not in stopwords.words('english')]
    
                # Stemming
                stemmer = PorterStemmer()
                stemmed_words = [stemmer.stem(word) for word in filtered_words]
    
                # Join stemmed words back into sentence
                preprocessed_sentence = ' '.join(stemmed_words)
                preprocessed_sentences.append(preprocessed_sentence)
    
            # Join preprocessed sentences back into paragraph
            preprocessed_paragraph = ' '.join(preprocessed_sentences)
    
            # Check if preprocessed paragraph has been seen before
            if preprocessed_paragraph not in seen_paragraphs:
                seen_paragraphs.add(preprocessed_paragraph)
                unique_paragraphs.append(paragraph)
            else:
                duplicate_paragraphs += 1
    
        preserved_paragraphs = len(unique_paragraphs)
        similarity_percent = ((total_paragraphs - duplicate_paragraphs) / total_paragraphs) * 100

        return unique_paragraphs, total_paragraphs, preserved_paragraphs, duplicate_paragraphs, similarity_percent

    def generate_dynamic_entries_section(self):
        dynamic_entries_section = ""

        entry_keys = self.get_entry_keys()

        if entry_keys:
            dynamic_entries_section += "\n\\section{Aviso Importante}\n"
            dynamic_entries_section += "\\textbf{Este documento foi gerado usando processamento de linguística computacional auxiliado por inteligência artificial.} "
            dynamic_entries_section += "Para tanto foram analisadas as seguintes fontes:  "

            for i, entry_key in enumerate(entry_keys):
                dynamic_entries_section += f"\\cite{{{entry_key}}}"

                if i < len(entry_keys) - 1:
                    dynamic_entries_section += ", "

            dynamic_entries_section += ".\n"
        else:
            dynamic_entries_section += "\n\\section{Aviso Importante}\n"
            dynamic_entries_section += "\\textbf{Este documento foi gerado usando processamento de linguística computacional auxiliado por inteligência artificial.} "
        dynamic_entries_section += "\\textbf{Portanto este conteúdo requer revisão humana, pois pode conter erros.} Decisões jurídicas, de saúde, financeiras ou similares "
        dynamic_entries_section += "não devem ser tomadas com base somente neste documento. A Ephor - Linguística Computacional não se responsabiliza "
        dynamic_entries_section += "por decisões ou outros danos oriundos da tomada de decisão sem a consulta dos devidos especialistas.\n"
        dynamic_entries_section += "A consulta da originalidade deste conteúdo para fins de verificação de plágio pode ser feita em "
        dynamic_entries_section += "\\href{http://www.ephor.com.br}{ephor.com.br}.\n"

        return dynamic_entries_section

    def get_entry_keys(self):
        with open(f"{os.path.join(TexFileGenerator.base_dir, self.caminho_bib)}.bib", 'r', encoding='utf-8') as bib_file:
            bib_content = bib_file.read()

        entry_keys = re.findall(r'@online{([^,]+),', bib_content)
        return entry_keys

    def generate_pdf_from_tex(self, tex_file):
        tex_script = os.path.join(os.path.dirname(__file__), 'tex_studio.sh')

        try:
            subprocess.run([tex_script, tex_file], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: The subprocess returned a non-zero exit code: {e.returncode}")
            return

        pdf_file = os.path.splitext(os.path.basename(tex_file))[0] + '.pdf'
        pdf_file_path = os.path.join(self.base_dir, pdf_file)

        shutil.move(tex_file, os.path.join(self.base_dir, os.path.basename(tex_file)))
        shutil.move(pdf_file, pdf_file_path)

        if os.path.exists(pdf_file_path):
            print(f"PDF file generated: {pdf_file_path}")
        else:
            print(f"Error: The PDF file {pdf_file_path} does not exist.")

        temp_file_prefix = os.path.splitext(os.path.basename(tex_file))[0]
        temp_files = [f for f in os.listdir(self.base_dir) if f.startswith(temp_file_prefix)]

        for temp_file in temp_files:
            temp_file_path = os.path.join(self.base_dir, temp_file)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

def main(db_name):
    tex_generator = TexFileGenerator(db_name)
    tex_db_handler = DatabaseHandler(db_name)

    relato_gpt4_list = tex_db_handler.get_all_elements_from_db("relato", 'resume_gpt4')
    contexto_gpt4_list = tex_db_handler.get_all_elements_from_db("contexto", 'resume_gpt4')
    entidades_gpt4_list = tex_db_handler.get_all_elements_from_db("entidades", 'resume_gpt4')
    linha_tempo_gpt4_list = tex_db_handler.get_all_elements_from_db("linha_tempo", 'resume_gpt4')
    contradicoes_gpt4_list = tex_db_handler.get_all_elements_from_db("contradicoes", 'resume_gpt4')
    conclusao_gpt4_list = tex_db_handler.get_all_elements_from_db("conclusao", 'resume_gpt4')
    questionario_gpt4_list = tex_db_handler.get_all_elements_from_db("questionario", 'resume_gpt4')

    # Tratando as listas de strings extraídas do banco de dados
    relato_gpt4 = "\n\n".join(filter(None, relato_gpt4_list))
    contexto_gpt4 = "\n\n".join(filter(None, contexto_gpt4_list))
    entidades_gpt4 = "\n\n".join(filter(None, entidades_gpt4_list))
    linha_tempo_gpt4 = "\n\n".join(filter(None, linha_tempo_gpt4_list))
    contradicoes_gpt4 = "\n\n".join(filter(None, contradicoes_gpt4_list))
    conclusao_gpt4 = "\n\n".join(filter(None, conclusao_gpt4_list))
    questionario_gpt4 = "\n\n".join(filter(None, questionario_gpt4_list))

    # Obtendo o título a partir da lista relato_gpt4 e removendo a decoração \title
    if relato_gpt4:
        title_line = relato_gpt4.split('\n\n')[0]
        title = title_line.replace(r'\title{', '').replace('}', '').strip()
    else:
        title = "Título não encontrado"

    paragraphs_fin = [title, relato_gpt4, contexto_gpt4, entidades_gpt4, linha_tempo_gpt4, contradicoes_gpt4, conclusao_gpt4, questionario_gpt4]
    generated_tex_file = tex_generator.generate_tex_file(paragraphs_fin)
    tex_generator.generate_pdf_from_tex(generated_tex_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 tex_generator.py database_name.db")
        sys.exit(1)

    db_name = sys.argv[1]
    main(db_name)
