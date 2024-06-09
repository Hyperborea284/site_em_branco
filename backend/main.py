import sqlite3
import re
import os
import sys
import termios
import tty
import json
from goose3 import Goose
from datetime import datetime
import subprocess
import requests
from backend.summarize import Summarizer

class Main:
    def __init__(self, nome_banco='database.db'):
        self.nome_banco = nome_banco
        global caminho_banco
        self.caminho_banco = os.path.join('databases', nome_banco)
        self.conexao = None
        self.cursor = None
        self.goose = Goose()
        self.numero_links = 0
        #self.verificar_tabelas()

    def loop_inserir_links(self):
        print("\nAtivação do Loop de Inserção de Links")
        print("Pressione 's' para encerrar o loop e iniciar a sumarização.")
        
        while True:
            link = input('Digite o link que deseja registrar: ')
            
            if link.lower() == 's':
                break
            
            if link.strip().lower() == 's':
                print("Link inválido. Por favor, forneça um link válido ou 's' para encerrar.")
                continue
    
            try:
                response = requests.get(link, timeout=10)
                response.raise_for_status()
                self.registrar_link(link)
            except requests.RequestException as e:
                print(f"Erro ao acessar o link: {e}")
                print("Não foi possível registrar o link.")

    def ativar_loop_inserir_links(self):
        print("\n\nAtivação do Loop de Inserção de Links")
        print("Pressione s para encerrar o loop e iniciar a sumarização.")
        
        original_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        
        try:
            self.loop_inserir_links()
        except KeyboardInterrupt:
            pass 
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_settings)

    def interacao_usuario(self):
        self.mostrar_tabelas()
        escolha = input('\nEscolha a opção:\n'
                        '1. Inserir links\n'
                        '2. Remover dados\n'
                        '3. Alterar dados\n'
                        '4. Continuar para a geração do documento\n'
                        '5. Encerrar\n'
                        'Digite o número da opção desejada: \n')

        if escolha == '1':
            self.ativar_loop_inserir_links()
        elif escolha == '2':
            self.remover_dados()
        elif escolha == '3':
            self.alterar_dados()
        elif escolha == '4':
            self.verificar_tabelas()
        elif escolha == '5':
            sys.exit(0)
        else:
            print("Opção inválida. Tente novamente.")

        self.ativar_summarize()
        self.tex_generator()

    def limpar_tela(self):
        os.system('clear')

    def exibir_logo(self):
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logo = f'''
        ╔══════════════════════════════════════════════════╗
        ║                                                  ║
        ║      Bem-vindo ao Registrador de Links!          ║
        ║                                                  ║
        ║   Este programa registra e analisa informações   ║
        ║   de links, armazenando dados como autores,      ║
        ║   texto limpo, URL final, meta descrição e mais. ║
        ║                                                  ║
        ║   Funções Principais:                            ║
        ║   - Registro de Links                            ║
        ║   - Análise e Armazenamento de Dados             ║
        ║   - Exibição de Informações Registradas          ║
        ║                                                  ║
        ║   Data e Hora: {data}               ║
        ║                                                  ║
        ╚══════════════════════════════════════════════════╝
        '''
        print(logo)
        print(f'\n\n')

    def diagrama_legivel(self, link):
        self.conectar()
        self.cursor.execute('''
            SELECT * FROM links WHERE analised_link = ?
        ''', (link,))
        link_data = self.cursor.fetchone()
        self.desconectar()

        if link_data:
            diagrama = f'''
            Dados registrados para o link: {link} \n\n
            plataform: {link_data[0]}  \n\n
            Link Analisado: {link_data[1]}  \n\n
            Authors: {link_data[2]}  \n\n
            Cleaned Text: {link_data[3]}  \n\n
            Domain: {link_data[4]}  \n\n
            Final URL: {link_data[5]}  \n\n
            Link Hash: {link_data[6]}  \n\n
            Extracted Links: {link_data[7]}  \n\n
            Meta Description: {link_data[8]}  \n\n
            Meta Encoding: {link_data[9]}  \n\n
            Meta Lang: {link_data[10]}  \n\n
            Publish Date: {link_data[11]}  \n\n
            Title: {link_data[12]}  \n\n
            Tags: {link_data[13]}  \n\n
            Schema: {link_data[14]}  \n\n
            Opengraph: {link_data[15]}  \n\n
            Extracted Infos: {link_data[16]}  \n\n
            '''
            return diagrama
        else:
            return print(f'\n"Nenhum dado encontrado para o link fornecido, no contexto do banco de dados."\n')

    def extrair_info(self, link):
        article = self.goose.extract(link)
        return article

    def escolher_ou_criar_banco(self):
        bancos_existentes = [file for file in os.listdir('databases') if file.endswith('.db')]

        if bancos_existentes:
            print(f'\n"Bancos de dados existentes: "\n')
            print()
            for i, banco in enumerate(bancos_existentes):
                print(f" {i+1}. {banco}")

            resposta = input(f'\n"Deseja usar um banco de dados existente? (S/N): "\n')

            if resposta.lower() == 's':
                try:
                    indice_banco = int(input(f'\n"Digite o número do banco de dados desejado: "\n'))
                    if 1 <= indice_banco <= len(bancos_existentes):
                        nome_banco = bancos_existentes[indice_banco - 1]
                    else:
                        print(f'\n"Erro: Índice inválido. Criando um novo banco."\n')
                        nome_banco = input(f'\n"Digite o nome para o novo banco de dados, insira a terminação .db no nome: "\n')
                except ValueError:
                    print(f'\n"Erro: Entrada inválida. Criando um novo banco."\n')
                    nome_banco = input(f'\n"Digite o nome para o novo banco de dados, insira a terminação .db no nome: "\n')
            else:
                nome_banco = input(f'\n"Digite o nome para o novo banco de dados, insira a terminação .db no nome: "\n')
        else:
            nome_banco = input(f'\n"Digite o nome para o novo banco de dados, insira a terminação .db no nome: "\n')

        self.atualizar_banco(nome_banco)
        self.verificar_tabelas()
        self.obter_nomes_tabelas()
        self.mostrar_tabelas()

    def atualizar_banco(self, novo_nome):
        self.nome_banco = novo_nome
        self.caminho_banco = os.path.join('databases', novo_nome)
        print(f'\n"Banco de dados atualizado para {self.caminho_banco}."\n')
        self.conectar()

    def criar_banco_e_tabela(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                plataform TEXT,
                analised_link TEXT,
                authors TEXT,
                cleaned_text TEXT,
                domain TEXT,
                final_url TEXT,
                extracted_links TEXT,
                meta_description TEXT,
                meta_encoding TEXT,
                meta_lang TEXT,
                publish_date TEXT,
                title TEXT,
                tags TEXT,
                schema TEXT,
                opengraph TEXT,
                extracted_infos TEXT,
                data_registro TEXT,
                top_node_raw_html TEXT
            )
        ''')
        self.conexao.commit()

    def criar_tabela_relato(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS relato (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()
    
    def criar_tabela_contexto(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contexto (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            ) 
        ''')
        self.conexao.commit()
    
    def criar_tabela_entidades(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entidades (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()
    
    def criar_tabela_linha_tempo(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS linha_tempo (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()
    
    def criar_tabela_contradicoes(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contradicoes (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()
    
    def criar_tabela_conclusao(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conclusao (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                resume_gpt4 TEXT,
                hashes_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()
    
    def criar_tabela_questionario(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS questionario (
                hashes_gpt3 TEXT,
                resume_gpt3 TEXT,
                hashes_gpt4 TEXT,
                resume_gpt4 TEXT,
                PRIMARY KEY (hashes_gpt3, hashes_gpt4)
            )
        ''')
        self.conexao.commit()

    def criar_tabela_metaresumo(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS metaresumo (
                data TEXT,
                aggregate_links TEXT,
                resume TEXT
            )
        ''')
        self.conexao.commit()

    def verificar_tabelas(self):
        tabelas_verificar = [
            "links",
            "relato",
            "contexto",
            "entidades",
            "linha_tempo",
            "contradicoes", 
            "conclusao", 
            "questionario",
            "metaresumo",
        ]
        self.conectar()

        for tabela in tabelas_verificar:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
            tabela_existe = self.cursor.fetchone() is not None

            if tabela == "links" and not tabela_existe:
                self.criar_tabela_links()
            elif tabela.startswith("relato") and not tabela_existe:
                self.criar_tabela_relato()
            elif tabela.startswith("contexto") and not tabela_existe:
                self.criar_tabela_contexto()
            elif tabela.startswith("entidades") and not tabela_existe:
                self.criar_tabela_entidades()
            elif tabela.startswith("linha_tempo") and not tabela_existe:
                self.criar_tabela_linha_tempo()
            elif tabela.startswith("contradicoes") and not tabela_existe:
                self.criar_tabela_contradicoes()
            elif tabela.startswith("conclusao") and not tabela_existe:
                self.criar_tabela_conclusao()
            elif tabela.startswith("questionario") and not tabela_existe:
                self.criar_tabela_questionario()
            elif tabela.startswith("metaresumo") and not tabela_existe:
                self.criar_tabela_metaresumo()
        self.desconectar()

    def conectar(self):
        if not os.path.exists(self.caminho_banco):
            self.conexao = sqlite3.connect(self.caminho_banco)
            self.cursor = self.conexao.cursor()
            self.criar_banco_e_tabela()
        else:
            self.conexao = sqlite3.connect(self.caminho_banco)
            self.cursor = self.conexao.cursor()

    def desconectar(self):
        if self.conexao:
            self.cursor.close()
            self.conexao.commit()
            self.conexao.close()
            self.conexao = None 

    def receber_links_usuario(self):
        self.numero_links = int(input(f'\n"Quantos links deseja registrar? "\n'))
        self.conectar()
        for _ in range(self.numero_links):
            link = input(f'\n"Digite o link que deseja registrar: "\n')
            self.registrar_link(link)
        self.desconectar()

    def obter_nomes_tabelas(self):
        self.conectar()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = self.cursor.fetchall()
        self.desconectar()
        self.tabelas = [t[0] for t in tabelas]

    def obter_nomes_colunas(self, tabela):
        self.conectar()
        self.cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = self.cursor.fetchall()
        self.desconectar()
        return [c[1] for c in colunas]

    def manipular_dados(self):
        self.obter_nomes_tabelas()

        while True:
            print(f'\n"Opções de manipulação de dados:"\n')
            print(f'\n"1. Inserir dados"')
            print(f'\n"2. Remover dados"')
            print(f'\n"3. Alterar dados"')
            print(f'\n"4. Continuar para escolha ou criação de banco"\n')
            escolha = input(f'\n"Escolha a opção (1/2/3/4): "\n')

            if escolha == '1':
                self.inserir_dados()
            elif escolha == '2':
                self.remover_dados()
            elif escolha == '3':
                self.alterar_dados()
            elif escolha == '4':
                break
            else:
                print("Opção inválida. Tente novamente.")

    def mostrar_tabelas(self):
        print("\nTabelas disponíveis:")
        for i, tabela in enumerate(self.tabelas, start=1):
            print(f"{i}. {tabela}")

    def mostrar_colunas(self, tabela):
        colunas = self.obter_nomes_colunas(tabela)
        print("\nColunas disponíveis:")
        for i, coluna in enumerate(colunas, start=1):
            print(f"{i}. {coluna}")

    def inserir_dados(self):
        self.mostrar_tabelas()
        num_tabela = int(input("Digite o número da tabela para inserir dados: "))
        tabela = self.tabelas[num_tabela - 1]

        colunas = self.obter_nomes_colunas(tabela)
        self.mostrar_colunas(tabela)
        num_colunas = input("Digite os números das colunas separados por vírgula: ")
        colunas_selecionadas = [colunas[int(num) - 1] for num in num_colunas.split(",")]

        valores = input("Digite os valores separados por vírgula: ")

        try:
            self.conectar()
            query = f"INSERT INTO {tabela} ({', '.join(colunas_selecionadas)}) VALUES ({valores})"
            self.cursor.execute(query)
            self.conexao.commit()
            print("Dados inseridos com sucesso!")
        except sqlite3.Error as e:
            print(f"Erro ao inserir dados: {e}")
        finally:
            self.desconectar()

    def remover_dados(self):
        self.mostrar_tabelas()
        num_tabela = int(input("Digite o número da tabela para remover dados: "))
        tabela = self.tabelas[num_tabela - 1]

        condicao = input("Digite a condição para remoção (ex: id=1): ")

        try:
            self.conectar()
            query = f"DELETE FROM {tabela} WHERE {condicao}"
            self.cursor.execute(query)
            self.conexao.commit()
            print("Dados removidos com sucesso!")
        except sqlite3.Error as e:
            print(f"Erro ao remover dados: {e}")
        finally:
            self.desconectar()

    def alterar_dados(self):
        self.mostrar_tabelas()
        num_tabela = int(input("Digite o número da tabela para alterar dados: "))
        tabela = self.tabelas[num_tabela - 1]

        colunas = self.obter_nomes_colunas(tabela)
        self.mostrar_colunas(tabela)
        num_coluna = int(input("Digite o número da coluna para alteração: "))
        coluna_selecionada = colunas[num_coluna - 1]

        novo_valor = input(f"Digite o novo valor para a coluna '{coluna_selecionada}': ")
        condicao = input("Digite a condição para alteração (ex: id=1): ")

        try:
            self.conectar()
            query = f"UPDATE {tabela} SET {coluna_selecionada}='{novo_valor}' WHERE {condicao}"
            self.cursor.execute(query)
            self.conexao.commit()
            print("Dados alterados com sucesso!")
        except sqlite3.Error as e:
            print(f"Erro ao alterar dados: {e}")
        finally:
            self.desconectar()

    def registrar_link(self, link):
        try:
            self.conectar()
            response = requests.get(link, timeout=10) 
            response.raise_for_status()
            infos = self.extrair_info(link)
            if infos:
                plataform = self.identificar_plataform(link)
                if plataform:
                    campos_esperados = [
                        'authors', 'cleaned_text', 'domain', 'final_url', 'links',
                        'meta_description', 'meta_encoding', 'meta_lang', 'publish_date', 'title',
                        'tags', 'schema', 'opengraph', 'infos', 'top_node_raw_html'
                    ]
                    valores = {}
                    for campo in campos_esperados:
                        try:
                            valores[campo] = getattr(infos, campo)
                        except AttributeError:
                            valores[campo] = f"Aviso: Campo '{campo}' não disponível"
                    valores = [str(valores[campo]) for campo in campos_esperados]

                    self.inserir_link(
                                    plataform,
                                    link,
                                    infos.authors,
                                    infos.cleaned_text,
                                    infos.domain,
                                    infos.final_url,
                                    str(infos.links),
                                    infos.meta_description,
                                    infos.meta_encoding,
                                    infos.meta_lang,
                                    infos.publish_date,
                                    infos.title,
                                    str(infos.tags),
                                    str(infos.schema),
                                    infos.opengraph,
                                    str(infos.infos),
                                    getattr(infos, 'top_node_raw_html', None)
                                )
                    self.desconectar()

        except requests.RequestException as e:
            print(f"Erro ao acessar o link: {e}")
            print("Não foi possível registrar o link.")

    def inserir_link(self, plataform, analised_link, authors, cleaned_text, domain, final_url,
                     extracted_links, meta_description, meta_encoding, meta_lang, publish_date, title, tags, schema,
                     opengraph, extracted_infos, top_node_raw_html=None):
        self.conectar()
    
        data_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
        values = (
            plataform,
            analised_link,
            authors if authors is not None else None,
            cleaned_text if cleaned_text is not None else None,
            domain if domain is not None else None,
            final_url if final_url is not None else None,
            extracted_links if extracted_links is not None else None,
            meta_description if meta_description is not None else None,
            meta_encoding if meta_encoding is not None else None,
            meta_lang if meta_lang is not None else None,
            publish_date if publish_date is not None else None,
            title if title is not None else None,
            tags if tags is not None else None,
            schema if schema is not None else None,
            opengraph if opengraph is not None else None,
            extracted_infos if extracted_infos is not None else None,
            data_registro,
            top_node_raw_html if top_node_raw_html else None,
        )
    
        values = tuple(str(value) if value is not None else None for value in values)
    
        self.cursor.execute('''
            DELETE FROM links 
            WHERE plataform = ? AND analised_link = ?
        ''', (plataform, analised_link))
    
        self.cursor.execute('''
            INSERT OR IGNORE INTO links VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', values)
    
        self.conexao.commit()
        self.desconectar()

    def identificar_plataform(self, link):
        if link.startswith('http://') or link.startswith('https://'):
            dominio = re.findall(r'://(?:www\.)?([^/]+)', link)
            if dominio:
                dominio = dominio[0]
                partes_dominio = dominio.split('.')
                plataform = None
    
                if 'www' in partes_dominio:
                    index_www = partes_dominio.index('www')
                    if index_www + 1 < len(partes_dominio):
                        plataform = '.'.join(partes_dominio[index_www + 1:])
                else:
                    for i in range(len(partes_dominio)):
                        if len(partes_dominio[i]) > 1 and not partes_dominio[i].isdigit():
                            plataform = '.'.join(partes_dominio[i:])
                            break
    
                if plataform:
                    infos = self.extrair_info(link)
                    if infos:
                        top_node_raw_html = getattr(infos, 'top_node_raw_html', None)
                        self.analisar_e_inserir_link(link, plataform)
                        return plataform
        return None

    def analisar_e_inserir_link(self, link, plataform):
        self.conectar()
        infos = self.extrair_info(link)
        print(self.diagrama_legivel(link))
        if infos:
            top_node_raw_html = getattr(infos, 'top_node_raw_html', None)
            self.inserir_link(
                plataform,
                link,
                infos.authors,
                infos.cleaned_text,
                infos.domain,
                infos.final_url,
                str(infos.links),
                infos.meta_description,
                infos.meta_encoding,
                infos.meta_lang,
                infos.publish_date,
                infos.title,
                str(infos.tags),
                str(infos.schema),
                infos.opengraph,
                str(infos.infos),
            )
        self.desconectar()

    def ativar_summarize(self):
        self.summarizer = Summarizer(self.nome_banco)

        print('\n\n    Gerando Metaresumo \n\n')
        try:
            final_summary = self.summarizer.synthesize_with_gpt(self.nome_banco)
            self.salvar_metaresumo(final_summary)
        except Exception as e:
            print(f"Error in ativar_summarize: {e}")

    def salvar_metaresumo(self, resume):
        self.conectar()
    
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Inicializando strings para armazenar os conteúdos
        resume_gpt3_content = ""
        resume_gpt4_content = ""
    
        try:
            # Listando todas as tabelas
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = self.cursor.fetchall()
    
            # Percorrendo todas as tabelas
            for table in tables:
                table_name = table[0]
                # Verificando se a tabela possui a coluna 'resume_gpt3'
                self.cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [column[1] for column in self.cursor.fetchall()]
                
                if 'resume_gpt3' in columns:
                    self.cursor.execute(f"SELECT resume_gpt3 FROM {table_name}")
                    resumes = self.cursor.fetchall()
                    resume_gpt3_content += "\n".join([resume[0] for resume in resumes if resume[0]]) + "\n"
                
                if 'resume_gpt4' in columns:
                    self.cursor.execute(f"SELECT resume_gpt4 FROM {table_name}")
                    resumes = self.cursor.fetchall()
                    resume_gpt4_content += "\n".join([resume[0] for resume in resumes if resume[0]]) + "\n"
            
            # Concatenando os conteúdos de 'resume_gpt3' e 'resume_gpt4'
            combined_resumes = resume_gpt3_content + resume_gpt4_content
            
            # Checando se o resumo combinado já existe no banco de dados
            self.cursor.execute("SELECT COUNT(*) FROM metaresumo WHERE resume = ?", (combined_resumes,))
            count_existing = self.cursor.fetchone()[0]
    
            if count_existing == 0:
                aggregate_links = self.obter_indices_links_usados()
                self.cursor.execute('''
                    INSERT INTO metaresumo (data, aggregate_links, resume) VALUES (?, ?, ?)
                ''', (data, json.dumps(aggregate_links), combined_resumes))
                self.conexao.commit()
                print("Registro de resumo adicionado com sucesso!")
            else:
                print("O resumo já existe no banco de dados. Não foi adicionado um novo registro.")
    
        except sqlite3.Error as e:
            print(f"Erro ao salvar textos na tabela 'metaresumo': {e}")
            self.conexao.rollback()
    
        finally:
            self.desconectar()

    def obter_indices_links_usados(self):
        indices_links = []
        try:
            self.cursor.execute("SELECT analised_link FROM links")
            links_data = self.cursor.fetchall()
            for extracted_links in links_data:
                if extracted_links[0] is not None:
                    extracted_links_list = extracted_links[0].split(',')
                    for link in extracted_links_list:
                        indices_links.append(link.strip())
        except sqlite3.Error as e:
            print(f"Erro ao obter links usados: {e}")
        return indices_links

    def tex_generator(self):
        comando = ['python3', 'tex_generator.py', self.caminho_banco]
    
        try:
            resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
            resultado_resumo = resultado.stdout.strip()
            return resultado_resumo
        except subprocess.CalledProcessError as e:
            print(f"Erro ao chamar o script tex_generator: {e}\nSaída padrão: {e.stdout}\nErro padrão: {e.stderr}")
            return "Erro na execução do script tex_generator"
    

if __name__ == "__main__":
    database = Main()
    database.limpar_tela()
    database.exibir_logo()
    database.escolher_ou_criar_banco()
    database.interacao_usuario()
