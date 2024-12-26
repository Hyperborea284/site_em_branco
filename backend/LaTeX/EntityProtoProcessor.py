import os
import re
import string
import logging
import spacy
import nltk
from langdetect import detect
from typing import List
from nltk.tokenize import word_tokenize

# Configuração do logger para capturar eventos e erros
logging.basicConfig(filename='EntityProtoProcessor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Certifique-se de que os recursos do nltk foram baixados
nltk.download('punkt')
nltk.download('stopwords')

class EntityProtoProcessor:
    def __init__(self):
        """
        Inicializa o processador de entidades e termos, com suporte para análise em português e inglês.
        """
        self.supported_languages = {
            'en': ('english', 'en_core_web_sm'),
            'pt': ('portuguese', 'pt_core_news_sm')
        }

    def process_text(self, text: str) -> dict:
        """
        Detecta o idioma, extrai entidades e realiza a limpeza do texto.
        """
        try:
            lang_code = detect(text)
            logging.info(f"Idioma detectado: {lang_code}")
            if lang_code not in self.supported_languages:
                logging.warning(f"Idioma não suportado detectado: {lang_code}")
                return {"language": "", "entities": [], "filtered_words": []}
    
            lang_code_short, lang_code_full = self.supported_languages[lang_code]
            nlp = spacy.load(lang_code_full)
            doc = nlp(text)
    
            entities = [entity.text for entity in doc.ents if entity.text]
            logging.info(f"Entidades extraídas: {entities}")
    
            stopwords = set(nltk.corpus.stopwords.words(lang_code_short))
            punctuation = string.punctuation + '`“”©–//'
            text_tokens = word_tokenize(text)
    
            filtered_words = [
                re.sub(r'[0-9]', '', word.lower())
                for word in text_tokens
                if word.lower() not in stopwords and word not in punctuation and len(word) > 1
            ]
            logging.info(f"Palavras filtradas: {filtered_words}")
    
            return {
                "language": lang_code,
                "entities": entities,
                "filtered_words": filtered_words
            }
        except Exception as e:
            logging.error(f"Erro ao processar o texto: {e}")
            return {"language": "", "entities": [], "filtered_words": []}
