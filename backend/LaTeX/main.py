import os
import sys
import logging
from datetime import datetime
from DatabaseUtils import DatabaseUtils, LinkManager
from SummarizerManager import SummarizerManager
from LlamaQueryEngine import LlamaDatabaseQuery
from TexGenerator import TexGenerator
from BibGenerator import BibGenerator
from TexGenerator import TexGenerator

# Configuração de logging
logging.basicConfig(filename='main.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Main:
    def __init__(self):
        """
        Inicializa a aplicação principal, configura banco de dados, e cria os componentes necessários.
        """
        self.db_utils = None
        self.link_manager = None
        self.nome_banco = None
        self.pdf_generator = None
        self.query_engine = None

    def escolher_ou_criar_banco(self):
        """
        Exibe os bancos de dados existentes e permite ao usuário selecionar ou criar um novo.
        """
        os.makedirs('databases', exist_ok=True)
        bancos_existentes = [file for file in os.listdir('databases') if file.endswith('.db')]

        if bancos_existentes:
            print("\nBancos de dados existentes:")
            for i, banco in enumerate(bancos_existentes, 1):
                print(f"{i}. {banco}")

            escolha = input("Deseja usar um banco de dados existente? (S/N): ").strip().lower()
            if escolha == 's':
                indice = int(input("Digite o número do banco de dados desejado: "))
                self.nome_banco = bancos_existentes[indice - 1]
            else:
                self.nome_banco = input("Digite o nome do novo banco de dados (inclua '.db'): ").strip()
        else:
            self.nome_banco = input("Digite o nome do novo banco de dados (inclua '.db'): ").strip()

        self.atualizar_banco(self.nome_banco)

    def atualizar_banco(self, nome_banco: str):
        """
        Configura o banco de dados para ser usado pela aplicação.
        """
        caminho_banco = os.path.join(os.getcwd(), "databases", nome_banco)
        self.db_utils = DatabaseUtils(caminho_banco)
        self.link_manager = LinkManager(caminho_banco)
        self.query_engine = LlamaDatabaseQuery()

        # Verifica e garante a criação de tabelas necessárias
        self.db_utils.create_and_populate_references_table()  # Garantir bib_references
        self.db_utils.create_summary_tables()  # Garantir tabelas de resumo

        print(f"Banco de dados configurado: {caminho_banco}")

    def limpar_tela(self):
        """
        Limpa o terminal.
        """
        os.system('clear' if os.name == 'posix' else 'cls')

    def exibir_logo(self):
        """
        Exibe o logotipo da aplicação.
        """
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logo = f"""
        ╔══════════════════════════════════════════════════╗
        ║                                                  ║
        ║      Bem-vindo ao Sistema de Gerenciamento!      ║
        ║                                                  ║
        ║   Este programa gerencia informações de links,   ║
        ║   realiza sumarizações e gera relatórios.        ║
        ║                                                  ║
        ║   Data e Hora: {data}               ║
        ╚══════════════════════════════════════════════════╝
        """
        print(logo)

    def loop_inserir_links(self):
        """
        Loop para registro de links fornecidos pelo usuário.
        """
        print("\nAtivação do Loop de Inserção de Links")
        print("Pressione 's' para encerrar o loop e iniciar a sumarização.")

        while True:
            link = input('Digite o link que deseja registrar: ')
            if link.lower() == 's':
                break

            if not self.link_manager.is_valid_url(link):
                print("Link inválido. Por favor, forneça um link válido.")
                continue

            try:
                sucesso = self.link_manager.fetch_and_store_link(link)
                if sucesso:
                    print(f"Link registrado com sucesso: {link}")
                else:
                    print(f"Falha ao registrar o link: {link}")
            except Exception as e:
                print(f"Erro ao registrar o link: {e}")

    def remover_link_especifico(self):
        """
        Exibe uma lista de links e permite ao usuário escolher um para remoção.
        """
        links = self.link_manager.get_all_links()
        if not links:
            print("Não há links para remover.")
            return

        print("\nLinks disponíveis para remoção:")
        for i, link in enumerate(links, 1):
            print(f"{i}. {link['link']}")

        escolha = int(input("Digite o número do link que deseja remover: "))
        if 1 <= escolha <= len(links):
            link_escolhido = links[escolha - 1]["link"]
            if self.link_manager.delete_link(link_escolhido):
                print(f"Link removido com sucesso: {link_escolhido}")
            else:
                print(f"Erro ao remover o link: {link_escolhido}")
        else:
            print("Número inválido.")

    def gerar_pdf(self):
        """
        Realiza o fluxo completo: sumarização, geração de BibTeX, LaTeX e PDF.
        """
        print("\nGerando PDF com os dados registrados...")
        try:
            # Etapa 1: Ativar sumarização ou carregar resumos existentes
            print("Ativando sumarização e memoizando resultados...")
            summarizer = SummarizerManager(self.nome_banco)
            summaries = summarizer.synthesize_content()  # Processa links e memoiza os resumos
    
            if not summaries:
                print("Erro: Nenhum resumo novo foi gerado. Verificando se existem resumos já armazenados.")
                logging.error("Nenhum resumo foi gerado. Carregando resumos existentes do banco.")
                summaries = summarizer.db_utils.fetch_all_existing_summaries()  # Carregar resumos existentes
    
            if not summaries:
                print("Erro: Nenhum resumo disponível para gerar o PDF.")
                logging.error("Nenhum resumo disponível. Processo de geração interrompido.")
                return
    
            # Etapa 2: Gerar arquivo BibTeX
            print("Gerando arquivo BibTeX...")
            bib_generator = BibGenerator(self.nome_banco)
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")  # Geração de timestamp
            bib_path = bib_generator.generate_and_save_bib(timestamp)
    
            if not bib_path or os.path.getsize(bib_path) == 0:
                print("Erro ao gerar o arquivo BibTeX ou arquivo vazio.")
                logging.error(f"Arquivo BibTeX gerado vazio ou inexistente: {bib_path}")
                return
    
            # Log de sucesso na geração do BibTeX
            logging.info(f"Arquivo BibTeX gerado com sucesso: {bib_path}")
    
            # Etapa 3: Gerar PDF
            print("Gerando PDF a partir dos dados...")
            tex_generator = TexGenerator(self.nome_banco)
            pdf_path = tex_generator.generate_and_compile_document(summaries=summaries, bib_path=bib_path)
    
            if pdf_path:
                print(f"PDF gerado com sucesso: {pdf_path}")
                logging.info(f"PDF gerado com sucesso: {pdf_path}")
            else:
                print("Erro ao gerar o PDF.")
                logging.error("Erro ao gerar o PDF.")
        except Exception as e:
            print(f"Erro ao gerar o PDF: {e}")
            logging.error(f"Erro geral no processo de geração de PDF: {e}")

    def consultar_db_llama(self):
        """
        Inicia uma sessão de consulta interativa ao banco de dados usando o LlamaDatabaseQuery.
        """
        try:
            self.query_engine.select_database()
            self.query_engine.initialize_query_engine()
            self.query_engine.run_interactive_session()
        except Exception as e:
            print(f"Erro ao iniciar sessão de consulta: {e}")
            logging.error(f"Erro na consulta interativa: {e}")

    def menu_principal(self):
        """
        Exibe o menu principal e gerencia a interação com o usuário.
        """
        while True:
            print("\nEscolha uma opção:")
            print("1. Inserir links")
            print("2. Remover link específico")
            print("3. Gerar PDF")
            print("4. Consultar banco de dados")
            print("5. Sair")

            escolha = input("Digite o número da opção desejada: ").strip()
            if escolha == '1':
                self.loop_inserir_links()
            elif escolha == '2':
                self.remover_link_especifico()
            elif escolha == '3':
                self.gerar_pdf()
            elif escolha == '4':
                self.consultar_db_llama()
            elif escolha == '5':
                print("Encerrando o sistema...")
                break
            else:
                print("Opção inválida. Tente novamente.")

    def iniciar(self):
        """
        Inicia o fluxo principal do programa.
        """
        self.limpar_tela()
        self.exibir_logo()
        self.escolher_ou_criar_banco()
        self.menu_principal()


if __name__ == "__main__":
    app = Main()
    app.iniciar()
