#!/usr/bin/env python3
"""
Módulo dedicado ao salvamento de textos de proposições

Responsabilidades:
- Extração de textos de proposições sem texto
- Processamento e upload para GCS
- Validação de integridade
- Recuperação de textos faltantes
"""

import time
import logging
import sys
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.db_utils import get_db_session
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager
from utils.texto_utils import TextoProposicaoUtils
from etl.coleta_proposicoes import ColetorProposicoes

logger = logging.getLogger(__name__)


class TextoSalvamentoModule:
    """Módulo especializado em salvamento de textos de proposições."""
    
    def __init__(self):
        self.gcs = get_gcs_manager()
        self.texto_utils = TextoProposicaoUtils()
        self.coletor = ColetorProposicoes()
        
        if not self.gcs or not self.gcs.is_available():
            raise RuntimeError("GCS não disponível para salvamento de textos")
        
        logger.info("✅ Módulo de salvamento de textos inicializado")
    
    def verificar_textos_faltantes(self, limite: int = 50, ano_minimo: int = 2023) -> List[Dict]:
        """
        Identifica proposições que não têm texto completo no GCS.
        
        Args:
            limite: Número máximo de proposições a retornar
            ano_minimo: Ano mínimo para considerar proposições
            
        Returns:
            Lista de dicionários com informações das proposições
        """
        logger.info(f"🔍 Buscando proposições sem texto (limite: {limite}, ano >= {ano_minimo})")
        
        session = get_db_session()
        
        try:
            query = text("""
                SELECT id, api_camara_id, tipo, numero, ano, ementa, gcs_url
                FROM proposicoes 
                WHERE ano >= :ano_minimo
                ORDER BY data_apresentacao DESC
                LIMIT :limite
            """)
            
            result = session.execute(query, {
                'ano_minimo': ano_minimo,
                'limite': limite
            }).fetchall()
            
            props_sem_texto = []
            
            for row in result:
                prop_info = {
                    'id': row[0],
                    'api_camara_id': row[1],
                    'tipo': row[2],
                    'numero': row[3],
                    'ano': row[4],
                    'ementa': row[5] or '',
                    'gcs_url': row[6] or ''
                }
                
                # Verificar se texto realmente existe no GCS
                if not self._verificar_texto_existe(prop_info):
                    props_sem_texto.append(prop_info)
            
            logger.info(f"📊 Encontradas {len(props_sem_texto)} proposições sem texto")
            return props_sem_texto
            
        finally:
            session.close()
    
    def _verificar_texto_existe(self, prop_info: Dict) -> bool:
        """
        Verifica se o texto de uma proposição existe no GCS.
        
        Args:
            prop_info: Dicionário com informações da proposição
            
        Returns:
            True se texto existe, False caso contrário
        """
        possible_paths = self._get_possible_text_paths(prop_info)
        
        for path in possible_paths:
            try:
                data = self.gcs.download_text(path, compressed=False)
                if data and len(data.strip()) > 100:  # Mínimo de 100 caracteres
                    return True
            except:
                continue
        
        return False
    
    def _get_possible_text_paths(self, prop_info: Dict) -> List[str]:
        """
        Gera possíveis paths para o texto da proposição no GCS.
        
        Args:
            prop_info: Dicionário com informações da proposição
            
        Returns:
            Lista de paths possíveis
        """
        api_id = prop_info['api_camara_id']
        tipo = prop_info['tipo']
        ano = prop_info['ano']
        
        return [
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt",
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/documento/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}.json"
        ]
    
    def extrair_e_salvar_textos(self, proposicoes: List[Dict], delay_segundos: float = 2.0) -> Dict:
        """
        Extrai e salva textos para uma lista de proposições.
        
        Args:
            proposicoes: Lista de dicionários com informações das proposições
            delay_segundos: Delay entre requisições para evitar rate limiting
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        logger.info(f"🚀 Iniciando extração de {len(proposicoes)} textos")
        
        stats = {
            'total': len(proposicoes),
            'sucesso': 0,
            'falha': 0,
            'pulado': 0,
            'erros': []
        }
        
        for i, prop_info in enumerate(proposicoes, 1):
            logger.info(f"📄 Processando {i}/{stats['total']}: {prop_info['tipo']} {prop_info['numero']}/{prop_info['ano']} (ID: {prop_info['id']})")
            
            try:
                # Preparar dados para o coletor
                dados_proposicao = {
                    'id': prop_info['id'],
                    'api_camara_id': prop_info['api_camara_id'],
                    'tipo': prop_info['tipo'],
                    'numero': prop_info['numero'],
                    'ano': prop_info['ano'],
                    'ementa': prop_info['ementa']
                }
                
                # Usar o coletor para baixar e processar
                resultado = self.coletor.salvar_proposicao(dados_proposicao, salvar_gcs=True)
                
                if resultado:
                    # Validar que o texto foi realmente salvo
                    if self._verificar_texto_existe(prop_info):
                        stats['sucesso'] += 1
                        logger.info(f"✅ Texto salvo com sucesso: {prop_info['id']}")
                        
                        # Atualizar GCS URL no banco se necessário
                        self._atualizar_gcs_url(prop_info)
                    else:
                        stats['falha'] += 1
                        erro_msg = f"Texto não encontrado após salvamento: {prop_info['id']}"
                        stats['erros'].append(erro_msg)
                        logger.error(f"❌ {erro_msg}")
                else:
                    stats['falha'] += 1
                    erro_msg = f"Falha no salvamento: {prop_info['id']}"
                    stats['erros'].append(erro_msg)
                    logger.error(f"❌ {erro_msg}")
                
                # Rate limiting
                if delay_segundos > 0:
                    time.sleep(delay_segundos)
                    
            except Exception as e:
                stats['falha'] += 1
                erro_msg = f"Erro ao processar {prop_info['id']}: {str(e)}"
                stats['erros'].append(erro_msg)
                logger.error(f"❌ {erro_msg}", exc_info=True)
        
        # Calcular taxa de sucesso
        stats['taxa_sucesso'] = (stats['sucesso'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        logger.info(f"📊 Processamento concluído: {stats['sucesso']}/{stats['total']} ({stats['taxa_sucesso']:.1f}%)")
        return stats
    
    def _atualizar_gcs_url(self, prop_info: Dict):
        """
        Atualiza o campo gcs_url no banco de dados.
        
        Args:
            prop_info: Dicionário com informações da proposição
        """
        api_id = prop_info['api_camara_id']
        tipo = prop_info['tipo']
        ano = prop_info['ano']
        
        # Gerar URL correta do GCS
        gcs_url = f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt"
        
        session = get_db_session()
        
        try:
            session.execute(text("""
                UPDATE proposicoes 
                SET gcs_url = :gcs_url
                WHERE id = :prop_id
            """), {
                'gcs_url': gcs_url,
                'prop_id': prop_info['id']
            })
            session.commit()
            logger.debug(f"🔄 GCS URL atualizado: {prop_info['id']} -> {gcs_url}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro ao atualizar GCS URL {prop_info['id']}: {e}")
        finally:
            session.close()
    
    def processar_lote_textos(self, limite: int = 50, delay_segundos: float = 2.0) -> Dict:
        """
        Processa um lote completo de textos faltantes.
        
        Args:
            limite: Número máximo de proposições a processar
            delay_segundos: Delay entre requisições
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        logger.info(f"🚀 Iniciando processamento em lote (limite: {limite})")
        
        # Buscar proposições sem texto
        props_sem_texto = self.verificar_textos_faltantes(limite=limite)
        
        if not props_sem_texto:
            logger.info("✅ Todas as proposições já têm texto!")
            return {
                'total': 0,
                'sucesso': 0,
                'falha': 0,
                'taxa_sucesso': 100.0,
                'mensagem': 'Nenhuma proposição sem texto encontrada'
            }
        
        # Processar textos
        stats = self.extrair_e_salvar_textos(props_sem_texto, delay_segundos)
        
        return stats
    
    def validar_integridade_geral(self, amostra: int = 100) -> Dict:
        """
        Valida a integridade geral dos textos no GCS.
        
        Args:
            amostra: Número de proposições para amostrar
            
        Returns:
            Dicionário com estatísticas de validação
        """
        logger.info(f"🔍 Validando integridade geral (amostra: {amostra})")
        
        session = get_db_session()
        
        try:
            query = text("""
                SELECT id, api_camara_id, tipo, numero, ano
                FROM proposicoes 
                WHERE ano >= 2023
                ORDER BY RANDOM()
                LIMIT :amostra
            """)
            
            result = session.execute(query, {'amostra': amostra}).fetchall()
            
            validacoes = {
                'total_amostra': len(result),
                'com_texto': 0,
                'sem_texto': 0,
                'taxa_cobertura': 0.0
            }
            
            for row in result:
                prop_info = {
                    'id': row[0],
                    'api_camara_id': row[1],
                    'tipo': row[2],
                    'numero': row[3],
                    'ano': row[4]
                }
                
                if self._verificar_texto_existe(prop_info):
                    validacoes['com_texto'] += 1
                else:
                    validacoes['sem_texto'] += 1
            
            validacoes['taxa_cobertura'] = (validacoes['com_texto'] / validacoes['total_amostra'] * 100) if validacoes['total_amostra'] > 0 else 0
            
            logger.info(f"📊 Validação concluída: {validacoes['com_texto']}/{validacoes['total_amostra']} ({validacoes['taxa_cobertura']:.1f}%)")
            return validacoes
            
        finally:
            session.close()
    
    def gerar_relatorio_status(self) -> Dict:
        """
        Gera um relatório completo do status dos textos.
        
        Returns:
            Dicionário com informações detalhadas
        """
        logger.info("📊 Gerando relatório de status")
        
        session = get_db_session()
        
        try:
            # Estatísticas gerais
            stats = session.execute(text("""
                SELECT 
                    COUNT(*) as total_props,
                    COUNT(CASE WHEN gcs_url IS NOT NULL THEN 1 END) as com_gcs_url,
                    COUNT(CASE WHEN ano >= 2023 THEN 1 END) as props_recentes
                FROM proposicoes
            """)).fetchone()
            
            # Validação por amostragem
            validacao = self.validar_integridade_geral(amostra=50)
            
            relatorio = {
                'timestamp': datetime.now().isoformat(),
                'estatisticas_gerais': {
                    'total_proposicoes': stats.total_props,
                    'com_gcs_url': stats.com_gcs_url,
                    'proposicoes_recentes': stats.props_recentes
                },
                'validacao_amostragem': validacao,
                'status_geral': 'OK' if validacao['taxa_cobertura'] > 80 else 'CRÍTICO'
            }
            
            return relatorio
            
        finally:
            session.close()


def main():
    """Função principal para testes."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        modulo = TextoSalvamentoModule()
        
        # Testar com um lote pequeno
        stats = modulo.processar_lote_textos(limite=5, delay_segundos=1.0)
        print(f"📊 Estatísticas: {stats}")
        
        # Gerar relatório
        relatorio = modulo.gerar_relatorio_status()
        print(f"📋 Relatório: {relatorio}")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)


if __name__ == "__main__":
    main()
