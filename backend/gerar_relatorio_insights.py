#!/usr/bin/env python3
"""
Gerador de Relatório de Insights dos Dados Kritikos
Analisa todos os dados coletados (deputados, gastos, emendas, etc) e gera insights
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar modelos
from models.database import get_db
from models.politico_models import Deputado, Mandato
from models.emenda_models import EmendaParlamentar, RankingEmendas
from models.financeiro_models import GastoParlamentar
from models.remuneracao_models import Remuneracao, VerbaIndenizatoria
from models.ranking_models import CalculoIDP, SituacaoLegal

class AnalisadorInsights:
    """
    Classe principal para análise de dados e geração de insights
    """
    
    def __init__(self):
        """Inicializa o analisador"""
        self.db = next(get_db())
        self.insights = {}
        self.data_geracao = datetime.now()
        
        print("🔍 INICIANDO ANÁLISE DE INSIGHTS KRITIKOS")
        print("=" * 60)
        print(f"📅 Data/Hora: {self.data_geracao.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🗄️  Banco: PostgreSQL")
        print("=" * 60)

    def analisar_deputados(self) -> Dict[str, Any]:
        """
        Analisa dados demográficos e políticos dos deputados
        """
        print("\n👥 ANALISANDO DADOS DE DEPUTADOS")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Total de deputados
            total_deputados = self.db.query(Deputado).count()
            insights['total_deputados'] = total_deputados
            
            # Distribuição por gênero
            genero_dist = self.db.query(
                Deputado.sexo, 
                func.count(Deputado.id).label('quantidade')
            ).group_by(Deputado.sexo).all()
            
            insights['distribuicao_genero'] = {
                'M': next((q for s, q in genero_dist if s == 'M'), 0),
                'F': next((q for s, q in genero_dist if s == 'F'), 0),
                'outros': next((q for s, q in genero_dist if s not in ['M', 'F']), 0)
            }
            
            # Distribuição por UF
            uf_dist = self.db.query(
                Mandato.estado_id,
                func.count(Deputado.id).label('quantidade')
            ).join(Mandato).group_by(Mandato.estado_id).order_by(desc('quantidade')).limit(10).all()
            
            insights['top_ufs'] = [{'uf': uf, 'quantidade': q} for uf, q in uf_dist]
            
            # Distribuição por escolaridade
            escol_dist = self.db.query(
                Deputado.escolaridade,
                func.count(Deputado.id).label('quantidade')
            ).filter(Deputado.escolaridade.isnot(None)).group_by(Deputado.escolaridade).order_by(desc('quantidade')).all()
            
            insights['distribuicao_escolaridade'] = [{'escolaridade': e, 'quantidade': q} for e, q in escol_dist]
            
            # Idade média
            idade_media = self.db.query(
                func.avg(func.age(Deputado.data_nascimento))
            ).filter(Deputado.data_nascimento.isnot(None)).scalar()
            
            if idade_media:
                insights['idade_media_anos'] = idade_media.days / 365.25
            
            print(f"   ✅ Total de deputados: {total_deputados}")
            print(f"   ✅ Gênero - M: {insights['distribuicao_genero']['M']}, F: {insights['distribuicao_genero']['F']}")
            print(f"   ✅ UF com mais deputados: {insights['top_ufs'][0]['uf'] if insights['top_ufs'] else 'N/A'}")
            
        except Exception as e:
            print(f"   ❌ Erro na análise de deputados: {e}")
            insights['erro'] = str(e)
        
        return insights

    def analisar_emendas(self) -> Dict[str, Any]:
        """
        Analisa dados de emendas parlamentares
        """
        print("\n📄 ANALISANDO DADOS DE EMENDAS")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Total de emendas
            total_emendas = self.db.query(EmendaParlamentar).count()
            insights['total_emendas'] = total_emendas
            
            # Distribuição por tipo
            tipo_dist = self.db.query(
                EmendaParlamentar.tipo_emenda,
                func.count(EmendaParlamentar.id).label('quantidade')
            ).group_by(EmendaParlamentar.tipo_emenda).order_by(desc('quantidade')).all()
            
            insights['distribuicao_tipo'] = [{'tipo': t, 'quantidade': q} for t, q in tipo_dist]
            
            # Distribuição por ano
            ano_dist = self.db.query(
                EmendaParlamentar.ano,
                func.count(EmendaParlamentar.id).label('quantidade')
            ).group_by(EmendaParlamentar.ano).order_by(desc(EmendaParlamentar.ano)).all()
            
            insights['distribuicao_ano'] = [{'ano': a, 'quantidade': q} for a, q in ano_dist]
            
            # Valor total de emendas
            valor_total = self.db.query(
                func.sum(EmendaParlamentar.valor_emenda)
            ).filter(EmendaParlamentar.valor_emenda.isnot(None)).scalar() or 0
            
            insights['valor_total_emendas'] = float(valor_total)
            
            # Valor médio por emenda
            valor_medio = self.db.query(
                func.avg(EmendaParlamentar.valor_emenda)
            ).filter(EmendaParlamentar.valor_emenda.isnot(None)).scalar() or 0
            
            insights['valor_medio_emenda'] = float(valor_medio)
            
            # Top 10 deputados com mais emendas
            top_deputados_emendas = self.db.query(
                Deputado.nome,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total')
            ).join(EmendaParlamentar).filter(
                EmendaParlamentar.deputado_id.isnot(None)
            ).group_by(Deputado.id, Deputado.nome).order_by(desc('quantidade')).limit(10).all()
            
            insights['top_deputados_emendas'] = [
                {'nome': nome, 'quantidade': q, 'valor_total': float(v or 0)}
                for nome, q, v in top_deputados_emendas
            ]
            
            # Beneficiários mais frequentes
            top_beneficiarios = self.db.query(
                EmendaParlamentar.beneficiario_principal,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total')
            ).filter(
                EmendaParlamentar.beneficiario_principal.isnot(None)
            ).group_by(EmendaParlamentar.beneficiario_principal).order_by(desc('quantidade')).limit(10).all()
            
            insights['top_beneficiarios'] = [
                {'beneficiario': b, 'quantidade': q, 'valor_total': float(v or 0)}
                for b, q, v in top_beneficiarios
            ]
            
            print(f"   ✅ Total de emendas: {total_emendas}")
            print(f"   ✅ Valor total: R$ {valor_total:,.2f}")
            print(f"   ✅ Valor médio: R$ {valor_medio:,.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro na análise de emendas: {e}")
            insights['erro'] = str(e)
        
        return insights

    def analisar_gastos(self) -> Dict[str, Any]:
        """
        Analisa dados de gastos parlamentares
        """
        print("\n💸 ANALISANDO DADOS DE GASTOS")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Total de gastos
            total_gastos = self.db.query(GastoParlamentar).count()
            insights['total_gastos'] = total_gastos
            
            # Valor total gasto
            valor_total = self.db.query(
                func.sum(GastoParlamentar.valor_liquido)
            ).filter(GastoParlamentar.valor_liquido.isnot(None)).scalar() or 0
            
            insights['valor_total_gastos'] = float(valor_total)
            
            # Distribuição por tipo de despesa
            tipo_despesa_dist = self.db.query(
                GastoParlamentar.tipo_despesa,
                func.count(GastoParlamentar.id).label('quantidade'),
                func.sum(GastoParlamentar.valor_liquido).label('valor_total')
            ).group_by(GastoParlamentar.tipo_despesa).order_by(desc('valor_total')).limit(10).all()
            
            insights['top_tipos_despesa'] = [
                {'tipo': t, 'quantidade': q, 'valor_total': float(v or 0)}
                for t, q, v in tipo_despesa_dist
            ]
            
            # Top 10 fornecedores
            top_fornecedores = self.db.query(
                GastoParlamentar.fornecedor_nome,
                func.count(GastoParlamentar.id).label('quantidade'),
                func.sum(GastoParlamentar.valor_liquido).label('valor_total')
            ).filter(
                GastoParlamentar.fornecedor_nome.isnot(None)
            ).group_by(GastoParlamentar.fornecedor_nome).order_by(desc('valor_total')).limit(10).all()
            
            insights['top_fornecedores'] = [
                {'fornecedor': f, 'quantidade': q, 'valor_total': float(v or 0)}
                for f, q, v in top_fornecedores
            ]
            
            # Gasto médio por deputado
            gasto_medio_deputado = self.db.query(
                Deputado.nome,
                func.sum(GastoParlamentar.valor_liquido).label('total_gasto')
            ).join(GastoParlamentar).group_by(Deputado.id, Deputado.nome).order_by(desc('total_gasto')).limit(10).all()
            
            insights['top_deputados_gastos'] = [
                {'nome': nome, 'total_gasto': float(g or 0)}
                for nome, g in gasto_medio_deputado
            ]
            
            # Distribuição mensal
            mensal_dist = self.db.query(
                GastoParlamentar.ano,
                GastoParlamentar.mes,
                func.sum(GastoParlamentar.valor_liquido).label('valor_total')
            ).group_by(GastoParlamentar.ano, GastoParlamentar.mes).order_by(GastoParlamentar.ano, GastoParlamentar.mes).all()
            
            insights['distribuicao_mensal'] = [
                {'ano': a, 'mes': m, 'valor_total': float(v or 0)}
                for a, m, v in mensal_dist
            ]
            
            print(f"   ✅ Total de registros: {total_gastos}")
            print(f"   ✅ Valor total: R$ {valor_total:,.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro na análise de gastos: {e}")
            insights['erro'] = str(e)
        
        return insights

    def analisar_remuneracao(self) -> Dict[str, Any]:
        """
        Analisa dados de remuneração dos deputados
        """
        print("\n💰 ANALISANDO DADOS DE REMUNERAÇÃO")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Total de registros de remuneração
            total_registros = self.db.query(Remuneracao).count()
            insights['total_registros_remuneracao'] = total_registros
            
            # Remuneração média
            remuneracao_media = self.db.query(
                func.avg(Remuneracao.total_bruto)
            ).filter(Remuneracao.total_bruto.isnot(None)).scalar() or 0
            
            insights['remuneracao_media'] = float(remuneracao_media)
            
            # Distribuição por tipo de verba
            verbas_dist = self.db.query(
                VerbaIndenizatoria.tipo_verba,
                func.count(VerbaIndenizatoria.id).label('quantidade'),
                func.sum(VerbaIndenizatoria.valor).label('valor_total')
            ).group_by(VerbaIndenizatoria.tipo_verba).order_by(desc('valor_total')).limit(10).all()
            
            insights['top_verbas'] = [
                {'tipo': t, 'quantidade': q, 'valor_total': float(v or 0)}
                for t, q, v in verbas_dist
            ]
            
            # Top 10 remunerações mais altas
            top_remuneracoes = self.db.query(
                Deputado.nome,
                func.avg(Remuneracao.total_bruto).label('remuneracao_media')
            ).join(Remuneracao).filter(
                Remuneracao.total_bruto.isnot(None)
            ).group_by(Deputado.id, Deputado.nome).order_by(desc('remuneracao_media')).limit(10).all()
            
            insights['top_remuneracoes'] = [
                {'nome': nome, 'remuneracao_media': float(r)}
                for nome, r in top_remuneracoes
            ]
            
            # Evolução temporal da remuneração
            evolucao_temporal = self.db.query(
                Remuneracao.ano,
                Remuneracao.mes,
                func.avg(Remuneracao.total_bruto).label('media_mensal')
            ).group_by(Remuneracao.ano, Remuneracao.mes).order_by(Remuneracao.ano, Remuneracao.mes).all()
            
            insights['evolucao_temporal'] = [
                {'ano': a, 'mes': m, 'media_mensal': float(med)}
                for a, m, med in evolucao_temporal
            ]
            
            print(f"   ✅ Total de registros: {total_registros}")
            print(f"   ✅ Remuneração média: R$ {remuneracao_media:,.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro na análise de remuneração: {e}")
            insights['erro'] = str(e)
        
        return insights

    def analisar_rankings(self) -> Dict[str, Any]:
        """
        Analisa dados de rankings e desempenho
        """
        print("\n📈 ANALISANDO DADOS DE RANKINGS")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Total de cálculos IDP
            total_idp = self.db.query(CalculoIDP).count()
            insights['total_calculos_idp'] = total_idp
            
            # IDP médio
            idp_medio = self.db.query(
                func.avg(CalculoIDP.idp_final)
            ).filter(CalculoIDP.idp_final.isnot(None)).scalar() or 0
            
            insights['idp_medio'] = float(idp_medio)
            
            # Top 10 melhores IDP
            top_idp = self.db.query(
                Deputado.nome,
                CalculoIDP.idp_final,
                CalculoIDP.data_calculo
            ).join(CalculoIDP).order_by(desc(CalculoIDP.idp_final)).limit(10).all()
            
            insights['top_idp'] = [
                {'nome': nome, 'idp_final': float(idp), 'data': data.strftime('%d/%m/%Y')}
                for nome, idp, data in top_idp
            ]
            
            # Situações legais
            situacoes_legais = self.db.query(
                SituacaoLegal.tipo_situacao,
                func.count(SituacaoLegal.id).label('quantidade')
            ).group_by(SituacaoLegal.tipo_situacao).order_by(desc('quantidade')).all()
            
            insights['situacoes_legais'] = [
                {'tipo': t, 'quantidade': q}
                for t, q in situacoes_legais
            ]
            
            # Rankings de emendas
            rankings_emendas = self.db.query(
                Deputado.nome,
                RankingEmendas.quantidade_emendas,
                RankingEmendas.valor_total_emendas,
                RankingEmendas.ano_referencia
            ).join(RankingEmendas).order_by(desc(RankingEmendas.quantidade_emendas)).limit(10).all()
            
            insights['top_rankings_emendas'] = [
                {'nome': nome, 'quantidade': q, 'valor_total': float(v or 0), 'ano': a}
                for nome, q, v, a in rankings_emendas
            ]
            
            print(f"   ✅ Total de cálculos IDP: {total_idp}")
            print(f"   ✅ IDP médio: {idp_medio:.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro na análise de rankings: {e}")
            insights['erro'] = str(e)
        
        return insights

    def gerar_insights_cruzados(self) -> Dict[str, Any]:
        """
        Gera insights cruzados entre diferentes módulos
        """
        print("\n🔗 GERANDO INSIGHTS CRUZADOS")
        print("-" * 40)
        
        insights = {}
        
        try:
            # Correlação remuneração vs emendas
            correlacao_query = self.db.query(
                Deputado.nome,
                func.avg(Remuneracao.total_bruto).label('remuneracao_media'),
                func.count(EmendaParlamentar.id).label('quantidade_emendas'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_emendas')
            ).outerjoin(Remuneracao).outerjoin(EmendaParlamentar).group_by(
                Deputado.id, Deputado.nome
            ).having(
                func.count(EmendaParlamentar.id) > 0
            ).all()
            
            insights['correlacao_remuneracao_emendas'] = [
                {
                    'nome': nome,
                    'remuneracao_media': float(r or 0),
                    'quantidade_emendas': q,
                    'valor_emendas': float(v or 0)
                }
                for nome, r, q, v in correlacao_query
            ]
            
            # Correlação gastos vs desempenho
            correlacao_gastos_desempenho = self.db.query(
                Deputado.nome,
                func.sum(GastoParlamentar.valor_liquido).label('total_gastos'),
                CalculoIDP.idp_final
            ).outerjoin(GastoParlamentar).outerjoin(CalculoIDP).group_by(
                Deputado.id, Deputado.nome, CalculoIDP.idp_final
            ).having(
                func.sum(GastoParlamentar.valor_liquido) > 0
            ).all()
            
            insights['correlacao_gastos_desempenho'] = [
                {
                    'nome': nome,
                    'total_gastos': float(g or 0),
                    'idp_final': float(idp) if idp else None
                }
                for nome, g, idp in correlacao_gastos_desempenho
            ]
            
            print(f"   ✅ Correlação remuneração vs emendas: {len(insights['correlacao_remuneracao_emendas'])} deputados")
            print(f"   ✅ Correlação gastos vs desempenho: {len(insights['correlacao_gastos_desempenho'])} deputados")
            
        except Exception as e:
            print(f"   ❌ Erro nos insights cruzados: {e}")
            insights['erro'] = str(e)
        
        return insights

    def gerar_relatorio_completo(self) -> Dict[str, Any]:
        """
        Gera o relatório completo com todos os insights
        """
        print("\n📊 GERANDO RELATÓRIO COMPLETO")
        print("=" * 60)
        
        relatorio = {
            'metadata': {
                'data_geracao': self.data_geracao.isoformat(),
                'versao': '1.0',
                'sistema': 'Kritikos Insights'
            },
            'insights': {}
        }
        
        # Executar todas as análises
        relatorio['insights']['deputados'] = self.analisar_deputados()
        relatorio['insights']['emendas'] = self.analisar_emendas()
        relatorio['insights']['gastos'] = self.analisar_gastos()
        relatorio['insights']['remuneracao'] = self.analisar_remuneracao()
        relatorio['insights']['rankings'] = self.analisar_rankings()
        relatorio['insights']['cruzados'] = self.gerar_insights_cruzados()
        
        # Gerar resumo executivo
        relatorio['resumo_executivo'] = self.gerar_resumo_executivo(relatorio['insights'])
        
        print("\n✅ RELATÓRIO GERADO COM SUCESSO!")
        print("=" * 60)
        
        return relatorio

    def gerar_resumo_executivo(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera um resumo executivo com os principais KPIs
        """
        resumo = {}
        
        try:
            # KPIs principais
            resumo['kpis_principais'] = {
                'total_deputados': insights.get('deputados', {}).get('total_deputados', 0),
                'total_emendas': insights.get('emendas', {}).get('total_emendas', 0),
                'valor_total_emendas': insights.get('emendas', {}).get('valor_total_emendas', 0),
                'total_gastos': insights.get('gastos', {}).get('total_gastos', 0),
                'valor_total_gastos': insights.get('gastos', {}).get('valor_total_gastos', 0),
                'remuneracao_media': insights.get('remuneracao', {}).get('remuneracao_media', 0),
                'idp_medio': insights.get('rankings', {}).get('idp_medio', 0)
            }
            
            # Principais destaques
            resumo['destaques'] = []
            
            # Destaque de gênero
            genero = insights.get('deputados', {}).get('distribuicao_genero', {})
            if genero.get('F', 0) > 0:
                percentual_f = (genero['F'] / genero.get('M', 1)) * 100
                resumo['destaques'].append(f"Mulheres representam {percentual_f:.1f}% dos deputados")
            
            # Destaque de emendas
            valor_emendas = insights.get('emendas', {}).get('valor_total_emendas', 0)
            if valor_emendas > 0:
                resumo['destaques'].append(f"Valor total de emendas: R$ {valor_emendas:,.2f}")
            
            # Destaque de gastos
            valor_gastos = insights.get('gastos', {}).get('valor_total_gastos', 0)
            if valor_gastos > 0:
                resumo['destaques'].append(f"Valor total de gastos: R$ {valor_gastos:,.2f}")
            
            # Destaque de IDP
            idp_medio = insights.get('rankings', {}).get('idp_medio', 0)
            if idp_medio > 0:
                resumo['destaques'].append(f"IDP médio dos deputados: {idp_medio:.2f}")
            
        except Exception as e:
            print(f"   ⚠️ Erro ao gerar resumo executivo: {e}")
            resumo['erro'] = str(e)
        
        return resumo

    def salvar_relatorio(self, relatorio: Dict[str, Any], formato: str = 'json') -> str:
        """
        Salva o relatório em diferentes formatos
        """
        timestamp = self.data_geracao.strftime('%Y%m%d_%H%M%S')
        
        if formato == 'json':
            filename = f"relatorio_insights_kritikos_{timestamp}.json"
            filepath = Path(__file__).parent / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"   💾 Relatório JSON salvo: {filepath}")
            return str(filepath)
        
        return ""

def main():
    """
    Função principal para execução
    """
    print("🚀 GERADOR DE RELATÓRIO DE INSIGHTS KRITIKOS")
    print("=" * 60)
    
    analisador = AnalisadorInsights()
    
    try:
        # Gerar relatório completo
        relatorio = analisador.gerar_relatorio_completo()
        
        # Salvar relatório
        arquivo_relatorio = analisador.salvar_relatorio(relatorio, 'json')
        
        print(f"\n🎉 RELATÓRIO GERADO COM SUCESSO!")
        print(f"📁 Arquivo: {arquivo_relatorio}")
        print(f"📊 Insights gerados para {len(relatorio['insights'])} módulos")
        
        # Exibir resumo
        resumo = relatorio.get('resumo_executivo', {})
        kpis = resumo.get('kpis_principais', {})
        
        print(f"\n📋 RESUMO EXECUTIVO:")
        print(f"   👥 Deputados: {kpis.get('total_deputados', 0)}")
        print(f"   📄 Emendas: {kpis.get('total_emendas', 0)}")
        print(f"   💰 Valor Emendas: R$ {kpis.get('valor_total_emendas', 0):,.2f}")
        print(f"   💸 Valor Gastos: R$ {kpis.get('valor_total_gastos', 0):,.2f}")
        print(f"   💵 Remuneração Média: R$ {kpis.get('remuneracao_media', 0):,.2f}")
        print(f"   📈 IDP Médio: {kpis.get('idp_medio', 0):.2f}")
        
        if resumo.get('destaques'):
            print(f"\n🌟 PRINCIPAIS DESTAQUES:")
            for destaque in resumo['destaques']:
                print(f"   • {destaque}")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A GERAÇÃO DO RELATÓRIO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analisador.db.close()

if __name__ == "__main__":
    main()
