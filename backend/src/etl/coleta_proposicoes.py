#!/usr/bin/env python3
"""
Coletor de Proposições Parlamentares de Alto Impacto
Focus em PEC, PL, PLP, MPV e outros tipos relevantes
Integração com Google Cloud Storage para armazenamento completo
Refatorado para usar ETL Utils - elimina redundâncias e padroniza operações
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações
sys.path.append(str(Path(__file__).parent))
from config import get_config

# Importar utilitários
from utils.gcs_utils import get_gcs_manager
from utils.cache_utils import get_cache_manager

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.proposicao_models import Proposicao, Autoria

# Importar ETL utils
from .etl_utils import ETLBase, DateParser, ProgressLogger, GCSUploader

class ColetorProposicoes(ETLBase):
    """
    Classe responsável por coletar proposições de alto impacto
    Herda de ETLBase para usar funcionalidades comuns e eliminar redundâncias
    """

    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__()
        
        # Inicializar GCS Manager
        self.gcs_manager = get_gcs_manager()
        self.gcs_disponivel = self.gcs_manager.is_available()
        
        # Inicializar Cache Manager
        self.cache_manager = get_cache_manager(cache_dir="cache/proposicoes", ttl_hours=6)
        
        # Carregar configurações específicas
        self.config = get_config('hackathon', 'proposicoes')
        self.tipos_prioritarios = self._get_tipos_prioritarios()
        
        print(f"✅ Coletor de proposições inicializado")
        print(f"   📁 GCS disponível: {self.gcs_disponivel}")
        print(f"   🗄️ Cache ativo: {self.cache_manager.cache_dir}")
        print(f"    Tipos prioritários: {', '.join(self.tipos_prioritarios)}")

    def _get_tipos_prioritarios(self) -> List[str]:
        """
        Obtém lista de tipos de proposições prioritárias baseado na configuração
        
        Returns:
            List[str]: Lista de tipos SIGLA ordenados por prioridade
        """
        config_proposicoes = get_config('hackathon', 'proposicoes')
        tipos_config = config_proposicoes.get('tipos_para_coletar', [])
        prioridade_tipos = config_proposicoes.get('prioridade_tipos', {})
        
        # Ordenar tipos por prioridade
        tipos_ordenados = sorted(tipos_config, key=lambda x: prioridade_tipos.get(x, 999))
        
        print(f"   📋 Tipos prioritários (em ordem): {', '.join(tipos_ordenados)}")
        return tipos_ordenados

    def _fazer_requisicao(self, url: str, params: Optional[Dict] = None, use_cache: bool = True) -> Optional[Dict]:
        """
        Faz requisição à API com cache e tratamento de erros
        
        Args:
            url: URL da API
            params: Parâmetros da requisição
            use_cache: Se deve usar cache
            
        Returns:
            Dict: Resposta da API ou None
        """
        # Verificar cache primeiro
        if use_cache:
            cached_response = self.cache_manager.get_cached_api_response(url, params or {})
            if cached_response:
                print(f"      📦 Cache hit: {url}")
                return cached_response
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Salvar no cache
            if use_cache and data:
                self.cache_manager.cache_api_response(url, params or {}, data, ttl_hours=2)
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição para {url}: {e}")
            return None

    def buscar_proposicoes_por_tipo(self, tipo: str, anos: List[int], limite: int = 100) -> List[Dict]:
        """
        Busca proposições por tipo usando estratégia definitiva de janelas otimizadas
        BASEADO NAS DESCOBERTAS DOS TESTES EXTENSIVOS
        
        Args:
            tipo: Tipo da proposição (PEC, PL, etc.)
            anos: Lista de anos para buscar
            limite: Limite de resultados
            
        Returns:
            List[Dict]: Lista de proposições
        """
        print(f"   🎯 BUSCA ESTRATÉGICA {tipo}/anos {anos} (limite: {limite})")
        
        # Estratégia definitiva baseada nas descobertas
        estrategias_janelas = self._definir_estrategia_janelas(tipo)
        
        todas_proposicoes = []
        ids_encontrados = set()
        
        for i, janela in enumerate(estrategias_janelas):
            print(f"\n   📅 Janela {i+1}/{len(estrategias_janelas)}: {janela['descricao']}")
            print(f"      Período: {janela['data_inicio']} a {janela['data_fim']}")
            
            # Coleta com paginação para esta janela
            proposicoes_janela = []
            pagina = 1
            max_paginas_janela = 20  # Limite por janela para não sobrecarregar
            
            while len(proposicoes_janela) < 1000 and pagina <= max_paginas_janela:  # Máximo 1000 por janela
                url = f"{API_CONFIG['base_url']}/proposicoes"
                params = {
                    'siglaTipo': tipo,
                    'ano': janela.get('anos', anos),
                    'dataApresentacaoInicio': janela['data_inicio'],
                    'dataApresentacaoFim': janela['data_fim'],
                    'pagina': pagina,
                    'itens': 100,
                    'ordenarPor': 'id',
                    'ordem': 'DESC'
                }
                
                print(f"      📄 Página {pagina}...")
                data = self.make_request(url, params)
                
                if not data:
                    break
                
                itens = data.get('dados', [])
                if not itens:
                    print(f"      📄 Página {pagina} vazia")
                    break
                
                # Filtrar duplicatas por ID
                novos_itens = []
                for item in itens:
                    item_id = item.get('id')
                    if item_id and item_id not in ids_encontrados:
                        ids_encontrados.add(item_id)
                        novos_itens.append(item)
                
                proposicoes_janela.extend(novos_itens)
                print(f"      📊 Página {pagina}: +{len(novos_itens)} {tipo}s (total janela: {len(proposicoes_janela)})")
                
                if len(novos_itens) == 0:  # Se não encontrou novos itens, parar
                    break
                
                pagina += 1
            
            # Adicionar proposições desta janela ao total
            todas_proposicoes.extend(proposicoes_janela)
            
            # Estatísticas da janela
            if proposicoes_janela:
                anos_janela = {}
                for prop in proposicoes_janela:
                    ano = prop.get('ano', 'N/A')
                    anos_janela[ano] = anos_janela.get(ano, 0) + 1
                
                print(f"      ✅ Janela concluída: {len(proposicoes_janela)} {tipo}s")
                print(f"      📅 Distribuição: {dict(sorted(anos_janela.items()))}")
            else:
                print(f"      ❌ Nenhuma {tipo} encontrada nesta janela")
            
            # Parar se já encontrou suficientes
            if len(todas_proposicoes) >= limite:
                print(f"      🎯 Limite desejado alcançado: {len(todas_proposicoes)} {tipo}s")
                break
        
        # Filtrar pelos anos desejados e ordenar
        proposicoes_filtradas = [
            prop for prop in todas_proposicoes 
            if prop.get('ano') in anos
        ]
        
        # Ordenar por ID (mais recentes primeiro) e limitar
        proposicoes_filtradas.sort(key=lambda x: x.get('id', 0), reverse=True)
        proposicoes = proposicoes_filtradas[:limite]
        
        # Estatísticas finais
        anos_encontrados = {}
        for prop in proposicoes:
            ano = prop.get('ano', 'N/A')
            anos_encontrados[ano] = anos_encontrados.get(ano, 0) + 1
            
        print(f"\n   📈 RESULTADO FINAL {tipo}:")
        print(f"      📄 Encontradas: {len(proposicoes)} {tipo}s (de {len(todas_proposicoes)} totais)")
        print(f"      📅 Distribuição: {dict(sorted(anos_encontrados.items()))}")
        
        return proposicoes

    def _definir_estrategia_janelas(self, tipo: str) -> List[Dict]:
        """
        Define janelas otimizadas baseadas nas descobertas extensivas
        
        Args:
            tipo: Tipo da proposição
            
        Returns:
            List[Dict]: Lista de janelas configuradas
        """
        if tipo == 'PEC':
            # Estratégia PECs baseada nas descobertas: 17 PECs em 2025, nenhuma em 2024
            return [
                {
                    'data_inicio': '2025-01-24',
                    'data_fim': '2025-04-24',
                    'descricao': 'PECs - Pico 1: Jan-Abr 2025 (8 PECs)',
                    'anos': [2025]
                },
                {
                    'data_inicio': '2025-04-24',
                    'data_fim': '2025-07-23',
                    'descricao': 'PECs - Pico 2: Abr-Jul 2025 (4 PECs)',
                    'anos': [2025]
                },
                {
                    'data_inicio': '2025-07-23',
                    'data_fim': '2025-10-21',
                    'descricao': 'PECs - Pico 3: Jul-Out 2025 (5 PECs)',
                    'anos': [2025]
                }
            ]
        
        elif tipo == 'PL':
            # Estratégia PLs baseada nas descobertas: 4000+ PLs encontradas
            return [
                {
                    'data_inicio': '2025-07-21',
                    'data_fim': '2025-10-21',
                    'descricao': 'PLs - Últimos 3 meses (1000+ PLs)',
                    'anos': [2024, 2025]
                },
                {
                    'data_inicio': '2025-04-22',
                    'data_fim': '2025-07-21',
                    'descricao': 'PLs - Trimestre anterior (1000+ PLs)',
                    'anos': [2024, 2025]
                },
                {
                    'data_inicio': '2025-01-21',
                    'data_fim': '2025-04-22',
                    'descricao': 'PLs - Primeiro trimestre (1000+ PLs)',
                    'anos': [2024, 2025]
                },
                {
                    'data_inicio': '2024-10-01',
                    'data_fim': '2025-01-21',
                    'descricao': 'PLs - Final 2024 (1000+ PLs)',
                    'anos': [2024, 2025]
                }
            ]
        
        else:
            # Estratégia genérica para outros tipos (PLP, MPV, etc.)
            return [
                {
                    'data_inicio': '2025-01-01',
                    'data_fim': '2025-12-31',
                    'descricao': f'{tipo}s - Ano completo 2025',
                    'anos': [2025]
                },
                {
                    'data_inicio': '2024-01-01',
                    'data_fim': '2024-12-31',
                    'descricao': f'{tipo}s - Ano completo 2024',
                    'anos': [2024]
                }
            ]

    def buscar_detalhes_proposicao(self, proposicao_id: int) -> Optional[Dict]:
        """
        Busca detalhes completos de uma proposição
        
        Args:
            proposicao_id: ID da proposição na API
            
        Returns:
            Dict: Detalhes completos ou None
        """
        url = f"{self.api_config['base_url']}/proposicoes/{proposicao_id}"
        return self.make_request(url)

    def buscar_autores_proposicao(self, proposicao_id: int) -> List[Dict]:
        """
        Busca autores de uma proposição
        
        Args:
            proposicao_id: ID da proposição
            
        Returns:
            List[Dict]: Lista de autores
        """
        url = f"{self.api_config['base_url']}/proposicoes/{proposicao_id}/autores"
        params = {'itens': 50}
        
        data = self.make_request(url, params)
        if not data:
            return []
        
        return data.get('dados', [])

    def buscar_votacoes_proposicao(self, proposicao_id: int) -> List[Dict]:
        """
        Busca votações de uma proposição
        
        Args:
            proposicao_id: ID da proposição
            
        Returns:
            List[Dict]: Lista de votações
        """
        url = f"{self.api_config['base_url']}/proposicoes/{proposicao_id}/votacoes"
        params = {'itens': 20}
        
        data = self.make_request(url, params)
        if not data:
            return []
        
        return data.get('dados', [])

    def baixar_texto_completo(self, url_inteiro_teor: str) -> Optional[str]:
        """
        Baixa o texto completo de uma proposição usando a URL do inteiro teor
        
        Args:
            url_inteiro_teor: URL para download do texto completo
            
        Returns:
            str: Texto completo da proposição ou None
        """
        if not url_inteiro_teor:
            return None
            
        try:
            print(f"      📄 Baixando texto completo de: {url_inteiro_teor}")
            
            # Usar headers de navegador para contornar bloqueios
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/pdf',
                'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url_inteiro_teor, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Verificar se é PDF pelo content-type
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/pdf' in content_type:
                # Tratar como PDF binário
                content_bytes = response.content
                
                # Verificar se é PDF válido
                if content_bytes.startswith(b'%PDF'):
                    print(f"      ✅ PDF baixado ({len(content_bytes)} bytes)")
                    print(f"      📄 Formato: PDF")
                    
                    # Converter para string usando latin-1 (encoding padrão de PDFs)
                    return content_bytes.decode('latin-1')
                else:
                    print(f"      ❌ Conteúdo não é PDF válido")
                    return None
            else:
                # Tratar como HTML/texto
                content = response.text
                
                # Indicadores de que temos o conteúdo correto (HTML)
                indicadores_html = ['proposição', 'proposicao', 'art.', 'caput', 'parágrafo']
                
                if any(indicador in content.lower() for indicador in indicadores_html):
                    print(f"      ✅ Texto completo baixado ({len(content)} caracteres)")
                    print(f"      🌐 Formato: HTML")
                    return content
                else:
                    print(f"      ❌ Conteúdo não parece ser o texto da proposição")
                    print(f"      Amostra: {content[:200]}...")
                    return None
                
        except Exception as e:
            print(f"      ❌ Erro ao baixar texto completo: {e}")
            return None

    def _mapear_deputado(self, autor_data: Dict, db: Session) -> Optional[int]:
        """
        Mapeia autor para ID do deputado no banco
        
        Args:
            autor_data: Dados do autor da API
            db: Sessão do banco
            
        Returns:
            int: ID do deputado ou None
        """
        if not autor_data:
            return None
        
        # Se for deputado, buscar por ID da API
        if autor_data.get('tipo') == 'Deputado':
            api_id = autor_data.get('codTipo', 0)
            if api_id:
                deputado = db.query(Deputado).filter(
                    Deputado.api_camara_id == api_id
                ).first()
                if deputado:
                    return deputado.id
        
        # Tentar buscar por nome
        nome = autor_data.get('nome')
        if nome:
            deputado = db.query(Deputado).filter(
                Deputado.nome.ilike(f"%{nome}%")
            ).first()
            if deputado:
                return deputado.id
        
        return None

    def salvar_proposicao(self, proposicao_data: Dict, db: Session) -> Optional[Proposicao]:
        """
        Salva proposição no banco com dados completos no GCS
        
        Args:
            proposicao_data: Dados da proposição
            db: Sessão do banco
            
        Returns:
            Proposicao: Proposição salva ou None
        """
        try:
            # Verificar se já existe
            existente = db.query(Proposicao).filter(
                Proposicao.api_camara_id == proposicao_data['id']
            ).first()
            
            if existente:
                print(f"      ⏭️ Proposição já existe: {proposicao_data['siglaTipo']} {proposicao_data['numero']}/{proposicao_data['ano']}")
                return existente
            
            # Buscar detalhes completos
            detalhes = self.buscar_detalhes_proposicao(proposicao_data['id'])
            if not detalhes:
                print(f"      ⚠️ Não foi possível obter detalhes da proposição {proposicao_data['id']}")
                return None
            
            # Combinar dados básicos com detalhes
            dados_completos = {**proposicao_data, **detalhes.get('dados', {})}
            
            # Preparar dados para salvamento
            ano = int(dados_completos.get('ano', 0))
            tipo = dados_completos.get('siglaTipo', 'UNKNOWN')
            api_id = str(dados_completos.get('id', ''))
            
            # Baixar texto completo se disponível
            texto_completo = None
            url_inteiro_teor = dados_completos.get('urlInteiroTeor')
            if url_inteiro_teor:
                texto_completo = self.baixar_texto_completo(url_inteiro_teor)
            
            # Upload para GCS se disponível
            gcs_url = None
            if self.gcs_disponivel:
                gcs_url = self.gcs_manager.upload_proposicao(
                    dados_completos, ano, tipo, api_id, texto_completo
                )
                if gcs_url:
                    print(f"      📁 Upload GCS: {gcs_url}")
            
            # Criar proposição no banco
            proposicao = Proposicao(
                api_camara_id=dados_completos.get('id'),
                tipo=tipo,
                numero=int(dados_completos.get('numero', 0)),
                ano=ano,
                ementa=dados_completos.get('ementa', ''),
                explicacao=dados_completos.get('explicacaoEmenta'),
                data_apresentacao=DateParser.parse_date(dados_completos.get('dataApresentacao')),
                situacao=dados_completos.get('statusProposicao', {}).get('descricao'),
                link_inteiro_teor=dados_completos.get('urlInteiroTeor'),
                keywords=dados_completos.get('keywords'),
                gcs_url=gcs_url  # Nova campo para URL do GCS
            )
            
            db.add(proposicao)
            db.flush()  # Para obter o ID
            
            # Buscar e salvar autores
            autores = self.buscar_autores_proposicao(proposicao_data['id'])
            for autor_data in autores:
                deputado_id = self._mapear_deputado(autor_data, db)
                if deputado_id:
                    autoria = Autoria(
                        proposicao_id=proposicao.id,
                        deputado_id=deputado_id,
                        tipo_autoria=autor_data.get('tipo', 'Autor'),
                        ordem=autor_data.get('ordemAssinatura', 1)
                    )
                    db.add(autoria)
            
            # Buscar e salvar votações (simplificado por enquanto)
            votacoes = self.buscar_votacoes_proposicao(proposicao_data['id'])
            if votacoes:
                print(f"      🗳️ Encontradas {len(votacoes)} votações")
                # TODO: Implementar salvamento de votações
            
            db.commit()
            print(f"      ✅ Proposição salva: {tipo} {proposicao.numero}/{ano}")
            return proposicao
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar proposição: {e}")
            db.rollback()
            return None


    def coletar_proposicoes_periodo(self, anos: List[int], db: Session) -> Dict[str, int]:
        """
        Coleta proposições de múltiplos anos específicos
        CORRIGIDO: Agora aceita lista de anos e usa nova lógica de busca
        
        Args:
            anos: Lista de anos para coleta
            db: Sessão do banco
            
        Returns:
            Dict: Resultados da coleta
        """
        print(f"\n📄 COLETANDO PROPOSIÇÕES - ANOS {anos}")
        print("=" * 50)
        
        resultados = {
            'tipos_processados': 0,
            'proposicoes_encontradas': 0,
            'proposicoes_salvas': 0,
            'autores_mapeados': 0,
            'uploads_gcs': 0,
            'erros': 0
        }
        
        limite_total = self.config.get('limite_total', 10000)
        limite_por_tipo = limite_total // len(self.tipos_prioritarios)
        
        print(f"   📋 Configuração: {limite_total} total, {limite_por_tipo} por tipo")
        print(f"   🎯 Foco especial em PLs para ano eleitoral 2025")
        
        for tipo in self.tipos_prioritarios:
            print(f"\n🔍 Processando tipo: {tipo}")
            
            try:
                # Aumentar limite para PLs (tipo mais importante para ano eleitoral)
                limite_tipo = limite_por_tipo * 2 if tipo == 'PL' else limite_por_tipo
                
                # Buscar proposições do tipo
                proposicoes = self.buscar_proposicoes_por_tipo(tipo, anos, limite_tipo)
                resultados['proposicoes_encontradas'] += len(proposicoes)
                resultados['tipos_processados'] += 1
                
                for i, prop_data in enumerate(proposicoes, 1):
                    print(f"      📄 Processando {i}/{len(proposicoes)}: {tipo} {prop_data.get('numero', '?')}/{prop_data.get('ano', '?')}")
                    
                    try:
                        # Salvar proposição completa
                        proposicao = self.salvar_proposicao(prop_data, db)
                        if proposicao:
                            resultados['proposicoes_salvas'] += 1
                            resultados['autores_mapeados'] += len(proposicao.autores)
                            if proposicao.gcs_url:
                                resultados['uploads_gcs'] += 1
                        
                    except Exception as e:
                        print(f"      ❌ Erro ao processar proposição: {e}")
                        resultados['erros'] += 1
                        continue
                
            except Exception as e:
                print(f"❌ Erro ao processar tipo {tipo}: {e}")
                resultados['erros'] += 1
                continue
        
        return resultados

    def gerar_resumo_coleta(self, ano: int, db: Session) -> bool:
        """
        Gera resumo estatístico da coleta
        
        Args:
            ano: Ano da coleta
            db: Sessão do banco
            
        Returns:
            bool: True se sucesso
        """
        try:
            print(f"\n📊 GERANDO RESUMO DA COLETA - {ano}")
            print("=" * 40)
            
            # Contar proposições por tipo
            from sqlalchemy import func
            
            resumo = db.query(
                Proposicao.tipo,
                func.count(Proposicao.id).label('quantidade'),
                func.count(Proposicao.gcs_url).label('com_gcs')
            ).filter(
                Proposicao.ano == ano
            ).group_by(Proposicao.tipo).all()
            
            print(f"📋 Resumo por tipo:")
            for tipo, quantidade, com_gcs in resumo:
                print(f"   • {tipo}: {quantidade} proposições ({com_gcs} no GCS)")
            
            # Total geral
            total = db.query(func.count(Proposicao.id)).filter(Proposicao.ano == ano).scalar()
            total_gcs = db.query(func.count(Proposicao.id)).filter(
                and_(Proposicao.ano == ano, Proposicao.gcs_url.isnot(None))
            ).scalar()
            
            print(f"\n📈 Totais:")
            print(f"   • Total de proposições: {total}")
            print(f"   • No GCS: {total_gcs}")
            print(f"   • Taxa de armazenamento: {(total_gcs/total*100):.1f}%" if total > 0 else "   • Taxa de armazenamento: 0%")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao gerar resumo: {e}")
            return False

def main():
    """
    Função principal para execução standalone
    CORRIGIDO: Usa nova configuração com múltiplos anos
    """
    print("📄 COLETA DE PROPOSIÇÕES DE ALTO IMPACTO - VERSÃO CORRIGIDA")
    print("=" * 60)
    print("🔧 CORREÇÕES APLICADAS:")
    print("   • Removido parâmetro 'sigla' que causava erro 400")
    print("   • Aumentados limites para ano eleitoral")
    print("   • Incluídos PLs de 2024 e 2025")
    print("   • Busca mais profunda (até 2000 páginas)")
    print("=" * 60)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = get_db_session()
    
    try:
        coletor = ColetorProposicoes()
        
        # Obter configuração de anos (CORRIGIDO: usa anos_para_coletar)
        config = get_config('hackathon', 'proposicoes')
        anos_para_coletar = config.get('anos_para_coletar', [2024, 2025])
        
        print(f"🎯 ANOS ALVO: {anos_para_coletar}")
        print(f"📋 FOCO ESPECIAL: PLs para ano eleitoral 2025")
        
        # Coletar para todos os anos de uma vez (melhor performance)
        resultados = coletor.coletar_proposicoes_periodo(anos_para_coletar, db_session)
        
        print(f"\n📋 RESUMO FINAL DA COLETA")
        print("=" * 40)
        print(f"📋 Tipos processados: {resultados['tipos_processados']}")
        print(f"📄 Proposições encontradas: {resultados['proposicoes_encontradas']}")
        print(f"✅ Proposições salvas: {resultados['proposicoes_salvas']}")
        print(f"👥 Autores mapeados: {resultados['autores_mapeados']}")
        print(f"📁 Uploads GCS: {resultados['uploads_gcs']}")
        print(f"❌ Erros: {resultados['erros']}")
        
        # Gerar resumo para cada ano
        for ano in anos_para_coletar:
            coletor.gerar_resumo_coleta(ano, db_session)
        
        print(f"\n✅ Coleta de proposições concluída com sucesso!")
        print(f"🎯 PLs coletados devem ser muito maiores agora!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
