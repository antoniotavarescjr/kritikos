#!/usr/bin/env python3
"""
Versão melhorada do coletor de textos restantes.
- Remove hardcoded offset
- Suporta todos os tipos de proposições
- Calcula offset dinamicamente
- Mantém simplicidade e performance
"""

import sys
import os
import time
from datetime import datetime
import logging

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.db_utils import get_db_session
from sqlalchemy import text
from utils.gcs_utils import GCSManager
from etl.pdf_coleta_module import PDFColetaManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ColetorTextosRestantesV2:
    """Classe melhorada para coletar textos restantes de todos os tipos."""
    
    def __init__(self):
        self.gcs_manager = GCSManager('kritikos-emendas-prod')
        self.pdf_coleta = PDFColetaManager()
        
    def analisar_situacao_por_tipo(self, tipo):
        """Analisa situação da coleta para um tipo específico."""
        logger.info(f"🔍 Analisando situação do tipo {tipo}...")
        
        session = get_db_session()
        
        try:
            # Verificar proposições do tipo
            resultado = session.execute(text('''
                SELECT 
                    COUNT(*) as total_props,
                    COUNT(CASE WHEN link_inteiro_teor IS NOT NULL AND link_inteiro_teor != '' THEN 1 END) as com_url,
                    COUNT(CASE WHEN gcs_url IS NOT NULL AND gcs_url != '' THEN 1 END) as com_gcs_url
                FROM proposicoes 
                WHERE ano = 2025
                AND tipo = :tipo
            '''), {'tipo': tipo}).fetchone()
            
            # Verificar arquivos no GCS para este tipo
            arquivos_gcs = self.gcs_manager.list_blobs(f'proposicoes/2025/{tipo}/texto-completo/')
            
            logger.info(f"📊 Estatísticas {tipo} 2025:")
            logger.info(f"   Total: {resultado.total_props:,}")
            logger.info(f"   Com URL: {resultado.com_url:,}")
            logger.info(f"   Com GCS URL: {resultado.com_gcs_url:,}")
            logger.info(f"   Arquivos no GCS: {len(arquivos_gcs):,}")
            
            # Calcular gap
            gap = resultado.com_gcs_url - len(arquivos_gcs)
            logger.info(f"   Gap: {gap:,}")
            
            return {
                'tipo': tipo,
                'total_props': resultado.total_props,
                'com_url': resultado.com_url,
                'com_gcs_url': resultado.com_gcs_url,
                'arquivos_gcs': len(arquivos_gcs),
                'gap': gap
            }
            
        finally:
            session.close()
    
    def calcular_offset_dinamico(self, tipo):
        """Calcula offset dinâmico baseado nos arquivos já existentes."""
        logger.info(f"🔢 Calculando offset dinâmico para {tipo}...")
        
        # Contar arquivos já existentes no GCS
        arquivos_gcs = self.gcs_manager.list_blobs(f'proposicoes/2025/{tipo}/texto-completo/')
        offset = len(arquivos_gcs)
        
        logger.info(f"   Offset calculado: {offset} (baseado em {len(arquivos_gcs)} arquivos existentes)")
        return offset
    
    def identificar_faltantes_por_tipo(self, tipo, offset=0, limite=500):
        """Identifica proposições faltantes para um tipo específico."""
        logger.info(f"🔍 Identificando {tipo}s faltantes (offset: {offset}, limite: {limite})...")
        
        session = get_db_session()
        
        try:
            # Buscar proposições com URL mas sem arquivo no GCS, com offset
            resultado = session.execute(text('''
                SELECT api_camara_id, tipo, numero, ano, link_inteiro_teor, gcs_url
                FROM proposicoes 
                WHERE ano = 2025
                AND tipo = :tipo
                AND link_inteiro_teor IS NOT NULL 
                AND link_inteiro_teor != ''
                ORDER BY id
                OFFSET :offset
                LIMIT :limite
            '''), {'tipo': tipo, 'offset': offset, 'limite': limite}).fetchall()
            
            logger.info(f"📋 Encontrados {len(resultado)} {tipo}s para verificar (offset: {offset})")
            
            # Verificar quais realmente faltam no GCS
            props_faltantes = []
            for row in resultado:
                # Verificar se arquivo existe no GCS
                nome_arquivo = f"{tipo}-{row.api_camara_id}-texto-completo.txt"
                blob_path = f"proposicoes/2025/{tipo}/texto-completo/{nome_arquivo}"
                
                metadata = self.gcs_manager.get_blob_metadata(blob_path)
                if not metadata:
                    props_faltantes.append({
                        'api_camara_id': row.api_camara_id,
                        'tipo': row.tipo,
                        'numero': row.numero,
                        'ano': row.ano,
                        'link_inteiro_teor': row.link_inteiro_teor,
                        'gcs_url': row.gcs_url
                    })
            
            logger.info(f"❌ {tipo}s realmente faltantes: {len(props_faltantes)}")
            return props_faltantes, offset + len(resultado)
            
        finally:
            session.close()
    
    def coletar_textos_faltantes(self, props_faltantes):
        """Coleta textos para proposições faltantes (método já testado)."""
        logger.info(f"🚀 Coletando textos para {len(props_faltantes)} proposições faltantes...")
        
        sucesso = 0
        falhas = 0
        
        for i, prop in enumerate(props_faltantes):
            try:
                logger.info(f"📄 Processando {prop['tipo']} {prop['api_camara_id']} ({i+1}/{len(props_faltantes)})")
                
                # Preparar dados para o PDFColetaManager
                dados_prop = {
                    'id': prop['api_camara_id'],
                    'siglaTipo': prop['tipo'],
                    'tipo': prop['tipo'],
                    'ano': prop['ano'],
                    'urlInteiroTeor': prop['link_inteiro_teor'],
                    'uri': f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{prop['api_camara_id']}"
                }
                
                # Coletar texto usando o PDFColetaManager
                resultado = self.pdf_coleta.coletar_pdf_proposicao(dados_prop)
                
                if resultado['sucesso']:
                    sucesso += 1
                    logger.info(f"✅ {prop['tipo']} {prop['api_camara_id']}: texto coletado")
                else:
                    falhas += 1
                    logger.warning(f"❌ {prop['tipo']} {prop['api_camara_id']}: {resultado['erro']}")
                
                # Pequena pausa para não sobrecarregar
                time.sleep(0.5)
                
            except Exception as e:
                falhas += 1
                logger.error(f"❌ Erro ao processar {prop['tipo']} {prop['api_camara_id']}: {e}")
        
        logger.info(f"📊 Resultado da coleta: {sucesso} sucesso, {falhas} falhas")
        return sucesso, falhas
    
    def analisar_situacao_completa(self):
        """Analisa situação completa de todos os tipos."""
        logger.info("🔍 Analisando situação completa de todos os tipos...")
        
        # Tipos que precisamos verificar
        tipos_para_verificar = ['PL', 'PEC', 'PLP', 'MPV', 'PLV', 'SUG']
        
        situacoes = []
        gap_total = 0
        
        for tipo in tipos_para_verificar:
            situacao = self.analisar_situacao_por_tipo(tipo)
            situacoes.append(situacao)
            gap_total += situacao['gap']
        
        logger.info(f"\n📊 RESUMO COMPLETO:")
        logger.info(f"   Gap total: {gap_total:,}")
        
        return situacoes, gap_total
    
    def executar_coleta_completa(self, limite_por_lote=500):
        """Executa coleta completa para todos os tipos."""
        logger.info("🔧 INICIANDO COLETA COMPLETA DE TEXTOS V2")
        print("=" * 80)
        print("     🚀 COLETOR TEXTOS RESTANTES V2 - VERSÃO MELHORADA")
        print("=" * 80)
        
        # Etapa 1: Análise completa
        print(f"\n{'='*60}")
        print(f"🔍 ETAPA 1/3: Análise Completa da Situação")
        print(f"{'='*60}")
        
        situacoes, gap_total = self.analisar_situacao_completa()
        
        if gap_total == 0:
            logger.info("✅ Não há gap - todos os textos estão no GCS!")
            return True
        
        # Etapa 2: Coleta por tipo
        print(f"\n{'='*60}")
        print(f"🚀 ETAPA 2/3: Coleta por Tipo")
        print(f"{'='*60}")
        
        total_coletados = 0
        
        for situacao in situacoes:
            if situacao['gap'] > 0:
                tipo = situacao['tipo']
                logger.info(f"\n🔄 Processando tipo {tipo} (gap: {situacao['gap']})")
                
                # Calcular offset dinâmico
                offset = self.calcular_offset_dinamico(tipo)
                lote = 1
                
                while situacao['gap'] > 0:
                    logger.info(f"🔄 Lote {lote} para {tipo} (offset: {offset})")
                    
                    props_faltantes, novo_offset = self.identificar_faltantes_por_tipo(
                        tipo=tipo,
                        offset=offset,
                        limite=limite_por_lote
                    )
                    
                    if not props_faltantes:
                        logger.info(f"✅ Não há mais {tipo}s faltantes neste lote!")
                        offset = novo_offset
                        lote += 1
                        continue
                    
                    sucesso, falhas = self.coletar_textos_faltantes(props_faltantes)
                    total_coletados += sucesso
                    
                    logger.info(f"📊 Lote {lote} ({tipo}) concluído: {sucesso} sucesso, {falhas} falhas")
                    
                    # Atualizar situação do tipo
                    situacao = self.analisar_situacao_por_tipo(tipo)
                    
                    offset = novo_offset
                    lote += 1
                    
                    # Pequena pausa entre lotes
                    time.sleep(2)
        
        # Etapa 3: Verificação final
        print(f"\n{'='*60}")
        print(f"✅ ETAPA 3/3: Verificação Final")
        print(f"{'='*60}")
        
        situacoes_finais, gap_final = self.analisar_situacao_completa()
        
        # Resumo final
        print(f"\n{'='*60}")
        print("✅ COLETA COMPLETA V2 CONCLUÍDA")
        print(f"{'='*60}")
        print(f"📊 Resumo Final:")
        print(f"   Total coletados nesta sessão: {total_coletados}")
        print(f"   Gap inicial: {gap_total:,}")
        print(f"   Gap final: {gap_final:,}")
        
        if gap_final == 0:
            print(f"   🎉 TODOS OS TEXTOS FORAM COLETADOS!")
        else:
            print(f"   ⚠️ Ainda restam {gap_final:,} textos")
        
        print("=" * 80)
        
        return gap_final == 0


def main():
    """Função principal."""
    coletor = ColetorTextosRestantesV2()
    
    # Executar coleta completa
    sucesso = coletor.executar_coleta_completa(limite_por_lote=500)
    
    if sucesso:
        logger.info("✅ Coleta completa concluída com sucesso!")
        return 0
    else:
        logger.warning("⚠️ Coleta completa concluída, mas ainda há textos faltando")
        return 1


if __name__ == "__main__":
    exit(main())
