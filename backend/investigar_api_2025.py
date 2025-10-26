#!/usr/bin/env python3
"""
Investigar por que não há dados de emendas de 2025 na API do Portal da Transparência
"""

import os
import requests
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def investigar_api_2025():
    """Investigar disponibilidade de dados de 2025 na API"""
    print("🔍 INVESTIGANDO DISPONIBILIDADE DE DADOS DE 2025")
    print("=" * 60)
    
    # Obter chave API
    api_key = os.getenv('CHAVE_API_DADOS')
    if not api_key:
        print("❌ Chave API não encontrada")
        return
    
    print(f"✅ Chave API: {api_key[:10]}...")
    
    # Configurar requisição
    url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    # Testar diferentes anos
    anos_teste = [2025, 2024, 2023, 2022, 2021]
    
    print(f"\n📊 TESTANDO DISPONIBILIDADE POR ANO")
    print("=" * 40)
    
    for ano in anos_teste:
        print(f"\n📅 Testando ano: {ano}")
        
        params = {
            'ano': ano,
            'pagina': 1,
            'itens': 10  # Apenas para testar disponibilidade
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"   ✅ Dados encontrados: {len(dados)} registros")
                
                if dados and len(dados) > 0:
                    # Analisar primeiro registro
                    primeiro = dados[0]
                    print(f"   📄 Exemplo - Código: {primeiro.get('codigoEmenda', 'N/A')}")
                    print(f"   💰 Valor: {primeiro.get('valorEmpenhado', 'N/A')}")
                    print(f"   🏛️ Autor: {primeiro.get('autor', 'N/A')}")
                    
                    # Verificar meses disponíveis
                    meses_encontrados = set()
                    for reg in dados[:10]:  # Primeiros 10 registros
                        if 'data' in reg or 'mes' in reg:
                            print(f"      📅 Data disponível: {reg}")
                    
                else:
                    print(f"   ⚠️ Nenhum registro encontrado para {ano}")
                    
            else:
                print(f"   ❌ Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Erro na requisição: {e}")

def testar_parametros_alternativos():
    """Testar parâmetros alternativos para 2025"""
    print(f"\n🔧 TESTANDO PARÂMETROS ALTERNATIVOS PARA 2025")
    print("=" * 50)
    
    api_key = os.getenv('CHAVE_API_DADOS')
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    
    # Testes alternativos
    testes = [
        {'ano': 2025, 'pagina': 1},
        {'ano': 2025, 'itens': 100},
        {'ano': 2025, 'pagina': 1, 'itens': 50},
        {'ano': 2025, 'mes': 1},  # Janeiro
        {'ano': 2025, 'mes': 6},  # Junho
        {'ano': 2025, 'mes': 10}, # Outubro
        {},  # Sem filtros (mais recente)
        {'pagina': 1},  # Apenas paginação
        {'itens': 10},  # Apenas limite
    ]
    
    for i, params in enumerate(testes, 1):
        print(f"\n🧪 Teste #{i}: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"   ✅ Registros: {len(dados)}")
                
                if dados:
                    # Verificar anos dos dados retornados
                    anos_dados = set()
                    for reg in dados[:5]:
                        if 'ano' in reg:
                            anos_dados.add(reg['ano'])
                    
                    if anos_dados:
                        print(f"   📅 Anos encontrados: {sorted(anos_dados)}")
                    
                    # Mostrar exemplo mais recente
                    mais_recente = dados[0] if dados else None
                    if mais_recente:
                        print(f"   📄 Mais recente: {mais_recente.get('ano', 'N/A')} - {mais_recente.get('codigoEmenda', 'N/A')}")
            else:
                print(f"   ❌ Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

def verificar_endpoints_alternativos():
    """Verificar endpoints alternativos da API"""
    print(f"\n🌐 VERIFICANDO ENDPOINTS ALTERNATIVOS")
    print("=" * 40)
    
    api_key = os.getenv('CHAVE_API_DADOS')
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    # Possíveis endpoints
    endpoints = [
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/ano/2025",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano=2025",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/recentes",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/ultimas",
    ]
    
    for endpoint in endpoints:
        print(f"\n🔗 Testando: {endpoint}")
        
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                if isinstance(dados, list):
                    print(f"   ✅ Lista com {len(dados)} itens")
                    if dados:
                        print(f"   📄 Primeiro item: {str(dados[0])[:100]}...")
                elif isinstance(dados, dict):
                    print(f"   ✅ Dicionário com chaves: {list(dados.keys())[:5]}")
            else:
                print(f"   ❌ Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

def analisar_documentacao_api():
    """Analisa possíveis parâmetros baseados na documentação"""
    print(f"\n📚 ANÁLISE BASEADA EM DOCUMENTAÇÃO")
    print("=" * 40)
    
    api_key = os.getenv('CHAVE_API_DADOS')
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    
    # Parâmetros comuns em APIs governamentais
    parametros_teste = [
        {'anoExercicio': 2025},
        {'exercicio': 2025},
        {'anoOrcamentario': 2025},
        {'dataInicio': '2025-01-01'},
        {'dataFim': '2025-12-31'},
        {'periodo': '2025'},
        {'anoReferencia': 2025},
    ]
    
    for i, params in enumerate(parametros_teste, 1):
        print(f"\n🔍 Teste #{i}: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"   ✅ Registros: {len(dados)}")
                
                if dados:
                    # Verificar se temos dados de 2025
                    for reg in dados[:3]:
                        ano = reg.get('ano', 'N/A')
                        print(f"   📅 Registro ano: {ano}")
                        
            elif response.status_code != 404:  # Ignorar 404 (parâmetro não suportado)
                print(f"   ⚠️ Status {response.status_code}: {response.text[:80]}...")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

if __name__ == "__main__":
    print("🚀 INVESTIGAÇÃO COMPLETA DA API - DADOS DE 2025")
    print("=" * 70)
    
    # Investigar disponibilidade por ano
    investigar_api_2025()
    
    # Testar parâmetros alternativos
    testar_parametros_alternativos()
    
    # Verificar endpoints alternativos
    verificar_endpoints_alternativos()
    
    # Analisar documentação
    analisar_documentacao_api()
    
    print(f"\n🏁 INVESTIGAÇÃO CONCLUÍDA")
    print(f"\n💡 POSSÍVEIS CONCLUSÕES:")
    print(f"   1. API pode não ter dados de 2025 ainda")
    print(f"   2. Parâmetros para 2025 podem ser diferentes")
    print(f"   3. Dados mais recentes podem estar em outro endpoint")
    print(f"   4. Pode haver delay na disponibilização dos dados")
