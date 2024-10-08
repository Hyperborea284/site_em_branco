import matplotlib
matplotlib.use('Agg')  # Usar backend não-GUI

import itertools
import nltk
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime
from pathlib import Path
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import RSLPStemmer
from nltk.probability import FreqDist
from django.conf import settings
from .base import raiva, tristeza, surpresa, medo, desgosto, alegria
import re
from time import sleep
from threading import Thread
from queue import Queue
import subprocess


# Importando as funções do script dist_normal.py para análise e geração de gráficos de distribuição
from .dist_normal import analyze_data, detect_outliers, plot_distribution

class SentimentAnalyzer:
    """
    Classe para análise de sentimentos em textos utilizando processamento de linguagem natural.
    """
    def __init__(self):
        """Inicializa o analisador de sentimentos, baixando recursos necessários do NLTK."""
        self.reset_analyzer()

    def executar_script_r(self):
        # Caminho dentro do container Docker para script R e diretório de saída
        script_path = "/app/backend/nlp.R"
        output_path = "/app/media/generated_images"

        # Executa o script R dentro do container R
        subprocess.run([
            'docker', 'run', '--rm',
            '-v', '/app/backend/nlp.R:' + script_path,
            '-v', '/app/media/generated_images:' + output_path,
            'r-container',  # Nome do serviço Docker para o container R
            'Rscript', script_path
        ])

    def reset_analyzer(self):
        """Reinicializa o analisador de sentimentos."""
        print("Reinicializando SentimentAnalyzer...")
        nltk.download('stopwords')
        nltk.download('punkt')
        self.stopwordsnltk = nltk.corpus.stopwords.words('portuguese')
        self.emotions_funcs = {
            'raiva': raiva,
            'tristeza': tristeza,
            'surpresa': surpresa,
            'medo': medo,
            'desgosto': desgosto,
            'alegria': alegria
        }
        self.generated_images_dir = Path(settings.MEDIA_ROOT) / 'generated_images'
        self.generated_images_dir.mkdir(parents=True, exist_ok=True)
        self.classificador = None
        self.palavrasunicas = None

    def deactivate_analyzer(self):
        """Desativa o analisador de sentimentos, limpando todas as variáveis e buffers."""
        print("Desativando SentimentAnalyzer...")
        self.classificador = None
        self.palavrasunicas = None

    @staticmethod
    def count_paragraphs(text: str) -> list:
        """Conta parágrafos no texto, retornando apenas os parágrafos não vazios.
        
        Args:
            text (str): Texto a ser analisado.

        Returns:
            list: Lista de parágrafos não vazios.
        """
        print("Contando parágrafos...")
        paragraphs = text.split('\n\n')
        return [p for p in paragraphs if p.strip()]

    @staticmethod
    def count_sentences(text: str) -> list:
        """Conta frases no texto utilizando o tokenizador de sentenças do NLTK.

        Args:
            text (str): Texto a ser analisado.

        Returns:
            list: Lista de frases tokenizadas.
        """
        print("Contando frases...")
        return sent_tokenize(text, language='portuguese')

    @staticmethod
    def is_valid_html(content: str) -> bool:
        """Verifica se o conteúdo é um HTML válido específico.

        Args:
            content (str): Conteúdo a ser verificado.

        Returns:
            bool: Verdadeiro se o conteúdo for HTML válido, falso caso contrário.
        """
        print("Verificando se o conteúdo é HTML válido...")
        # Verificação simplificada para a estrutura de HTML gerada
        return bool(re.search(r'<h1>Texto Analisado</h1>.*?<div.*?>.*?</div>.*?<h1>Data e Hora da Análise</h1>.*?<div.*?>.*?</div>.*?<h1>Número de Parágrafos e Frases</h1>.*?<div.*?>.*?</div>', content, re.DOTALL))

    def process_document(self, filepath: str) -> tuple:
        """Processa um documento para separar em parágrafos e frases.

        Args:
            filepath (str): Caminho do arquivo a ser processado.

        Returns:
            tuple: Tupla contendo uma lista de parágrafos e uma lista de frases.
        """
        print("Processando documento...")
        with open(filepath, 'r', encoding='utf-8') as file:
            text = file.read()
        paragraphs = self.count_paragraphs(text)
        sentences = self.count_sentences(text)
        return paragraphs, sentences

    def process_text(self, text: str) -> tuple:
        """Processa um texto para separar em parágrafos e frases."""
        print("Processando texto...")
        text = text.replace('\r\n', '\n')  # Normaliza quebras de linha
        paragraphs = self.count_paragraphs(text)
        sentences = self.count_sentences(text)
        return paragraphs, sentences

    def analyze_paragraphs(self, paragraphs: list) -> tuple:
        """Analisa cada parágrafo para obter pontuações de sentimentos.

        Args:
            paragraphs (list): Lista de parágrafos para análise.

        Returns:
            tuple: Tupla contendo uma lista de pontuações de sentimentos e índices do final dos parágrafos.
        """
        print("Analisando parágrafos...")
        scores_list = []
        paragraph_end_indices = []
        sentence_count = 0
        for paragraph in paragraphs:
            sents = self.count_sentences(paragraph)
            for sentence in sents:
                scores = self.classify_emotion(sentence)
                scores_list.append(scores)
            sentence_count += len(sents)
            paragraph_end_indices.append(sentence_count)
        return scores_list, paragraph_end_indices

    def aplicastemmer(self, texto: list) -> list:
        """Aplica um algoritmo de stemming às palavras do texto.

        Args:
            texto (list): Lista de tuplas contendo palavras e suas respectivas emoções.

        Returns:
            list: Lista de tuplas com palavras após aplicação de stemming e suas emoções.
        """
        print("Aplicando stemming...")
        stemmer = RSLPStemmer()
        frasesstemming = []
        for (palavras, emocao) in texto:
            comstemming = [str(stemmer.stem(p)) for p in word_tokenize(palavras) if p not in self.stopwordsnltk]
            frasesstemming.append((comstemming, emocao))
        return frasesstemming

    def buscapalavras(self, frases: list) -> list:
        """Busca todas as palavras fornecidas nas frases.

        Args:
            frases (list): Lista de frases para extração de palavras.

        Returns:
            list: Lista de palavras extraídas das frases.
        """
        print("Buscando palavras nas frases...")
        all_words = []
        for (words, _) in frases:
            all_words.extend(words)
        return all_words

    def buscafrequencia(self, palavras: list) -> FreqDist:
        """Calcula a frequência das palavras fornecidas.

        Args:
            palavras (list): Lista de palavras.

        Returns:
            FreqDist: Distribuição de frequência das palavras.
        """
        print("Calculando frequência das palavras...")
        freq = FreqDist(palavras)
        return freq

    def buscapalavrasunicas(self, frequencia: FreqDist) -> list:
        """Busca palavras únicas a partir da frequência de palavras.

        Args:
            frequencia (FreqDist): Distribuição de frequência das palavras.

        Returns:
            list: Lista de palavras únicas.
        """
        print("Buscando palavras únicas...")
        return list(frequencia.keys())

    def extratorpalavras(self, documento: list) -> dict:
        """Extrai palavras do documento comparando com palavras únicas.

        Args:
            documento (list): Lista de palavras do documento.

        Returns:
            dict: Dicionário de características das palavras.
        """
        print("Extraindo palavras do documento...")
        doc = set(documento)
        features = {word: (word in doc) for word in self.palavrasunicas}
        return features

    def classify_emotion(self, sentence: str) -> np.array:
        """Classifica uma frase para cada emoção usando um Classificador Bayesiano Ingênuo.

        Args:
            sentence (str): Frase a ser classificada.

        Returns:
            np.array: Array de probabilidades para cada emoção.
        """
        print("Classificando emoção na frase...")
        if not self.classificador:
            print("Treinando classificador Bayesiano Ingênuo...")
            training_base = sum((self.emotions_funcs[emotion]() for emotion in self.emotions_funcs), [])
            frasesstemming = self.aplicastemmer(training_base)
            palavras = self.buscapalavras(frasesstemming)
            frequencia = self.buscafrequencia(palavras)
            self.palavrasunicas = self.buscapalavrasunicas(frequencia)
            complete_base = nltk.classify.apply_features(lambda doc: self.extratorpalavras(doc), frasesstemming)
            self.classificador = nltk.NaiveBayesClassifier.train(complete_base)

        test_stemming = [RSLPStemmer().stem(p) for p in word_tokenize(sentence)]
        new_features = self.extratorpalavras(test_stemming)
        result = self.classificador.prob_classify(new_features)
        return np.array([result.prob(emotion) for emotion in self.emotions_funcs.keys()])

    def plot_individual_emotion_charts(self, scores_list: list, paragraph_end_indices: list, timestamp: str):
        """Plota gráficos de linhas individuais para cada sentimento e decide qual distribuição estatística é mais adequada.
    
        Args:
            scores_list (list): Lista de pontuações de emoções.
            paragraph_end_indices (list): Lista indicando fim dos parágrafos.
            timestamp (str): Carimbo de data/hora para nomear os arquivos salvos.
        """
        print("Plotando gráficos de linhas individuais para cada emoção...")
        emotions = list(self.emotions_funcs.keys())
    
        for i, emotion in enumerate(emotions):
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot([score[i] for score in scores_list], label=f'{emotion} pontuações')
            for end_idx in paragraph_end_indices:
                ax.axvline(x=end_idx, color='grey', linestyle='--', label='Fim do Parágrafo' if end_idx == paragraph_end_indices[0] else "")
            ax.legend(loc='upper right')
            ax.set_title(f'Evolução da Pontuação: {emotion}')
            ax.set_xlabel('Contagem de frases')
            ax.set_ylabel('Pontuações')
            plt.tight_layout()
    
            # Salvando a imagem de pontuação para cada emoção
            emotion_image_path = self.generated_images_dir / f'{emotion}_score_{timestamp}.png'
            plt.savefig(emotion_image_path)
            plt.close()
    
            # Analisando os dados e gerando o gráfico de distribuição mais adequado
            emotion_scores = [score[i] for score in scores_list]
            nature = analyze_data(emotion_scores)  # Identificação da característica da distribuição
            outliers, lower_bound, upper_bound = detect_outliers(emotion_scores)  # Detecção de outliers
            
            # Incluindo o caminho de salvamento correto para o gráfico de distribuição
            distribution_image_path = self.generated_images_dir / f'{emotion}_distribution_{timestamp}.png'
            plot_distribution(emotion_scores, f'{emotion} ({nature})', outliers, lower_bound, upper_bound, distribution_image_path)  # Geração do gráfico com save_path

    def plot_pie_chart(self, scores_list: list, timestamp: str):
        """Plota um gráfico de pizza da distribuição de emoções.

        Args:
            scores_list (list): Lista de pontuações de emoções.
            timestamp (str): Carimbo de data/hora para nomear os arquivos salvos.
        """
        print("Plotando gráfico de pizza de emoções...")
        labels = list(self.emotions_funcs.keys())
        sizes = [np.mean([score[idx] for score in scores_list]) for idx in range(len(labels))]
        colors = ['gold', 'yellowgreen', 'lightcoral', 'lightskyblue', 'lightgreen', 'orange']
        plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.title('Proporção de Cada Sentimento')
        self.pie_chart_path = self.generated_images_dir / f'pie_chart_{timestamp}.png'
        plt.savefig(self.pie_chart_path)
        plt.close()

    def plot_bar_chart(self, scores_list: list, timestamp: str):
        """Plota um gráfico de barras das frequências de emoções.

        Args:
            scores_list (list): Lista de pontuações de emoções.
            timestamp (str): Carimbo de data/hora para nomear os arquivos salvos.
        """
        print("Plotando gráfico de barras de emoções...")
        labels = list(self.emotions_funcs.keys())
        sizes = [np.sum([score[idx] for score in scores_list]) for idx in range(len(labels))]
        plt.figure(figsize=(10, 6))
        plt.bar(labels, sizes, color='purple', edgecolor='black')
        plt.title('Frequência de Emoções Detectadas')
        plt.xlabel('Emoção')
        plt.ylabel('Frequência')
        self.bar_chart_path = self.generated_images_dir / f'bar_chart_{timestamp}.png'
        plt.savefig(self.bar_chart_path)
        plt.close()

    def generate_html_content(self, timestamp: str, paragraphs: list, sentences: list) -> str:
        """Cria uma visualização HTML dos dados analisados, destacando o final de cada frase e incluindo numeração.

        Args:
            timestamp (str): Carimbo de data/hora da análise.
            paragraphs (list): Lista de parágrafos do texto analisado.
            sentences (list): Lista de frases do texto analisado.
        """       
        print("Gerando conteúdo HTML...")
        base_path = settings.MEDIA_URL + 'generated_images/'
        
        html_paragraphs = []
        sentence_counter = 1
        for paragraph in paragraphs:
            marked_paragraph = paragraph
            for sentence in sentences:
                if sentence in marked_paragraph:
                    marked_paragraph = marked_paragraph.replace(sentence, f'{sentence} <span style="color:red;">[{sentence_counter}]</span>')
                    sentence_counter += 1
            html_paragraphs.append(f'<p>{marked_paragraph}</p>')

        self.html_content_paragraphs = ''.join(html_paragraphs)
        
        # Constrói o conteúdo HTML do texto
        self.html_content = f"""
            <h1>Texto Analisado</h1>
            <div style='border:1px solid black; padding:10px;'>{self.html_content_paragraphs}</div>
            <h1>Data e Hora da Análise</h1>
            <div style='border:1px solid black; padding:10px;'>{timestamp}</div>
            <h1>Número de Parágrafos e Frases</h1>
            <div style='border:1px solid black; padding:10px;'>Parágrafos: {len(paragraphs)}, Frases: {len(sentences)}</div>
        """
        
        # Adiciona gráficos de emoções e suas distribuições
        emotions = list(self.emotions_funcs.keys())
        for emotion in emotions:
            self.html_content += f"""
                <h2>{emotion.capitalize()}</h2>
                <div style='border:1px solid black; padding:10px;'>
                    <img src='{base_path}{emotion}_score_{timestamp}.png' alt='Gráfico de linhas para {emotion}'>
                    <img src='{base_path}{emotion}_distribution_{timestamp}.png' alt='Distribuição Normal para {emotion}'>
                </div>
            """

        # Inclui os gráficos de pizza e barras no HTML
        self.html_content += f"""
            <h1>Gráficos Gerais</h1>
            <div style='border:1px solid black; padding:10px;'>
                <img src='{base_path}pie_chart_{timestamp}.png' alt='Gráfico de pizza de sentimentos'>
                <img src='{base_path}bar_chart_{timestamp}.png' alt='Gráfico de barras de sentimentos'>
            </div>
        """

        return self.html_content

    def execute_analysis_text(self, text: str) -> tuple:
        """
        Realiza a análise de sentimentos no texto fornecido, gerando gráficos e conteúdo HTML.

        Args:
            text (str): Texto a ser analisado.
        """
        self.reset_analyzer()
        print("Executando análise de texto...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Processamento do texto e obtenção de parágrafos e frases
        paragraphs, sentences = self.process_text(text)
        scores_list, paragraph_end_indices = self.analyze_paragraphs(paragraphs)
        
        # Plotar gráficos individuais para cada emoção com decisão automática da distribuição
        self.plot_individual_emotion_charts(scores_list, paragraph_end_indices, timestamp)
        
        # Geração de gráficos gerais de pizza e barras
        self.plot_pie_chart(scores_list, timestamp)
        self.plot_bar_chart(scores_list, timestamp)

        # Geração do HTML
        self.html_content, relative_paths = None, []
        attempts = 0
        max_attempts = 5
        
        def generate_html_content_process(queue, timestamp, paragraphs, sentences):
            html_content = self.generate_html_content(timestamp, paragraphs, sentences)
            queue.put(html_content)
        
        while attempts < max_attempts:
            print(f"Tentativa {attempts + 1} de {max_attempts} para gerar HTML...")
            queue = Queue()
            thread = Thread(target=generate_html_content_process, args=(queue, timestamp, paragraphs, sentences))
            thread.start()
            thread.join()
            self.html_content = queue.get()
            print(f"{self.html_content}\n\n\n\n HTML no backend")
        
            if self.is_valid_html(self.html_content):
                print("HTML válido gerado.")
                break
            attempts += 1
            sleep(2 * (attempts + 1))  # Pausa progressiva para reativação
        
        if not self.is_valid_html(self.html_content):
            print("Erro ao gerar HTML válido após múltiplas tentativas.")
            raise ValueError("Erro ao gerar HTML válido. Tente novamente.")
        
        return self.html_content, relative_paths
