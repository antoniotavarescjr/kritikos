#!/usr/bin/env python3
"""
Script para consultar os dados da análise salva no banco de dados
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from models.analise_models import AnaliseProposicao, LogProcessamento
from models.proposicao_models import Proposicao
from sqlalchemy import text

def consultar_analise_proposicao(proposicao_id: int):
    """
    Consulta todos os dados da análise de uma proposição.
    
    Args:
        proposicao_id: ID da proposição no banco
    """
    session = get_db_session()
    
    try:
        print("🔍 CONSULTANDO ANÁLISE SALVA NO BANCO")
        print("=" * 60)
        
        # 1. Dados da proposição
        print("\n📋 1. DADOS DA PROPOSIÇÃO:")
        print("-" * 40)
        
        prop = session.query(Proposicao).filter(Proposicao.id == proposicao_id).first()
        if prop:
            print(f"ID: {prop.id}")
            print(f"API ID: {prop.api_camara_id}")
            print(f"Tipo: {prop.tipo}")
            print(f"Número: {prop.numero}")
            print(f"Ano: {prop.ano}")
            print(f"Ementa: {prop.ementa}")
            print(f"Data Apresentação: {prop.data_apresentacao}")
            print(f"Situação: {prop.situacao}")
            print(f"GCS URL: {prop.gcs_url}")
        else:
            print(f"❌ Proposição {proposicao_id} não encontrada")
            return
        
        # 2. Análise salva
        print("\n📊 2. ANÁLISE SALVA:")
        print("-" * 40)
        
        analise = session.query(AnaliseProposicao).filter(
            AnaliseProposicao.proposicao_id == proposicao_id
        ).first()
        
        if analise:
            print(f"ID Análise: {analise.id}")
            print(f"Proposição ID: {analise.proposicao_id}")
            print(f"Versão Análise: {analise.versao_analise}")
            print(f"Data Análise: {analise.data_analise}")
            print(f"Data Resumo: {analise.data_resumo}")
            print(f"Data Filtro Trivial: {analise.data_filtro_trivial}")
            
            print(f"\n📝 RESUMO:")
            print(f"Caracteres: {len(analise.resumo_texto) if analise.resumo_texto else 0}")
            print(f"Conteúdo: {analise.resumo_texto[:200]}..." if analise.resumo_texto else "Nulo")
            
            print(f"\n🎯 RESULTADO DO FILTRO:")
            print(f"É Trivial: {analise.is_trivial}")
            print(f"Interpretação: {'TRIVIAL (não relevante)' if analise.is_trivial else 'RELEVANTE (merece análise completa)'}")
            
            if not analise.is_trivial and analise.par_score:
                print(f"\n📈 ANÁLISE PAR COMPLETA:")
                print(f"PAR Score Final: {analise.par_score}")
                print(f"Escopo Impacto: {analise.escopo_impacto}")
                print(f"Alinhamento ODS: {analise.alinhamento_ods}")
                print(f"Inovação Eficiência: {analise.inovacao_eficiencia}")
                print(f"Sustentabilidade Fiscal: {analise.sustentabilidade_fiscal}")
                print(f"Penalidade Oneração: {analise.penalidade_oneracao}")
                
                print(f"\n🎯 ODS IDENTIFICADOS:")
                if analise.ods_identificados:
                    for ods in analise.ods_identificados:
                        print(f"  - {ods}")
                else:
                    print("  Nenhum ODS identificado")
                
                print(f"\n📋 RESUMO DA ANÁLISE:")
                print(analise.resumo_analise[:300] + "..." if analise.resumo_analise and len(analise.resumo_analise) > 300 else analise.resumo_analise)
            else:
                print(f"\n⚠️ Análise PAR não realizada (proposição classificada como trivial)")
        else:
            print("❌ Nenhuma análise encontrada para esta proposição")
        
        # 3. Logs de processamento
        print("\n📝 3. LOGS DE PROCESSAMENTO:")
        print("-" * 40)
        
        logs = session.query(LogProcessamento).filter(
            LogProcessamento.proposicao_id == proposicao_id
        ).order_by(LogProcessamento.data_fim.desc()).all()
        
        if logs:
            for log in logs:
                print(f"\n🔄 {log.tipo_processo.upper()} - {log.status.upper()}")
                print(f"   Data: {log.data_fim}")
                print(f"   Duração: {log.duracao_segundos}s" if log.duracao_segundos else "   Duração: N/A")
                
                if log.mensagem:
                    print(f"   Mensagem: {log.mensagem}")
                
                if log.dados_entrada:
                    print(f"   Entrada: {log.dados_entrada}")
                
                if log.dados_saida:
                    print(f"   Saída: {log.dados_saida}")
        else:
            print("Nenhum log de processamento encontrado")
        
        # 4. Estatísticas
        print("\n📊 4. ESTATÍSTICAS:")
        print("-" * 40)
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_logs,
                AVG(duracao_segundos) as avg_duracao,
                SUM(CASE WHEN status = 'sucesso' THEN 1 ELSE 0 END) as sucessos,
                SUM(CASE WHEN status = 'erro' THEN 1 ELSE 0 END) as erros
            FROM logs_processamento 
            WHERE proposicao_id = :prop_id
        """)
        
        stats = session.execute(stats_query, {'prop_id': proposicao_id}).fetchone()
        
        if stats:
            print(f"Total de processamentos: {stats.total_logs}")
            print(f"Duração média: {stats.avg_duracao:.1f}s" if stats.avg_duracao else "Duração média: N/A")
            print(f"Sucessos: {stats.sucessos}")
            print(f"Erros: {stats.erros}")
            print(f"Taxa de sucesso: {(stats.sucessos/stats.total_logs*100):.1f}%" if stats.total_logs > 0 else "Taxa de sucesso: N/A")
        
        print("\n" + "=" * 60)
        print("✅ CONSULTA CONCLUÍDA")
        
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

def main():
    """Função principal."""
    print("🔍 CONSULTOR DE ANÁLISE SALVA")
    print("=" * 60)
    
    # Proposição que analisamos no teste
    proposicao_id = 4577
    
    consultar_analise_proposicao(proposicao_id)

if __name__ == "__main__":
    main()
