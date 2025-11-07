#!/usr/bin/env python3
"""
Script para análise em lote de proposições existentes
Evita reanálises e processa de forma controlada
"""

import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agents'))

# Imports do backend
from models.db_utils import get_db_session
from models.analise_models import AnaliseProposicao
from models.proposicao_models import Proposicao
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager

# Imports dos agents
from pipeline_analise_agents import PipelineAnaliseAgents

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnaliseEmLote:
    """
    Classe para análise em lote de proposições existentes.
    Evita reanálises e processa de forma controlada.
    """
    
    def __init__(self, lote_size: int = 10):
        """Inicializa o analisador em lote."""
        self.lote_size = lote_size
        self.pipeline = PipelineAnaliseAgents()
        self.gcs = get_gcs_manager()
        
        # Estatísticas
        self.stats = {
            'total': 0,
            'processadas': 0,
            'erros': 0,
            'relevantes': 0,
            'triviais': 0,
            'com_par': 0,
            'pulas': 0,  # Já analisadas
            'inicio': datetime.utcnow(),
            'lotes': []
        }
        
        logger.info(f"Analisador em lote inicializado - Lote size: {self.lote_size}")
    
    def buscar_proposicoes_sem_analise(self) -> List[Dict]:
        """
        Busca proposições que ainda não foram analisadas.
        
        Returns:
            Lista de dicionários com dados das proposições
        """
        logger.info("Buscando proposições sem análise...")
        
        try:
            session = get_db_session()
            
            # Query para buscar proposições sem análise
            query = text("""
                SELECT 
                    p.id,
                    p.api_camara_id,
                    p.tipo,
                    p.numero,
                    p.ano,
                    p.ementa,
                    p.gcs_url,
                    p.link_inteiro_teor
                FROM proposicoes p
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE ap.id IS NULL
                AND p.ano >= 2023
                ORDER BY p.data_apresentacao DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, {'limit': self.lote_size}).fetchall()
            session.close()
            
            # Converter para lista de dicionários
            proposicoes = []
            for row in result:
                proposicoes.append({
                    'id': row[0],
                    'api_camara_id': row[1],
                    'tipo': row[2],
                    'numero': row[3],
                    'ano': row[4],
                    'ementa': row[5],
                    'gcs_url': row[6],
                    'link_inteiro_teor': row[7]
                })
            
            logger.info(f"Encontradas {len(proposicoes)} proposições sem análise")
            return proposicoes
            
        except Exception as e:
            logger.error(f"Erro ao buscar proposições: {e}")
            return []
    
    def verificar_texto_disponivel(self, proposicao: Dict) -> bool:
        """
        Verifica se o texto completo está disponível no GCS.
        
        Args:
            proposicao: Dicionário com dados da proposição
            
        Returns:
            True se texto está disponível
        """
        if not self.gcs or not self.gcs.is_available():
            return True  # Se não tem GCS, tenta com link
        
        ano = proposicao['ano']
        tipo = proposicao['tipo']
        api_id = proposicao['api_camara_id']
        
        # Verificar path principal
        texto_path = f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt"
        
        try:
            data = self.gcs.download_text(texto_path, compressed=False)
            if data and len(data.strip()) > 100:
                logger.debug(f"Texto disponível: {texto_path}")
                return True
        except:
            pass
        
        # Tentar paths alternativos
        possible_paths = [
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/documento/{tipo}-{api_id}-texto.html",
            f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}.json"
        ]
        
        for path in possible_paths:
            try:
                data = self.gcs.download_text(path, compressed=False)
                if data and len(data.strip()) > 100:
                    logger.debug(f"Texto encontrado em path alternativo: {path}")
                    return True
            except:
                continue
        
        logger.warning(f"Texto não encontrado para {tipo} {proposicao['numero']}/{ano}")
        return False
    
    def processar_lote(self) -> Dict:
        """
        Processa um lote de proposições.
        
        Returns:
            Dicionário com estatísticas do lote
        """
        logger.info(f"Iniciando processamento do lote...")
        
        # Buscar proposições sem análise
        proposicoes = self.buscar_proposicoes_sem_analise()
        
        if not proposicoes:
            logger.info("Nenhuma proposição para analisar neste lote")
            return {'status': 'sem_dados', 'mensagem': 'Nenhuma proposição para analisar'}
        
        # Estatísticas do lote
        lote_stats = {
            'total': len(proposicoes),
            'processadas': 0,
            'erros': 0,
            'relevantes': 0,
            'triviais': 0,
            'com_par': 0,
            'pulas': 0,
            'inicio': datetime.utcnow(),
            'proposicoes': []
        }
        
        # Processar cada proposição
        for i, prop in enumerate(proposicoes, 1):
            logger.info(f"Processando {i}/{len(proposicoes)}: {prop['tipo']} {prop['numero']}/{prop['ano']} (ID: {prop['id']})")
            
            try:
                # Verificar se texto está disponível
                if not self.verificar_texto_disponivel(prop):
                    logger.warning(f"Pulando {prop['id']} - texto não disponível")
                    lote_stats['pulas'] += 1
                    continue
                
                # Criar tupla no formato esperado pelo pipeline
                tupla_proposicao = (
                    prop['id'],
                    prop['api_camara_id'],
                    prop['tipo'],
                    prop['numero'],
                    prop['ano'],
                    prop['ementa'],
                    prop['gcs_url'],
                    prop['link_inteiro_teor']
                )
                
                # Analisar proposição
                resultado = self.pipeline.analisar_proposicao(tupla_proposicao)
                
                if resultado:
                    # Salvar análise no banco
                    if self.pipeline.salvar_analise_proposicao(prop['id'], resultado):
                        lote_stats['processadas'] += 1
                        
                        # Atualizar estatísticas
                        if not resultado['is_trivial']:
                            lote_stats['relevantes'] += 1
                            if resultado['par_score']:
                                lote_stats['com_par'] += 1
                        else:
                            lote_stats['triviais'] += 1
                        
                        # Adicionar à lista de resultados
                        lote_stats['proposicoes'].append({
                            'id': prop['id'],
                            'tipo': prop['tipo'],
                            'numero': prop['numero'],
                            'ano': prop['ano'],
                            'is_trivial': resultado['is_trivial'],
                            'par_score': resultado['par_score']
                        })
                        
                        logger.info(f"✅ Análise concluída: {prop['id']} - {resultado['is_trivial']} - PAR: {resultado['par_score']}")
                    else:
                        lote_stats['erros'] += 1
                        logger.error(f"❌ Erro ao salvar análise: {prop['id']}")
                else:
                    lote_stats['erros'] += 1
                    logger.error(f"❌ Falha na análise: {prop['id']}")
                
                # Delay entre processamentos (rate limiting)
                time.sleep(2)
                
            except Exception as e:
                lote_stats['erros'] += 1
                logger.error(f"❌ Erro inesperado: {prop['id']} - {e}")
        
        # Finalizar estatísticas do lote
        lote_stats['fim'] = datetime.utcnow()
        lote_stats['duracao'] = (lote_stats['fim'] - lote_stats['inicio']).total_seconds()
        lote_stats['taxa_sucesso'] = (lote_stats['processadas'] / lote_stats['total']) * 100 if lote_stats['total'] > 0 else 0
        
        # Adicionar às estatísticas gerais
        self.stats['total'] += lote_stats['total']
        self.stats['processadas'] += lote_stats['processadas']
        self.stats['erros'] += lote_stats['erros']
        self.stats['relevantes'] += lote_stats['relevantes']
        self.stats['triviais'] += lote_stats['triviais']
        self.stats['com_par'] += lote_stats['com_par']
        self.stats['pulas'] += lote_stats['pulas']
        self.stats['lotes'].append(lote_stats)
        
        # Log do lote
        logger.info("=" * 60)
        logger.info("LOTE CONCLUÍDO")
        logger.info("=" * 60)
        logger.info(f"Total: {lote_stats['total']}")
        logger.info(f"Processadas: {lote_stats['processadas']}")
        logger.info(f"Erros: {lote_stats['erros']}")
        logger.info(f"Puladas: {lote_stats['pulas']}")
        logger.info(f"Taxa de sucesso: {lote_stats['taxa_sucesso']:.1f}%")
        logger.info(f"Relevantes: {lote_stats['relevantes']}")
        logger.info(f"Triviais: {lote_stats['triviais']}")
        logger.info(f"Com PAR: {lote_stats['com_par']}")
        logger.info(f"Duração: {lote_stats['duracao']:.1f} segundos")
        
        return lote_stats
    
    def executar_analise_continua(self, max_lotes: int = None):
        """
        Executa análise contínua em lotes.
        
        Args:
            max_lotes: Número máximo de lotes (None = ilimitado)
        """
        logger.info("Iniciando análise contínua em lotes...")
        
        lote_num = 0
        while True:
            if max_lotes and lote_num >= max_lotes:
                logger.info(f"Limite de {max_lotes} lotes alcançado")
                break
            
            lote_num += 1
            logger.info(f"\n🚀 PROCESSANDO LOTE {lote_num}")
            
            # Processar lote
            resultado = self.processar_lote()
            
            if resultado.get('status') == 'sem_dados':
                logger.info("Não há mais proposições para analisar")
                break
            
            # Pausa entre lotes
            logger.info(f"Pausa de 10 segundos antes do próximo lote...")
            time.sleep(10)
        
        # Estatísticas finais
        self.mostrar_estatisticas_finais()
    
    def mostrar_estatisticas_finais(self):
        """Mostra estatísticas finais da análise."""
        self.stats['fim'] = datetime.utcnow()
        self.stats['duracao_total'] = (self.stats['fim'] - self.stats['inicio']).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("ANÁLISE EM LOTE - ESTATÍSTICAS FINAIS")
        logger.info("=" * 80)
        logger.info(f"Lotes processados: {len(self.stats['lotes'])}")
        logger.info(f"Total de proposições: {self.stats['total']}")
        logger.info(f"Processadas: {self.stats['processadas']}")
        logger.info(f"Erros: {self.stats['erros']}")
        logger.info(f"Puladas (sem texto): {self.stats['pulas']}")
        logger.info(f"Taxa de sucesso: {(self.stats['processadas']/self.stats['total']*100):.1f}%" if self.stats['total'] > 0 else "N/A")
        logger.info(f"Relevantes: {self.stats['relevantes']}")
        logger.info(f"Triviais: {self.stats['triviais']}")
        logger.info(f"Com PAR: {self.stats['com_par']}")
        logger.info(f"Duração total: {self.stats['duracao_total']:.1f} segundos")
        
        if self.stats['processadas'] > 0:
            tempo_medio = self.stats['duracao_total'] / self.stats['processadas']
            logger.info(f"Tempo médio por proposição: {tempo_medio:.1f} segundos")
        
        logger.info("=" * 80)


def main():
    """
    Função principal para execução da análise em lote.
    """
    print("🚀 ANÁLISE EM LOTE DE PROPOSIÇÕES")
    print("=" * 60)
    
    # Configurações
    lote_size = 10
    max_lotes = 5  # Limitar a 5 lotes por execução (50 proposições)
    
    print(f"Configurações:")
    print(f"  - Tamanho do lote: {lote_size} proposições")
    print(f"  - Máximo de lotes: {max_lotes}")
    print(f"  - Total máximo: {lote_size * max_lotes} proposições")
    print()
    
    # Criar e executar analisador
    analisador = AnaliseEmLote(lote_size=lote_size)
    analisador.executar_analise_continua(max_lotes=max_lotes)
    
    print("\n🎯 Análise em lote concluída!")


if __name__ == "__main__":
    main()
