"""
Script simplificado para cruzar dados de emendas parlamentares com informações dos deputados
Versão robusta que evita erros de dados nulos
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar modelos
import models
from models.database import get_db
from models.politico_models import Deputado, Mandato
from models.base_models import Partido, Estado
from models.emenda_models import EmendaParlamentar, RankingEmendas
from models.financeiro_models import GastoParlamentar

class CruzamentoSimplificado:
    """
    Classe simplificada para cruzamento de dados
    """

    def __init__(self):
        """Inicializa o sistema de cruzamento."""
        print("✅ Sistema de Cruzamento Simplificado inicializado")

    def gerar_analise_completa(self, db: Session) -> Dict[str, Any]:
        """
        Gera análise completa de forma segura
        """
        try:
            print("\n🔍 GERANDO ANÁLISE SIMPLIFICADA")
            print("=" * 50)
            
            # 1. Resumo geral dos dados
            resumo = self._gerar_resumo_geral(db)
            
            # 2. Top deputados por valor em emendas
            top_deputados = self._analisar_top_deputados(db)
            
            # 3. Análise por partido
            analise_partidos = self._analisar_partidos_simplificado(db)
            
            # 4. Comparação com gastos
            comparacao_gastos = self._comparar_gastos_simplificado(db)
            
            # 5. Insights básicos
            insights = self._gerar_insights_simplificado(db)
            
            resultado = {
                "resumo_geral": resumo,
                "top_deputados": top_deputados,
                "analise_partidos": analise_partidos,
                "comparacao_gastos": comparacao_gastos,
                "insights": insights,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            
            print(f"✅ Análise simplificada gerada com sucesso!")
            return resultado
            
        except Exception as e:
            print(f"❌ Erro ao gerar análise: {e}")
            return {"erro": str(e)}

    def _gerar_resumo_geral(self, db: Session) -> Dict[str, Any]:
        """
        Gera resumo geral dos dados de forma segura
        """
        try:
            # Contagens básicas
            total_deputados = db.query(Deputado).count()
            total_emendas = db.query(EmendaParlamentar).count()
            total_gastos = db.query(GastoParlamentar).count()
            
            # Valores totais com segurança
            valor_total_emendas = db.query(func.sum(EmendaParlamentar.valor_empenhado)).scalar() or 0
            valor_total_gastos = db.query(func.sum(GastoParlamentar.valor_documento)).scalar() or 0
            
            # Distribuição por ano
            emendas_por_ano = db.query(
                EmendaParlamentar.ano,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_empenhado).label('valor_total')
            ).group_by(EmendaParlamentar.ano).all()
            
            return {
                "total_deputados": total_deputados,
                "total_emendas": total_emendas,
                "total_gastos": total_gastos,
                "valor_total_emendas": float(valor_total_emendas),
                "valor_total_gastos": float(valor_total_gastos),
                "taxa_execucao_geral": self._calcular_taxa_execucao_geral(db),
                "emendas_por_ano": [
                    {
                        "ano": ano,
                        "quantidade": quantidade,
                        "valor_total": float(valor_total or 0)
                    }
                    for ano, quantidade, valor_total in emendas_por_ano
                ]
            }
        except Exception as e:
            print(f"⚠️ Erro no resumo geral: {e}")
            return {"erro": str(e)}

    def _calcular_taxa_execucao_geral(self, db: Session) -> float:
        """
        Calcula taxa de execução geral de forma segura
        """
        try:
            total_empenhado = db.query(func.sum(EmendaParlamentar.valor_empenhado)).scalar() or 0
            total_pago = db.query(func.sum(EmendaParlamentar.valor_pago)).scalar() or 0
            
            if total_empenhado > 0:
                return round(float(total_pago) / float(total_empenhado) * 100, 2)
            return 0.0
        except:
            return 0.0

    def _analisar_top_deputados(self, db: Session) -> Dict[str, Any]:
        """
        Analisa top deputados por valor em emendas
        """
        try:
            print("\n📊 Analisando top deputados...")
            
            # Query simplificada para evitar joins complexos
            query = db.query(
                EmendaParlamentar.deputado_id,
                Deputado.nome.label('deputado_nome'),
                func.count(EmendaParlamentar.id).label('quantidade_emendas'),
                func.sum(EmendaParlamentar.valor_empenhado).label('valor_total_emendado'),
                func.sum(EmendaParlamentar.valor_pago).label('valor_total_pago'),
                func.avg(EmendaParlamentar.valor_empenhado).label('valor_medio_emenda')
            ).join(
                Deputado, EmendaParlamentar.deputado_id == Deputado.id
            ).group_by(
                EmendaParlamentar.deputado_id, Deputado.nome
            ).order_by(
                desc(func.sum(EmendaParlamentar.valor_empenhado))
            ).limit(10).all()
            
            resultado = []
            for row in query:
                taxa_execucao = 0.0
                if row.valor_total_emendado and row.valor_total_emendado > 0:
                    taxa_execucao = round(float(row.valor_total_pago or 0) / float(row.valor_total_emendado) * 100, 2)
                
                resultado.append({
                    "deputado": row.deputado_nome,
                    "quantidade_emendas": row.quantidade_emendas,
                    "valor_total_emendado": float(row.valor_total_emendado or 0),
                    "valor_total_pago": float(row.valor_total_pago or 0),
                    "valor_medio_emenda": float(row.valor_medio_emenda or 0),
                    "taxa_execucao": taxa_execucao
                })
            
            return {
                "top_valor": resultado,
                "total_analisados": len(resultado)
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de top deputados: {e}")
            return {"erro": str(e)}

    def _analisar_partidos_simplificado(self, db: Session) -> Dict[str, Any]:
        """
        Analisa emendas por partido de forma simplificada
        """
        try:
            print("\n🏛️ Analisando partidos...")
            
            # Query com join para obter informações do partido
            query = db.query(
                Partido.sigla.label('partido_sigla'),
                Partido.nome.label('partido_nome'),
                func.count(func.distinct(Deputado.id)).label('quantidade_deputados'),
                func.count(EmendaParlamentar.id).label('quantidade_emendas'),
                func.sum(EmendaParlamentar.valor_empenhado).label('valor_total_emendado'),
                func.sum(EmendaParlamentar.valor_pago).label('valor_total_pago')
            ).join(
                Mandato, Partido.id == Mandato.partido_id
            ).join(
                Deputado, Mandato.deputado_id == Deputado.id
            ).join(
                EmendaParlamentar, Deputado.id == EmendaParlamentar.deputado_id, isouter=True
            ).group_by(
                Partido.id, Partido.sigla, Partido.nome
            ).order_by(
                desc(func.sum(EmendaParlamentar.valor_empenhado))
            ).all()
            
            resultado = []
            for row in query:
                taxa_execucao = 0.0
                if row.valor_total_emendado and row.valor_total_emendado > 0:
                    taxa_execucao = round(float(row.valor_total_pago or 0) / float(row.valor_total_emendado) * 100, 2)
                
                resultado.append({
                    "partido": row.partido_sigla,
                    "partido_nome": row.partido_nome,
                    "quantidade_deputados": row.quantidade_deputados,
                    "quantidade_emendas": row.quantidade_emendas,
                    "valor_emendado": float(row.valor_total_emendado or 0),
                    "valor_pago": float(row.valor_total_pago or 0),
                    "taxa_execucao": taxa_execucao
                })
            
            return {
                "partidos": resultado,
                "total_analisados": len(resultado)
            }
        except Exception as e:
            print(f"⚠️ Erro na análise de partidos: {e}")
            return {"erro": str(e)}

    def _comparar_gastos_simplificado(self, db: Session) -> Dict[str, Any]:
        """
        Compara valores de emendas com gastos de forma simplificada
        """
        try:
            print("\n💰 Comparando com gastos...")
            
            # Dados gerais
            total_emendas = db.query(func.sum(EmendaParlamentar.valor_empenhado)).scalar() or 0
            total_gastos = db.query(func.sum(GastoParlamentar.valor_documento)).scalar() or 0
            
            # Top deputados que tem ambos os dados
            query = db.query(
                Deputado.nome.label('deputado'),
                func.sum(EmendaParlamentar.valor_empenhado).label('total_emendas'),
                func.sum(GastoParlamentar.valor_documento).label('total_gastos')
            ).join(
                EmendaParlamentar, Deputado.id == EmendaParlamentar.deputado_id, isouter=True
            ).join(
                GastoParlamentar, Deputado.id == GastoParlamentar.deputado_id, isouter=True
            ).group_by(
                Deputado.id, Deputado.nome
            ).having(
                and_(
                    func.sum(EmendaParlamentar.valor_empenhado) > 0,
                    func.sum(GastoParlamentar.valor_documento) > 0
                )
            ).limit(10).all()
            
            resultado = []
            for row in query:
                relacao = 0.0
                if row.total_gastos and row.total_gastos > 0:
                    relacao = round(float(row.total_emendas or 0) / float(row.total_gastos), 2)
                
                resultado.append({
                    "deputado": row.deputado,
                    "total_emendas": float(row.total_emendas or 0),
                    "total_gastos": float(row.total_gastos or 0),
                    "relacao_emendas_gastos": relacao
                })
            
            return {
                "resumo_geral": {
                    "total_emendas": float(total_emendas),
                    "total_gastos": float(total_gastos),
                    "relacao_geral": round(float(total_emendas) / float(total_gastos), 2) if total_gastos > 0 else 0
                },
                "top_relacao": resultado
            }
        except Exception as e:
            print(f"⚠️ Erro na comparação de gastos: {e}")
            return {"erro": str(e)}

    def _gerar_insights_simplificado(self, db: Session) -> List[Dict[str, Any]]:
        """
        Gera insights básicos de forma segura
        """
        try:
            print("\n💡 Gerando insights...")
            
            insights = []
            
            # Insight 1: Taxa de execução geral
            taxa_geral = self._calcular_taxa_execucao_geral(db)
            insights.append({
                "tipo": "execucao_geral",
                "titulo": "Taxa de Execução Geral",
                "valor": f"{taxa_geral}%",
                "descricao": "Percentual total de emendas executadas em relação ao valor empenhado"
            })
            
            # Insight 2: Top 3 deputados por valor
            top_deps = db.query(
                Deputado.nome,
                func.sum(EmendaParlamentar.valor_empenhado).label('total')
            ).join(
                EmendaParlamentar, Deputado.id == EmendaParlamentar.deputado_id
            ).group_by(
                Deputado.id, Deputado.nome
            ).order_by(
                desc(func.sum(EmendaParlamentar.valor_empenhado))
            ).limit(3).all()
            
            top_nomes = [f"{dep.nome} (R$ {float(dep.total or 0):,.2f})" for dep in top_deps]
            insights.append({
                "tipo": "top_deputados",
                "titulo": "Top 3 Deputados por Valor",
                "valor": top_nomes,
                "descricao": "Deputados com maior valor total em emendas"
            })
            
            # Insight 3: Volume de dados
            total_emendas = db.query(EmendaParlamentar).count()
            total_deputados = db.query(Deputado).count()
            
            insights.append({
                "tipo": "volume_dados",
                "titulo": "Volume de Dados Analisados",
                "valor": f"{total_emendas} emendas de {total_deputados} deputados",
                "descricao": "Quantidade total de registros no banco de dados"
            })
            
            return insights
        except Exception as e:
            print(f"⚠️ Erro nos insights: {e}")
            return [{"erro": str(e)}]

def main():
    """
    Função principal para execução standalone
    """
    print("🔍 CRUZAMENTO SIMPLIFICADO - EMENDAS vs DEPUTADOS")
    print("=" * 60)
    
    from models.db_utils import get_db_session
    
    db_session = get_db_session()
    
    try:
        cruzamento = CruzamentoSimplificado()
        
        # Gerar análise completa
        analise = cruzamento.gerar_analise_completa(db_session)
        
        if "erro" not in analise:
            print(f"\n📋 RESUMO DA ANÁLISE")
            print("=" * 30)
            
            resumo = analise["resumo_geral"]
            print(f"👥 Total de deputados: {resumo['total_deputados']}")
            print(f"📄 Total de emendas: {resumo['total_emendas']}")
            print(f"💰 Valor total emendas: R$ {resumo['valor_total_emendas']:,.2f}")
            print(f"💸 Valor total gastos: R$ {resumo['valor_total_gastos']:,.2f}")
            print(f"📈 Taxa de execução geral: {resumo['taxa_execucao_geral']}%")
            
            # Top 5 deputados por valor
            if "top_valor" in analise["top_deputados"]:
                print(f"\n🏆 TOP 5 DEPUTADOS - MAIOR VALOR EMENDAS")
                print("=" * 45)
                for i, dep in enumerate(analise["top_deputados"]["top_valor"][:5], 1):
                    print(f"{i}. {dep['deputado']}")
                    print(f"   💰 R$ {dep['valor_total_emendado']:,.2f} | 📊 {dep['quantidade_emendas']} emendas | 📈 {dep['taxa_execucao']}% execução")
            
            # Insights principais
            print(f"\n💡 INSIGHTS PRINCIPAIS")
            print("=" * 25)
            for insight in analise["insights"]:
                print(f"\n📌 {insight['titulo']}")
                print(f"   {insight['descricao']}")
                if isinstance(insight['valor'], list):
                    for item in insight['valor']:
                        print(f"   • {item}")
                else:
                    print(f"   📊 {insight['valor']}")
            
            print(f"\n📈 Análise gerada em: {analise['data_geracao']}")
        
        print(f"\n✅ Cruzamento simplificado concluído!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE O CRUZAMENTO: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
