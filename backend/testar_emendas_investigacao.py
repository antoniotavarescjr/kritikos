#!/usr/bin/env python3
"""
Script para investigar o problema das emendas
"""

import sys
from pathlib import Path

# Adicionar src ao path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

from etl.coleta_emendas import ColetorEmendas
from models.db_utils import get_db_session

def testar_api_camara_direta():
    """Testar API da Câmara diretamente"""
    print("🔍 TESTANDO API DA CÂMARA DIRETAMENTE")
    print("=" * 50)
    
    import requests
    
    # Testar endpoint de proposições
    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    params = {
        'pagina': 1,
        'itens': 10,
        'ordem': 'DESC',
        'ordenarPor': 'id'
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Total de proposições: {len(data.get('dados', []))}")
        
        # Verificar tipos de proposições
        tipos = {}
        for prop in data.get('dados', []):
            tipo = prop.get('siglaTipo', 'UNKNOWN')
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        print("\nTipos encontrados:")
        for tipo, count in tipos.items():
            print(f"  {tipo}: {count}")
        
        # Procurar por emendas
        emendas = [p for p in data.get('dados', []) if 'EM' in p.get('siglaTipo', '')]
        print(f"\nEmendas encontradas: {len(emendas)}")
        
        if emendas:
            print("\nPrimeira emenda encontrada:")
            print(f"  ID: {emendas[0].get('id')}")
            print(f"  Tipo: {emendas[0].get('siglaTipo')}")
            print(f"  Número: {emendas[0].get('numero')}")
            print(f"  Ano: {emendas[0].get('ano')}")
            print(f"  Ementa: {emendas[0].get('ementa', '')[:100]}...")
        
    except Exception as e:
        print(f"Erro: {e}")

def testar_emendas_2024():
    """Testar emendas de 2024"""
    print("\n🔍 TESTANDO EMENDAS DE 2024")
    print("=" * 50)
    
    db = get_db_session()
    coletor = ColetorEmendas()
    
    try:
        # Testar busca de emendas 2024
        emendas = coletor.buscar_emendas_por_tipo('EMD', 2024, limite=20)
        print(f"Emendas EMD/2024 encontradas: {len(emendas)}")
        
        if emendas:
            print("\nPrimeira emenda:")
            print(f"  ID: {emendas[0].get('id')}")
            print(f"  Tipo: {emendas[0].get('siglaTipo')}")
            print(f"  Número: {emendas[0].get('numero')}")
            print(f"  Ano: {emendas[0].get('ano')}")
        
        # Testar com EMP
        emendas_emp = coletor.buscar_emendas_por_tipo('EMP', 2024, limite=20)
        print(f"Emendas EMP/2024 encontradas: {len(emendas_emp)}")
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

def testar_varios_anos():
    """Testar vários anos"""
    print("\n🔍 TESTANDO VÁRIOS ANOS")
    print("=" * 50)
    
    db = get_db_session()
    coletor = ColetorEmendas()
    
    anos = [2022, 2023, 2024]
    tipos = ['EMD', 'EMP', 'EMC', 'EMR', 'EMP', 'EPV', 'EPL']
    
    try:
        for ano in anos:
            print(f"\nAno: {ano}")
            for tipo in tipos:
                emendas = coletor.buscar_emendas_por_tipo(tipo, ano, limite=10)
                if emendas:
                    print(f"  {tipo}: {len(emendas)} emendas")
                    break
            else:
                print(f"  Nenhuma emenda encontrada em {ano}")
                
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

def investigar_siop():
    """Investigar API SIOP"""
    print("\n🔍 INVESTIGANDO API SIOP")
    print("=" * 50)
    
    import requests
    
    # Endpoints SIOP mencionados na documentação
    endpoints = [
        "https://siop.planejamento.gov.br/modulo/itens/api",
        "https://siop.planejamento.gov.br/modulo/emendas/api",
        "https://siop.planejamento.gov.br/modulo/impedimentos/api"
    ]
    
    for endpoint in endpoints:
        print(f"\nTestando: {endpoint}")
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  Resposta: {response.text[:200]}...")
            else:
                print(f"  Erro: {response.text[:200]}...")
        except Exception as e:
            print(f"  Falha: {e}")

if __name__ == "__main__":
    print("🔍 INVESTIGAÇÃO COMPLETA DAS EMENDAS")
    print("=" * 60)
    
    # Testar API da Câmara diretamente
    testar_api_camara_direta()
    
    # Testar emendas 2024
    testar_emendas_2024()
    
    # Testar vários anos
    testar_varios_anos()
    
    # Investigar SIOP
    investigar_siop()
    
    print("\n✅ INVESTIGAÇÃO CONCLUÍDA")
