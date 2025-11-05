#!/usr/bin/env python3
"""
Pipeline de coleta OTIMIZADO para hackaton.

Integra todas as etapas em um único fluxo automático:
1. Coleta de dados básicos
2. Coleta de emendas parlamentares
3. Processamento de autorias (com deduplicação)
4. Geração de rankings
5. Limpeza automática de cache
"""

import sys
import os
import time
import shutil
from datetime import datetime
import logging

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text
from etl.pipeline_coleta import ColetaPipeline
from etl.coleta_proposicoes import ColetorProposicoes
from etl.coletor_emendas import ColetorEmendasGenerico
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineOtimizado:
    """Pipeline otimizado para execução completa automática."""
    
    def __init__(self):
        self.pipeline = ColetaPipeline()
        self.coletor = ColetorProposicoes()
        self.coletor_emendas = ColetorEmendasGenerico()
        
    def limpar_cache_antigo(self):
        """Limpa cache antigo para liberar espaço."""
        logger.info("🧹 Limpando cache antigo...")
        
        cache_dirs = [
            'coletorproposicoes',
            'cache',
            'src/coletorproposicoes'
        ]
        
        total_limpado = 0
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    # Remover apenas arquivos antigos (mais de 1 dia)
                    current_time = time.time()
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                file_age = current_time - os.path.getmtime(file_path)
                                if file_age > 86400:  # 1 dia em segundos
                                    os.remove(file_path)
                                    total_limpado += 1
                except Exception as e:
                    logger.warning(f"Erro ao limpar {cache_dir}: {e}")
        
        logger.info(f"✅ Cache limpo: {total_limpado} arquivos removidos")
        return total_limpado
    
    def coletar_emendas_parlamentares(self):
        """Executa coleta de emendas parlamentares."""
        logger.info("💰 Coletando emendas parlamentares...")
        
        try:
            session = get_db_session()
            resultado = self.coletor_emendas.coletar_emendas(session)
            session.close()
            
            if resultado and resultado.get('emendas_salvas', 0) > 0:
                logger.info(f"✅ Emendas coletadas: {resultado['emendas_salvas']}")
                logger.info(f"📊 Taxa de matching: {resultado.get('taxa_matching', 0):.1f}%")
                return True
            else:
                logger.warning("⚠️ Nenhuma emenda salva")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na coleta de emendas: {e}")
            return False
    
    def executar_coleta_principal(self):
        """Executa coleta principal de dados."""
        logger.info("🚀 Iniciando coleta principal...")
        
        try:
            resultado = self.pipeline.executar_pipeline_configurado()
            return resultado.get('etapas', {})
        except Exception as e:
            logger.error(f"❌ Erro na coleta principal: {e}")
            return {}
    
    def processar_autorias_deduplicadas(self):
        """Processa autorias com deduplicação automática."""
        logger.info("👥 Processando autorias com deduplicação...")
        
        try:
            session = get_db_session()
            
            # Limpar autorias duplicadas primeiro
            logger.info("🧹 Limpando autorias duplicadas...")
            session.execute(text("""
                DELETE FROM autorias 
                WHERE ctid NOT IN (
                    SELECT min(ctid)
                    FROM autorias 
                    GROUP BY proposicao_id, deputado_id, tipo_autoria
                )
            """))
            session.commit()
            
            # Obter proposições sem autor
            props_sem_autor = session.execute(text("""
                SELECT id, api_camara_id, tipo, numero, ano 
                FROM proposicoes 
                WHERE ano = 2025 
                AND id NOT IN (
                    SELECT DISTINCT proposicao_id 
                    FROM autorias 
                    WHERE deputado_id IS NOT NULL
                )
                LIMIT 1000
            """)).fetchall()
            
            logger.info(f"📊 Processando {len(props_sem_autor)} proposições sem autor...")
            
            # Download único de autores
            autores_data = self.coletor.baixar_json_autores(2025)
            
            processadas = 0
            erros = 0
            
            for prop in props_sem_autor:
                prop_id, api_id, tipo, num, ano = prop
                autores = autores_data.get(api_id, [])
                
                if autores:
                    try:
                        self.coletor._salvar_autoria_otimizado(prop_id, autores)
                        processadas += 1
                    except Exception as e:
                        erros += 1
                        continue
            
            session.commit()
            session.close()
            
            logger.info(f"✅ Autorias processadas: {processadas} sucesso, {erros} erros")
            return {'processadas': processadas, 'erros': erros}
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de autorias: {e}")
            return {'processadas': 0, 'erros': 1}
    
    def gerar_ranking_final(self):
        """Gera ranking final de deputados."""
        logger.info("🏆 Gerando ranking final...")
        
        try:
            session = get_db_session()
            
            # Query otimizada para ranking
            ranking_data = session.execute(text("""
                SELECT 
                    d.id,
                    d.nome,
                    COUNT(DISTINCT p.id) as total_proposicoes,
                    COUNT(a.id) as total_autorias,
                    STRING_AGG(DISTINCT p.tipo, ', ') as tipos_proposicoes
                FROM deputados d
                JOIN autorias a ON d.id = a.deputado_id
                JOIN proposicoes p ON a.proposicao_id = p.id
                WHERE p.ano = 2025
                AND a.deputado_id IS NOT NULL
                GROUP BY d.id, d.nome
                HAVING COUNT(DISTINCT p.id) > 0
                ORDER BY total_proposicoes DESC, total_autorias DESC
            """)).fetchall()
            
            ranking = []
            for i, row in enumerate(ranking_data, 1):
                ranking.append({
                    'posicao': i,
                    'id_deputado': row[0],
                    'nome': row[1],
                    'total_proposicoes': row[2],
                    'total_autorias': row[3],
                    'tipos_proposicoes': row[4]
                })
            
            # Salvar em CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'ranking_final_otimizado_{timestamp}.csv'
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('Posicao,Nome,Total_Proposicoes,Total_Autorias,Tipos_Proposicoes\n')
                for item in ranking:
                    f.write(f"{item['posicao']},{item['nome']},")
                    f.write(f"{item['total_proposicoes']},{item['total_autorias']},")
                    f.write(f"\"{item['tipos_proposicoes']}\"\n")
            
            session.close()
            
            logger.info(f"✅ Ranking gerado: {filename} ({len(ranking)} deputados)")
            return {'arquivo': filename, 'total': len(ranking)}
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar ranking: {e}")
            return {'arquivo': None, 'total': 0}
    
    def exibir_resumo_final(self, resultados):
        """Exibe resumo final da execução."""
        print("\n" + "="*80)
        print("🎉 PIPELINE OTIMIZADO - RESUMO FINAL")
        print("="*80)
        
        # Estatísticas do banco
        try:
            session = get_db_session()
            stats = session.execute(text("""
                SELECT 
                    'deputados' as tabela, COUNT(*) as registros
                FROM deputados
                UNION ALL
                SELECT 
                    'proposicoes' as tabela, COUNT(*) as registros
                FROM proposicoes WHERE ano = 2025
                UNION ALL
                SELECT 
                    'autorias' as tabela, COUNT(*) as registros
                FROM autorias
                WHERE deputado_id IS NOT NULL
                UNION ALL
                SELECT 
                    'emendas' as tabela, COUNT(*) as registros
                FROM emendas_parlamentares
                WHERE deputado_id IS NOT NULL
            """)).fetchall()
            
            print(f"\n📊 Estatísticas Finais:")
            for tabela, count in stats:
                print(f"   {tabela}: {count:,} registros")
            
            # Cobertura de autorias
            cobertura = session.execute(text("""
                SELECT 
                    COUNT(DISTINCT p.id) as total_props,
                    COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN p.id END) as com_autoria,
                    ROUND(
                        COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN p.id END) * 100.0 / 
                        COUNT(DISTINCT p.id), 2
                    ) as cobertura_percent
                FROM proposicoes p
                LEFT JOIN autorias a ON p.id = a.proposicao_id
                WHERE p.ano = 2025
            """)).fetchone()
            
            if cobertura:
                print(f"\n📈 Cobertura de Autorias (2025):")
                print(f"   Proposições totais: {cobertura.total_props:,}")
                print(f"   Com autor: {cobertura.com_autoria:,}")
                print(f"   Cobertura: {cobertura.cobertura_percent}%")
            
            session.close()
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
        
        # Resultados do pipeline
        print(f"\n🚀 Resultados do Pipeline:")
        for etapa, resultado in resultados.items():
            if resultado:
                print(f"   ✅ {etapa}: Concluído com sucesso")
            else:
                print(f"   ❌ {etapa}: Falhou")
        
        print(f"\n🎯 Sistema pronto para o hackaton!")
        print("="*80)
    
    def executar_pipeline_completo(self):
        """Executa pipeline completo otimizado."""
        logger.info("🚀 Iniciando Pipeline Otimizado Completo")
        print("=" * 80)
        print("     🚀 PIPELINE OTIMIZADO - HACKATHON KRITIKOS")
        print("=" * 80)
        
        inicio_total = time.time()
        resultados = {}
        
        try:
            # Etapa 1: Limpar cache
            print(f"\n{'='*60}")
            print(f"🧹 ETAPA 1/5: Limpando Cache Antigo")
            print(f"{'='*60}")
            cache_limpado = self.limpar_cache_antigo()
            resultados['cache'] = cache_limpado > 0
            
            # Etapa 2: Coleta principal
            print(f"\n{'='*60}")
            print(f"📋 ETAPA 2/5: Coleta Principal de Dados")
            print(f"{'='*60}")
            coleta_result = self.executar_coleta_principal()
            resultados['coleta'] = bool(coleta_result)
            
            # Etapa 3: Coleta de emendas
            print(f"\n{'='*60}")
            print(f"💰 ETAPA 3/5: Coleta de Emendas Parlamentares")
            print(f"{'='*60}")
            emendas_result = self.coletar_emendas_parlamentares()
            resultados['emendas'] = emendas_result
            
            # Etapa 4: Processar autorias
            print(f"\n{'='*60}")
            print(f"👥 ETAPA 4/5: Processamento de Autorias")
            print(f"{'='*60}")
            autorias_result = self.processar_autorias_deduplicadas()
            resultados['autorias'] = autorias_result['erros'] < autorias_result['processadas']
            
            # Etapa 5: Gerar ranking
            print(f"\n{'='*60}")
            print(f"🏆 ETAPA 5/5: Geração de Ranking Final")
            print(f"{'='*60}")
            ranking_result = self.gerar_ranking_final()
            resultados['ranking'] = ranking_result['total'] > 0
            
            # Resumo final
            fim_total = time.time()
            duracao_total = fim_total - inicio_total
            
            print(f"\n⏱️ Duração total: {duracao_total:.1f}s ({duracao_total/60:.1f}min)")
            
            self.exibir_resumo_final(resultados)
            
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no pipeline: {e}", exc_info=True)
            return {'erro': str(e)}


def main():
    """Função principal."""
    pipeline = PipelineOtimizado()
    pipeline.executar_pipeline_completo()


if __name__ == "__main__":
    main()
