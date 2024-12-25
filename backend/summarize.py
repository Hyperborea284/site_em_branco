import os
import re
import sys
import time
import subprocess
import hashlib
import sqlite3
import json
import tiktoken
from functools import wraps
from typing import List
from openai import APIConnectionError, APIError, RateLimitError, OpenAI
from dotenv import load_dotenv

load_dotenv(".env")

class Summarizer:
    def __init__(self, nome_banco):
        self.MAX_ATTEMPTS = 3
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.actual_tokens = 0
        self.nome_banco = nome_banco
        self.model_name_gpt3 = "gpt-3.5-turbo-1106"
        self.model_name_gpt4 = "gpt-4-0125-preview"
        self.context_gpt3 = 16385
        self.context_gpt4 = 128000
        self.model_last_request_time = {
            self.model_name_gpt3: 0,
            self.model_name_gpt4: 0,
        }
        self.total_tokens_used = {
            self.model_name_gpt3: 0,
            self.model_name_gpt4: 0,
        }
        self.requests_per_minute_limit = {
            self.model_name_gpt3: 5000,
            self.model_name_gpt4: 500,
        }
        self.requests_per_day_limit = {
            self.model_name_gpt3: 10000,
            self.model_name_gpt4: 10000,
        }
        self.tokens_per_minute_limit = {
            self.model_name_gpt3: 80000,
            self.model_name_gpt4: 450000,
        }
        self.target_summary_size = 4096
        self.summary_input_size = ""
        self.nome_bib = ""
        self.bib_file_content = ""
        self.bib_names_str = ""
        self.remaining_text = []

    def memoize_to_db(table_name):
        def decorator(func):
            @wraps(func)
            def wrapped(self, *args, **kwargs):
                try:
                    concatenated_args = "\n".join(map(str, args)) + "\n" + "\n".join(f"{k}={v}" for k, v in kwargs.items())
                    arg_hash = hashlib.sha256(concatenated_args.encode("utf-8")).hexdigest()
    
                    with sqlite3.connect(f'databases/{self.nome_banco}') as conn:
                        cursor = conn.cursor()
                        cursor.execute(f'SELECT resume_gpt3 FROM {table_name} WHERE hashes_gpt3 = ?', (arg_hash,))
                        row = cursor.fetchone()
    
                        if row:
                            print(f"Resultado encontrado no cache para hash {arg_hash}.")
                            return row[0]
                        else:
                            print(f"Resultado não encontrado no cache para hash {arg_hash}. Chamando a função original.")
                            result = func(self, *args, **kwargs)
                            if result is not None:
                                cursor.execute(f'INSERT INTO {table_name} (hashes_gpt3, resume_gpt3) VALUES (?, ?)', (arg_hash, result))
                                conn.commit()
                    return result
                except Exception as e:
                    print(f"Erro ao memoizar para o banco de dados: {e}")
                    return None
            return wrapped
        return decorator

    def initialize_objects(self):
        try:
            self.nome_bib = self.nome_banco.replace('.db', '.bib')
            bib_command = ["python3", "bib_generator.py", f"databases/{self.nome_banco}", f"pdf_output/{self.nome_bib}"]
            subprocess.run(bib_command)
    
            with open(f"pdf_output/{self.nome_bib}", "r", encoding="utf-8") as bib_file:
                bib_content = bib_file.read()
                self.bib_file_content = bib_content
    
            # Usamos expressões regulares para encontrar todos os nomes dentro das estruturas @online{nome
            bib_names = re.findall(r'@online\{([^,]+),', bib_content)
            # Convertendo a lista de nomes em uma string separada por espaços em branco e ;
            self.bib_names_str = ' '.join(bib_names) + ';'
    
        except Exception as e:
            print(f"Error initializing objects: {e}")

    def synthesize_with_gpt(self, db_path: str) -> List[str]:
        aggregated_objects = []
        try:
            conn = sqlite3.connect(f'databases/{db_path}')
            c = conn.cursor()
            c.execute("SELECT cleaned_text FROM links")
            all_entries = c.fetchall()
            if not all_entries:
                print("No text found in the database. Exiting...")
                return []

            entries = [entry[0] for entry in all_entries]
            conn.close()  # Fechar a conexão após o uso.

            for prompt_name in ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao", "questionario"]:
                if hasattr(self, prompt_name):
                    method = getattr(self, prompt_name)
                    result = method(entries, self.model_name_gpt3, db_path)
                    aggregated_objects.append(result)

                    conn = sqlite3.connect(f'databases/{db_path}')
                    c = conn.cursor()

                    c.execute(f"SELECT resume_gpt3 FROM {prompt_name}")
                    texto = c.fetchall()
                    
                    try:
                        if len(texto) == 1:
                            texto_str = texto[0][0]
                        else:
                            texto_str = '\n\n'.join([t[0] for t in texto])
                    except Exception as e:
                        print(f"Error while processing text: {e}")
                        texto_str = texto[0][0] if texto else ""
                    
                    self.latex_gpt4(texto_str, self.model_name_gpt4, db_path, prompt_name)
                    conn.close()  # Fechar a conexão após o uso.

        except Exception as e:
            print(f"Error while synthesizing with GPT: {e}")
        return aggregated_objects
    
    @memoize_to_db(table_name="relato")
    def relato(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em um relato.")

            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado relatório.
                """.strip()},
                {"role": "user", "content": f"""
                    Este relatório deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho deve conter um título \title aludindo ao contexto, 
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente,
                    seguido de uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "relato")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em relato: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="contexto")
    def contexto(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em um apontamento do contexto analisado.")

            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado texto apresentando
                    o contexto geral, os elementos conjunturais e a casuística analisada nos textos.
                """.strip()},
                {"role": "user", "content": f"""
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Este texto sobre o contexto deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    Este trecho deve possuir uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "contexto")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em contexto: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="entidades")
    def entidades(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em um apontamento das entidades.")

            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-as e sintetize-as em um único e mais
                    detalhado texto apresentando todas 
                    as entidades mencionadas, com atenção para as pessoas físicas, 
                    jurídicas, e outros sujeitos presentes nos textos.
                """.strip()},
                {"role": "user", "content": f"""
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Este texto sobre as entidades deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    Este trecho deve possuir uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "entidades")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em entidades: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="linha_tempo")
    def linha_tempo(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em uma linha do tempo.")

            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado texto apresentando todas 
                    as linhas do tempo deduzidas do conteúdo ou, explícitamente mencionadas.
                    Profunda atenção deve ser dada para as sequências lógicas de eventos presentes nos textos.
                """.strip()},
                {"role": "user", "content": f"""
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Este texto sobre as cronologias deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    Este trecho deve possuir uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "linha_tempo")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em linha_tempo: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="contradicoes")
    def contradicoes(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em uma linha do tempo.")

            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado texto apresentando todas 
                    as contradições, polarizações e tensões dialéticas presentes nos textos,
                    com atenção para as extremidades das polarizações presentes nos textos.
                """.strip()},
                {"role": "user", "content": f"""
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Este texto sobre as contradições deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    Este trecho deve possuir uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais.  Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "contradicoes")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em contradicoes: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="conclusao")
    def conclusao(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em uma conclusão.")
                
            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado texto apresentando
                    uma conclusão sintética dos conteúdos presentes nos textos,
                    com atenção para as implicações dos conteúdos presentes nos textos.
                """.strip()},
                {"role": "user", "content": f"""
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Este texto sobre as conclusões deve ser o mais detalhado possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    Este trecho deve possuir uma quantidade generosa de texto
                    contendo citações latex no formato \cite e, conforme necessário, 
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos. 
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "conclusao")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em conclusao: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    @memoize_to_db(table_name="questionario")
    def questionario(self, lista_textos: List[str], model: str, db_path: str) -> str:
        try:
            print(f"Sintetizando {len(lista_textos)} análises em um questionário.")
            
            initial_messages = [
                {"role": "user", "content": f"""
                    Realize a análise destes textos temáticos.
                    Por favor, revise-os e sintetize-os em um único e mais detalhado questionário.
                """.strip()},
                {"role": "user", "content": f"""

                    Este trecho do documento deve conter única e exclusivamente questões profundas, 
                    de nível superior e pós-graduado, com a mesma dificuldade de questões de concursos públicos
                    para nível superior. 
                    Gere o máximo possível de questões, considerando o mínimo de 10, todas de alto nível, 
                    sobre os conteúdos contidos nos textos, visando cobrir todos os 
                    aspectos do conteúdo, sendo cada uma com 4 alternativas A B C D, onde três são respostas erradas e a
                    resposta certa aparece numa posição aleatória.
                    Este trecho deverá começar com uma \section contendo o tema geral do argumento presente.
                    Estas questões devem ser o mais detalhadas possível, possuindo
                    grande verbosidade, preferindo uma quantidade de texto mais próxima 
                    ao limite de tokens permitido pelo modelo.
                    O trecho não deve conter um título geral, pois este será definido numa etapa separada.
                    O trecho deve conter, caso necessário,
                    as seguintes estruturas, devidamente divididas:
                    seções \section, subseções  \subsection e, caso necessário e items \itemize para cada alternativa
                    entre as respostas. 
                    Considere que a existência de um seção sempre antecede a
                    existência de uma subseção e que nos títulos de seções e subseções não podem existir caracteres
                    especiais. Se esforce para manter a continuidade entre as seções, 
                    evitando omissões na cobertura dos conteúdos.
                    Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do 
                    tipo seções, subseções e, na medida em que for necessário, citações e items.
                """.strip()},
            ]

            generated_messages = self.generate_messages(lista_textos)
            messages = initial_messages + generated_messages

            section, remaining_sections = self.split_message_into_sections(messages, model, "questionario")
            if section is None:
                return ""  # Retorna uma string vazia se houver erro ao dividir as mensagens em seções

            generated_text = self.generate_response(section, model)

            # Processa as seções restantes
            self.process_remaining_sections(remaining_sections, model, db_path)                

            return generated_text
        except Exception as e:
            print(f"Erro em questionario: {e}")
            return ""  # Retorna uma string vazia em caso de erro

    def latex_gpt4(self, texto: str, model: str, db_path: str, prompt_name: str) -> str:
        try:
            print(f"Gerando o trecho latex de {prompt_name} com {model}")
    
            # Memoization logic integrated directly within the function
            concatenated_args = "\n".join(map(str, [texto, model, db_path, prompt_name]))
            arg_hash = hashlib.sha256(concatenated_args.encode("utf-8")).hexdigest()
    
            with sqlite3.connect(f'databases/{self.nome_banco}') as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT resume_gpt4 FROM {prompt_name} WHERE hashes_gpt4 = ?", (arg_hash,))
                row = cursor.fetchone()
    
                if row:
                    print(f"Resultado encontrado no cache para hash {arg_hash} e modelo {model}.")
                    return row[0]
                else:
                    print(f"Resultado não encontrado no cache para hash {arg_hash} e modelo {model}. Chamando a função original.")
    
                    initial_messages = [
                        {"role": "user", "content": """
                            Realize a análise destes trechos latex temáticos.
                            Por favor, organize-os em um único e mais detalhado trecho latex, o qual será inserido
                            em um template latex, o qual já contêm todos os elementos funcionais e decorações latex
                            omitidas aqui.
                            Considerando a presença já assegurada dos elementos latex não explícitamente designados,
                            se limite à organizar as estruturas descritas aqui,
                            não inserindo qualquer outro elemento, anotações ou caracteres especiais fora dos
                            explicitamente orientados, não importando sua funcionalidade ou contexto.
                            Seja estrito e rigoroso quando tratar desta etapa.
                        """.strip()},
                        {"role": "user", "content": """
                            Este trecho deve ser o mais detalhado possível, sendo expandido para possuir
                            grande verbosidade, preferindo a quantidade de texto mais próxima
                            ao limite de tokens permitido pelo modelo.
                            Garanta que esta expansão cubra todos os temas presentes nos textos originais.
                            Caso o trecho contenha um título geral \title, preserve-o; caso este não esteja presente
                            prossiga sem inserir um campo de título novo.
                            Este trecho deve possuir uma quantidade generosa de texto
                            contendo citações latex no formato \cite, usando das fontes 
                            as quais estarão nas mensagens de contexto adiante.
                            E, conforme necessário, adicione
                            as seguintes estruturas, devidamente divididas:
                            seções \section, subseções \subsection e, caso necessário e items \itemize.
                            Considere que a existência de uma seção sempre antecede a
                            existência de uma subseçãoe que nos títulos de seções e subseções não podem existir caracteres
                            especiais.  Se esforce para manter a continuidade entre as seções,
                            evitando omissões na cobertura dos conteúdos.
                            Se for necessário, para cobrir todos os conteúdos, adicione tantas estruturas do
                            tipo seções, subseções e, na medida em que for necessário, citações e items.
                        """.strip()},
                    ]
    
                    # Chama generate_messages para obter mensagens processadas
                    processed_messages = self.generate_messages([texto])
    
                    # Concatena initial_messages com processed_messages sem duplicar texto
                    messages = initial_messages + processed_messages
    
                    section, remaining_sections = self.split_message_into_sections(messages, model, prompt_name)
                    if section is None:
                        return ""
    
                    generated_text = self.generate_response(section, model)
    
                    self.process_remaining_sections(remaining_sections, model, db_path)
    
                    # Save the result in the database for memoization
                    cursor.execute(f"INSERT INTO {prompt_name} (hashes_gpt4, resume_gpt4) VALUES (?, ?)", (arg_hash, generated_text))
                    conn.commit()
    
                    return generated_text
    
        except Exception as e:
            print(f"Erro em latex: {e}")
            return ""

    def generate_messages(self, lista_textos):
        try:
            self.initialize_objects()
            processed_messages = []
    
            # Adiciona as chaves de entrada do arquivo .bib
            processed_messages.append({"role": "user", "content": f"As chaves de cada entrada no arquivo bib, para se gerar as citações latex necessárias estão aqui: {self.bib_names_str}".strip()})
    
            # Adiciona o conteúdo das strings de texto presentes em lista_textos
            for texto in lista_textos:
                processed_messages.append({"role": "user", "content": str(texto).strip()})
    
            return processed_messages
        except Exception as e:
            print(f"Erro ao gerar mensagens: {e}")
            return []

    def split_message_into_sections(self, messages, model, table_name):
        enc = tiktoken.encoding_for_model(model)
        
        # Verifica os limites de contexto do modelo ativado pelo prompt
        if model == "gpt-3.5-turbo-1106":
            max_tokens = self.context_gpt3 - 50
        elif model == "gpt-4-0125-preview":
            max_tokens = self.context_gpt4 - 50
        else:
            print("Modelo não reconhecido")
            return None, None
    
        try:
            total_tokens = 0
            counted_messages = []
            remaining_messages = []
            remaining_tokens = 0
    
            for message in messages:
                token_count = len(enc.encode(str(message["content"])))  # Contagem de tokens baseada no conteúdo do texto
    
                # Se a mensagem atual exceder o limite de contexto
                if total_tokens + token_count > max_tokens:
                    # Calcula a quantidade de tokens excedidos
                    exceeded_tokens = total_tokens + token_count - max_tokens
                    # Divide o conteúdo do texto para se ajustar ao limite
                    message_content = message["content"]
                    parts = []
                    current_part = ""
                    for word in message_content.split():
                        if len(enc.encode(current_part + " " + word)) <= exceeded_tokens:
                            current_part += " " + word
                        else:
                            parts.append({"role": "user", "content": current_part.strip()})
                            current_part = word
                    parts.append({"role": "user", "content": current_part.strip()})
                    
                    # Verifica se a divisão excedeu o limite de tokens do contexto
                    for part in parts:
                        part_token_count = len(enc.encode(str(part["content"])))
                        if total_tokens + part_token_count > max_tokens:
                            remaining_messages.append(part)
                        else:
                            counted_messages.append(part)
                            total_tokens += part_token_count
                else:
                    # Se a mensagem estiver dentro do limite, adicione-a às mensagens contadas
                    counted_messages.append(message)
                    # Atualiza a quantidade total de tokens
                    total_tokens += token_count

            last_entry = self.get_last_entry_from_db(table_name)
            if last_entry:
                remaining_messages.insert(0, last_entry)
    
            return counted_messages, remaining_messages
        except Exception as e:
            print(f"Erro ao dividir mensagens em seções: {e}")
            return None, None

    def get_last_entry_from_db(self, table_name):
        try:
            conn = sqlite3.connect(f'databases/{self.nome_banco}')
            cursor = conn.cursor()
            cursor.execute(f'SELECT resume FROM {table_name} ORDER BY resume DESC LIMIT 1')
            last_entry = cursor.fetchone()
            conn.close()
            return last_entry[0] if last_entry else ""
        except Exception as e:
            print(f"Erro ao obter a última entrada do banco de dados: {e}")
            return ""

    def process_remaining_sections(self, remaining_sections: List[str], model: str, db_path: str) -> None:
        try:
            for section in remaining_sections:
                prompt_names = ["relato", "questionario", "entidades", "contexto", "linha_tempo", "contradicoes", "conclusao"]
                for prompt_name in prompt_names:
                    if hasattr(self, prompt_name):
                        getattr(self, prompt_name)([section], model, db_path)  # Ativa o prompt correspondente com a seção restante
        except Exception as e:
            print(f"Erro ao processar as seções restantes: {e}")

    def generate_response(self, messages, model):
        try:
            print(f"Messages before sending to API:\n, {messages}\n\n")
            remaining_tokens = self.remaining_tokens(model)
    
            max_wait_time = 3600  # 1 hora de espera máxima
            max_attempts = 5  # Número máximo de tentativas
            
            wait_time = 60  # Tempo inicial de espera (em segundos)
            attempts = 0  # Contador de tentativas
    
            while remaining_tokens <= 0 and attempts < max_attempts:
                print("Limite de tokens ou requisições atingido. Aguardando para fazer a próxima tentativa...")
                time.sleep(wait_time)
                remaining_tokens = self.remaining_tokens(model)
    
                # Exponencialmente aumenta o tempo de espera
                wait_time *= 2
                attempts += 1
    
                if wait_time > max_wait_time:
                    print("Tempo máximo de espera atingido. Abortando solicitação.")
                    return None
    
            if remaining_tokens <= 0:
                print("Limite de tokens ou requisições excedidos após várias tentativas. Abortando solicitação.")
                return None
    
            response = self.client.chat.completions.create(
                messages=messages, 
                model=model,
                max_tokens=self.target_summary_size
            )
    
            generated_text = response.model_dump()['choices'][0]['message']['content']
    
        except Exception as e:
            print(f"Erro ao gerar a resposta usando o modelo {model}: {e}")
            return None
    
        return generated_text

    def remaining_tokens(self, model) -> int:
        try:
            requests_per_minute_limit = self.requests_per_minute_limit.get(model, 0)
            tokens_used_so_far = self.total_tokens_used[model]
            remaining_tokens = max(0, requests_per_minute_limit - tokens_used_so_far)
            return remaining_tokens
        except Exception as e:
            print(f"Erro ao calcular os tokens restantes: {e}")
            return 0

if __name__ == "__main__":
    try:
        db_path = "con_ger_pol_pub_05.db"
        model_name = "gpt-3.5-turbo-1106"
        sumarizador = Summarizer(db_path)
        sumarizador.synthesize_with_gpt(db_path, model_name)
    except Exception as e:
        print(f"Erro geral: {e}")

