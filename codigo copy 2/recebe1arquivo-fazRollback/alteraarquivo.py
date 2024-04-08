import json
import os
import requests
import subprocess
from azure.devops.connection import Connection
from azure.devops.v7_1.git.models import GitCommitRef, GitPush
from msrest.authentication import BasicAuthentication
from datetime import datetime

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
datadog_api_url = 'https://api.datadoghq.com/api/v1/synthetics/tests/'

# Autenticação no Azure DevOps
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

# Autenticação no Datadog
headers = {
    'DD-API-KEY': DATADOG_API_KEY,
    'DD-APPLICATION-KEY': DATADOG_APP_KEY
}

# Branch do repositório para o clone
branch_name = 'master'  # Altere conforme necessário

# Função para obter o arquivo mais recente com base na data no nome do arquivo
def get_latest_file(public_id):
    folder_path = os.path.join(repository_name, public_id)
    files = os.listdir(folder_path)
    if files:
        latest_file = max(files, key=lambda x: datetime.strptime(x.split('_')[0], '%d-%m-%Y-%H-%M-%S'))
        return os.path.join(folder_path, latest_file)
    return None

# Função para editar um teste sintético no Datadog com base no arquivo fornecido
def edit_datadog_synthetic_test(public_id, file_path):
    # Obter os detalhes do teste sintético do arquivo
    with open(file_path, 'r') as file:
        test_details = json.load(file)

    #Remove os parametros desnecessarios do arquivo yaml de origem
    unnecessary_params = ['monitor_id', 'created_at', 'creator', 'public_id', 'modified_at']
    for param in unnecessary_params:
        test_details.pop(param, None)

    # Editar o teste sintético no Datadog usando a API
    url = f'https://api.datadoghq.com/api/v1/synthetics/tests/api/{public_id}'
    response = requests.put(url, headers=headers, json=test_details)
    if response.status_code == 200:
        print(f"Teste sintético editado com sucesso no Datadog para o public_id {public_id}.")
    else:
        print(response)
        print(f"Falha ao editar o teste sintético no Datadog para o public_id {public_id}.")

if __name__ == '__main__':
    # Clone do repositório localmente
    print("Clonando o repositório...")
    subprocess.run(['git', 'clone', '-b', branch_name, f'{organization_url}/{project_name}/_git/{repository_name}'])
    print("Repositório clonado com sucesso!")

    while True:
        # Input do public_id
        #print("\nDigite o public_id do teste sintético (digite 'sair' para fechar): ")
        public_id_input = input("Digite o Test ID do teste sintético ou digite 'sair': ")
        
        if public_id_input.lower() == 'sair':
            break
        
        # Verificar se a pasta do public_id existe no repositório local
        folder_path = os.path.join(repository_name, public_id_input)
        if not os.path.exists(folder_path):
            print("Id inexistente. Digite um id válido ou digite 'sair' para fechar.")
            continue

        # Obter a lista de arquivos no diretório do public_id
        files = os.listdir(folder_path)
        if files:
            # Listar os arquivos disponíveis para escolha
            print("Arquivos disponíveis para envio ao Datadog:")
            for i, file_name in enumerate(files, start=1):
                print(f"{i}. {file_name}")

            # Input do número do arquivo a ser enviado
            while True:
                print("\nDigite o número do arquivo a ser enviado: ")
                file_index_input = input()
                if not file_index_input.isdigit():
                    print("Digite um número válido.")
                    continue
                file_index = int(file_index_input) - 1
                
                if 0 <= file_index < len(files):
                    # Obter o arquivo selecionado
                    selected_file = os.path.join(folder_path, files[file_index])

                    # Editar o teste sintético no Datadog com base no arquivo selecionado
                    edit_datadog_synthetic_test(public_id_input, selected_file)
                    break
                else:
                    print("Número de arquivo inválido.")
        else:
            print(f"Nenhum arquivo encontrado para o public_id {public_id_input}.")
