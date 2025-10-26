#!/usr/bin/env python3
"""
Coletor de Votações Fallback - Arquivos JSON da Câmara dos Deputados
Implementação robusta usando arquivos completos como fallback quando API está instável
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
sys.path.append(str(Path(__file__).parent))
from config import get_config

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.base_models import Partido, BlocoPartidario
from models.proposicao_models import Votacao, VotoDeputado, VotacaoObjeto, VotacaoProposicao, OrientacaoBancada

# Importar utilitários
from utils.gcs_utils import get_gcs_manager

class ColetorVotacoesFallback:
    """
    Classe responsável por coletar votações usando arquivos JSON como fallback
    Implementa abordagem completa com todos os relacionamentos
    """

    def __init__(self):
        """Inicializa o coletor fallback"""
        self.base_url = "http://dadosabertos.camara.leg.br/arquivos"
        self.cache_dir = Path("cache/votacoes")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        print(f"✅ Coletor de votações (Fallback JSON) inicializado")
        print(f"   📁 Cache: {self.cache_dir}")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")

    def baixar_arquivo_json(self, ano: int, tipo_arquivo: str, formato: str = 'json') -> Optional[List]:
        """
        Baixa arquivo JSON de votações da Câmara
        
        Args:
            ano: Ano das votações
            tipo_arquivo: Tipo do arquivo (votacoes, votacoesVotos, etc.)
            formato: Formato do arquivo (json, csv, etc.)
            
        Returns:
            Lista com os dados ou None em caso de erro
        """
        try:
            import requests
            
            url = f"{self.base_url}/{tipo_arquivo}/{formato}/{tipo_arquivo}-{ano}.{formato}"
            arquivo_local = self.cache_dir / f"{tipo_arquivo}-{ano}.{formato}"
            
            print(f"   📥 Baixando {tipo_arquivo}-{ano}.{formato}...")
            
            # Verificar se já existe em cache
            if arquivo_local.exists():
                print(f"      📁 Usando arquivo em cache: {arquivo_local}")
                with open(arquivo_local, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    # Extrair lista de dados se for um dicionário
                    if isinstance(dados, dict) and 'dados' in dados:
                        return dados['dados']
                    elif isinstance(dados, list):
                        return dados
                    else:
                        return []
            
            # Baixar arquivo
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Salvar em cache
            dados = response.json()
            with open(arquivo_local, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            # Extrair lista de dados se for um dicionário
            if isinstance(dados, dict) and 'dados' in dados:
                dados_lista = dados['dados']
            else:
                dados_lista = dados if isinstance(dados, list) else []
            
            print(f"      ✅ Download concluído: {len(dados_lista)} registros")
            return dados_lista
            
        except Exception as e:
            print(f"      ❌ Erro no download: {e}")
            return None

    def processar_votacoes_principais(self, dados_json: List[Dict], db: Session) -> int:
        """
        Processa dados principais das votações
        
        Args:
            dados_json: Lista de votações do arquivo JSON
            db: Sessão do banco de dados
            
        Returns:
            Número de votações processadas
        """
        print(f"   📊 Processando votações principais...")
        
        votacoes_processadas = 0
        
        for votacao_data in dados_json:
            try:
                # Verificar se já existe
                existente = db.query(Votacao).filter(
                    Votacao.api_camara_id == votacao_data.get('id')
                ).first()
                
                if existente:
                    continue
                
                # Mapear data da votação
                data_votacao = None
                if 'data' in votacao_data:
                    data_str = votacao_data['data']
                    if 'T' in data_str:
                        data_votacao = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                    else:
                        data_votacao = datetime.strptime(data_str, '%Y-%m-%d')
                
                # Criar votação
                votacao = Votacao(
                    api_camara_id=votacao_data.get('id'),
                    data_votacao=data_votacao,
                    objeto_votacao=votacao_data.get('objetoVotacao', ''),
                    tipo_votacao=votacao_data.get('descricaoTipoVotacao', ''),
                    resultado=votacao_data.get('descricaoResultado', ''),
                    votos_sim=votacao_data.get('placar', {}).get('Sim', 0),
                    votos_nao=votacao_data.get('placar', {}).get('Não', 0),
                    abstencoes=votacao_data.get('placar', {}).get('Abstenção', 0),
                    ausencias=votacao_data.get('placar', {}).get('Obstrução', 0),
                    quorum_minimo=votacao_data.get('quorumMinimo'),
                    
                    # Novos campos dos arquivos JSON
                    sigla_orgao=votacao_data.get('siglaOrgao'),
                    uri_orgao=votacao_data.get('uriOrgao'),
                    data_hora_registro=datetime.fromisoformat(votacao_data['dataHoraRegistro'].replace('Z', '+00:00')) if 'dataHoraRegistro' in votacao_data else None,
                    descricao_tipo_votacao=votacao_data.get('descricaoTipoVotacao'),
                    descricao_resultado=votacao_data.get('descricaoResultado'),
                    aprovacao=votacao_data.get('aprovacao', False),
                    uri_votacao=votacao_data.get('uri')
                )
                
                db.add(votacao)
                db.flush()
                votacoes_processadas += 1
                
                if votacoes_processadas % 100 == 0:
                    print(f"      📊 Processadas {votacoes_processadas} votações...")
                    
            except Exception as e:
                print(f"      ❌ Erro ao processar votação {votacao_data.get('id')}: {e}")
                continue
        
        db.commit()
        print(f"   ✅ Votações principais processadas: {votacoes_processadas}")
        return votacoes_processadas

    def processar_votos_deputados(self, dados_json: List[Dict], db: Session) -> int:
        """
        Processa votos individuais dos deputados
        
        Args:
            dados_json: Lista de votos do arquivo JSON
            db: Sessão do banco de dados
            
        Returns:
            Número de votos processados
        """
        print(f"   👥 Processando votos de deputados...")
        
        votos_processados = 0
        
        for voto_data in dados_json:
            try:
                # Buscar votação e deputado
                votacao = db.query(Votacao).filter(
                    Votacao.api_camara_id == voto_data.get('idVotacao')
                ).first()
                
                if not votacao:
                    continue
                
                deputado = None
                if 'deputado' in voto_data and 'id' in voto_data['deputado']:
                    deputado = db.query(Deputado).filter(
                        Deputado.api_camara_id == voto_data['deputado']['id']
                    ).first()
                
                if not deputado:
                    continue
                
                # Verificar se voto já existe
                existente = db.query(VotoDeputado).filter(
                    VotoDeputado.votacao_id == votacao.id,
                    VotoDeputado.deputado_id == deputado.id
                ).first()
                
                if existente:
                    continue
                
                # Criar voto
                voto = VotoDeputado(
                    votacao_id=votacao.id,
                    deputado_id=deputado.id,
                    voto=voto_data.get('voto', ''),
                    orientacao_partido=voto_data.get('deputado', {}).get('siglaPartido'),
                    seguiu_orientacao=voto_data.get('seguiuOrientacao', False)
                )
                
                db.add(voto)
                votos_processados += 1
                
                if votos_processados % 500 == 0:
                    print(f"      👥 Processados {votos_processados} votos...")
                    
            except Exception as e:
                print(f"      ❌ Erro ao processar voto {voto_data.get('idVotacao')}: {e}")
                continue
        
        db.commit()
        print(f"   ✅ Votos de deputados processados: {votos_processados}")
        return votos_processados

    def processar_objetos_votacao(self, dados_json: List[Dict], db: Session) -> int:
        """
        Processa objetos das votações (proposições objeto)
        
        Args:
            dados_json: Lista de objetos do arquivo JSON
            db: Sessão do banco de dados
            
        Returns:
            Número de objetos processados
        """
        print(f"   📋 Processando objetos das votações...")
        
        objetos_processados = 0
        
        for objeto_data in dados_json:
            try:
                # Buscar votação e proposição
                votacao = db.query(Votacao).filter(
                    Votacao.api_camara_id == objeto_data.get('idVotacao')
                ).first()
                
                if not votacao:
                    continue
                
                proposicao = None
                if 'proposicao' in objeto_data and 'id' in objeto_data['proposicao']:
                    proposicao = db.query(models.proposicao_models.Proposicao).filter(
                        models.proposicao_models.Proposicao.api_camara_id == objeto_data['proposicao']['id']
                    ).first()
                
                if not proposicao:
                    continue
                
                # Verificar se objeto já existe
                existente = db.query(VotacaoObjeto).filter(
                    VotacaoObjeto.votacao_id == votacao.id,
                    VotacaoObjeto.proposicao_id == proposicao.id
                ).first()
                
                if existente:
                    continue
                
                # Criar objeto
                objeto = VotacaoObjeto(
                    votacao_id=votacao.id,
                    proposicao_id=proposicao.id,
                    descricao_efeito=objeto_data.get('descricaoEfeito', '')
                )
                
                db.add(objeto)
                objetos_processados += 1
                
                if objetos_processados % 100 == 0:
                    print(f"      📋 Processados {objetos_processados} objetos...")
                    
            except Exception as e:
                print(f"      ❌ Erro ao processar objeto {objeto_data.get('idVotacao')}: {e}")
                continue
        
        db.commit()
        print(f"   ✅ Objetos processados: {objetos_processados}")
        return objetos_processados

    def processar_proposicoes_afetadas(self, dados_json: List[Dict], db: Session) -> int:
        """
        Processa proposições afetadas pelas votações
        
        Args:
            dados_json: Lista de proposições do arquivo JSON
            db: Sessão do banco de dados
            
        Returns:
            Número de proposições processadas
        """
        print(f"   📄 Processando proposições afetadas...")
        
        proposicoes_processadas = 0
        
        for prop_data in dados_json:
            try:
                # Buscar votação e proposição
                votacao = db.query(Votacao).filter(
                    Votacao.api_camara_id == prop_data.get('idVotacao')
                ).first()
                
                if not votacao:
                    continue
                
                proposicao = None
                if 'proposicao' in prop_data and 'id' in prop_data['proposicao']:
                    proposicao = db.query(models.proposicao_models.Proposicao).filter(
                        models.proposicao_models.Proposicao.api_camara_id == prop_data['proposicao']['id']
                    ).first()
                
                if not proposicao:
                    continue
                
                # Verificar se relação já existe
                existente = db.query(VotacaoProposicao).filter(
                    VotacaoProposicao.votacao_id == votacao.id,
                    VotacaoProposicao.proposicao_id == proposicao.id
                ).first()
                
                if existente:
                    continue
                
                # Criar relação
                votacao_prop = VotacaoProposicao(
                    votacao_id=votacao.id,
                    proposicao_id=proposicao.id,
                    descricao_efeito=prop_data.get('descricaoEfeito', '')
                )
                
                db.add(votacao_prop)
                proposicoes_processadas += 1
                
                if proposicoes_processadas % 100 == 0:
                    print(f"      📄 Processadas {proposicoes_processadas} proposições...")
                    
            except Exception as e:
                print(f"      ❌ Erro ao processar proposição {prop_data.get('idVotacao')}: {e}")
                continue
        
        db.commit()
        print(f"   ✅ Proposições afetadas processadas: {proposicoes_processadas}")
        return proposicoes_processadas

    def processar_orientacoes_bancada(self, dados_json: List[Dict], db: Session) -> int:
        """
        Processa orientações de bancada
        
        Args:
            dados_json: Lista de orientações do arquivo JSON
            db: Sessão do banco de dados
            
        Returns:
            Número de orientações processadas
        """
        print(f"   🏛️ Processando orientações de bancada...")
        
        orientacoes_processadas = 0
        
        for orient_data in dados_json:
            try:
                # Buscar votação
                votacao = db.query(Votacao).filter(
                    Votacao.api_camara_id == orient_data.get('idVotacao')
                ).first()
                
                if not votacao:
                    continue
                
                # Buscar partido ou bloco
                partido = None
                bloco = None
                
                if 'partido' in orient_data and 'id' in orient_data['partido']:
                    partido = db.query(Partido).filter(
                        Partido.id == orient_data['partido']['id']
                    ).first()
                
                if 'bloco' in orient_data and 'id' in orient_data['bloco']:
                    bloco = db.query(BlocoPartidario).filter(
                        BlocoPartidario.id == orient_data['bloco']['id']
                    ).first()
                
                # Verificar se orientação já existe
                existente = db.query(OrientacaoBancada).filter(
                    OrientacaoBancada.votacao_id == votacao.id,
                    OrientacaoBancada.partido_id == (partido.id if partido else None),
                    OrientacaoBancada.bloco_id == (bloco.id if bloco else None),
                    OrientacaoBancada.tipo_bancada == orient_data.get('tipoBancada', '')
                ).first()
                
                if existente:
                    continue
                
                # Criar orientação
                orientacao = OrientacaoBancada(
                    votacao_id=votacao.id,
                    partido_id=partido.id if partido else None,
                    bloco_id=bloco.id if bloco else None,
                    orientacao=orient_data.get('orientacao', ''),
                    tipo_bancada=orient_data.get('tipoBancada', '')
                )
                
                db.add(orientacao)
                orientacoes_processadas += 1
                
                if orientacoes_processadas % 100 == 0:
                    print(f"      🏛️ Processadas {orientacoes_processadas} orientações...")
                    
            except Exception as e:
                print(f"      ❌ Erro ao processar orientação {orient_data.get('idVotacao')}: {e}")
                continue
        
        db.commit()
        print(f"   ✅ Orientações processadas: {orientacoes_processadas}")
        return orientacoes_processadas

    def coletar_votacoes_periodo(self, ano: int = 2024, limite: int = 10000) -> Dict[str, int]:
        """
        Coleta votações de um período usando arquivos JSON completos
        
        Args:
            ano: Ano das votações (default: 2024)
            limite: Limite de registros (default: 10000)
            
        Returns:
            Dicionário com resultados da coleta
        """
        print(f"\n🗳️ COLETANDO VOTAÇÕES - Fallback JSON")
        print("=" * 70)
        print(f"📅 Ano: {ano}")
        print(f"🎯 Limite: {limite} registros por arquivo")
        
        # Usar sessão do banco
        db = next(get_db())
        
        resultados = {
            'votacoes_principais': 0,
            'votos_deputados': 0,
            'objetos_votacao': 0,
            'proposicoes_afetadas': 0,
            'orientacoes_bancada': 0,
            'erros': 0
        }
        
        try:
            # Baixar e processar cada tipo de arquivo
            arquivos = [
                ('votacoes', self.processar_votacoes_principais),
                ('votacoesVotos', self.processar_votos_deputados),
                ('votacoesObjetos', self.processar_objetos_votacao),
                ('votacoesProposicoes', self.processar_proposicoes_afetadas),
                ('votacoesOrientacoes', self.processar_orientacoes_bancada)
            ]
            
            for tipo_arquivo, processador in arquivos:
                print(f"\n📁 Processando arquivo: {tipo_arquivo}-{ano}.json")
                
                dados = self.baixar_arquivo_json(ano, tipo_arquivo)
                if dados:
                    try:
                        # Limitar quantidade de registros
                        if isinstance(dados, list) and len(dados) > limite:
                            dados = dados[:limite]
                            print(f"      ⚠️ Limitado a {limite} registros")
                        
                        quantidade = processador(dados, db)
                        resultados[tipo_arquivo] = quantidade
                        
                        print(f"   ✅ {tipo_arquivo}: {quantidade} registros")
                        
                    except Exception as e:
                        print(f"   ❌ Erro ao processar {tipo_arquivo}: {e}")
                        resultados['erros'] += 1
                else:
                    print(f"   ❌ Falha no download do arquivo {tipo_arquivo}")
                    resultados['erros'] += 1
                
                # Rate limiting entre downloads
                time.sleep(1)
            
            # Upload para GCS dos dados completos
            if self.gcs_disponivel:
                self._upload_dados_completos_gcs(resultados, ano)
            
        except Exception as e:
            print(f"❌ Erro geral na coleta: {e}")
            resultados['erros'] += 1
        
        finally:
            db.close()
        
        # Resumo final
        print(f"\n📊 RESUMO DA COLETA - {ano}")
        print("=" * 50)
        for tipo, quantidade in resultados.items():
            if tipo != 'erros':
                print(f"   {tipo}: {quantidade} registros")
        print(f"   erros: {resultados['erros']}")
        
        return resultados

    def _upload_dados_completos_gcs(self, resultados: Dict[str, int], ano: int):
        """
        Faz upload dos dados completos para o GCS
        
        Args:
            resultados: Resultados da coleta
            ano: Ano dos dados
        """
        try:
            dados_completos = {
                'coleta': {
                    'ano': ano,
                    'data_coleta': datetime.now().isoformat(),
                    'resultados': resultados,
                    'fonte': 'Arquivos JSON - Dados Abertos',
                    'versao': '1.0'
                },
                'metadados': {
                    'tipos_arquivos': [
                        'votacoes',
                        'votacoesVotos', 
                        'votacoesObjetos',
                        'votacoesProposicoes',
                        'votacoesOrientacoes'
                    ],
                    'data_geracao': datetime.now().isoformat()
                }
            }
            
            # Fazer upload
            gcs_url = self.gcs_manager.upload_votacoes_completas(dados_completos, ano)
            
            if gcs_url:
                print(f"      📁 Upload GCS realizado: votacoes-{ano}")
            else:
                print(f"      ❌ Erro no upload GCS")
                
        except Exception as e:
            print(f"      ❌ Erro no upload GCS: {e}")

def main():
    """
    Função principal para execução standalone
    """
    print("🗳️ COLETA DE VOTAÇÕES - FALLBACK JSON")
    print("=" * 70)
    
    coletor = ColetorVotacoesFallback()
    
    # Coletar anos disponíveis (foco em anos recentes)
    anos_para_coletar = [2024, 2023, 2022]  # Anos com dados completos
    
    for ano in anos_para_coletar:
        print(f"\n🎯 COLETANDO VOTAÇÕES DE {ano}")
        resultados = coletor.coletar_votacoes_periodo(ano)
        
        total_registros = sum(v for k, v in resultados.items() if k != 'erros')
        print(f"✅ {ano}: {total_registros} registros totais")
    
    print(f"\n🎉 COLETA DE VOTAÇÕES CONCLUÍDA!")

if __name__ == "__main__":
    main()
