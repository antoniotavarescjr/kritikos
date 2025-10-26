#!/usr/bin/env python3
"""
Testar endpoints específicos para emendas na API da Câmara
"""

import requests
import json

def testar_endpoints_emendas():
    """Testar vários endpoints que podem conter emendas"""
    print("🔍 TESTANDO ENDPOINTS ESPECÍFICOS PARA EMENDAS")
    print("=" * 60)
    
    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    
    # Possíveis endpoints para emendas
    endpoints = [
        "/proposicoes?siglaTipo=EMD",
        "/proposicoes?siglaTipo=EMP", 
        "/proposicoes?siglaTipo=EMC",
        "/proposicoes?siglaTipo=EMR",
        "/proposicoes?siglaTipo=EPV",
        "/proposicoes?siglaTipo=EPL",
        "/proposicoes?ano=2024&siglaTipo=EMD",
        "/proposicoes?ano=2023&siglaTipo=EMD",
        "/proposicoes?ano=2022&siglaTipo=EMD",
        "/proposicoes?tipo=Emenda",
        "/proposicoes?keywords=emenda",
        "/emendas",  # Endpoint direto se existir
        "/emendas parlamentares",  # Possível endpoint
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 Testando: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                dados = data.get('dados', [])
                print(f"   ✅ Sucesso! Encontrados: {len(dados)} itens")
                
                if dados and len(dados) > 0:
                    primeiro = dados[0]
                    print(f"   📄 Primeiro item:")
                    print(f"      ID: {primeiro.get('id')}")
                    print(f"      Tipo: {primeiro.get('siglaTipo')}")
                    print(f"      Ano: {primeiro.get('ano')}")
                    print(f"      Ementa: {primeiro.get('ementa', '')[:100]}...")
                    
                    # Se encontrou emendas, testar mais
                    if 'EM' in primeiro.get('siglaTipo', ''):
                        print(f"   🎉 EMENDA ENCONTRADA! Buscando mais...")
                        return True
            else:
                print(f"   ❌ Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Falha: {e}")
    
    return False

def testar_referencias_emendas():
    """Testar se há referências a emendas em outros endpoints"""
    print("\n🔍 TESTANDO REFERÊNCIAS A EMENDAS")
    print("=" * 50)
    
    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    
    # Buscar proposições recentes e verificar se há emendas
    url = f"{base_url}/proposicoes"
    params = {
        'pagina': 1,
        'itens': 100,
        'ordem': 'DESC',
        'ordenarPor': 'id'
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            proposicoes = data.get('dados', [])
            
            print(f"Analisando {len(proposicoes)} proposições...")
            
            # Procurar por qualquer menção a emenda
            emendas_encontradas = []
            for prop in proposicoes:
                # Verificar se é uma emenda
                if 'EM' in prop.get('siglaTipo', ''):
                    emendas_encontradas.append(prop)
                
                # Verificar se descrição menciona emenda
                descricao = prop.get('ementa', '').lower()
                if 'emenda' in descricao:
                    print(f"   📄 Proposição menciona emenda: {prop.get('siglaTipo')} {prop.get('numero')}/{prop.get('ano')}")
            
            print(f"\n📊 Resultados:")
            print(f"   Emendas diretas: {len(emendas_encontradas)}")
            
            if emendas_encontradas:
                print(f"\n🎉 EMENDAS ENCONTRADAS!")
                for emenda in emendas_encontradas[:5]:  # Primeiras 5
                    print(f"   📄 {emenda.get('siglaTipo')} {emenda.get('numero')}/{emenda.get('ano')}")
                    print(f"      ID: {emenda.get('id')}")
                    print(f"      Ementa: {emenda.get('ementa', '')[:100]}...")
                
                return True
            else:
                print(f"   ❌ Nenhuma emenda encontrada nas proposições recentes")
                
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return False

def testar_documentacao_api():
    """Verificar documentação da API para encontrar endpoints corretos"""
    print("\n🔍 VERIFICANDO DOCUMENTAÇÃO DA API")
    print("=" * 50)
    
    # Endpoint de referência da API
    url = "https://dadosabertos.camara.leg.br/api/v2"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ API principal acessível")
            
            # Tentar descobrir endpoints disponíveis
            endpoints_comuns = [
                "/proposicoes",
                "/deputados", 
                "/partidos",
                "/votacoes",
                "/eventos",
                "/orgaos",
                "/referencias"
            ]
            
            for endpoint in endpoints_comuns:
                url_test = f"https://dadosabertos.camara.leg.br/api/v2{endpoint}"
                try:
                    resp = requests.get(url_test, timeout=5)
                    if resp.status_code == 200:
                        print(f"   ✅ {endpoint} disponível")
                except:
                    print(f"   ❌ {endpoint} indisponível")
                    
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🔍 INVESTIGAÇÃO DE EMENDAS NA API DA CÂMARA")
    print("=" * 60)
    
    # Testar endpoints específicos
    encontrou_emendas = testar_endpoints_emendas()
    
    if not encontrou_emendas:
        # Testar referências
        encontrou_emendas = testar_referencias_emendas()
    
    # Verificar documentação
    testar_documentacao_api()
    
    if encontrou_emendas:
        print(f"\n🎉 SOLUÇÃO ENCONTRADA! Existem emendas na API da Câmara")
    else:
        print(f"\n❌ CONFIRMADO: API da Câmara não tem emendas acessíveis")
        print(f"📝 RECOMENDAÇÃO: Implementar coletor SIOP ou buscar dados alternativos")
    
    print(f"\n✅ INVESTIGAÇÃO CONCLUÍDA")
