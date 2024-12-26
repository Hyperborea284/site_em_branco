import os
import subprocess
import logging
from datetime import datetime
from pylatexenc.latexencode import UnicodeToLatexEncoder
from dotenv import load_dotenv
import shutil

# Configuração do logger para capturar eventos e erros
logging.basicConfig(filename='PDFGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(".env")

class PDFGenerator:
    """
    Classe responsável pela geração de arquivos PDF a partir de conteúdo LaTeX.
    A PDFGenerator lida com a criação do arquivo LaTeX, compilação para PDF e
    limpeza de arquivos auxiliares gerados durante o processo.
    """
    base_dir = 'pdf_output/'

    def __init__(self):
        """
        Inicializa a classe PDFGenerator, criando o diretório de saída para PDFs e arquivos auxiliares,
        além de configurar o encoder para garantir compatibilidade com o LaTeX.
        """
        os.makedirs(self.base_dir, exist_ok=True)
        self.encoder = UnicodeToLatexEncoder(unknown_char_policy='replace')

    @staticmethod
    def generate_timestamp():
        """
        Gera um timestamp formatado para ser usado em nomes de arquivos, evitando sobreposição e facilitando o histórico.

        Retorna:
        str: Timestamp formatado como 'AAAA-MM-DD-HH-MM-SS'.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo .tex em um arquivo PDF.

        Parâmetros:
        tex_file_path (str): Caminho do arquivo .tex.

        Retorna:
        str: Caminho do arquivo PDF gerado ou string vazia se houve erro.
        """
        if not os.path.exists(tex_file_path):
            logging.error(f"Arquivo .tex não encontrado: {tex_file_path}")
            return ""

        try:
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
            pdf_file_path = os.path.splitext(tex_file_path)[0] + ".pdf"
            if os.path.exists(pdf_file_path):
                logging.info(f"PDF gerado com sucesso: {pdf_file_path}")
                return pdf_file_path
            else:
                logging.error(f"Erro: PDF não foi gerado.")
                return ""
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao compilar o arquivo LaTeX: {e}")
            return ""

    def cleanup_auxiliary_files(self, tex_file_path: str):
        """
        Remove arquivos auxiliares gerados durante a compilação LaTeX, mantendo apenas o arquivo PDF final.

        Parâmetros:
        tex_file_path (str): Caminho completo do arquivo LaTeX (.tex) cuja base será usada para encontrar os arquivos auxiliares.
        """
        base_name = os.path.splitext(os.path.basename(tex_file_path))[0]
        aux_extensions = ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.toc', '.synctex.gz', '.bbl', '.blg']

        for ext in aux_extensions:
            aux_file = os.path.join(self.base_dir, base_name + ext)
            if os.path.exists(aux_file):
                try:
                    os.remove(aux_file)
                    logging.info(f"Removed auxiliary file: {aux_file}")
                except OSError as e:
                    logging.warning(f"Failed to remove {aux_file}: {e}")

    def move_pdf_to_output(self, pdf_file_path: str) -> str:
        """
        Move o arquivo PDF final para o diretório de saída, se necessário, e retorna o caminho final.

        Parâmetros:
        pdf_file_path (str): Caminho completo do arquivo PDF que será movido.

        Retorna:
        str: Caminho final do PDF na pasta de saída ou uma string vazia em caso de erro.
        """
        final_pdf_path = os.path.join(self.base_dir, os.path.basename(pdf_file_path))

        try:
            shutil.move(pdf_file_path, final_pdf_path)
            logging.info(f"PDF moved to output directory: {final_pdf_path}")
            return final_pdf_path
        except Exception as e:
            logging.error(f"Error moving PDF to output directory: {e}")
            return ""

    def open_pdf_with_okular(self, pdf_file_path: str):
        """
        Abre o arquivo PDF gerado usando o visualizador Okular.

        Parâmetros:
        pdf_file_path (str): Caminho completo do arquivo PDF a ser aberto.
        """
        try:
            subprocess.Popen(['okular', pdf_file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info(f"PDF opened with Okular: {pdf_file_path}")
        except Exception as e:
            logging.error(f"Failed to open PDF with Okular: {e}")

    def generate_and_compile_pdf(self, tex_content: str, file_name_prefix: str) -> str:
        """
        Gera um arquivo LaTeX (.tex) com base no conteúdo fornecido, compila-o em PDF,
        e limpa arquivos auxiliares após a compilação.

        Parâmetros:
        tex_content (str): Conteúdo LaTeX a ser salvo e compilado.
        file_name_prefix (str): Prefixo para o nome do arquivo, facilitando a identificação do arquivo gerado.

        Retorna:
        str: Caminho completo do arquivo PDF gerado ou uma string vazia em caso de erro.
        """
        # Geração do caminho para o arquivo .tex com timestamp para evitar sobrescrita
        timestamp = self.generate_timestamp()
        tex_file_path = os.path.join(self.base_dir, f"{file_name_prefix}_{timestamp}.tex")

        # Salvar o conteúdo LaTeX no arquivo .tex para posterior compilação
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        logging.info(f"LaTeX file saved for compilation: {tex_file_path}")

        # Compilação do arquivo .tex em .pdf
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)

        if pdf_file_path:
            # Limpeza de arquivos auxiliares gerados durante a compilação
            self.cleanup_auxiliary_files(tex_file_path)
            # Movendo o PDF final para o diretório de saída
            final_pdf_path = self.move_pdf_to_output(pdf_file_path)
            # Abrindo o PDF com Okular
            if final_pdf_path:
                self.open_pdf_with_okular(final_pdf_path)
            return final_pdf_path
        else:
            logging.error(f"PDF compilation failed for: {tex_file_path}")
            return ""
