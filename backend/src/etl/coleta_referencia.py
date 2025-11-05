#!/usr/bin/env python3
"""
Coletor de Dados de Referência da Câmara dos Deputados
Responsável por coletar partidos, deputados e gastos parlamentares
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
from config import get_config, HACKATHON_CONFIG, DEDUPLICATION_CONFIG, get_coleta_config, get_data_inicio_coleta, deve_respeitar_data_inicio, coleta_habilitada

# Coletores de proposições e frequência removidos - Evolução Futura
# MOVIDO PARA deprecated/ - será implementado em versão futura

# Importar modelos
import models
from models import database
from models.politico_models import Deputado, Mandato
from models.base_models import Partido, Estado, Legislatura
from models.financeiro_models import GastoParlamentar

# Importar ETL utils
from .etl_utils import ETLBase, DateParser, ProgressLogger, DatabaseManager, HashGenerator


class ColetorDadosCamara(ETLBase):
    """
    Classe responsável por coletar dados da API da Câmara dos Deputados
    Herda de ETLBase para usar funcionalidades comuns e eliminar redundâncias
    """

    def __init__(self):
        """Inicializa o coletor usando ETLBase"""
        super().__init__()
        
        # Configurações específicas
        self.config = HACKATHON_CONFIG
        self.dedup_config = DEDUPLICATION_CONFIG
        self.api_base_url = self.api_config['base_url']
        
        # Configurações de coleta centralizadas
        self.coleta_config = get_coleta_config()
        self.data_inicio = get_data_inicio_coleta()
        
        print(f"✅ Coletor de dados da Câmara inicializado")
        print(f"📅 Período de coleta: {self.data_inicio} até hoje")
        print(f"🔧 Respeitar data início: {deve_respeitar_data_inicio('referencia')}")


    def buscar_e_salvar_partidos(self, db: Session) -> int:
        """
        Busca todos os partidos na API da Câmara e os salva no banco de dados.
        Retorna o número de partidos processados.
        """
        print("🏛️ Buscando dados de partidos...")
        url = f"{self.api_base_url}/partidos?ordem=ASC&ordenarPor=sigla&itens=100"
        
        partidos_processados = 0
        
        while url:
            data = self.make_request(url)
            if not data:
                break
                
            partidos_api = data.get("dados", [])
            print(f"   📊 Processando lote de {len(partidos_api)} partidos...")
            
            for partido_data in partidos_api:
                try:
                    # Verificar se partido já existe pela sigla
                    partido_existente = db.query(Partido).filter(
                        Partido.sigla == partido_data['sigla']
                    ).first()
                    
                    if partido_existente:
                        # Atualizar dados existentes
                        partido_existente.nome = partido_data['nome']
                        partido_existente.status = partido_data.get('status', 'Ativo')
                        print(f"      🔄 Atualizado: {partido_data['sigla']} - {partido_data['nome']}")
                    else:
                        # Criar novo partido
                        novo_partido = Partido(
                            sigla=partido_data['sigla'],
                            nome=partido_data['nome'],
                            numero=partido_data.get('numero'),
                            status=partido_data.get('status', 'Ativo')
                        )
                        db.add(novo_partido)
                        print(f"      ✅ Inserido: {partido_data['sigla']} - {partido_data['nome']}")
                    
                    partidos_processados += 1
                    
                except Exception as e:
                    print(f"      ❌ Erro ao processar partido {partido_data.get('sigla', 'desconhecido')}: {e}")
                    continue
            
            # Verificar próxima página
            links = {link['rel']: link['href'] for link in data.get('links', [])}
            url = links.get('next')
        
        db.commit()
        print(f"✅ Busca de partidos concluída. Total processados: {partidos_processados}")
        return partidos_processados

    def _buscar_detalhes_deputado(self, deputado_id: int) -> Optional[Dict]:
        """Busca detalhes completos de um deputado."""
        url = f"{self.api_base_url}/deputados/{deputado_id}"
        data = self.make_request(url)
        return data.get('dados') if data else None

    def buscar_e_salvar_deputados(self, db: Session) -> int:
        """
        Busca deputados em exercício na API da Câmara com limitações do hackathon.
        Retorna o número de deputados processados.
        """
        config_dep = self.config['deputados']
        limite_total = config_dep['limite_total']
        
        print(f"\n👥 Buscando dados de deputados (limite: {limite_total})...")
        url = f"{self.api_base_url}/deputados?itens={get_config('api', 'batch_size')}&ordem=ASC&ordenarPor=nome"
        
        deputados_processados = 0
        
        while url and deputados_processados < limite_total:
            data = self.make_request(url)
            if not data:
                break
                
            deputados_api = data.get("dados", [])
            print(f"   📊 Processando lote de {len(deputados_api)} deputados...")
            
            for deputado_data in deputados_api:
                if deputados_processados >= limite_total:
                    print(f"   ⏹️ Limite de {limite_total} deputados atingido")
                    break
                
                try:
                    # Buscar detalhes completos do deputado
                    detalhes = self._buscar_detalhes_deputado(deputado_data['id'])
                    if not detalhes:
                        print(f"      ⚠️ Não foi possível obter detalhes do deputado {deputado_data.get('nome', 'desconhecido')}")
                        continue
                    
                    # Combinar dados básicos com detalhes
                    dados_completos = {**deputado_data, **detalhes}
                    
                    # Verificar duplicação por ID da API
                    if self._verificar_duplicacao('deputados', dados_completos, db):
                        print(f"      ⏭️  {dados_completos['nome']}: já existe")
                        continue
                    
                    # Criar novo deputado
                    novo_deputado = self._criar_deputado(dados_completos, db)
                    db.add(novo_deputado)
                    db.commit()  # Commit imediato para garantir persistência
                    print(f"      ✅ Inserido: {dados_completos['nome']} ({dados_completos.get('siglaPartido', 'N/A')})")
                    
                    # Criar/atualizar mandato atual
                    self._processar_mandato(db, dados_completos)
                    db.commit()  # Commit do mandato também
                    
                    deputados_processados += 1
                    
                except KeyError as e:
                    print(f"      ⚠️ Campo ausente nos dados do deputado {deputado_data.get('nome', 'desconhecido')}: {e}")
                    continue
                except Exception as e:
                    print(f"      ❌ Erro ao processar deputado {deputado_data.get('nome', 'desconhecido')}: {e}")
                    db.rollback()
                    continue
            
            # Verificar próxima página
            links = {link['rel']: link['href'] for link in data.get('links', [])}
            url = links.get('next')
        
        db.commit()
        print(f"✅ Busca de deputados concluída. Total processados: {deputados_processados}")
        return deputados_processados

    def _criar_deputado(self, detalhes: Dict, db: Session) -> Deputado:
        """Cria um novo objeto Deputado com dados da API."""
        # Buscar referências - tratar caso não tenha siglaPartido
        partido = None
        sigla_partido = detalhes.get('siglaPartido')
        if sigla_partido:
            partido = db.query(Partido).filter(Partido.sigla == sigla_partido).first()
        
        return Deputado(
            api_camara_id=detalhes['id'],
            nome=detalhes['nome'],
            nome_civil=detalhes.get('nomeCivil'),
            cpf=detalhes.get('cpf'),
            sexo=detalhes.get('sexo'),
            data_nascimento=DateParser.parse_date(detalhes.get('dataNascimento')),
            municipio_nascimento=detalhes.get('municipioNascimento'),
            uf_nascimento=detalhes.get('ufNascimento'),
            escolaridade=detalhes.get('escolaridade'),
            profissao=detalhes.get('profissao'),
            email=detalhes.get('email'),
            telefone=detalhes.get('telefone'),
            foto_url=detalhes.get('urlFoto'),
            situacao=detalhes.get('situacao', 'Exercício'),
            condicao=detalhes.get('condicaoEleitoral')
        )

    def _atualizar_deputado(self, deputado: Deputado, detalhes: Dict):
        """Atualiza dados de um deputado existente."""
        deputado.nome = detalhes['nome']
        deputado.nome_civil = detalhes.get('nomeCivil')
        deputado.cpf = detalhes.get('cpf')
        deputado.sexo = detalhes.get('sexo')
        deputado.data_nascimento = DateParser.parse_date(detalhes.get('dataNascimento'))
        deputado.municipio_nascimento = detalhes.get('municipioNascimento')
        deputado.uf_nascimento = detalhes.get('ufNascimento')
        deputado.escolaridade = detalhes.get('escolaridade')
        deputado.profissao = detalhes.get('profissao')
        deputado.email = detalhes.get('email')
        deputado.telefone = detalhes.get('telefone')
        deputado.foto_url = detalhes.get('urlFoto')
        deputado.situacao = detalhes.get('situacao', 'Exercício')
        deputado.condicao = detalhes.get('condicaoEleitoral')

    def _processar_mandato(self, db: Session, detalhes: Dict):
        """Processa e cria/atualiza o mandato atual do deputado."""
        # Buscar referências - tratar campos opcionais
        sigla_partido = detalhes.get('siglaPartido')
        sigla_uf = detalhes.get('siglaUf')
        
        partido = None
        if sigla_partido:
            partido = db.query(Partido).filter(Partido.sigla == sigla_partido).first()
        
        estado = None
        if sigla_uf:
            estado = db.query(Estado).filter(Estado.sigla == sigla_uf).first()
        
        if not partido and sigla_partido:
            print(f"      ⚠️ Partido {sigla_partido} não encontrado para {detalhes['nome']}")
            # Criar partido se não existir
            partido = Partido(
                sigla=sigla_partido,
                nome=sigla_partido,  # Usar sigla como nome temporariamente
                status='Ativo'
            )
            db.add(partido)
            db.commit()
            print(f"      ✅ Partido {sigla_partido} criado automaticamente")
        
        if not estado and sigla_uf:
            print(f"      ⚠️ Estado {sigla_uf} não encontrado para {detalhes['nome']}")
            # Criar estado se não existir
            estado = Estado(
                sigla=sigla_uf,
                nome=sigla_uf,  # Usar sigla como nome temporariamente
                regiao='Sudeste'  # Valor padrão, será atualizado depois
            )
            db.add(estado)
            db.commit()
            print(f"      ✅ Estado {sigla_uf} criado automaticamente")
        
        # Buscar legislatura atual
        legislatura = db.query(Legislatura).filter(Legislatura.ativa == True).first()
        if not legislatura:
            print(f"      ⚠️ Nenhuma legislatura ativa encontrada")
            # Criar legislatura atual
            ano_atual = datetime.now().year
            legislatura = Legislatura(
                numero=ano_atual,  # Simplificado
                data_inicio=datetime(ano_atual, 2, 1).date(),
                data_fim=datetime(ano_atual + 4, 1, 31).date(),
                ativa=True
            )
            db.add(legislatura)
            db.commit()
            print(f"      ✅ Legislatura {ano_atual} criada automaticamente")
        
        # Buscar deputado
        deputado = db.query(Deputado).filter(Deputado.api_camara_id == detalhes['id']).first()
        
        # Verificar se mandato já existe
        mandato_existente = db.query(Mandato).filter(
            and_(
                Mandato.deputado_id == deputado.id,
                Mandato.legislatura_id == legislatura.id
            )
        ).first()
        
        if not mandato_existente and partido and estado:
            novo_mandato = Mandato(
                deputado_id=deputado.id,
                legislatura_id=legislatura.id,
                partido_id=partido.id,
                estado_id=estado.id,
                data_inicio=datetime.now().date()  # Será atualizado com dados reais
            )
            db.add(novo_mandato)
        elif not mandato_existente:
            print(f"      ⚠️ Mandato não criado para {detalhes['nome']}: partido ou estado não disponível")

    def buscar_e_salvar_gastos(self, db: Session, meses_historico: int = 12) -> int:
        """
        Busca gastos parlamentares dos últimos meses e salva no banco.
        Retorna o número de registros processados.
        """
        print(f"\n💰 Buscando gastos dos últimos {meses_historico} meses...")
        
        gastos_processados = 0
        data_atual = datetime.now()
        
        # Buscar todos os deputados ativos
        deputados = db.query(Deputado).filter(
            Deputado.situacao == 'Exercício'
        ).all()
        
        print(f"   📊 Processando gastos para {len(deputados)} deputados...")
        
        for deputado in deputados:
            for mes_offset in range(meses_historico):
                try:
                    data_ref = data_atual - timedelta(days=mes_offset * 30)
                    ano = data_ref.year
                    mes = data_ref.month
                    
                    # Verificar se já temos gastos para este período
                    gastos_existentes = db.query(GastoParlamentar).filter(
                        and_(
                            GastoParlamentar.deputado_id == deputado.id,
                            GastoParlamentar.ano == ano,
                            GastoParlamentar.mes == mes
                        )
                    ).count()
                    
                    if gastos_existentes > 0:
                        print(f"      ⏭️  {deputado.nome} - {mes}/{ano}: já coletado ({gastos_existentes} registros)")
                        continue
                    
                    # Buscar gastos da API
                    url = f"{self.api_base_url}/deputados/{deputado.api_camara_id}/despesas"
                    params = {
                        'ano': ano,
                        'mes': mes,
                        'ordem': 'ASC',
                        'itens': 100
                    }
                    
                    data = self.make_request(url, params)
                    if not data:
                        continue
                    
                    despesas = data.get('dados', [])
                    if not despesas:
                        continue
                    
                    # Processar cada despesa
                    for despesa in despesas:
                        gasto = GastoParlamentar(
                            deputado_id=deputado.id,
                            ano=ano,
                            mes=mes,
                            tipo_despesa=despesa.get('tipoDespesa'),
                            descricao=despesa.get('descricao'),
                            fornecedor_nome=despesa.get('nomeFornecedor'),
                            fornecedor_cnpj=despesa.get('cnpjFornecedor'),
                            valor_documento=despesa.get('valorDocumento'),
                            valor_glosa=despesa.get('valorGlosa', 0),
                            valor_liquido=despesa.get('valorLiquido'),
                            data_documento=DateParser.parse_date(despesa.get('dataDocumento')),
                            numero_documento=despesa.get('numeroDocumento'),
                            numero_ressarcimento=despesa.get('numeroRessarcimento'),
                            parcela=despesa.get('parcela')
                        )
                        db.add(gasto)
                        gastos_processados += 1
                    
                    print(f"      💸 {deputado.nome} - {mes}/{ano}: {len(despesas)} despesas")
                    
                except Exception as e:
                    print(f"      ❌ Erro ao processar gastos de {deputado.nome}: {e}")
                    continue
        
        db.commit()
        print(f"✅ Busca de gastos concluída. Total processados: {gastos_processados}")
        return gastos_processados



    def _verificar_duplicacao(self, tipo: str, dados: Dict, db: Session) -> bool:
        """
        Verifica se um registro já existe no banco usando a estratégia de deduplicação.
        Retorna True se o registro já existe.
        """
        if not self.dedup_config['verificar_existencia']:
            return False
        
        campos_unicos = self.dedup_config['campos_unicos'].get(tipo, [])
        
        if tipo == 'deputados':
            # Verificar por ID da API ou CPF
            api_id = dados.get('id')
            cpf = dados.get('cpf')
            
            if api_id:
                existente = db.query(Deputado).filter(Deputado.api_camara_id == api_id).first()
                if existente:
                    return True
            if cpf:
                existente = db.query(Deputado).filter(Deputado.cpf == cpf).first()
                if existente:
                    return True
                    
        elif tipo == 'gastos':
            # Verificar por chave composta
            deputado_id = dados.get('deputado_id')
            ano = dados.get('ano')
            mes = dados.get('mes')
            numero_doc = dados.get('numero_documento')
            valor = dados.get('valor_liquido')
            
            if all([deputado_id, ano, mes, numero_doc, valor]):
                existente = db.query(GastoParlamentar).filter(
                    and_(
                        GastoParlamentar.deputado_id == deputado_id,
                        GastoParlamentar.ano == ano,
                        GastoParlamentar.mes == mes,
                        GastoParlamentar.numero_documento == numero_doc,
                        GastoParlamentar.valor_liquido == valor
                    )
                ).first()
                if existente:
                    return True
                    
        elif tipo == 'partidos':
            # Verificar por sigla
            sigla = dados.get('sigla')
            if sigla:
                existente = db.query(Partido).filter(Partido.sigla == sigla).first()
                if existente:
                    return True
        
        return False


    def executar_coleta_completa(self, db: Session) -> Dict[str, int]:
        """
        Executa toda a coleta de dados de forma organizada.
        Retorna um dicionário com contadores de cada tipo de dado coletado.
        """
        print("🚀 INICIANDO COLETA COMPLETA DE DADOS DA CÂMARA")
        print("=" * 60)
        
        resultados = {}
        
        # 1. Coletar dados de referência (partidos, deputados)
        print("\n📋 ETAPA 1: DADOS DE REFERÊNCIA")
        resultados['partidos'] = self.buscar_e_salvar_partidos(db)
        resultados['deputados'] = self.buscar_e_salvar_deputados(db)
        
        # 2. Coletar dados financeiros
        print("\n💰 ETAPA 2: DADOS FINANCEIROS")
        meses_historico = self.config['gastos']['meses_historico']
        resultados['gastos'] = self.buscar_e_salvar_gastos(db, meses_historico=meses_historico)
        
        # 3. Proposições e Frequência removidos - Evolução Futura
        print("\n📄 ETAPA 3: PROPOSIÇÕES E FREQUÊNCIA (REMOVIDOS)")
        print("   ❌ Proposições e Frequência foram removidos - evolução futura")
        resultados['proposicoes'] = 0
        resultados['autores_mapeados'] = 0
        resultados['uploads_gcs'] = 0
        resultados['frequencias'] = 0
        resultados['detalhes_frequencia'] = 0
        
        # Resumo final
        print("\n📋 RESUMO COMPLETO DA COLETA")
        print("=" * 50)
        for tipo, quantidade in resultados.items():
            if quantidade > 0:
                print(f"   • {tipo.replace('_', ' ').capitalize()}: {quantidade} registros")
        
        total_geral = sum(v for v in resultados.values() if isinstance(v, int))
        print(f"\n🎯 TOTAL GERAL: {total_geral} registros processados")
        print("\n✅ COLETA COMPLETA FINALIZADA COM SUCESSO!")
        return resultados




if __name__ == "__main__":
    # Bloco para permitir a execução standalone do script para testes
    print("--- INICIANDO COLETA DE DADOS DE REFERÊNCIA ---")
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    from models.database import get_db
    
    db_session = next(get_db())
    
    try:
        coletor = ColetorDadosCamara()
        resultados = coletor.executar_coleta_completa(db_session)
        print(f"\n--- COLETA FINALIZADA ---")
        print(f"Total de registros processados: {sum(resultados.values())}")
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()
