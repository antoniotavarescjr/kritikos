#!/usr/bin/env python3
"""
Testar API do Portal da Transparência para coleta de emendas orçamentárias
"""

import os
import requests
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def testar_api_transparencia():
    """Testar conexão e estrutura da API do Portal da Transparência"""
    print("🔍 TESTANDO API DO PORTAL DA TRANSPARÊNCIA")
    print("=" * 60)
    
    # Obter chave API do ambiente
    api_key = os.getenv('CHAVE_API_DADOS')
    
    if not api_key:
        print("❌ Chave API não encontrada no .env")
        print("   Verifique se CHAVE_API_DADOS está configurada")
        return False
    
    print(f"✅ Chave API encontrada: {api_key[:10]}...")
    
    # Configurar requisição
    url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    # Testar diferentes parâmetros
    testes = [
        {"ano": 2024, "pagina": 1},
        {"ano": 2023, "pagina": 1},
        {"ano": 2024, "pagina": 1, "codigoFuncao": "10"},  # Saúde
        {"ano": 2024, "pagina": 1, "codigoMunicipio": "5300108"},  # Brasília
    ]
    
    for i, params in enumerate(testes, 1):
        print(f"\n📋 Teste #{i}: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"   ✅ Sucesso! Encontrados: {len(dados)} registros")
                
                if dados and len(dados) > 0:
                    # Analisar primeiro registro
                    primeiro = dados[0]
                    print(f"   📄 Estrutura do primeiro registro:")
                    
                    for chave, valor in primeiro.items():
                        if isinstance(valor, str) and len(str(valor)) > 100:
                            print(f"      {chave}: {str(valor)[:100]}...")
                        else:
                            print(f"      {chave}: {valor}")
                    
                    # Verificar campos importantes
                    campos_importantes = ['valorEmpenhado', 'valorLiquidado', 'valorPago', 
                                        'nomeParlamentar', 'nomeMunicipio', 'anoEmenda',
                                        'codigoFuncao', 'codigoSubfuncao', 'codigoPrograma']
                    
                    print(f"\n   🔍 Campos importantes encontrados:")
                    for campo in campos_importantes:
                        if campo in primeiro:
                            valor = primeiro[campo]
                            print(f"      ✅ {campo}: {valor}")
                        else:
                            print(f"      ❌ {campo}: Não encontrado")
                    
                    # Se encontrou dados, analisar valores
                    if 'valorEmpenhado' in primeiro:
                        try:
                            valor = float(primeiro['valorEmpenhado'])
                            print(f"\n   💰 Valor empenhado: R$ {valor:,.2f}")
                            if valor > 0:
                                print(f"   🎉 EMENDA COM VALOR MONETÁRIO ENCONTRADA!")
                                return True
                        except:
                            print(f"   ⚠️ Valor empenhado não é numérico")
                    
                    # Limitar a 1 teste com dados para não sobrecarregar
                    if len(dados) > 0:
                        print(f"\n   📊 Análise dos primeiros {min(5, len(dados))} registros:")
                        for j, reg in enumerate(dados[:5], 1):
                            nome_parlamentar = reg.get('nomeParlamentar', 'N/A')
                            municipio = reg.get('nomeMunicipio', 'N/A')
                            valor = reg.get('valorEmpenhado', '0')
                            print(f"      {j}. {nome_parlamentar} - {municipio} - R$ {valor}")
                        
                        return True
                
            else:
                print(f"   ❌ Erro: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout (30s)")
        except requests.exceptions.ConnectionError:
            print(f"   🌐 Erro de conexão")
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
    
    print(f"\n❌ Nenhum dado de emenda com valor encontrado")
    return False

def testar_outros_endpoints():
    """Testar outros endpoints possíveis da API"""
    print(f"\n🔍 TESTANDO OUTROS ENDPOINTS")
    print("=" * 40)
    
    api_key = os.getenv('CHAVE_API_DADOS')
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    # Possíveis endpoints relacionados
    endpoints = [
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/por-ano",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/por-autor",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/por-localidade",
        "http://api.portaldatransparencia.gov.br/api-de-dados/emendas/relatorio"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testando: {endpoint}")
        
        try:
            response = requests.get(endpoint, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"   ✅ Sucesso! Tipo: {type(dados)}")
                if isinstance(dados, list):
                    print(f"   📊 Registros: {len(dados)}")
                elif isinstance(dados, dict):
                    print(f"   📊 Chaves: {list(dados.keys())[:5]}")
            else:
                print(f"   ❌ Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

def analisar_limites_api():
    """Analisar limites e rate limiting da API"""
    print(f"\n⏱️ ANÁLISE DE LIMITES DA API")
    print("=" * 40)
    
    api_key = os.getenv('CHAVE_API_DADOS')
    headers = {
        "chave-api-dados": api_key,
        "Accept": "application/json"
    }
    
    url = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    
    # Testar múltiplas requisições rápidas
    print("   Testando múltiplas requisições...")
    
    sucessos = 0
    falhas = 0
    
    for i in range(5):
        try:
            params = {"ano": 2024, "pagina": i + 1}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                sucessos += 1
                print(f"      ✅ Requisição {i+1}: {len(dados)} registros")
            else:
                falhas += 1
                print(f"      ❌ Requisição {i+1}: Status {response.status_code}")
                
        except Exception as e:
            falhas += 1
            print(f"      ❌ Requisição {i+1}: Erro {e}")
    
    print(f"\n   📊 Resultado: {sucessos} sucessos, {falhas} falhas")

if __name__ == "__main__":
    print("🚀 TESTE COMPLETO DA API DO PORTAL DA TRANSPARÊNCIA")
    print("=" * 70)
    
    # Testar endpoint principal
    sucesso = testar_api_transparencia()
    
    if sucesso:
        print(f"\n🎉 API FUNCIONANDO! Emendas com valores encontradas!")
        
        # Testar outros endpoints
        testar_outros_endpoints()
        
        # Analisar limites
        analisar_limites_api()
        
        print(f"\n✅ PRÓXIMO PASSO: Implementar coletor completo")
        
    else:
        print(f"\n❌ PROBLEMAS NA API. Verificar:")
        print(f"   • Chave API está válida?")
        print(f"   • Conexão com internet está OK?")
        print(f"   • API está disponível?")
    
    print(f"\n🏁 TESTE CONCLUÍDO")
