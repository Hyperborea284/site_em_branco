import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from time import sleep
import datetime

# Determina o caminho do geckodriver com base no nome de usuário
username = os.getenv('USER')
geckodriver_path = f'/home/{username}/.geckodriver'

# Configurações iniciais
options = Options()
options.headless = False  # Mude para True se não quiser ver a janela do navegador
service = Service(geckodriver_path)
driver = webdriver.Firefox(service=service, options=options)

# Tela inicial no console
print("\n\n\n\n\nBem-vindo ao Testador de URLs com Selenium")
print("\n1 - Testar URLs Gerais")
print("\n2 - Testar URLs de Administração")
print("\n3 - Testar URLs de Account")
choice = input("\nEscolha uma opção (1, 2, 3): ")


choice = input("\nEscolha uma opção (1, 2, 3): ")

print("\n1 - Localhost --- http://0.0.0.0:8080/accounts/login/")
print("\n2 - Ephor     --- http://ephor/accounts/login/")
url_choice = input("\nEscolha a URL inicial (1, 2): ")

# URL inicial para login
if url_choice == '1':
    initial_url = 'http://0.0.0.0:8080/accounts/login/'
elif url_choice == '2':
    initial_url = 'http://ephor/accounts/login/'
else:
    print("Opção inválida. Usando URL padrão.")
    initial_url = 'http://0.0.0.0:8080/accounts/login/'

driver.get(initial_url)

sleep(2)

# Login
username = "note"
password = "ephor666"
driver.find_element(By.ID, "id_login").send_keys(username)
driver.find_element(By.ID, "id_password").send_keys(password)
driver.find_element(By.CSS_SELECTOR, "button.btn").click()
sleep(5)

# URLs para testar
general_urls = [
    "http://0.0.0.0:8080/",
    "http://0.0.0.0:8080/post/new/",
    "http://0.0.0.0:8080/choose_database/",
    "http://0.0.0.0:8080/main_menu/",
    "http://0.0.0.0:8080/insert_links/",
    "http://0.0.0.0:8080/remove_data/",
    "http://0.0.0.0:8080/update_data/",
    "http://0.0.0.0:8080/generate_document/",
]

admin_urls = [
    "http://0.0.0.0:8080/admin/",
    "http://0.0.0.0:8080/admin/login/",
    "http://0.0.0.0:8080/admin/blog/post/",
    "http://0.0.0.0:8080/admin/blog/post/add/",
    "http://0.0.0.0:8080/admin/blog/post/<int:post_id>/change/",
    "http://0.0.0.0:8080/admin/blog/post/<int:post_id>/delete/",
]

account_urls = [
    "http://0.0.0.0:8080/accounts/login/",
    "http://0.0.0.0:8080/accounts/logout/",
    "http://0.0.0.0:8080/accounts/signup/",
    "http://0.0.0.0:8080/accounts/email/",
    "http://0.0.0.0:8080/accounts/password_reset/",
    "http://0.0.0.0:8080/accounts/password_reset/done/",
    "http://0.0.0.0:8080/accounts/password_change/",
    "http://0.0.0.0:8080/accounts/password_change/done/",
]

# Escolhendo o grupo de URLs a partir da entrada do usuário
urls_to_test = {
    '1': general_urls,
    '2': admin_urls,
    '3': account_urls
}.get(choice, [])

# Função para obter o código de status
def get_status_code(url):
    try:
        response = requests.get(url)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
        return None

# Gerando o arquivo de log
log_filename = "test_results.log"
header = ("Códigos de status HTTP:\n"
          "1xx - Informacional\n"
          "2xx - Sucesso\n"
          "3xx - Redirecionamento\n"
          "4xx - Erro do cliente\n"
          "5xx - Erro do servidor\n\n")

# Apenas cria o cabeçalho se o arquivo não existir
if not os.path.exists(log_filename):
    with open(log_filename, "w") as file:
        file.write(header)

# Testando as URLs escolhidas
with open(log_filename, "a") as file:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file.write(f"\nTeste em {timestamp}\n")
    for url in urls_to_test:
        status_code = get_status_code(url)
        result_text = f"URL: {url}, Status Code: {status_code}"
        file.write(f"{result_text}\n")
        print(result_text)
        if status_code:
            driver.get(url)
            sleep(5)  # Tempo para carregar a página

# Fecha o navegador após visitar todas as páginas
driver.quit()

# Informações finais
print(f"Teste concluído. Resultados adicionados ao log em {log_filename}")
