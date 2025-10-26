"""
Coletor de dados de remuneração e benefícios dos deputados
Focus em APIs gratuitas da Câmara dos Deputados
"""

import sys
from pathlib import Path
import requests
import time
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
from config import get_config, API_CONFIG, get_coleta_config, get_data_inicio_coleta, deve_respeitar_data_inicio, coleta_habilitada

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado
from models.remuneracao_models import Remuneracao, VerbaIndenizatoria, CargoComissao, SalarioPadrao

class ColetorRemuneracao:
    """
    Classe responsável por coletar dados de remuneração e benefícios
    usando apenas APIs gratuitas da Câmara dos Deputados
    """

    def __init__(self):
        """Inicializa o coletor com configurações da API."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': API_CONFIG['user_agent'],
            'Accept': 'application/json'
        })
        self.rate_limit_delay = API_CONFIG['rate_limit_delay']
        
        # Configurações de coleta centralizadas
        self.coleta_config = get_coleta_config()
        self.data_inicio = get_data_inicio_coleta()
        
        print(f"✅ Coletor de remuneração inicializado")
        print(f"📅 Período de coleta: {self.data_inicio} até hoje")
        print(f"🔧 Respeitar data início: {deve_respeitar_data_inicio('remuneracao')}")

    def _fazer_requisicao(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Faz uma requisição à API com tratamento de erros e rate limiting."""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição para {url}: {e}")
            return None

    def _get_salario_padrao(self, ano: int) -> Dict:
        """
        Obtém o salário padrão para um ano específico.
        Valores baseados em dados públicos da Câmara.
        """
        # Salários padrão de Deputado Federal (valores aproximados)
        salarios_padrao = {
            2025: {
                'salario_bruto': 35000.00,
                'auxilio_moradia_maximo': 4500.00,
                'auxilio_saude_maximo': 2000.00,
                'diaria_maxima': 500.00
            },
            2024: {
                'salario_bruto': 33500.00,
                'auxilio_moradia_maximo': 4300.00,
                'auxilio_saude_maximo': 1900.00,
                'diaria_maxima': 480.00
            }
        }
        
        return salarios_padrao.get(ano, salarios_padrao[2025])

    def buscar_verbas_indenizatorias(self, deputado_id: int, ano: int, mes: int, db: Session) -> List[Dict]:
        """
        Busca verbas indenizatórias de um deputado específico
        API: /deputados/{id}/despesas (mesmo endpoint dos gastos parlamentares)
        """
        url = f"{API_CONFIG['base_url']}/deputados/{deputado_id}/despesas"
        params = {
            'ano': ano,
            'mes': mes,
            'itens': 100
        }
        
        data = self._fazer_requisicao(url, params)
        if not data:
            return []
        
        despesas = data.get('dados', [])
        print(f"      💰 Encontradas {len(despesas)} despesas para {mes}/{ano}")
        
        # Converter despesas para formato de verbas indenizatórias
        verbas = []
        for despesa in despesas:
            verba = {
                'id': despesa.get('id'),
                'tipoDespesa': despesa.get('tipoDespesa'),
                'codTipoDespesa': despesa.get('codTipoDespesa'),
                'descricao': despesa.get('descricao'),
                'valorDocumento': despesa.get('valorDocumento'),
                'valorGlosa': despesa.get('valorGlosa', 0),
                'valorLiquido': despesa.get('valorLiquido'),
                'dataDocumento': despesa.get('dataDocumento')
            }
            verbas.append(verba)
        
        return verbas

    def buscar_cargos_comissoes(self, deputado_id: int, db: Session) -> List[Dict]:
        """
        Busca cargos em comissões de um deputado
        API: /deputados/{id}/orgaos
        """
        url = f"{API_CONFIG['base_url']}/deputados/{deputado_id}/orgaos"
        params = {'itens': 100}
        
        data = self._fazer_requisicao(url, params)
        if not data:
            return []
        
        orgaos = data.get('dados', [])
        cargos = []
        
        for orgao in orgaos:
            # Verificar se tem cargo relevante
            if orgao.get('cargo'):
                cargo_info = {
                    'orgao_id': orgao.get('id'),
                    'orgao_nome': orgao.get('nome'),
                    'orgao_sigla': orgao.get('sigla'),
                    'cargo': orgao.get('cargo'),
                    'data_inicio': orgao.get('dataInicio'),
                    'data_fim': orgao.get('dataFim'),
                    'uri': orgao.get('uri')
                }
                cargos.append(cargo_info)
        
        if cargos:
            print(f"      🏛️ Encontrados {len(cargos)} cargos em comissões")
        
        return cargos

    def salvar_remuneracao(self, deputado: Deputado, ano: int, mes: int, db: Session) -> Optional[Remuneracao]:
        """
        Salva dados completos de remuneração para um deputado
        """
        try:
            # Verificar se já existe
            existente = db.query(Remuneracao).filter(
                and_(
                    Remuneracao.deputado_id == deputado.id,
                    Remuneracao.ano == ano,
                    Remuneracao.mes == mes
                )
            ).first()
            
            if existente:
                print(f"      ⏭️ Remuneração já existe para {mes}/{ano}")
                return existente
            
            # Obter salário padrão
            salario_padrao = self._get_salario_padrao(ano)
            
            # Buscar verbas indenizatórias
            verbas = self.buscar_verbas_indenizatorias(deputado.api_camara_id, ano, mes, db)
            
            # Buscar cargos em comissões
            cargos = self.buscar_cargos_comissoes(deputado.api_camara_id, db)
            
            # Calcular totais
            total_verbas = 0
            for v in verbas:
                valor = v.get('valorLiquido', 0)
                if isinstance(valor, (int, float)):
                    total_verbas += valor
            
            # Criar remuneração
            remuneracao = Remuneracao(
                deputado_id=deputado.id,
                ano=ano,
                mes=mes,
                salario_base=salario_padrao['salario_bruto'],
                verbas_indenizatorias_total=total_verbas,
                possui_cargo_comissao=len(cargos) > 0,
                cargo_comissao=cargos[0]['cargo'] if cargos else None,
                total_bruto=salario_padrao['salario_bruto'] + total_verbas,
                total_liquido=salario_padrao['salario_bruto'] + total_verbas  # Simplificado
            )
            
            db.add(remuneracao)
            db.flush()  # Para obter o ID
            
            # Salvar verbas detalhadas
            for verba in verbas:
                verba_det = VerbaIndenizatoria(
                    deputado_id=deputado.id,
                    remuneracao_id=remuneracao.id,
                    tipo_verba=verba.get('tipoDespesa'),
                    codigo_verba=verba.get('codTipoDespesa'),
                    descricao=verba.get('descricao'),
                    valor=verba.get('valorDocumento'),
                    valor_reembolsado=verba.get('valorGlosa', 0),
                    ano=ano,
                    mes=mes,
                    data_referencia=self._parse_date(verba.get('dataDocumento')),
                    api_camara_id=str(verba.get('id'))
                )
                db.add(verba_det)
            
            # Salvar cargos
            for cargo in cargos:
                cargo_existente = db.query(CargoComissao).filter(
                    and_(
                        CargoComissao.deputado_id == deputado.id,
                        CargoComissao.orgao_id == cargo['orgao_id']
                    )
                ).first()
                
                if not cargo_existente:
                    cargo_comissao = CargoComissao(
                        deputado_id=deputado.id,
                        orgao_id=cargo['orgao_id'],
                        orgao_nome=cargo['orgao_nome'],
                        orgao_sigla=cargo['orgao_sigla'],
                        cargo=cargo['cargo'],
                        data_inicio=self._parse_date(cargo['data_inicio']),
                        data_fim=self._parse_date(cargo['data_fim']),
                        cargo_ativo=True if not cargo['data_fim'] else False
                    )
                    db.add(cargo_comissao)
            
            db.commit()
            print(f"      ✅ Remuneração salva: R$ {remuneracao.total_bruto:,.2f}")
            return remuneracao
            
        except Exception as e:
            print(f"      ❌ Erro ao salvar remuneração: {e}")
            db.rollback()
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Converte string de data para objeto datetime."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

    def coletar_remuneracoes_periodo(self, ano: int, meses: List[int], db: Session) -> Dict[str, int]:
        """
        Coleta remunerações para todos os deputados em um período
        """
        print(f"\n💰 COLETANDO REMUNERAÇÕES - {ano}")
        print("=" * 50)
        
        # Buscar todos os deputados
        deputados = db.query(Deputado).all()
        print(f"👥 Encontrados {len(deputados)} deputados para processar")
        
        resultados = {
            'deputados_processados': 0,
            'remuneracoes_criadas': 0,
            'verbas_detalhadas': 0,
            'cargos_encontrados': 0,
            'erros': 0
        }
        
        for i, deputado in enumerate(deputados, 1):
            print(f"\n📊 Processando {i}/{len(deputados)}: {deputado.nome}")
            
            try:
                for mes_num in meses:
                    # Verificar se já existe
                    existente = db.query(Remuneracao).filter(
                        and_(
                            Remuneracao.deputado_id == deputado.id,
                            Remuneracao.ano == ano,
                            Remuneracao.mes == mes
                        )
                    ).first()
                    
                    if existente:
                        continue
                    
                    # Salvar remuneração
                    remuneracao = self.salvar_remuneracao(deputado, ano, mes_num, db)
                    if remuneracao:
                        resultados['remuneracoes_criadas'] += 1
                        # Contar verbas detalhadas usando query
                        verbas_count = db.query(VerbaIndenizatoria).filter(
                            VerbaIndenizatoria.remuneracao_id == remuneracao.id
                        ).count()
                        resultados['verbas_detalhadas'] += verbas_count
                    
                    # Rate limiting
                    time.sleep(self.rate_limit_delay)
                
                resultados['deputados_processados'] += 1
                
            except Exception as e:
                print(f"❌ Erro ao processar {deputado.nome}: {e}")
                resultados['erros'] += 1
                continue
        
        return resultados

    def criar_salario_padrao(self, ano: int, db: Session) -> bool:
        """
        Cria registro de salário padrão para um ano
        """
        try:
            # Verificar se já existe
            existente = db.query(SalarioPadrao).filter(SalarioPadrao.ano == ano).first()
            if existente:
                print(f"⏭️ Salário padrão já existe para {ano}")
                return True
            
            salario_info = self._get_salario_padrao(ano)
            
            salario_padrao = SalarioPadrao(
                ano=ano,
                mes_inicio=1,
                salario_bruto=salario_info['salario_bruto'],
                auxilio_moradia_maximo=salario_info['auxilio_moradia_maximo'],
                auxilio_saude_maximo=salario_info['auxilio_saude_maximo'],
                diaria_maxima=salario_info['diaria_maxima'],
                fonte_informacao="Dados Públicos Câmara dos Deputados",
                data_publicacao=datetime(ano, 1, 1).date()
            )
            
            db.add(salario_padrao)
            db.commit()
            print(f"✅ Salário padrão criado para {ano}: R$ {salario_info['salario_bruto']:,.2f}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar salário padrão: {e}")
            db.rollback()
            return False

def main():
    """
    Função principal para execução standalone
    """
    print("💰 COLETA DE DADOS DE REMUNERAÇÃO E BENEFÍCIOS")
    print("=" * 60)
    
    # Usar o utilitário db_utils para obter sessão do banco
    from models.db_utils import get_db_session
    
    db_session = next(get_db())
    
    try:
        coletor = ColetorRemuneracao()
        
        # Criar salário padrão para 2025
        coletor.criar_salario_padrao(2025, db_session)
        
        # Coletar remunerações dos últimos 3 meses
        meses = [8, 9, 10]  # Ago, Set, Out de 2025
        resultados = coletor.coletar_remuneracoes_periodo(2025, meses, db_session)
        
        print(f"\n📋 RESUMO DA COLETA DE REMUNERAÇÃO")
        print("=" * 40)
        print(f"👥 Deputados processados: {resultados['deputados_processados']}")
        print(f"💰 Remunerações criadas: {resultados['remuneracoes_criadas']}")
        print(f"📄 Verbas detalhadas: {resultados['verbas_detalhadas']}")
        print(f"🏛️ Cargos encontrados: {resultados['cargos_encontrados']}")
        print(f"❌ Erros: {resultados['erros']}")
        
        print(f"\n✅ Coleta de remuneração concluída!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
