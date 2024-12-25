#!/bin/bash

# Função para esperar pelo MySQL
wait_for_mysql() {
  echo "Aguardando o MySQL iniciar..."
  until mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" --silent; do
    sleep 1
  done
  echo "MySQL está pronto e aceitando conexões."
}

# Esperar pelo MySQL antes de iniciar o Django
wait_for_mysql

# Iniciar o servidor Django com uWSGI
echo "Iniciando Django com uWSGI..."
uwsgi --ini /app/uwsgi.ini
