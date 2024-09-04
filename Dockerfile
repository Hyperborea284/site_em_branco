# Use Python 3.10 como imagem base
FROM python:3.10

ENV PYTHONUNBUFFERED=1

# Defina o diretório de trabalho para /app
WORKDIR /app

# Atualize pacotes e instale dependências necessárias, excluindo R e LaTeX
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev libicu-dev libharfbuzz-dev libfribidi-dev python3-tk nano netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Atualize pip e instale pacotes Python
RUN pip3 install --upgrade pip && pip3 install mysqlclient numpy

# Copie requirements.txt e .env para o diretório /app
COPY requirements.txt .env /app/

# Instale dependências do projeto
RUN pip3 install --no-cache-dir -r requirements.txt

# Baixe modelos de linguagem Spacy
RUN python3 -m spacy download pt_core_news_sm
RUN python3 -m spacy download es_core_news_sm
RUN python3 -m spacy download en_core_web_sm

# Copie apenas o diretório backend para /app/backend para rodar o script loads.py
COPY backend /app/backend

# Baixe arquivos para nltk e tensorflow usando backend/loads.py
RUN python3 backend/loads.py

# Defina variáveis de ambiente necessárias
ENV PYTHONPATH="/app/backend"
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copie o restante dos arquivos para /app (mantendo o backend intacto)
COPY . /app/

# Copie o entrypoint.sh e defina permissões de execução
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Configure os diretórios e permissões
RUN mkdir -p /var/log/uwsgi
RUN chown -R www-data:www-data /var/log/uwsgi /app
RUN chmod -R 777 /var/log/uwsgi /app

# Exponha a porta 8080 para uwsgi
EXPOSE 8080

# Defina o entrypoint para o script de inicialização com o shell especificado
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
