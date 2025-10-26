import requests

def testar_url():
    try:
        r = requests.get('http://dadosabertos.camara.leg.br/arquivos/votacoes/json/votacoes-2024.json')
        print(f'Status: {r.status_code}')
        data = r.json()
        print(f'Tipo: {type(data)}')
        if isinstance(data, list):
            print(f'Tamanho: {len(data)}')
            if len(data) > 0:
                print(f'Primeiro item: {data[0]}')
        else:
            print('Dados não é uma lista')
    except Exception as e:
        print(f'Erro: {e}')

if __name__ == "__main__":
    testar_url()
