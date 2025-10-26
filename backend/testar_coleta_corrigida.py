#!/usr/bin/env python3
"""
Teste de Coleta Corrigida de Emendas
Usando o código fornecido para validar a escala real dos dados
"""

import sys
import os
import requests
from pathlib import Path
from datetime import datetime

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Configuração da API - usar a mesma chave do coletor existente
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('CHAVE_API_DADOS')
if not API_KEY:
    print("❌ CHAVE_API_DADOS não encontrada no .env")
    exit(1)

BASE_URL = "http://api.portaldatransparencia.gov.br/api-de-dados/emendas"
HEADERS = {
    "chave-api-dados": API_KEY,
    "Accept": "application/json"
}

print(f"🔑 Usando chave API: {API_KEY[:10]}...")

def obter_todas_emendas_deputado(nome_deputado, ano):
    """
    Coleta TODAS as emendas de um deputado em um ano
    Versão corrigida com paginação completa
    """
    print(f"\n🔍 Coletando emendas de {nome_deputado} - {ano}")
    print("=" * 60)
    
    all_emendas = []
    pagina = 1
    
    while True:
        params = {
            "ano": ano,
            "nomeAutor": nome_deputado,  # Só isso! Sem outros filtros
            "pagina": pagina
        }
        
        print(f"📄 Buscando página {pagina}...")
        
        try:
            response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
            
            if response.status_code == 200:
                emendas = response.json()
                
                if not emendas:  # Acabaram as emendas
                    print(f"✅ Fim da coleta - página {pagina-1} foi a última")
                    break
                
                print(f"  → {len(emendas)} emendas encontradas")
                all_emendas.extend(emendas)
                pagina += 1
                
                # Pequeno delay para não sobrecarregar a API
                import time
                time.sleep(0.5)
                
            elif response.status_code == 429:
                print(f"⏳ Rate limit - aguardando 5 segundos...")
                import time
                time.sleep(5)
                continue
            else:
                print(f"❌ Erro {response.status_code}: {response.text[:200]}")
                break
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            break
    
    if all_emendas:
        # Calcular totais sem pandas
        total_empenhado = sum(float(str(emenda.get('valorEmpenhado', 0)).replace('.', '').replace(',', '.') or 0) for emenda in all_emendas)
        total_pago = sum(float(str(emenda.get('valorPago', 0)).replace('.', '').replace(',', '.') or 0) for emenda in all_emendas)
        total_liquidado = sum(float(str(emenda.get('valorLiquidado', 0)).replace('.', '').replace(',', '.') or 0) for emenda in all_emendas)
        
        # Análise adicional
        municipios = set()
        funcoes = {}
        subfuncoes = set()
        
        for emenda in all_emendas:
            if 'nomeMunicipio' in emenda and emenda['nomeMunicipio']:
                municipios.add(emenda['nomeMunicipio'])
            
            if 'funcao' in emenda and emenda['funcao']:
                funcao = emenda['funcao']
                funcoes[funcao] = funcoes.get(funcao, 0) + 1
            
            if 'subfuncao' in emenda and emenda['subfuncao']:
                subfuncoes.add(emenda['subfuncao'])
        
        print(f"\n{'='*60}")
        print(f"📊 RESULTADO - DEPUTADO: {nome_deputado} - ANO: {ano}")
        print(f"{'='*60}")
        print(f"📄 Total de emendas: {len(all_emendas)}")
        print(f"💰 Valor empenhado: R$ {total_empenhado:,.2f}")
        print(f"💰 Valor pago: R$ {total_pago:,.2f}")
        print(f"💰 Valor liquidado: R$ {total_liquidado:,.2f}")
        print(f"🏙️ Municípios beneficiados: {len(municipios)}")
        print(f"📋 Funções: {len(funcoes)}")
        
        # Top 3 funções
        if funcoes:
            print(f"   Top 3 funções:")
            funcoes_ordenadas = sorted(funcoes.items(), key=lambda x: x[1], reverse=True)
            for func, count in funcoes_ordenadas[:3]:
                print(f"   - {func}: {count} emendas")
        
        print(f"📂 Subfunções: {len(subfuncoes)}")
        print(f"{'='*60}")
        
        return all_emendas
    else:
        print(f"❌ Nenhuma emenda encontrada para {nome_deputado} em {ano}")
        return []

def comparar_com_dados_atuais(nome_deputado, ano):
    """
    Compara os dados coletados com os dados atuais no banco
    """
    print(f"\n🔍 Comparando com dados atuais no banco...")
    
    try:
        # Importar modelos do banco
        from models.db_utils import get_db_session
        from models.emenda_models import EmendaParlamentar
        from models.politico_models import Deputado
        from sqlalchemy import func
        
        db_session = get_db_session()
        
        # Buscar deputado
        deputado = db_session.query(Deputado).filter(
            func.upper(Deputado.nome) == func.upper(nome_deputado)
        ).first()
        
        if not deputado:
            print(f"❌ Deputado {nome_deputado} não encontrado no banco")
            return
        
        # Buscar emendas do deputado no ano
        emendas_db = db_session.query(EmendaParlamentar).filter(
            EmendaParlamentar.deputado_id == deputado.id,
            EmendaParlamentar.ano == ano
        ).all()
        
        total_db = len(emendas_db)
        valor_db = sum(e.valor_emenda or 0 for e in emendas_db)
        
        print(f"📊 DADOS ATUAIS NO BANCO:")
        print(f"   📄 Total de emendas: {total_db}")
        print(f"   💰 Valor total: R$ {valor_db:,.2f}")
        
        db_session.close()
        
        return total_db, valor_db
        
    except Exception as e:
        print(f"❌ Erro ao consultar banco: {e}")
        return 0, 0

def testar_deputados_referencia():
    """
    Testa com deputados de referência para validar escala
    """
    print("🚀 TESTE DE COLETA CORRIGIDA - ESCALA REAL")
    print("=" * 70)
    
    # Deputados para teste (nomes exatos da API)
    deputados_teste = [
        "NIKOLAS FERREIRA",
        "TABATA AMARAL", 
        "KIM KATAGUIRI",
        "CARLA ZAMBELLI"
    ]
    
    anos_teste = [2024, 2023]  # Anos mais recentes
    
    resultados = []
    
    for deputado in deputados_teste:
        for ano in anos_teste:
            print(f"\n{'='*70}")
            print(f"🎯 TESTANDO: {deputado} - {ano}")
            print(f"{'='*70}")
            
            # Coletar dados corretos
            emendas_corrigido = obter_todas_emendas_deputado(deputado, ano)
            
            if emendas_corrigido:
                # Comparar com dados atuais
                total_db, valor_db = comparar_com_dados_atuais(deputado, ano)
                
                # Calcular diferença
                total_corrigido = len(emendas_corrigido)
                valor_corrigido = sum(float(str(emenda.get('valorEmpenhado', 0)).replace('.', '').replace(',', '.') or 0) for emenda in emendas_corrigido)
                
                dif_total = total_corrigido - total_db
                dif_valor = valor_corrigido - valor_db
                
                print(f"\n📈 COMPARAÇÃO:")
                print(f"   📊 Banco: {total_db} emendas, R$ {valor_db:,.2f}")
                print(f"   📊 Corrigido: {total_corrigido} emendas, R$ {valor_corrigido:,.2f}")
                print(f"   📊 Diferença: +{dif_total} emendas, +R$ {dif_valor:,.2f}")
                
                if valor_db > 0:
                    percentual_diferenca = (dif_valor / valor_db) * 100
                    print(f"   📊 Percentual diferença: +{percentual_diferenca:.1f}%")
                
                resultados.append({
                    'deputado': deputado,
                    'ano': ano,
                    'total_banco': total_db,
                    'valor_banco': valor_db,
                    'total_corrigido': total_corrigido,
                    'valor_corrigido': valor_corrigido,
                    'diferenca_total': dif_total,
                    'diferenca_valor': dif_valor
                })
            
            print(f"\n⏳ Aguardando 2 segundos antes do próximo teste...")
            import time
            time.sleep(2)
    
    # Relatório final
    print(f"\n{'='*70}")
    print(f"📋 RELATÓRIO FINAL DA COMPARAÇÃO")
    print(f"{'='*70}")
    
    if resultados:
        # Calcular totais sem pandas
        total_banco_geral = sum(r['valor_banco'] for r in resultados)
        total_corrigido_geral = sum(r['valor_corrigido'] for r in resultados)
        diferenca_geral = total_corrigido_geral - total_banco_geral
        
        print(f"💰 VALOR TOTAL BANCO: R$ {total_banco_geral:,.2f}")
        print(f"💰 VALOR TOTAL CORRIGIDO: R$ {total_corrigido_geral:,.2f}")
        print(f"💰 DIFERENÇA TOTAL: R$ {diferenca_geral:,.2f}")
        
        if total_banco_geral > 0:
            percentual_geral = (diferenca_geral / total_banco_geral) * 100
            print(f"📈 AUMENTO PERCENTUAL: +{percentual_geral:.1f}%")
        
        print(f"\n📊 DETALHES:")
        for row in resultados:
            print(f"   {row['deputado']} ({row['ano']}): "
                  f"R$ {row['valor_banco']:,.2f} → R$ {row['valor_corrigido']:,.2f} "
                  f"(+R$ {row['diferenca_valor']:,.2f})")
        
        # Salvar resultados como CSV simples
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"relatorio_teste_coleta_corrigida_{timestamp}.csv"
        caminho_arquivo = Path(__file__).parent / nome_arquivo
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write("deputado,ano,total_banco,valor_banco,total_corrigido,valor_corrigido,diferenca_total,diferenca_valor\n")
            for row in resultados:
                f.write(f"{row['deputado']},{row['ano']},{row['total_banco']},{row['valor_banco']},"
                       f"{row['total_corrigido']},{row['valor_corrigido']},{row['diferenca_total']},"
                       f"{row['diferenca_valor']}\n")
        
        print(f"\n📁 Resultados salvos: {caminho_arquivo}")
        
        return resultados
    else:
        print("❌ Nenhum resultado para comparar")
        return []

def main():
    """
    Função principal
    """
    print("🚀 TESTE DE COLETA CORRIGIDA DE EMENDAS")
    print("=" * 70)
    print("🎯 Objetivo: Validar escala real dos dados")
    print("🔧 Método: Coleta completa sem filtros restritivos")
    print("📊 Comparação: Dados atuais vs dados corrigidos")
    print("=" * 70)
    
    try:
        # Executar teste completo
        resultados = testar_deputados_referencia()
        
        if resultados:
            print(f"\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print(f"📊 Foram analisados {len(resultados)} casos")
            print(f"🔍 Use os resultados para validar a correção necessária")
        else:
            print(f"\n⚠️ TESTE CONCLUÍDO COM ALERTAS!")
            print(f"🔧 Verifique os logs acima para identificar problemas")
            
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
