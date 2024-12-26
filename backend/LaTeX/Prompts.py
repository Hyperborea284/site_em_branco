from typing import List
import logging
from EntityProtoProcessor import EntityProtoProcessor
from DatabaseUtils import memoize_to_db, DatabaseUtils

# Configuração do logger para registrar eventos e erros em 'Prompts.log'
logging.basicConfig(
    filename='Prompts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class PromptProcessor:
    def __init__(self, db_name: str):
        """
        Inicializa o processador de prompts, incluindo o EntityProtoProcessor e a integração com o banco de dados.

        Parâmetros:
        db_name (str): Nome do banco de dados a ser utilizado.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.entity_processor = EntityProtoProcessor()

    def _fetch_sources_from_db(self) -> List[str]:
        """
        Busca todas as fontes registradas no banco de dados.

        Retorna:
        List[str]: Lista de fontes disponíveis no banco de dados.
        """
        query = "SELECT DISTINCT url FROM bib_references"
        try:
            with self.db_utils.connect() as conn:
                rows = conn.execute(query).fetchall()
            sources = [row[0] for row in rows]
            logging.info(f"Fontes recuperadas do banco de dados: {sources}")
            return sources
        except Exception as e:
            logging.error(f"Erro ao buscar fontes do banco de dados: {e}")
            return []

    def _generate_prompt_with_entities(self, section_name: str, texts: List[str], description: str, sources: List[str]) -> str:
        """
        Gera o prompt completo, incluindo a análise de entidades e fontes.

        Parâmetros:
        section_name (str): Nome da seção para o qual o prompt está sendo gerado.
        texts (List[str]): Lista de textos para análise e resumo.
        description (str): Descrição detalhada do propósito do resumo.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Prompt gerado para a seção.
        """
        try:
            combined_text = " ".join(texts)
            logging.info(f"Texto combinado para '{section_name}': {combined_text}")
    
            processed_result = self.entity_processor.process_text(combined_text)
            entities = processed_result.get("entities", [])
            logging.info(f"Entidades identificadas para '{section_name}': {entities}")
    
            entities_info = (
                "\n".join([f"- {entity}" for entity in entities])
                if entities
                else "Nenhuma entidade identificada."
            )
            sources_info = (
                "\n".join([f"- {source}" for source in sources])
                if sources
                else "Nenhuma fonte disponível."
            )
    
            prompt = f"""
    Seção: {section_name}
    Descrição: {description}
    Entidades identificadas no texto:
    {entities_info}
    Fontes utilizadas:
    {sources_info}
    
    Gere um resumo considerando apenas as informações disponíveis acima. Cite as fontes usando estritamente \cite{'fonte'}, quando necessário. 
    Em absolutamente nenhuma situação, insira, coloque ou adicione qualquer outro elemento latex diferente de \cite{'fonte'}, pois quebrará o código adiante.
    """
            logging.info(f"Prompt gerado para '{section_name}': {prompt.strip()}")
            return prompt.strip()
        except Exception as e:
            logging.error(f"Erro ao gerar prompt para '{section_name}': {e}")
            return ""

    @memoize_to_db(table_name="relato")
    def relato(self, texts: List[str]) -> str:
        """
        Gera um resumo do tipo 'relato' baseado nos textos fornecidos.

        Parâmetros:
        texts (List[str]): Lista de textos a serem resumidos.

        Retorna:
        str: Resumo gerado para o tipo 'relato'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado do tipo 'relato' que destaca os principais eventos ou pontos mencionados."
        return self._generate_prompt_with_entities("Relato", texts, description, sources)

    @memoize_to_db(table_name="entidades")
    def entidades(self, texts: List[str]) -> str:
        """
        Gera um resumo com foco na análise de entidades, como pessoas e organizações.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'entidades'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado que apresenta as principais entidades mencionadas, incluindo pessoas, organizações e locais."
        return self._generate_prompt_with_entities("Entidades", texts, description, sources)

    @memoize_to_db(table_name="contexto")
    def contexto(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando o contexto geral e elementos contextuais.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contexto'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado que apresenta o contexto espacial geral, elementos contextuais e casuística analisada."
        return self._generate_prompt_with_entities("Contexto", texts, description, sources)

    @memoize_to_db(table_name="linha_tempo")
    def linha_tempo(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando as linhas do tempo deduzidas ou mencionadas.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'linha do tempo'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado detalhado das sequências temporais e eventos apresentados."
        return self._generate_prompt_with_entities("Linha do Tempo", texts, description, sources)

    @memoize_to_db(table_name="contradicoes")
    def contradicoes(self, texts: List[str]) -> str:
        """
        Gera um resumo das contradições, polarizações e tensões dialéticas presentes nos textos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contradições'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado das contradições, polarizações e tensões dialéticas identificadas."
        return self._generate_prompt_with_entities("Contradições", texts, description, sources)

    @memoize_to_db(table_name="conclusao")
    def conclusao(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando as conclusões sintéticas dos conteúdos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'conclusão'.
        """
        sources = self._fetch_sources_from_db()
        description = "Texto detalhado conclusivo com atenção às implicações dos temas abordados."
        return self._generate_prompt_with_entities("Conclusão", texts, description, sources)
