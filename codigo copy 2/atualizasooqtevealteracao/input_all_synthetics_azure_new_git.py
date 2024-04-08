import json
import os
import requests
import subprocess
from azure.devops.connection import Connection
from azure.devops.v7_1.git.models import GitCommitRef, GitPush
from msrest.authentication import BasicAuthentication
from datetime import datetime
import yaml


# Desabilitar a verificação do certificado SSL
requests.packages.urllib3.disable_warnings()

# Configurações de autenticação do Azure DevOps
personal_access_token = 'xxxx'
# ATENCAO - Nao pode ter '/' no final de organization_url
organization_url = 'xxxx'
project_name = 'xxxx'
repository_name = 'xxxx'

# Configurações da API do Datadog
DATADOG_API_KEY = 'xxxx'
DATADOG_APP_KEY = 'xxxx'
datadog_api_url = 'xxxx'

# Autenticação no Azure DevOps
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

# Autenticação no Datadog
headers = {
    'DD-API-KEY': DATADOG_API_KEY,
    'DD-APPLICATION-KEY': DATADOG_APP_KEY
}

# Função para clonar o repositório do Azure DevOps localmente
def clone_azure_repo():
    subprocess.run(['git', 'clone', f'{organization_url}/{project_name}/_git/{repository_name}'])

# Função para puxar os arquivos existentes do repositório local
def pull_existing_files():
    os.chdir(repository_name)
    subprocess.run(['git', 'pull'])

# Função para criar uma nova branch se ela não existir
def create_branch_if_not_exists(branch_name):
    branches = subprocess.check_output(['git', 'branch'])
    branches = branches.decode('utf-8').split('\n')
    if branch_name not in branches:
        subprocess.run(['git', 'checkout', '-b', branch_name])

# Função para obter os testes sintéticos do Datadog e comparar com os arquivos existentes
def get_datadog_synthetic_tests():
    # Obter os testes sintéticos do Datadog
    response = requests.get('https://api.datadoghq.com/api/v1/synthetics/tests', headers=headers)
    tests = response.json().get('tests', [])

    # Iterar sobre os testes e salvar os arquivos localmente
    for test in tests:
        test_id = test.get('public_id')
        test_name = test.get('name', 'UnknownTest')

        # Obter detalhes do teste
        test_response = requests.get(f'https://api.datadoghq.com/api/v1/synthetics/tests/{test_id}', headers=headers)
        test_details = test_response.json()

        # Verificar se o teste é válido e tem configurações
        if test_details:
            # Nome do arquivo no formato 'dd-mm-yyyy_nome_do_teste.json'
            data_atual = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
            file_name = f'{data_atual}_{test_name}.json'

            # Caminho completo do arquivo
            directory = os.path.join(repository_name, test_id)
            if not os.path.exists(directory):
                os.makedirs(directory)  # Cria o diretório se não existir
                    
            file_path = os.path.join(directory, file_name)

            # Comparar com o arquivo existente, se existir
            if os.path.exists(file_path):
                # Encontrar o arquivo mais recente no diretório local
                latest_file = find_latest_file(directory)
                if latest_file:
                    with open(latest_file, 'r') as file:
                        existing_test_details = json.load(file)
                        if existing_test_details.get('modified_at') == test_details.get('modified_at'):
                            print(f"O arquivo para o teste {test_name} não foi atualizado. Não é necessário criar um novo arquivo.")
                            continue

            # Serializar e salvar arquivo localmente
            with open(file_path, 'w') as file:
                json.dump(test_details, file, indent=4)
                print(file_path + " criado com sucesso")

    # Mover-se para dentro do repositório clonado
    os.chdir(repository_name)

    # Adicionar novos arquivos ao repositório local
    subprocess.run(['git', 'add', '.'])

    # Nome da branch para commitar
    branch_name = 'master'

    # Verificar e criar a branch se não existir
    create_branch_if_not_exists(branch_name)

    # Commitar mudanças
    subprocess.run(['git', 'commit', '-m', '"Adicionados testes sintéticos"'])

    # Push commits to remote repository
    subprocess.run(['git', 'push', 'origin', branch_name])

# Função para encontrar o arquivo mais recente no diretório local
def find_latest_file(directory):
    latest_file = None
    if os.path.exists(directory):
        files = os.listdir(directory)
        if files:
            latest_modified_time = 0
            for file_name in files:
                file_path = os.path.join(directory, file_name)
                modified_time = os.path.getmtime(file_path)
                if modified_time > latest_modified_time:
                    latest_modified_time = modified_time
                    latest_file = file_path
    return latest_file

if __name__ == '__main__':
    clone_azure_repo()
    pull_existing_files()
    get_datadog_synthetic_tests()