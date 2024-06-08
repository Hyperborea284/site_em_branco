# Use Python 3.10 as base image
FROM python:3.10-bullseye

ENV PYTHONUNBUFFERED 1

# Set the working directory to /app
WORKDIR /app

# Update packages and install necessary dependencies
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev libicu-dev libharfbuzz-dev libfribidi-dev python3-tk r-base nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*User

# Upgrade pip and install Python packages
RUN pip3 install --upgrade pip && pip3 install mysqlclient numpy

# Copy requirements.txt and .env to the /app directory
COPY requirements.txt .env /app/

# Install project dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Download Spacy language models
RUN python3 -m spacy download pt_core_news_sm;
RUN python3 -m spacy download es_core_news_sm;
RUN python3 -m spacy download en_core_web_sm;

# Install required R packages syuzhet
RUN Rscript -e "install.packages(c('tidyverse', 'syuzhet', 'textshaping', 'ragg', 'tm', 'SnowballC', 'wordcloud', 'RColorBrewer', 'syuzhet', 'ggplot2', 'magrittr', 'quanteda', 'rainette'), repos='http://cran.us.r-project.org')"

# Copy loads.py file to the /app directory
COPY loads.py /app/

# Download files for nltk and tensorflow
RUN python3 loads.py

ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set the necessary environment variables
ENV DJANGO_SETTINGS_MODULE=production_2024.settings

# Expose port 8000 for uwsgi and 4747 for development
EXPOSE 8000 4747

# Copy the rest of the files to the /app directory
COPY . /app/

# Run makemigrations and migrate
RUN python3 manage.py makemigrations && python3 manage.py migrate && python3 manage.py collectstatic --noinput

# Restart uWSGI after configuration changes
CMD ["/bin/bash", "-c", "uwsgi --ini /path/to/your/uwsgi.ini & sleep 5 && uwsgi --stop /tmp/uwsgi.pid"]

# Start uwsgi server with uwsgi
CMD ["uwsgi", "--http", ":8000", "--module", "production_2024.wsgi", "--enable-threads"]
