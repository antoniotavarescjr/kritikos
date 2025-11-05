#!/usr/bin/env python3
"""
Script de integração entre o pipeline otimizado e os novos agentes de IA
Busca proposições no banco, aplica análise com os agents e salva resultados
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente do .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))

from models.db_utils import get_db_session
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager
from tools.document_summarizer_tool import summarize_proposal_text, analyze_proposal_par
from tools.trivial_filter_tool import is_summary_trivial
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_proposicoes_para_analisar(limit=10):
    """Busca proposições no banco que precisam ser analisadas."""
    print("🔍 Buscando proposições para análise...")
    
    try:
        session = get_db_session()
        
        # Buscar proposições sem análise ou com análise antiga
        proposicoes = session.execute(text("""
            SELECT 
                p.id,
                p.api_camara_id,
                p.tipo,
                p.numero,
                p.ano,
                p.ementa,
                p.gcs_url,
                p.link_inteiro_teor,
                ap.par_score is not null as tem_analise
            FROM proposicoes p
            LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
            WHERE p.ano = 2025
            AND (ap.id IS NULL OR ap.data_analise < NOW() - INTERVAL '7 days')
            ORDER BY p.id DESC
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        session.close()
        
        print(f"   📊 Encontradas {len(proposicoes)} proposições para análise")
        return proposicoes
        
    except Exception as e:
        print(f"   ❌ Erro ao buscar proposições: {e}")
        return []

def get_proposicao_text_from_gcs(proposicao):
    """Busca texto completo da proposição no GCS."""
    try:
        gcs = get_gcs_manager()
        
        if not gcs or not gcs.is_available():
            print(f"   ⚠️ GCS não disponível, tentando usar link_inteiro_teor")
            # Tentar usar link_inteiro_teor se disponível
            if len(proposicao) > 6 and proposicao[6]:  # link_inteiro_teor
                return f"Texto completo disponível em: {proposicao[6]}"
            return "Texto completo não disponível"
        
        # Tentar buscar no GCS
        api_id = proposicao[1]
        tipo = proposicao[2]
        ano = proposicao[3]
        
        # Caminhos possíveis no GCS
        possible_paths = [
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/documento/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}.json"
        ]
        
        for path in possible_paths:
            try:
                data = gcs.download_text(path, compressed=False)
                if data and len(data.strip()) > 100:
                    print(f"   📥 Texto encontrado no GCS: {path}")
                    return data
            except:
                continue
        
        print(f"   ⚠️ Texto não encontrado no GCS, tentando usar link_inteiro_teor")
        # Tentar usar link_inteiro_teor se disponível
        if len(proposicao) > 6 and proposicao[6]:  # link_inteiro_teor
            return f"Texto completo disponível em: {proposicao[6]}"
        
        return "Texto completo não disponível"
        
    except Exception as e:
        print(f"   ❌ Erro ao buscar texto GCS: {e}")
        return "Texto completo não disponível"

def analyze_proposicao_with_agents(proposicao):
    """Analisa uma proposição usando os novos agentes."""
    prop_id = proposicao[0]
    api_id = proposicao[1]
    tipo = proposicao[2]
    numero = proposicao[3]
    ano = proposicao[4]  # Corrigido: ano está na posição 4
    ementa = proposicao[5]  # Corrigido: ementa está na posição 5
    
    print(f"\n🧪 Analisando proposição {tipo} {numero}/{ano} (ID: {prop_id})")
    print(f"   📋 Ementa: {ementa[:100]}...")
    
    # Obter texto completo
    texto_completo = get_proposicao_text_from_gcs(proposicao)
    
    if not texto_completo or len(texto_completo.strip()) < 200:
        print(f"   ⚠️ Texto muito curto ou vazio, pulando análise")
        return None
    
    # Passo 1: Summarizer Agent
    print("   📝 Passo 1: Gerando resumo...")
    resumo = summarize_proposal_text(texto_completo, prop_id)
    
    if not resumo:
        print(f"   ❌ Falha no resumo")
        return None
    
    print(f"   ✅ Resumo gerado: {len(resumo)} caracteres")
    
    # Passo 2: Trivial Filter Agent
    print("   🔍 Passo 2: Verificando trivialidade...")
    is_trivial = is_summary_trivial(resumo, prop_id)
    
    resultado_filtro = "TRIVIAL" if is_trivial else "RELEVANTE"
    print(f"   ✅ Resultado: {resultado_filtro}")
    
    # Passo 3: PAR Analyzer (só se não for trivial)
    par_score = None
    if not is_trivial:
        print("   📊 Passo 3: Calculando PAR...")
        par_analysis = analyze_proposal_par(resumo, prop_id)
        
        if par_analysis:
            try:
                import json
                par_data = json.loads(par_analysis)
                par_score = par_data.get('par_final')
                print(f"   ✅ PAR Final: {par_score}")
            except:
                print(f"   ⚠️ PAR gerado mas com erro no JSON")
        else:
            print(f"   ❌ Falha na análise PAR")
    else:
        print("   ⏹️ Proposição trivial - análise PAR não necessária")
    
    return {
        'proposicao_id': prop_id,
        'api_camara_id': api_id,
        'tipo': tipo,
        'numero': numero,
        'ano': proposicao[3],
        'ementa': ementa,
        'resumo': resumo,
        'is_trivial': is_trivial,
        'par_score': par_score,
        'data_analise': datetime.now()
    }

def run_integration_test():
    """Executa teste de integração completo."""
    print("🚀 INTEGRAÇÃO PIPELINE + AGENTS")
    print("=" * 60)
    print("Testando integração entre backend e novos agentes de IA")
    print("=" * 60)
    
    # Buscar proposições para analisar
    proposicoes = get_proposicoes_para_analisar(limit=5)
    
    if not proposicoes:
        print("❌ Nenhuma proposição encontrada para análise")
        return False
    
    print(f"\n📊 Iniciando análise de {len(proposicoes)} proposições...\n")
    
    resultados = []
    erros = 0
    
    for i, proposicao in enumerate(proposicoes, 1):
        print(f"🔄 Análise {i}/{len(proposicoes)}")
        
        try:
            resultado = analyze_proposicao_with_agents(proposicao)
            
            if resultado:
                resultados.append(resultado)
                print(f"   ✅ Análise concluída com sucesso")
            else:
                erros += 1
                print(f"   ❌ Falha na análise")
                
        except Exception as e:
            erros += 1
            print(f"   ❌ Erro inesperado: {e}")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DA INTEGRAÇÃO")
    print("=" * 60)
    
    print(f"📋 Proposições processadas: {len(resultados)}")
    print(f"❌ Erros: {erros}")
    print(f"✅ Taxa de sucesso: {((len(resultados) / len(proposicoes)) * 100):.1f}%")
    
    # Estatísticas dos resultados
    if resultados:
        relevantes = [r for r in resultados if not r['is_trivial']]
        triviais = [r for r in resultados if r['is_trivial']]
        com_par = [r for r in relevantes if r['par_score'] is not None]
        
        print(f"\n📈 Estatísticas:")
        print(f"   📋 Relevantes: {len(relevantes)}")
        print(f"   📋 Triviais: {len(triviais)}")
        print(f"   📊 Com PAR: {len(com_par)}")
        
        if com_par:
            par_scores = [r['par_score'] for r in com_par]
            print(f"   📊 PAR médio: {sum(par_scores) / len(par_scores):.1f}")
            print(f"   📊 PAR máximo: {max(par_scores)}")
            print(f"   📊 PAR mínimo: {min(par_scores)}")
    
    print(f"\n🎯 Integração concluída!")
    
    return len(resultados) > 0

def main():
    """Função principal."""
    return run_integration_test()

if __name__ == "__main__":
    main()
