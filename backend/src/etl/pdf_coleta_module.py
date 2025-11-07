#!/usr/bin/env python3
"""
Módulo especializado em coleta de PDFs de proposições legislativas

Implementa estratégias modulares para lidar com diferentes formatos de JSON:
- Tipo 1: JSON com URI que requer chamada XML adicional
- Tipo 2: JSON com urlInteiroTeor direto

Este módulo abstrai a complexidade da coleta e fornece uma interface unificada.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from datetime import datetime

from models.db_utils import get_db_session
from sqlalchemy import text
from utils.texto_utils import TextoProposicaoUtils
from utils.gcs_utils import get_gcs_manager

logger = logging.getLogger(__name__)


class PDFColetaStrategy(ABC):
    """Classe abstrata para estratégias de coleta de PDFs."""
    
    def __init__(self):
        self.texto_utils = TextoProposicaoUtils()
        self.gcs_manager = get_gcs_manager()
    
    @abstractmethod
    def pode_processar(self, dados_proposicao: Dict) -> bool:
        """Verifica se esta estratégia pode processar os dados."""
        pass
    
    @abstractmethod
    def obter_url_pdf(self, dados_proposicao: Dict) -> Optional[str]:
        """Obtém a URL do PDF usando a estratégia específica."""
        pass
    
    def processar_proposicao(self, dados_proposicao: Dict) -> Dict[str, Any]:
        """
        Processa uma proposição usando esta estratégia.
        
        Args:
            dados_proposicao: Dicionário com dados da proposição
            
        Returns:
            Dicionário com resultado do processamento
        """
        resultado = {
            'proposicao_id': dados_proposicao.get('id'),
            'sucesso': False,
            'url_pdf': None,
            'texto_extraido': None,
            'gcs_url': None,
            'erro': None,
            'estrategia': self.__class__.__name__
        }
        
        try:
            # Obter URL do PDF
            url_pdf = self.obter_url_pdf(dados_proposicao)
            if not url_pdf:
                resultado['erro'] = 'Não foi possível obter URL do PDF'
                return resultado
            
            resultado['url_pdf'] = url_pdf
            
            # Baixar e extrair texto
            texto = self.texto_utils.obter_texto_completo(url_pdf, str(dados_proposicao.get('id')))
            if not texto:
                resultado['erro'] = 'Não foi possível extrair texto do PDF'
                return resultado
            
            resultado['texto_extraido'] = texto
            
            # Salvar no GCS
            gcs_url = self._salvar_no_gcs(dados_proposicao, texto)
            if gcs_url:
                resultado['gcs_url'] = gcs_url
                resultado['sucesso'] = True
            else:
                resultado['erro'] = 'Falha ao salvar no GCS'
            
        except Exception as e:
            resultado['erro'] = str(e)
            logger.error(f"Erro na estratégia {self.__class__.__name__}: {e}")
        
        return resultado
    
    def _salvar_no_gcs(self, dados_proposicao: Dict, texto: str) -> Optional[str]:
        """
        Salva o texto no GCS.
        
        Args:
            dados_proposicao: Dados da proposição
            texto: Texto extraído
            
        Returns:
            URL no GCS ou None
        """
        if not self.gcs_manager or not self.gcs_manager.is_available():
            logger.warning("GCS não disponível")
            return None
        
        try:
            api_id = dados_proposicao.get('id')
            tipo = dados_proposicao.get('siglaTipo', 'PROP')
            ano = dados_proposicao.get('ano', datetime.now().year)
            
            # Path para salvar texto
            filename = f"{tipo}-{api_id}-texto-completo.txt"
            blob_path = f"proposicoes/{ano}/{tipo}/texto-completo/{filename}"
            
            # Salvar no GCS
            if self.gcs_manager.upload_text(texto, blob_path, compress=True):
                gcs_url = f"https://storage.googleapis.com/{self.gcs_manager.bucket_name}/{blob_path}"
                logger.info(f"✅ Texto salvo no GCS: {tipo} {api_id}")
                return gcs_url
            
        except Exception as e:
            logger.error(f"Erro ao salvar no GCS: {e}")
        
        return None


class PDFColetaDiretaStrategy(PDFColetaStrategy):
    """
    Estratégia para proposições que já têm urlInteiroTeor no JSON.
    
    Exemplo de JSON:
    {
        "proposicao": {
            "urlInteiroTeor": "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2926623"
        }
    }
    """
    
    def pode_processar(self, dados_proposicao: Dict) -> bool:
        """Verifica se tem urlInteiroTeor direto."""
        # Verificar no nível principal ou dentro de 'proposicao'
        url_direta = (
            dados_proposicao.get('urlInteiroTeor') or 
            dados_proposicao.get('proposicao', {}).get('urlInteiroTeor')
        )
        return url_direta is not None and len(url_direta.strip()) > 0
    
    def obter_url_pdf(self, dados_proposicao: Dict) -> Optional[str]:
        """Retorna a URL direta do inteiro teor."""
        return (
            dados_proposicao.get('urlInteiroTeor') or 
            dados_proposicao.get('proposicao', {}).get('urlInteiroTeor')
        )


class PDFColetaViaXMLStrategy(PDFColetaStrategy):
    """
    Estratégia para proposições que precisam de chamada XML adicional.
    
    Exemplo de JSON:
    {
        "proposicao": {
            "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482129"
        }
    }
    """
    
    def pode_processar(self, dados_proposicao: Dict) -> bool:
        """Verifica se tem URI para chamada XML."""
        # Verificar no nível principal ou dentro de 'proposicao'
        uri = (
            dados_proposicao.get('uri') or 
            dados_proposicao.get('proposicao', {}).get('uri')
        )
        return uri is not None and len(uri.strip()) > 0
    
    def obter_url_pdf(self, dados_proposicao: Dict) -> Optional[str]:
        """Obtém URL fazendo chamada XML."""
        uri = (
            dados_proposicao.get('uri') or 
            dados_proposicao.get('proposicao', {}).get('uri')
        )
        
        if not uri:
            return None
        
        # Usar o utilitário existente para obter URL via XML
        return self.texto_utils.obter_url_inteiro_teor(uri)


class PDFColetaManager:
    """
    Gerenciador principal para coleta de PDFs de proposições.
    
    Coordena as diferentes estratégias e fornece uma interface unificada.
    """
    
    def __init__(self):
        self.estrategias = [
            PDFColetaDiretaStrategy(),  # Prioridade: mais rápida
            PDFColetaViaXMLStrategy()    # Fallback: mais lenta
        ]
        self.texto_utils = TextoProposicaoUtils()
        
        logger.info(f"PDFColetaManager inicializado com {len(self.estrategias)} estratégias")
    
    def detectar_tipo_proposicao(self, dados_proposicao: Dict) -> Optional[str]:
        """
        Detecta o tipo de proposição baseado na estrutura do JSON.
        
        Args:
            dados_proposicao: Dicionário com dados da proposição
            
        Returns:
            String com o tipo detectado ou None
        """
        for estrategia in self.estrategias:
            if estrategia.pode_processar(dados_proposicao):
                return estrategia.__class__.__name__
        
        return None
    
    def coletar_pdf_proposicao(self, dados_proposicao: Dict) -> Dict[str, Any]:
        """
        Coleta PDF de uma proposição usando a estratégia adequada.
        
        Args:
            dados_proposicao: Dicionário com dados da proposição
            
        Returns:
            Dicionário com resultado da coleta
        """
        # Tentar cada estratégia em ordem de prioridade
        for estrategia in self.estrategias:
            if estrategia.pode_processar(dados_proposicao):
                logger.debug(f"Usando estratégia: {estrategia.__class__.__name__}")
                return estrategia.processar_proposicao(dados_proposicao)
        
        # Nenhuma estratégia funcionou
        return {
            'proposicao_id': dados_proposicao.get('id'),
            'sucesso': False,
            'url_pdf': None,
            'texto_extraido': None,
            'gcs_url': None,
            'erro': 'Nenhuma estratégia disponível para este formato de JSON',
            'estrategia': 'Nenhuma'
        }
    
    def coletar_lote_proposicoes(self, lista_proposicoes: List[Dict], 
                                delay_segundos: float = 2.0) -> Dict[str, Any]:
        """
        Coleta PDFs para uma lista de proposições.
        
        Args:
            lista_proposicoes: Lista de dicionários com dados das proposições
            delay_segundos: Delay entre requisições para evitar rate limiting
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        logger.info(f"🚀 Iniciando coleta em lote: {len(lista_proposicoes)} proposições")
        
        estatisticas = {
            'total': len(lista_proposicoes),
            'sucesso': 0,
            'falha': 0,
            'estrategias_usadas': {},
            'erros': [],
            'resultados': []
        }
        
        for i, dados_prop in enumerate(lista_proposicoes, 1):
            prop_id = dados_prop.get('id', 'desconhecido')
            logger.info(f"📄 Processando {i}/{estatisticas['total']}: ID {prop_id}")
            
            try:
                resultado = self.coletar_pdf_proposicao(dados_prop)
                estatisticas['resultados'].append(resultado)
                
                # Atualizar estatísticas
                if resultado['sucesso']:
                    estatisticas['sucesso'] += 1
                    logger.info(f"✅ Sucesso: {prop_id} ({resultado['estrategia']})")
                else:
                    estatisticas['falha'] += 1
                    erro_msg = f"Falha {prop_id}: {resultado['erro']}"
                    estatisticas['erros'].append(erro_msg)
                    logger.error(f"❌ {erro_msg}")
                
                # Contar estratégias usadas
                estrategia = resultado['estrategia']
                estatisticas['estrategias_usadas'][estrategia] = \
                    estatisticas['estrategias_usadas'].get(estrategia, 0) + 1
                
                # Rate limiting
                if delay_segundos > 0:
                    time.sleep(delay_segundos)
                    
            except Exception as e:
                estatisticas['falha'] += 1
                erro_msg = f"Erro crítico {prop_id}: {str(e)}"
                estatisticas['erros'].append(erro_msg)
                logger.error(f"❌ {erro_msg}", exc_info=True)
        
        # Calcular taxa de sucesso
        estatisticas['taxa_sucesso'] = (
            (estatisticas['sucesso'] / estatisticas['total'] * 100) 
            if estatisticas['total'] > 0 else 0
        )
        
        logger.info(f"📊 Coleta concluída: {estatisticas['sucesso']}/{estatisticas['total']} "
                   f"({estatisticas['taxa_sucesso']:.1f}%)")
        
        return estatisticas
    
    def buscar_proposicoes_sem_texto(self, limite: int = 50, ano_minimo: int = 2023) -> List[Dict]:
        """
        Busca proposições que não têm texto no GCS.
        
        Args:
            limite: Número máximo de proposições
            ano_minimo: Ano mínimo para considerar
            
        Returns:
            Lista de dicionários com dados das proposições
        """
        logger.info(f"🔍 Buscando proposições sem texto (limite: {limite}, ano >= {ano_minimo})")
        
        session = get_db_session()
        
        try:
            query = text("""
                SELECT id, api_camara_id, tipo, numero, ano, ementa, 
                       COALESCE(gcs_url, '') as gcs_url
                FROM proposicoes 
                WHERE ano >= :ano_minimo
                AND (gcs_url IS NULL OR gcs_url = '')
                ORDER BY data_apresentacao DESC
                LIMIT :limite
            """)
            
            result = session.execute(query, {
                'ano_minimo': ano_minimo,
                'limite': limite
            }).fetchall()
            
            proposicoes = []
            for row in result:
                # Construir dicionário com todos os campos necessários
                prop_dict = {
                    'id': row[0],
                    'api_camara_id': row[1],
                    'siglaTipo': row[2],
                    'tipo': row[2],  # Para compatibilidade
                    'numero': row[3],
                    'ano': row[4],
                    'ementa': row[5] or '',
                    'gcs_url': row[6] or ''
                }
                
                # Não adicionar urlInteiroTeor pois não existe na tabela
                # A estratégia irá buscar via XML quando necessário
                
                # Adicionar URI para Tipo 1 (construída a partir do ID)
                if row[1]:  # api_camara_id
                    prop_dict['uri'] = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{row[1]}"
                
                proposicoes.append(prop_dict)
            
            logger.info(f"📊 Encontradas {len(proposicoes)} proposições sem texto")
            return proposicoes
            
        finally:
            session.close()
    
    def processar_lote_automatico(self, limite: int = 50, delay_segundos: float = 2.0) -> Dict[str, Any]:
        """
        Processa automaticamente um lote de proposições sem texto.
        
        Args:
            limite: Número máximo de proposições a processar
            delay_segundos: Delay entre requisições
            
        Returns:
            Dicionário com estatísticas do processamento
        """
        # Buscar proposições sem texto
        props_sem_texto = self.buscar_proposicoes_sem_texto(limite=limite)
        
        if not props_sem_texto:
            logger.info("✅ Todas as proposições já têm texto!")
            return {
                'total': 0,
                'sucesso': 0,
                'falha': 0,
                'taxa_sucesso': 100.0,
                'mensagem': 'Nenhuma proposição sem texto encontrada'
            }
        
        # Processar lote
        return self.coletar_lote_proposicoes(props_sem_texto, delay_segundos)
    
    def atualizar_gcs_url_banco(self, resultado_coleta: Dict[str, Any]) -> bool:
        """
        Atualiza o campo gcs_url no banco de dados após coleta bem-sucedida.
        
        Args:
            resultado_coleta: Resultado da coleta com gcs_url
            
        Returns:
            True se sucesso, False caso contrário
        """
        if not resultado_coleta.get('sucesso') or not resultado_coleta.get('gcs_url'):
            return False
        
        prop_id = resultado_coleta.get('proposicao_id')
        gcs_url = resultado_coleta.get('gcs_url')
        
        if not prop_id or not gcs_url:
            return False
        
        session = get_db_session()
        
        try:
            session.execute(text("""
                UPDATE proposicoes 
                SET gcs_url = :gcs_url
                WHERE id = :prop_id
            """), {
                'gcs_url': gcs_url,
                'prop_id': prop_id
            })
            session.commit()
            
            logger.debug(f"🔄 GCS URL atualizado no banco: {prop_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro ao atualizar GCS URL {prop_id}: {e}")
            return False
        finally:
            session.close()


def main():
    """Função principal para testes."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        manager = PDFColetaManager()
        
        # Teste com uma proposição de cada tipo
        testes = [
            {
                'id': 2520670,
                'siglaTipo': 'PLP',
                'urlInteiroTeor': 'https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2926623'  # Tipo 2
            },
            {
                'id': 2482129,
                'siglaTipo': 'PLP',
                'uri': 'https://dadosabertos.camara.leg.br/api/v2/proposicoes/2482129'  # Tipo 1
            }
        ]
        
        print("🧪 Testando detecção de tipos:")
        for teste in testes:
            tipo = manager.detectar_tipo_proposicao(teste)
            print(f"   ID {teste['id']}: {tipo}")
        
        print("\n🧪 Testando coleta (limitado a 1 para teste):")
        stats = manager.coletar_lote_proposicoes(testes[:1], delay_segundos=1.0)
        print(f"📊 Estatísticas: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}", exc_info=True)


if __name__ == "__main__":
    main()
