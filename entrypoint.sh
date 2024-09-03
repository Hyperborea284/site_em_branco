#!/bin/sh

# Espera o serviço do banco de dados estar disponível antes de rodar as migrações
echo "Aguardando o banco de dados..."

# Um loop que continua tentando conectar até que o DB esteja disponível
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

echo "Banco de dados está disponível. Aplicando migrações..."

# Executa as migrações
python3 manage.py migrate

# Coleta os arquivos estáticos
python3 manage.py collectstatic --noinput

# Executa o uWSGI
uwsgi --http :8080 --module production_2024.wsgi --enable-threads
