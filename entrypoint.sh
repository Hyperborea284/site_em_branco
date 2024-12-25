#!/bin/bash

# Função para esperar pelo MySQL
wait_for_mysql() {
  echo "Aguardando o MySQL iniciar..."
  until mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" --silent; do
    sleep 1
  done
  echo "MySQL está pronto e aceitando conexões."
}

# 1) Esperar pelo MySQL antes de iniciar o Django
wait_for_mysql

# 2) Executar makemigrations
echo "Executando makemigrations..."
python3 manage.py makemigrations

# 3) Executar migrate
echo "Executando migrate..."
python3 manage.py migrate

# 4) Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput || echo "Falha ao coletar estáticos, mas prosseguindo..."

# 5) Iniciar o servidor Django com uWSGI
echo "Iniciando Django com uWSGI..."
uwsgi --ini /app/uwsgi.ini
