# Use Python 3.10 como imagem base
FROM python:3.10

ENV PYTHONUNBUFFERED=1

# Defina o diretório de trabalho para /app
WORKDIR /app

# Atualize pacotes e instale dependências necessárias
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev libicu-dev libharfbuzz-dev libfribidi-dev python3-tk r-base nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instale pacotes R necessários
RUN Rscript -e "install.packages(c('tidyverse', 'syuzhet', 'textshaping', 'ragg', 'tm', 'SnowballC', 'wordcloud', 'RColorBrewer', 'syuzhet', 'ggplot2', 'magrittr', 'quanteda', 'rainette'), repos='http://cran.us.r-project.org')"

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

# Copie o diretório backend para /app
COPY backend /app/backend

# Baixe arquivos para nltk e tensorflow usando backend/loads.py
RUN python3 backend/loads.py

# Defina variáveis de ambiente necessárias
ENV PYTHONPATH="/app/backend"
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copie o restante dos arquivos para /app
COPY . /app/

# Execute migrações e colete arquivos estáticos
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Configure os diretórios e permissões
RUN mkdir -p /var/log/uwsgi
RUN chown -R www-data:www-data /var/log/uwsgi /app
RUN chmod -R 777 /var/log/uwsgi /app

# Exponha a porta 8080 para uwsgi
EXPOSE 8080

# Comando de entrada para iniciar uWSGI
CMD ["sh", "-c", "uwsgi --http :8080 --module production_2024.wsgi --enable-threads"]
