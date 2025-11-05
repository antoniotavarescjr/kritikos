"""
Script de Teste para Coleta de Proposições

Valida o funcionamento do coletor de proposições antes de integrar ao pipeline.
"""

import logging
import sys
import os
from datetime import datetime

# Adicionar path do src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.db_utils import get_db_session
from models.proposicao_models import Proposicao, Autoria
from models.politico_models import Deputado
from utils.common_utils import setup_logging
from sqlalchemy import text
from etl.coleta_proposicoes import ColetorProposicoes

logger = logging.getLogger(__name__)


def testar_coleta_json():
    """Testa coleta de proposições via JSON."""
    logger.info("🧪 TESTE 1: Coleta via JSON")
    
    try:
        coletor = ColetorProposicoes()
        
        # Testar com um ano específico e poucos tipos
        coletor.tipos_relevantes = ['PL', 'PEC']  # Apenas para teste
        
        total = coletor.coletar_por_json(ano=2024)
        
        logger.info(f"✅ Teste JSON: {total} proposições coletadas")
        return total > 0
        
    except Exception as e:
        logger.error(f"❌ Erro no teste JSON: {e}")
        return False


def testar_coleta_api():
    """Testa coleta de proposições via API."""
    logger.info("🧪 TESTE 2: Coleta via API")
    
    try:
        coletor = ColetorProposicoes()
        
        # Testar com poucos deputados
        total = coletor.coletar_por_deputados(limite_deputados=5)
        
        logger.info(f"✅ Teste API: {total} proposições coletadas")
        return total > 0
        
    except Exception as e:
        logger.error(f"❌ Erro no teste API: {e}")
        return False


def validar_dados_salvos():
    """Valida se os dados foram salvos corretamente no banco."""
    logger.info("🧪 TESTE 3: Validação de Dados")
    
    try:
        session = get_db_session()
        
        # Verificar proposições salvas
        total_props = session.execute(
            text("SELECT COUNT(*) FROM proposicoes")
        ).scalar()
        
        # Verificar autorias salvas
        total_autorias = session.execute(
            text("SELECT COUNT(*) FROM autorias")
        ).scalar()
        
        # Verificar proposições com autores
        props_com_autores = session.execute(text("""
            SELECT COUNT(DISTINCT p.id) FROM proposicoes p
            INNER JOIN autorias a ON p.id = a.proposicao_id
        """)).scalar()
        
        # Verificar distribuição por tipo
        tipos = session.execute(text("""
            SELECT tipo, COUNT(*) as quantidade 
            FROM proposicoes 
            GROUP BY tipo 
            ORDER BY quantidade DESC
        """)).fetchall()
        
        logger.info(f"📊 Total proposições: {total_props}")
        logger.info(f"👥 Total autorias: {total_autorias}")
        logger.info(f"🔗 Props com autores: {props_com_autores}")
        
        logger.info("📈 Distribuição por tipo:")
        for tipo, qtd in tipos:
            logger.info(f"   {tipo}: {qtd}")
        
        # Verificar se há dados
        dados_validos = total_props > 0 and total_autorias > 0 and props_com_autores > 0
        
        if dados_validos:
            logger.info("✅ Validação de dados: SUCESSO")
        else:
            logger.warning("⚠️ Validação de dados: PROBLEMAS")
        
        return dados_validos
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {e}")
        return False
    finally:
        session.close()


def testar_relacionamentos():
    """Testa se os relacionamentos estão funcionando."""
    logger.info("🧪 TESTE 4: Relacionamentos")
    
    try:
        session = get_db_session()
        
        # Buscar uma proposição e seus autores
        resultado = session.execute(text("""
            SELECT 
                p.id, p.tipo, p.numero, p.ano, p.ementa,
                d.nome as autor_nome, d.uf_nascimento as autor_uf,
                a.tipo_autoria, a.ordem
            FROM proposicoes p
            INNER JOIN autorias a ON p.id = a.proposicao_id
            INNER JOIN deputados d ON a.deputado_id = d.id
            LIMIT 10
        """)).fetchall()
        
        if not resultado:
            logger.warning("⚠️ Nenhuma proposição com autores encontrada")
            return False
        
        logger.info("🔗 Exemplo de relacionamentos:")
        for row in resultado:
            logger.info(f"   {row[0]} {row[1]}/{row[2]} - {row[3]} ({row[4]})")
        
        logger.info("✅ Relacionamentos: FUNCIONANDO")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro nos relacionamentos: {e}")
        return False
    finally:
        session.close()


def gerar_relatorio_teste():
    """Gera relatório completo dos testes."""
    logger.info("📋 GERANDO RELATÓRIO DE TESTE")
    
    resultados = {
        'data_teste': datetime.now().isoformat(),
        'testes': {}
    }
    
    # Executar testes
    resultados['testes']['coleta_json'] = testar_coleta_json()
    resultados['testes']['coleta_api'] = testar_coleta_api()
    resultados['testes']['validacao_dados'] = validar_dados_salvos()
    resultados['testes']['relacionamentos'] = testar_relacionamentos()
    
    # Calcular sucesso geral
    testes_passados = sum(resultados['testes'].values())
    total_testes = len(resultados['testes'])
    sucesso_geral = testes_passados == total_testes
    
    # Exibir resultados
    print("\n" + "=" * 60)
    print("📋 RELATÓRIO DE TESTE - COLETA DE PROPOSIÇÕES")
    print("=" * 60)
    print(f"📅 Data: {resultados['data_teste']}")
    print(f"🧪 Testes executados: {total_testes}")
    print(f"✅ Testes passados: {testes_passados}")
    print(f"❌ Testes falhados: {total_testes - testes_passados}")
    
    print("\n📊 Resultados Detalhados:")
    for teste, resultado in resultados['testes'].items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"   {teste}: {status}")
    
    print("\n🎯 Status Geral:", "✅ SUCESSO" if sucesso_geral else "❌ FALHA")
    print("=" * 60)
    
    return sucesso_geral


def main():
    """Função principal."""
    setup_logging()
    logger.info("🚀 Iniciando testes de coleta de proposições")
    
    try:
        sucesso = gerar_relatorio_teste()
        
        if sucesso:
            logger.info("🎉 Todos os testes passaram! Coleta pronta para integração.")
        else:
            logger.warning("⚠️ Alguns testes falharam. Verificar os logs.")
        
        return 0 if sucesso else 1
        
    except Exception as e:
        logger.error(f"❌ Erro fatal nos testes: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit(main())
