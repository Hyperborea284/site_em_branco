# Use Python 3.10 as base image
FROM python:latest

ENV PYTHONUNBUFFERED=1

# Set the working directory to /app
WORKDIR /app

# Update packages and install necessary dependencies
RUN apt-get update && \
    apt-get install -y nginx default-libmysqlclient-dev libicu-dev libharfbuzz-dev libfribidi-dev python3-tk r-base nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install required R packages syuzhet
RUN Rscript -e "install.packages(c('tidyverse', 'syuzhet', 'textshaping', 'ragg', 'tm', 'SnowballC', 'wordcloud', 'RColorBrewer', 'syuzhet', 'ggplot2', 'magrittr', 'quanteda', 'rainette'), repos='http://cran.us.r-project.org')"

# Upgrade pip and install Python packages
RUN pip3 install --upgrade pip && pip3 install mysqlclient numpy

# Copy requirements.txt and .env to the /app directory
COPY requirements.txt .env /app/

# Install project dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Download Spacy language models
RUN python3 -m spacy download pt_core_news_sm
RUN python3 -m spacy download es_core_news_sm
RUN python3 -m spacy download en_core_web_sm

# Copy the backend directory to the /app directory
COPY backend /app/backend

# Download files for nltk and tensorflow using backend/loads.py
RUN python3 backend/loads.py

# Expose port 8080 for uwsgi and nginx
EXPOSE 8080

# Copy the rest of the files to the /app directory
COPY . /app/

# Download files for nltk and tensorflow using backend/loads.py
RUN python3 backend/loads.py

# Set the necessary environment variables
ENV PYTHONPATH="/app/backend"
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Run makemigrations and migrate
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Start nginx and uwsgi
CMD /bin/bash -c "service nginx start && uwsgi --http :8080 --module production_2024.wsgi --enable-threads"



