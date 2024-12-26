import hashlib
import sqlite3
import os
import requests
from typing import List, Optional, Dict, Tuple
from openai import OpenAI
from functools import wraps
from DatabaseUtils import DatabaseUtils
from dotenv import load_dotenv
import logging
from Prompts import PromptProcessor

# Configuração do logger
logging.basicConfig(filename='SummarizerManager.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(".env")


class SummarizerManager:
    def __init__(self, db_name: str):
        """
        Inicializa o SummarizerManager, que gerencia a síntese de textos e a integração com o banco de dados 
        e a API OpenAI.

        Parâmetros:
        db_name (str): Nome do banco de dados SQLite onde os resumos e links são armazenados.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.prompts = PromptProcessor(db_name)
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.db_name = db_name

        # Garante que as tabelas necessárias estão criadas
        self.db_utils.create_summary_tables()

        # Configurações dos modelos e seus limites de contexto e tokens
        self.model_name_gpt3 = "gpt-3.5-turbo-1106"
        self.model_name_gpt4 = "gpt-4-0125-preview"
        self.context_gpt3 = 16385
        self.context_gpt4 = 128000
        self.requests_per_minute_limit = {self.model_name_gpt3: 5000, self.model_name_gpt4: 500}
        self.tokens_per_minute_limit = {self.model_name_gpt3: 80000, self.model_name_gpt4: 450000}
        self.total_tokens_used = {self.model_name_gpt3: 0, self.model_name_gpt4: 0}
        self.target_summary_size = 4096

    def synthesize_content(self) -> List[str]:
        """
        Faz a síntese de conteúdo para diferentes tipos de resumos e armazena no banco de dados.
        Utiliza resumos existentes caso já estejam armazenados.
        """
        summaries = {}
        try:
            logging.info("Iniciando recuperação de entradas do banco...")
            all_entries = self.db_utils.fetch_cleaned_texts()
            logging.info(f"Entradas recuperadas: {all_entries}")
    
            if not all_entries:
                logging.warning("Nenhuma entrada encontrada no banco de dados para síntese.")
                return summaries
    
            for prompt_name in ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao"]:
                description = f"Resumo para a seção {prompt_name}"
    
                # Verifica se já existem resumos na tabela
                logging.info(f"Verificando resumos existentes para a seção: {prompt_name}")
                existing_summaries = self.db_utils.fetch_summaries(prompt_name)
                if existing_summaries:
                    logging.info(f"Resumos já existentes encontrados para {prompt_name}. Utilizando os resumos existentes.")
                    summaries[prompt_name] = [entry["summary"] for entry in existing_summaries]
                    continue
    
                # Solicitar autorização antes de ativar o prompt
                logging.info(f"Solicitando autorização para ativar o prompt: {prompt_name}")
                user_confirmation = input(f"Deseja ativar o prompt para a seção '{prompt_name}'? (s/n): ").lower()
                if user_confirmation != 's':
                    logging.info(f"Operação cancelada pelo usuário para a seção {prompt_name}.")
                    continue
    
                logging.info(f"Processando resumo para: {prompt_name}")
                try:
                    # Gera o resumo usando _generate_summary
                    summary = self._generate_summary(prompt_name, all_entries, description)
                    if not summary:
                        logging.warning(f"Resumo cancelado ou não gerado para {prompt_name}.")
                        continue  # Continua com o próximo resumo
    
                    logging.info(f"Resumo gerado para {prompt_name}: {summary[:50]}")
                    summaries[prompt_name] = [summary]
                    combined_text = " ".join(all_entries)
                    prompt_hash = hashlib.sha256(combined_text.encode('utf-8')).hexdigest()
                    logging.info(f"Salvando resumo no banco com hash: {prompt_hash}")
                    self.db_utils.insert_summary(prompt_name, combined_text, summary, prompt_hash)
                except Exception as e:
                    logging.error(f"Erro ao processar resumo para {prompt_name}: {e}")
        except Exception as e:
            logging.error(f"Erro geral ao sintetizar conteúdo: {e}")
        return summaries

    def get_token_price(self) -> float:
        """
        Retorna o preço fixo por 1000 tokens.
        """
        logging.info("Usando preço fixo de $0.02 por 1000 tokens.")
        return 0.02  # Preço fixo

    def display_cost_estimate(self, token_count: int) -> bool:
        """
        Calcula e exibe uma estimativa de custo baseado no número de tokens e solicita confirmação do usuário.
    
        Parâmetros:
        token_count (int): Número de tokens estimados.
    
        Retorna:
        bool: True se o usuário confirmar a continuidade, False caso contrário.
        """
        try:
            token_price = self.get_token_price()
            estimated_cost = (token_count / 1000) * token_price
            logging.info(f"Tokens estimados: {token_count}, custo estimado: ${estimated_cost:.4f}")
            print(f"\n=== Estimativa de Custo ===")
            print(f"Tokens estimados: {token_count}")
            print(f"Custo estimado: ${estimated_cost:.4f}")
            confirm = input("Deseja continuar com a geração do resumo? (s/n): ").lower()
            return confirm == 's'
        except Exception as e:
            logging.error(f"Erro ao calcular a estimativa de custo: {e}")
            return False

    def _generate_summary(self, section_name: str, texts: List[str], description: str) -> str:
        """
        Gera um resumo baseado em uma lista de textos e uma descrição do tipo de resumo.
        """
        try:
            logging.info(f"Iniciando geração de resumo para a seção {section_name}.")
            messages = [{"role": "user", "content": f"Provide a {description} for the following texts:"}]
            for text in texts:
                messages.append({"role": "user", "content": text.strip()})
            logging.info(f"Mensagens para a seção {section_name}: {messages}")
    
            # Divide mensagens em seções e calcula estimativa de tokens
            sections, remaining_sections = self.split_message_into_sections(messages)
            estimated_tokens = sum(len(msg["content"].split()) for msg in sections)
            logging.info(f"Tokens estimados para {section_name}: {estimated_tokens}")
    
            if not self.display_cost_estimate(estimated_tokens):
                logging.info("Operação cancelada pelo usuário.")
                return ""
    
            # Gera o resumo principal
            summary_text = self.generate_response(sections)
            logging.info(f"Resumo gerado para a seção {section_name}: {summary_text[:50]}")
    
            # Processa seções restantes
            if remaining_sections:
                logging.info(f"Processando seções excedentes para {section_name}.")
                self.process_remaining_sections(remaining_sections, section_name)
    
            return summary_text
        except Exception as e:
            logging.error(f"Erro ao gerar resumo para {section_name}: {e}")
            return ""

    def split_message_into_sections(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Divide mensagens em seções com base no limite de tokens.

        Parâmetros:
        messages (List[Dict[str, str]]): Mensagens a serem enviadas.

        Retorna:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]: Seção principal e excedente.
        """
        total_tokens, max_tokens = 0, self.context_gpt3
        primary_section, overflow_section = [], []

        for message in messages:
            token_count = len(message["content"].split())
            if total_tokens + token_count <= max_tokens:
                primary_section.append(message)
                total_tokens += token_count
            else:
                overflow_section.append(message)

        return primary_section, overflow_section

    def process_remaining_sections(self, sections: List[Dict[str, str]], section_name: str) -> None:
        """
        Processa e memoiza as seções que excedem o limite.

        Parâmetros:
        sections (List[Dict[str, str]]): Lista de mensagens excedentes.
        section_name (str): Nome da seção.
        """
        for section in sections:
            method = getattr(self.prompts, section_name)
            method([section["content"]])

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Envia solicitação para a API OpenAI para gerar o resumo.
    
        Parâmetros:
        messages (List[Dict[str, str]]): Mensagens para enviar.
    
        Retorna:
        str: Conteúdo do resumo gerado.
        """
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name_gpt3,
                max_tokens=self.target_summary_size
            )
    
            # Verifica se o retorno contém a chave 'choices'
            if hasattr(response, 'choices') and len(response.choices) > 0:
                first_choice = response.choices[0]
                if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'content'):
                    generated_message = first_choice.message.content
                    logging.info(f"Resposta da API: {generated_message[:50]}")
                    return generated_message
            logging.warning("A resposta da API não contém conteúdo gerado.")
            return ""
        except AttributeError as e:
            logging.error(f"Formato inesperado na resposta da API: {e}")
            return ""
        except Exception as e:
            logging.error(f"Erro ao gerar resposta da API: {e}")
            return ""
