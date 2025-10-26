#!/usr/bin/env python3
"""
Coletor de Votações da Câmara dos Deputados - VERSÃO CORRIGIDA
Responsável por coletar TODAS as votações do período usando /votacoes diretamente
focando no período do hackathon (07/2025+)
Refatorado para usar ETL Utils - elimina redundâncias e padroniza operações
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.database import get_db
from models.proposicao_models import Votacao, VotoDeputado, Proposicao
from models.politico_models import Deputado
from models.emenda_models import VotacaoEmenda, EmendaParlamentar
from config import get_config, get_coleta_config, get_data_inicio_coleta, deve_respeitar_data_inicio, coleta_habilitada
from .etl_utils import ETLBase, DateParser, ProgressLogger, DatabaseManager

class ColetorVotacoes(ETLBase):
    """
    Coletor especializado em dados de votações da Câmara dos Deputados
    Abordagem CORRIGIDA: usa /votacoes diretamente para buscar TODAS as votações
    Herda de ETLBase para usar funcionalidades comuns
    """
    
    def __init__(self):
        """Inicializa o coletor de votações usando ETLBase"""
        super().__init__('votacoes')
        
        # Adicionar atributo para compatibilidade
        self.votacoes_config = self.specific_config
        
        # Configurações de coleta centralizadas
        self.coleta_config = get_coleta_config()
        self.data_inicio = get_data_inicio_coleta()
        
        print("🗳️ Coletor de Votações inicializado (VERSÃO CORRIGIDA)")
        print(f"📅 Período: {self.specific_config['data_inicio']} a {self.specific_config['data_fim']}")
        print(f"🎯 Limite: {self.specific_config['limite_total']} votações")
        print(f"🔧 Respeitar data início: {deve_respeitar_data_inicio('votacoes')}")
        print("🔧 ABORDAGEM: /votacoes diretamente (TODOS os órgãos)")
    
    
    def buscar_votacoes_periodo(self, db: Session) -> Dict[str, int]:
        """
        Busca TODAS as votações no período do hackathon usando /votacoes
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Dict: Estatísticas da coleta
        """
        if not self.votacoes_config.get('habilitado', False):
            print("⏸️ Coleta de votações desabilitada nas configurações")
            return {'status': 'desabilitado'}
        
        print("\n🗳️ INICIANDO COLETA DE VOTAÇÕES - ABORDAGEM CORRIGIDA")
        print("=" * 60)
        print("🔧 Usando /votacoes diretamente para buscar TODAS as votações")
        print("📂 Incluindo Plenário + Todas as Comissões")
        
        resultados = {
            'votacoes_encontradas': 0,
            'votacoes_salvas': 0,
            'votos_deputados_salvos': 0,
            'votacoes_com_proposicao': 0,
            'orgaos_diferentes': set(),
            'erros': 0
        }
        
        # Buscar votações usando a abordagem correta
        data_inicio = self.specific_config['data_inicio']
        data_fim = self.specific_config['data_fim']
        
        # Ajustar data_fim para a data atual se estiver no futuro
        from datetime import datetime
        data_atual = datetime.now().strftime('%Y-%m-%d')
        if data_fim > data_atual:
            data_fim = data_atual
            print(f"📅 Data fim ajustada para: {data_fim}")
        
        print(f"\n📅 Buscando votações de {data_inicio} a {data_fim}")
        
        # Buscar votações direto do endpoint /votacoes
        votacoes_data = self._buscar_votacoes_api(data_inicio, data_fim, db)
        
        if votacoes_data:
            print(f"📊 Encontradas {len(votacoes_data)} votações no período")
            resultados['votacoes_encontradas'] = len(votacoes_data)
            
            # Processar cada votação encontrada
            for i, votacao_data in enumerate(votacoes_data):
                try:
                    print(f"\n🗳️ Processando votação {i+1}/{len(votacoes_data)}: {votacao_data.get('id', 'N/A')}")
                    
                    # Salvar votação principal
                    resultado_salvamento = self._salvar_votacao_principal(votacao_data, db)
                    
                    if resultado_salvamento:
                        resultados['votacoes_salvas'] += 1
                        resultados['votos_deputados_salvos'] += resultado_salvamento.get('votos_salvos', 0)
                        
                        if resultado_salvamento.get('tem_proposicao'):
                            resultados['votacoes_com_proposicao'] += 1
                        
                        # Coletar órgãos diferentes
                        orgao = votacao_data.get('siglaOrgao', 'N/A')
                        resultados['orgaos_diferentes'].add(orgao)
                    
                    # Progresso
                    if (i + 1) % 50 == 0 or i == len(votacoes_data) - 1:
                        progresso = ((i + 1) / len(votacoes_data)) * 100
                        print(f"📊 Progresso: {progresso:.1f}% - {resultados['votacoes_salvas']} votações salvas")
                    
                    # Verificar limite
                    if resultados['votacoes_salvas'] >= self.votacoes_config['limite_total']:
                        print(f"🎯 Limite de votações atingido: {self.votacoes_config['limite_total']}")
                        break
                        
                except Exception as e:
                    print(f"❌ Erro ao processar votação {votacao_data.get('id', 'N/A')}: {e}")
                    resultados['erros'] += 1
                    continue
        
        # Converter set para lista para JSON serialização
        resultados['orgaos_diferentes'] = list(resultados['orgaos_diferentes'])
        
        return resultados
    
    def _buscar_votacoes_api(self, data_inicio: str, data_fim: str, db: Session) -> List[Dict]:
        """
        Busca votações diretamente do endpoint /votacoes com paginação
        
        Args:
            data_inicio: Data inicial no formato AAAA-MM-DD
            data_fim: Data final no formato AAAA-MM-DD
            db: Sessão do banco de dados
            
        Returns:
            List[Dict]: Lista de votações encontradas
        """
        print(f"🔍 Buscando votações via /votacoes")
        
        todas_votacoes = []
        pagina = 1
        max_paginas = 100  # Limite de segurança
        
        while pagina <= max_paginas:
            try:
                print(f"   📄 Buscando página {pagina}...")
                
                # Construir URL com parâmetros
                url = f"{self.api_config['base_url']}/votacoes"
                params = {
                    'dataInicio': data_inicio,
                    'dataFim': data_fim,
                    'pagina': pagina,
                    'itens': 100,  # Máximo permitido pela API
                    'ordem': 'DESC',
                    'ordenarPor': 'dataHoraRegistro'
                }
                
                # Fazer requisição com timeout maior
                data = self.make_request(url, params, use_cache=False, timeout=30)
                
                if not data:
                    print(f"   ⚠️ Sem resposta da API na página {pagina}")
                    break
                
                itens = data.get('dados', [])
                if not itens:
                    print(f"   📄 Página {pagina} vazia - fim dos resultados")
                    break
                
                print(f"   📊 Página {pagina}: +{len(itens)} votações")
                todas_votacoes.extend(itens)
                
                # Verificar se há próxima página
                links = data.get('links', [])
                proxima_pagina = any(link.get('rel') == 'next' for link in links)
                
                if not proxima_pagina:
                    print(f"   ✅ Última página alcançada")
                    break
                
                pagina += 1
                
                # Verificar limite total
                if len(todas_votacoes) >= self.votacoes_config['limite_total'] * 1.5:  # Buffer
                    print(f"   🎯 Limite de busca atingido: {len(todas_votacoes)} votações")
                    todas_votacoes = todas_votacoes[:self.votacoes_config['limite_total']]
                    break
                    
            except Exception as e:
                print(f"   ❌ Erro na página {pagina}: {e}")
                break
        
        print(f"✅ Busca concluída: {len(todas_votacoes)} votações encontradas")
        return todas_votacoes
    
    def _salvar_votacao_principal(self, votacao_data: Dict, db: Session) -> Optional[Dict]:
        """
        Salva votação principal no banco de dados
        
        Args:
            votacao_data: Dados da votação da API
            db: Sessão do banco
            
        Returns:
            Dict: Resultado do salvamento ou None se erro
        """
        try:
            # Verificar se já existe
            votacao_existente = db.query(Votacao).filter(
                Votacao.api_camara_id == votacao_data['id']
            ).first()
            
            if votacao_existente:
                print(f"   ⏭️ Votação {votacao_data['id']} já existe")
                return None
            
            # Extrair dados da votação
            votacao_id = votacao_data['id']
            data_votacao = DateParser.parse_datetime(votacao_data.get('dataHoraRegistro'))
            descricao = votacao_data.get('descricao', '')
            sigla_orgao = votacao_data.get('siglaOrgao', '')
            uri_orgao = votacao_data.get('uriOrgao', '')
            uri_evento = votacao_data.get('uriEvento', '')
            
            # Tentar associar a proposição se existir
            proposicao_id = None
            proposicao_objeto = votacao_data.get('proposicaoObjeto')
            uri_proposicao = votacao_data.get('uriProposicaoObjeto')
            
            if uri_proposicao:
                # Extrair ID da proposição da URI
                try:
                    proposicao_api_id = uri_proposicao.split('/')[-1]
                    proposicao = db.query(Proposicao).filter(
                        Proposicao.api_camara_id == proposicao_api_id
                    ).first()
                    
                    if proposicao:
                        proposicao_id = proposicao.id
                        print(f"   🔗 Associada à proposição: {proposicao.tipo} {proposicao.numero}/{proposicao.ano}")
                except:
                    pass
            
            # Criar votação
            votacao = Votacao(
                api_camara_id=votacao_id,
                proposicao_id=proposicao_id,
                data_votacao=data_votacao,
                objeto_votacao=descricao,
                tipo_votacao=votacao_data.get('aprovacao', 0),  # Aprovacao como tipo
                resultado=votacao_data.get('descricao', ''),  # Descricao como resultado
                votos_sim=0,  # Será preenchido depois
                votos_nao=0,   # Será preenchido depois
                abstencoes=0,  # Será preenchido depois
                ausencias=0,   # Será preenchido depois
                quorum_minimo=None
            )
            
            db.add(votacao)
            db.flush()  # Para obter o ID
            
            # Buscar detalhes completos da votação
            detalhes_votacao = self._buscar_detalhes_votacao(votacao_id)
            if detalhes_votacao:
                self._atualizar_detalhes_votacao(votacao, detalhes_votacao)
            
            # Buscar e salvar votos dos deputados
            votos_salvos = 0
            if self.votacoes_config.get('buscar_votos_deputados', True):
                votos_salvos = self._salvar_votos_deputados(votacao, db)
            
            db.commit()
            
            print(f"   ✅ Votação {votacao_id} salva:")
            print(f"      📋 Órgão: {sigla_orgao}")
            print(f"      📄 Descrição: {descricao[:50]}...")
            print(f"      🗳️ Votos: {votos_salvos}")
            if proposicao_id:
                print(f"      🔗 Proposição associada")
            
            return {
                'votacao_id': votacao.id,
                'votos_salvos': votos_salvos,
                'tem_proposicao': proposicao_id is not None
            }
            
        except Exception as e:
            print(f"   ❌ Erro ao salvar votação: {e}")
            db.rollback()
            return None
    
    def _buscar_detalhes_votacao(self, votacao_id: str) -> Optional[Dict]:
        """
        Busca detalhes completos de uma votação
        
        Args:
            votacao_id: ID da votação
            
        Returns:
            Dict: Detalhes da votação ou None
        """
        try:
            url = f"{self.api_config['base_url']}/votacoes/{votacao_id}"
            return self.make_request(url)
        except Exception as e:
            print(f"      ⚠️ Erro ao buscar detalhes: {e}")
            return None
    
    def _atualizar_detalhes_votacao(self, votacao: Votacao, detalhes: Dict):
        """
        Atualiza votação com detalhes completos
        
        Args:
            votacao: Objeto Votacao
            detalhes: Detalhes da API
        """
        try:
            dados = detalhes.get('dados', {})
            
            # Atualizar campos adicionais se disponíveis
            if 'votosSim' in dados:
                votacao.votos_sim = dados['votosSim']
            if 'votosNao' in dados:
                votacao.votos_nao = dados['votosNao']
            if 'votosAbstencao' in dados:
                votacao.abstencoes = dados['votosAbstencao']
            if 'votosAusentes' in dados:
                votacao.ausencias = dados['votosAusentes']
            
        except Exception as e:
            print(f"      ⚠️ Erro ao atualizar detalhes: {e}")
    
    def _salvar_votos_deputados(self, votacao: Votacao, db: Session) -> int:
        """
        Salva votos individuais dos deputados
        
        Args:
            votacao: Objeto Votacao
            db: Sessão do banco
            
        Returns:
            int: Número de votos salvos
        """
        try:
            # Buscar votos na API
            url = f"{self.api_config['base_url']}/votacoes/{votacao.api_camara_id}/votos"
            votos_data = self.make_request(url)
            
            if not votos_data or 'dados' not in votos_data:
                print(f"      📭 Sem votos individuais para esta votação")
                return 0
            
            votos_lista = votos_data['dados']
            if not votos_lista:
                print(f"      📭 Votação simbólica ou sem votos registrados")
                return 0
            
            votos_salvos = 0
            
            for voto_data in votos_lista:
                try:
                    # Encontrar deputado
                    deputado_info = voto_data.get('deputado_', {})
                    if not deputado_info:
                        continue
                    
                    deputado_api_id = deputado_info.get('id')
                    if not deputado_api_id:
                        continue
                    
                    deputado = db.query(Deputado).filter(
                        Deputado.api_camara_id == deputado_api_id
                    ).first()
                    
                    if not deputado:
                        continue  # Pular se deputado não encontrado
                    
                    # Verificar se voto já existe
                    voto_existente = db.query(VotoDeputado).filter(
                        and_(
                            VotoDeputado.votacao_id == votacao.id,
                            VotoDeputado.deputado_id == deputado.id
                        )
                    ).first()
                    
                    if voto_existente:
                        continue
                    
                    # Criar voto
                    voto = VotoDeputado(
                        votacao_id=votacao.id,
                        deputado_id=deputado.id,
                        voto=voto_data.get('tipoVoto', ''),
                        orientacao_partido='',  # Não disponível neste endpoint
                        seguiu_orientacao=None
                    )
                    
                    db.add(voto)
                    votos_salvos += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Erro ao salvar voto individual: {e}")
                    continue
            
            print(f"      🗳️ {votos_salvos} votos individuais salvos")
            return votos_salvos
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar votos de deputados: {e}")
            return 0
    
    def gerar_resumo_votacoes(self, db: Session):
        """
        Gera resumo estatístico das votações coletadas
        
        Args:
            db: Sessão do banco de dados
        """
        print("\n📊 RESUMO DAS VOTAÇÕES COLETADAS")
        print("=" * 50)
        
        # Contar votações de proposições
        votacoes_proposicoes = db.query(Votacao).count()
        votos_deputados = db.query(VotoDeputado).count()
        
        # Contar votações com proposição associada
        votacoes_com_proposicao = db.query(Votacao).filter(
            Votacao.proposicao_id.isnot(None)
        ).count()
        
        print(f"📋 Total de Votações: {votacoes_proposicoes:,}")
        print(f"🗳️ Votos de Deputados: {votos_deputados:,}")
        print(f"🔗 Com Proposição Associada: {votacoes_com_proposicao:,}")
        print(f"📊 Sem Proposição: {votacoes_proposicoes - votacoes_com_proposicao:,}")
        
        # Distribuição por resultado
        print(f"\n📈 Distribuição de Resultados:")
        
        if votacoes_proposicoes > 0:
            resultados = db.query(
                Votacao.resultado, 
                db.func.count(Votacao.id)
            ).group_by(Votacao.resultado).all()
            
            for resultado, count in sorted(resultados, key=lambda x: x[1], reverse=True):
                print(f"   📊 {resultado}: {count:,}")
        
        # Votações por órgão (se disponível)
        print(f"\n🏛️ Análise de Dados:")
        print(f"   💾 Média de votos por votação: {(votos_deputados / max(votacoes_proposicoes, 1)):.1f}")
        print(f"   🔗 Taxa de associação com proposições: {(votacoes_com_proposicao / max(votacoes_proposicoes, 1) * 100):.1f}%")

def main():
    """Função principal para testes"""
    print("🗳️ COLETOR DE VOTAÇÕES - VERSÃO CORRIGIDA")
    print("=" * 50)
    print("🔧 ABORDAGEM: /votacoes diretamente")
    
    coletor = ColetorVotacoes()
    db = next(get_db())
    
    try:
        resultados = coletor.buscar_votacoes_periodo(db)
        print(f"\n📋 RESULTADOS: {resultados}")
        
        coletor.gerar_resumo_votacoes(db)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
