#!/usr/bin/env python3
"""
Pipeline de Análise de Proposições com Agents Kritikos
Integração completa entre backend e agentes de IA para análise automatizada
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Carregar variáveis de ambiente
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

# Imports do backend
from models.db_utils import get_db_session
from models.analise_models import AnaliseProposicao, LogProcessamento
from models.proposicao_models import Proposicao
from sqlalchemy import text
from utils.gcs_utils import get_gcs_manager

# Imports dos agents
from tools.document_summarizer_tool import summarize_proposal_text, analyze_proposal_par
from tools.trivial_filter_tool import is_summary_trivial

# Imports de configuração
from etl.config import get_analise_config, get_limite_analise_proposicoes, get_versao_analise

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineAnaliseAgents:
    """
    Pipeline completo para análise de proposições usando agents Kritikos.
    Gerencia todo o fluxo: busca → análise → salvamento.
    """
    
    def __init__(self):
        """Inicializa o pipeline com configurações."""
        self.config = get_analise_config()
        self.limite = get_limite_analise_proposicoes()
        self.versao = get_versao_analise()
        self.gcs = get_gcs_manager()
        
        logger.info(f"Pipeline inicializado - Limite: {self.limite}, Versão: {self.versao}")
    
    def buscar_proposicoes_para_analisar(self) -> List[Tuple]:
        """
        Busca proposições que precisam ser analisadas.
        
        Returns:
            Lista de tuplas com dados das proposições
        """
        logger.info("Buscando proposições para análise...")
        
        try:
            session = get_db_session()
            
            # Query para buscar proposições sem análise ou com análise antiga
            query = text("""
                SELECT 
                    p.id,
                    p.api_camara_id,
                    p.tipo,
                    p.numero,
                    p.ano,
                    p.ementa,
                    p.gcs_url,
                    p.link_inteiro_teor,
                    ap.id as analise_id,
                    ap.data_analise as ultima_analise
                FROM proposicoes p
                LEFT JOIN analise_proposicoes ap ON p.id = ap.proposicao_id
                WHERE p.ano = 2025
                AND (
                    ap.id IS NULL 
                    OR ap.data_analise < NOW() - INTERVAL ':dias_para_reanalise days'
                )
                ORDER BY 
                    CASE WHEN ap.id IS NULL THEN 0 ELSE 1 END,
                    p.id DESC
                LIMIT :limite
            """)
            
            result = session.execute(query, {
                'limite': self.limite,
                'dias_para_reanalise': self.config.get('dias_para_reanalise', 7)
            }).fetchall()
            
            session.close()
            
            logger.info(f"Encontradas {len(result)} proposições para análise")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar proposições: {e}")
            return []
    
    def obter_texto_proposicao(self, proposicao: Tuple) -> str:
        """
        Obtém o texto completo da proposição.
        
        Args:
            proposicao: Tupla com dados da proposição
            
        Returns:
            Texto completo da proposição
        """
        prop_id = proposicao[0]
        api_id = proposicao[1]
        tipo = proposicao[2]
        numero = proposicao[3]
        ano = proposicao[4]
        ementa = proposicao[5]
        gcs_url = proposicao[6]
        link_inteiro_teor = proposicao[7]
        
        # Tentar obter do GCS primeiro (texto completo extraído do PDF)
        if self.gcs and self.gcs.is_available():
            # Path correto para textos completos baixados pelo novo pipeline
            texto_path = f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto-completo.txt"
            
            try:
                data = self.gcs.download_text(texto_path, compressed=False)
                if data and len(data.strip()) > 100:
                    logger.info(f"✅ Texto completo obtido do GCS: {tipo} {api_id}")
                    return data
            except Exception as e:
                logger.debug(f"Texto não encontrado em {texto_path}: {e}")
            
            # Tentar paths alternativos (legado)
            possible_paths = [
                f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}-texto.html",
                f"proposicoes/{ano}/{tipo}/documento/{tipo}-{api_id}-texto.html",
                f"proposicoes/{ano}/{tipo}/texto-completo/{tipo}-{api_id}.json"
            ]
            
            for path in possible_paths:
                try:
                    data = self.gcs.download_text(path, compressed=False)
                    if data and len(data.strip()) > 100:
                        logger.info(f"✅ Texto encontrado no GCS (legado): {path}")
                        return data
                except:
                    continue
        
        # Se não encontrar no GCS, usar link ou ementa
        if link_inteiro_teor:
            return f"Texto completo disponível em: {link_inteiro_teor}"
        
        # Último recurso: usar ementa
        ementa = proposicao[5]
        return f"Ementa: {ementa}"
    
    def salvar_analise_proposicao(self, proposicao_id: int, dados_analise: Dict) -> bool:
        """
        Salva os resultados da análise no banco.
        
        Args:
            proposicao_id: ID da proposição
            dados_analise: Dicionário com resultados da análise
            
        Returns:
            True se salvou com sucesso
        """
        try:
            session = get_db_session()
            
            # Verificar se já existe análise
            analise_existente = session.query(AnaliseProposicao).filter(
                AnaliseProposicao.proposicao_id == proposicao_id
            ).first()
            
            if analise_existente:
                # Atualizar análise existente
                for key, value in dados_analise.items():
                    if hasattr(analise_existente, key):
                        setattr(analise_existente, key, value)
                
                analise_existente.data_analise = datetime.utcnow()
                analise_existente.versao_analise = self.versao
                
                logger.info(f"Atualizando análise existente para proposição {proposicao_id}")
            else:
                # Criar nova análise
                dados_analise['proposicao_id'] = proposicao_id
                dados_analise['versao_analise'] = self.versao
                
                nova_analise = AnaliseProposicao(**dados_analise)
                session.add(nova_analise)
                
                logger.info(f"Criando nova análise para proposição {proposicao_id}")
            
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar análise da proposição {proposicao_id}: {e}")
            return False
    
    def salvar_log_processamento(self, tipo: str, proposicao_id: int, 
                             status: str, mensagem: str = None,
                             dados_entrada: Dict = None, dados_saida: Dict = None,
                             duracao: int = None) -> bool:
        """
        Salva log detalhado do processamento.
        
        Args:
            tipo: Tipo de processo ('resumo', 'filtro', 'par')
            proposicao_id: ID da proposição
            status: Status do processo
            mensagem: Mensagem de erro ou sucesso
            dados_entrada: Dados de entrada
            dados_saida: Dados de saída
            duracao: Duração em segundos
            
        Returns:
            True se salvou com sucesso
        """
        if not self.config.get('salvar_logs', True):
            return True
            
        try:
            session = get_db_session()
            
            log = LogProcessamento(
                tipo_processo=tipo,
                proposicao_id=proposicao_id,
                status=status,
                mensagem=mensagem,
                dados_entrada=dados_entrada,
                dados_saida=dados_saida,
                data_fim=datetime.utcnow(),
                duracao_segundos=duracao
            )
            
            session.add(log)
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar log: {e}")
            return False
    
    def analisar_proposicao(self, proposicao: Tuple) -> Optional[Dict]:
        """
        Analisa uma proposição completa usando os agents.
        
        Args:
            proposicao: Tupla com dados da proposição
            
        Returns:
            Dicionário com resultados da análise ou None
        """
        prop_id = proposicao[0]
        api_id = proposicao[1]
        tipo = proposicao[2]
        numero = proposicao[3]
        ano = proposicao[4]
        ementa = proposicao[5]
        
        logger.info(f"Analisando {tipo} {numero}/{ano} (ID: {prop_id})")
        
        # Obter texto completo
        texto_completo = self.obter_texto_proposicao(proposicao)
        
        if not texto_completo or len(texto_completo.strip()) < 200:
            logger.warning(f"Texto muito curto ou vazio para proposição {prop_id}")
            return None
        
        dados_analise = {
            'proposicao_id': prop_id,
            'resumo_texto': None,
            'data_resumo': None,
            'is_trivial': None,
            'data_filtro_trivial': None,
            'par_score': None,
            'escopo_impacto': None,
            'alinhamento_ods': None,
            'inovacao_eficiencia': None,
            'sustentabilidade_fiscal': None,
            'penalidade_oneracao': None,
            'ods_identificados': None,
            'resumo_analise': None
        }
        
        try:
            # Passo 1: Summarizer Agent
            inicio_resumo = datetime.utcnow()
            resumo = summarize_proposal_text(texto_completo, prop_id)
            duracao_resumo = (datetime.utcnow() - inicio_resumo).total_seconds()
            
            if resumo:
                dados_analise['resumo_texto'] = resumo
                dados_analise['data_resumo'] = datetime.utcnow()
                logger.info(f"Resumo gerado: {len(resumo)} caracteres")
                
                self.salvar_log_processamento(
                    'resumo', prop_id, 'sucesso', 
                    dados_entrada={'texto_length': len(texto_completo)},
                    dados_saida={'resumo_length': len(resumo)},
                    duracao=int(duracao_resumo)
                )
            else:
                logger.error(f"Falha no resumo da proposição {prop_id}")
                self.salvar_log_processamento('resumo', prop_id, 'erro', 'Falha no resumo')
                return None
            
            # Passo 2: Trivial Filter Agent
            inicio_filtro = datetime.utcnow()
            is_trivial = is_summary_trivial(resumo, prop_id)
            duracao_filtro = (datetime.utcnow() - inicio_filtro).total_seconds()
            
            dados_analise['is_trivial'] = is_trivial
            dados_analise['data_filtro_trivial'] = datetime.utcnow()
            
            resultado_filtro = "TRIVIAL" if is_trivial else "RELEVANTE"
            logger.info(f"Resultado do filtro: {resultado_filtro}")
            
            self.salvar_log_processamento(
                'filtro', prop_id, 'sucesso',
                dados_entrada={'resumo_length': len(resumo)},
                dados_saida={'is_trivial': is_trivial},
                duracao=int(duracao_filtro)
            )
            
            # Passo 3: PAR Analyzer (só se não for trivial)
            if not is_trivial:
                inicio_par = datetime.utcnow()
                par_analysis = analyze_proposal_par(resumo, prop_id)
                duracao_par = (datetime.utcnow() - inicio_par).total_seconds()
                
                if par_analysis:
                    try:
                        par_data = json.loads(par_analysis)
                        
                        # Extrair dados do PAR
                        dados_analise['par_score'] = par_data.get('par_final')
                        dados_analise['escopo_impacto'] = par_data.get('escopo_impacto')
                        dados_analise['alinhamento_ods'] = par_data.get('alinhamento_ods')
                        dados_analise['inovacao_eficiencia'] = par_data.get('inovacao_eficiencia')
                        dados_analise['sustentabilidade_fiscal'] = par_data.get('sustentabilidade_fiscal')
                        dados_analise['penalidade_oneracao'] = par_data.get('penalidade_oneracao')
                        dados_analise['ods_identificados'] = par_data.get('ods_identificados', [])
                        dados_analise['resumo_analise'] = par_data.get('resumo_analise')
                        
                        logger.info(f"PAR Final: {dados_analise['par_score']}")
                        
                        self.salvar_log_processamento(
                            'par', prop_id, 'sucesso',
                            dados_entrada={'resumo_length': len(resumo)},
                            dados_saida={'par_score': dados_analise['par_score']},
                            duracao=int(duracao_par)
                        )
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Erro ao decodificar JSON do PAR: {e}")
                        self.salvar_log_processamento('par', prop_id, 'erro', f'JSON decode error: {e}')
                        return None
                else:
                    logger.error(f"Falha na análise PAR da proposição {prop_id}")
                    self.salvar_log_processamento('par', prop_id, 'erro', 'Falha na análise PAR')
                    return None
            else:
                logger.info("Proposição trivial - análise PAR não necessária")
            
            return dados_analise
            
        except Exception as e:
            logger.error(f"Erro inesperado na análise da proposição {prop_id}: {e}")
            self.salvar_log_processamento('analise', prop_id, 'erro', str(e))
            return None
    
    def executar_pipeline(self) -> Dict:
        """
        Executa o pipeline completo de análise.
        
        Returns:
            Dicionário com estatísticas da execução
        """
        logger.info("Iniciando pipeline de análise com agents")
        
        # Verificar se análise está habilitada
        if not self.config.get('habilitado', True):
            logger.warning("Análise com agents está desabilitada na configuração")
            return {'status': 'desabilitado', 'mensagem': 'Análise desabilitada'}
        
        # Buscar proposições para analisar
        proposicoes = self.buscar_proposicoes_para_analisar()
        
        if not proposicoes:
            logger.info("Nenhuma proposição encontrada para análise")
            return {'status': 'sem_dados', 'mensagem': 'Nenhuma proposição para analisar'}
        
        # Estatísticas
        stats = {
            'total': len(proposicoes),
            'processadas': 0,
            'erros': 0,
            'relevantes': 0,
            'triviais': 0,
            'com_par': 0,
            'inicio': datetime.utcnow(),
            'proposicoes': []
        }
        
        # Processar cada proposição
        for i, proposicao in enumerate(proposicoes, 1):
            logger.info(f"Processando {i}/{len(proposicoes)}")
            
            try:
                # Analisar proposição
                resultado = self.analisar_proposicao(proposicao)
                
                if resultado:
                    # Salvar análise no banco
                    if self.salvar_analise_proposicao(proposicao[0], resultado):
                        stats['processadas'] += 1
                        
                        # Atualizar estatísticas
                        if not resultado['is_trivial']:
                            stats['relevantes'] += 1
                            if resultado['par_score']:
                                stats['com_par'] += 1
                        else:
                            stats['triviais'] += 1
                        
                        # Adicionar à lista de resultados
                        stats['proposicoes'].append({
                            'id': proposicao[0],
                            'tipo': proposicao[2],
                            'numero': proposicao[3],
                            'ano': proposicao[4],
                            'is_trivial': resultado['is_trivial'],
                            'par_score': resultado['par_score']
                        })
                        
                        logger.info(f"Análise concluída com sucesso: {proposicao[0]}")
                    else:
                        stats['erros'] += 1
                        logger.error(f"Erro ao salvar análise: {proposicao[0]}")
                else:
                    stats['erros'] += 1
                    logger.error(f"Falha na análise: {proposicao[0]}")
                
            except Exception as e:
                stats['erros'] += 1
                logger.error(f"Erro inesperado: {e}")
        
        # Finalizar estatísticas
        stats['fim'] = datetime.utcnow()
        stats['duracao'] = (stats['fim'] - stats['inicio']).total_seconds()
        stats['taxa_sucesso'] = (stats['processadas'] / stats['total']) * 100 if stats['total'] > 0 else 0
        
        # Log final
        logger.info("=" * 60)
        logger.info("PIPELINE DE ANÁLISE CONCLUÍDO")
        logger.info("=" * 60)
        logger.info(f"Total: {stats['total']}")
        logger.info(f"Processadas: {stats['processadas']}")
        logger.info(f"Erros: {stats['erros']}")
        logger.info(f"Taxa de sucesso: {stats['taxa_sucesso']:.1f}%")
        logger.info(f"Relevantes: {stats['relevantes']}")
        logger.info(f"Triviais: {stats['triviais']}")
        logger.info(f"Com PAR: {stats['com_par']}")
        logger.info(f"Duração: {stats['duracao']:.1f} segundos")
        
        return stats


def main():
    """
    Função principal para execução do pipeline.
    """
    print("🚀 PIPELINE DE ANÁLISE COM AGENTS KRITIKOS")
    print("=" * 60)
    
    # Criar e executar pipeline
    pipeline = PipelineAnaliseAgents()
    resultado = pipeline.executar_pipeline()
    
    # Exibir resultado final
    print(f"\n📊 RESULTADO FINAL:")
    print(f"   Status: {resultado.get('status', 'concluido')}")
    print(f"   Processadas: {resultado.get('processadas', 0)}")
    print(f"   Erros: {resultado.get('erros', 0)}")
    print(f"   Taxa de sucesso: {resultado.get('taxa_sucesso', 0):.1f}%")
    
    if resultado.get('relevantes', 0) > 0:
        print(f"   Relevantes: {resultado['relevantes']}")
        print(f"   Triviais: {resultado.get('triviais', 0)}")
        print(f"   Com PAR: {resultado.get('com_par', 0)}")
    
    print(f"\n🎯 Pipeline concluído!")
    
    return resultado


if __name__ == "__main__":
    main()
