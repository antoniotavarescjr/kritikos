#!/usr/bin/env python3
"""
Relatório de Visão dos Dados Coletados para Hackathon Kritikos 2025
Gera uma visão completa dos dados disponíveis para análise no hackathon

Autor: Kritikos Team
Data: Outubro/2025
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import json
from sqlalchemy import func

# Adicionar o diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from models.database import get_db
from models.politico_models import Deputado, Mandato
from models.base_models import Partido, Estado
from models.financeiro_models import GastoParlamentar
from models.proposicao_models import Proposicao, Votacao, VotoDeputado
from models.emenda_models import EmendaParlamentar, VotacaoEmenda

class RelatorioHackathon:
    """
    Gerador de relatório completo dos dados do hackathon
    """
    
    def __init__(self):
        """Inicializa o gerador de relatórios"""
        self.inicio_relatorio = datetime.now()
        self.dados = {}
        
        print("📊 GERADOR DE RELATÓRIO - HACKATHON KRITIKOS 2025")
        print("=" * 60)
        print(f"📅 Data/Hora: {self.inicio_relatorio.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🎯 Objetivo: Visão completa dos dados coletados para análise")
    
    def coletar_dados_gerais(self, db) -> Dict[str, Any]:
        """Coleta dados gerais do banco"""
        print("\n📊 COLETANDO DADOS GERAIS")
        print("=" * 40)
        
        dados = {
            'deputados': {},
            'partidos': {},
            'mandatos': {},
            'gastos': {},
            'votacoes': {},
            'proposicoes': {},
            'emendas': {}
        }
        
        # Deputados
        dados['deputados']['total'] = db.query(Deputado).count()
        dados['deputados']['em_exercicio'] = db.query(Deputado).filter(
            Deputado.situacao == 'Exercício'
        ).count()
        
        # Partidos
        dados['partidos']['total'] = db.query(Partido).count()
        
        # Mandatos
        dados['mandatos']['total'] = db.query(Mandato).count()
        
        # Gastos
        dados['gastos']['total'] = db.query(GastoParlamentar).count()
        
        # Votações
        dados['votacoes']['proposicoes'] = db.query(Votacao).count()
        dados['votacoes']['votos_deputados'] = db.query(VotoDeputado).count()
        dados['votacoes']['emendas'] = db.query(VotacaoEmenda).count()
        
        # Proposições
        dados['proposicoes']['total'] = db.query(Proposicao).count()
        
        # Emendas
        dados['emendas']['total'] = db.query(EmendaParlamentar).count()
        
        print(f"👥 Deputados: {dados['deputados']['total']} ({dados['deputados']['em_exercicio']} em exercício)")
        print(f"🏛️  Partidos: {dados['partidos']['total']}")
        print(f"💰 Gastos: {dados['gastos']['total']:,}")
        print(f"🗳️  Votações: {dados['votacoes']['proposicoes']} proposições + {dados['votacoes']['votos_deputados']:,} votos")
        print(f"📄 Proposições: {dados['proposicoes']['total']}")
        print(f"📝 Emendas: {dados['emendas']['total']}")
        
        return dados
    
    def analisar_deputados(self, db) -> Dict[str, Any]:
        """Analisa dados detalhados dos deputados"""
        print("\n👥 ANÁLISE DETALHADA - DEPUTADOS")
        print("=" * 40)
        
        analise = {
            'por_estado': {},
            'por_partido': {},
            'por_genero': {},
            'por_escolaridade': {},
            'top_gastos': []
        }
        
        # Análise por estado (através dos mandatos)
        estados = db.query(
            Estado.sigla,
            func.count(Deputado.id)
        ).join(Mandato, Mandato.deputado_id == Deputado.id)\
         .join(Estado, Estado.id == Mandato.estado_id)\
         .group_by(Estado.sigla)\
         .order_by(func.count(Deputado.id).desc()).all()
        
        for estado, count in estados[:10]:  # Top 10
            analise['por_estado'][estado] = count
        
        print(f"🗺️  Top 10 estados por número de deputados:")
        for estado, count in analise['por_estado'].items():
            print(f"   {estado}: {count} deputados")
        
        # Análise por partido
        partidos = db.query(
            Partido.sigla,
            func.count(Deputado.id)
        ).join(Mandato, Mandato.deputado_id == Deputado.id)\
         .join(Partido, Partido.id == Mandato.partido_id)\
         .group_by(Partido.sigla)\
         .order_by(func.count(Deputado.id).desc()).all()
        
        for partido, count in partidos[:10]:  # Top 10
            analise['por_partido'][partido] = count
        
        print(f"\n🏛️  Top 10 partidos por número de deputados:")
        for partido, count in analise['por_partido'].items():
            print(f"   {partido}: {count} deputados")
        
        # Análise por gênero
        generos = db.query(
            Deputado.sexo,
            func.count(Deputado.id)
        ).group_by(Deputado.sexo).all()
        
        for genero, count in generos:
            if genero:
                analise['por_genero'][genero] = count
        
        print(f"\n👤 Distribuição por gênero:")
        for genero, count in analise['por_genero'].items():
            print(f"   {genero}: {count} deputados")
        
        # Análise por escolaridade
        escolaridades = db.query(
            Deputado.escolaridade,
            func.count(Deputado.id)
        ).group_by(Deputado.escolaridade)\
         .order_by(func.count(Deputado.id).desc()).all()
        
        for esc, count in escolaridades[:5]:  # Top 5
            if esc:
                analise['por_escolaridade'][esc] = count
        
        print(f"\n🎓 Top 5 níveis de escolaridade:")
        for esc, count in analise['por_escolaridade'].items():
            print(f"   {esc}: {count} deputados")
        
        # Top gastos
        top_gastos = db.query(
            Deputado.nome,
            func.sum(GastoParlamentar.valor_liquido).label('total_gastos')
        ).join(GastoParlamentar, GastoParlamentar.deputado_id == Deputado.id)\
         .group_by(Deputado.id, Deputado.nome)\
         .order_by(func.sum(GastoParlamentar.valor_liquido).desc())\
         .limit(10).all()
        
        for nome, total in top_gastos:
            analise['top_gastos'].append({
                'nome': nome,
                'total_gastos': float(total)
            })
        
        print(f"\n💰 Top 10 deputados por gastos totais:")
        for i, item in enumerate(analise['top_gastos'], 1):
            print(f"   {i}. {item['nome']}: R$ {item['total_gastos']:,.2f}")
        
        return analise
    
    def analisar_gastos(self, db) -> Dict[str, Any]:
        """Analisa dados detalhados dos gastos"""
        print("\n💰 ANÁLISE DETALHADA - GASTOS PARLAMENTARES")
        print("=" * 40)
        
        analise = {
            'total_geral': 0,
            'por_mes': {},
            'por_categoria': {},
            'por_partido': {},
            'estatisticas': {}
        }
        
        # Total geral
        total_geral = db.query(func.sum(GastoParlamentar.valor_liquido)).scalar() or 0
        analise['total_geral'] = float(total_geral)
        
        print(f"💰 Total geral de gastos: R$ {analise['total_geral']:,.2f}")
        
        # Por mês
        gastos_mes = db.query(
            GastoParlamentar.ano,
            GastoParlamentar.mes,
            func.sum(GastoParlamentar.valor_liquido).label('total')
        ).group_by(GastoParlamentar.ano, GastoParlamentar.mes)\
         .order_by(GastoParlamentar.ano, GastoParlamentar.mes).all()
        
        for ano, mes, total in gastos_mes:
            chave = f"{ano}-{mes:02d}"
            analise['por_mes'][chave] = float(total)
        
        print(f"\n📅 Gastos por mês:")
        for mes, total in analise['por_mes'].items():
            print(f"   {mes}: R$ {total:,.2f}")
        
        # Por categoria
        gastos_cat = db.query(
            GastoParlamentar.tipo_despesa,
            func.sum(GastoParlamentar.valor_liquido).label('total'),
            func.count(GastoParlamentar.id).label('quantidade')
        ).group_by(GastoParlamentar.tipo_despesa)\
         .order_by(func.sum(GastoParlamentar.valor_liquido).desc()).all()
        
        for cat, total, qtd in gastos_cat[:10]:  # Top 10
            analise['por_categoria'][cat] = {
                'total': float(total),
                'quantidade': int(qtd)
            }
        
        print(f"\n📊 Top 10 categorias de despesa:")
        for cat, dados in analise['por_categoria'].items():
            print(f"   {cat}: R$ {dados['total']:,.2f} ({dados['quantidade']} despesas)")
        
        # Estatísticas
        media_gastos = db.query(func.avg(GastoParlamentar.valor_liquido)).scalar() or 0
        max_gastos = db.query(func.max(GastoParlamentar.valor_liquido)).scalar() or 0
        min_gastos = db.query(func.min(GastoParlamentar.valor_liquido)).scalar() or 0
        
        analise['estatisticas'] = {
            'media': float(media_gastos),
            'maximo': float(max_gastos),
            'minimo': float(min_gastos)
        }
        
        print(f"\n📈 Estatísticas dos gastos:")
        print(f"   Média: R$ {analise['estatisticas']['media']:,.2f}")
        print(f"   Máximo: R$ {analise['estatisticas']['maximo']:,.2f}")
        print(f"   Mínimo: R$ {analise['estatisticas']['minimo']:,.2f}")
        
        return analise
    
    def analisar_votacoes(self, db) -> Dict[str, Any]:
        """Analisa dados detalhados das votações"""
        print("\n🗳️ ANÁLISE DETALHADA - VOTAÇÕES")
        print("=" * 40)
        
        analise = {
            'proposicoes': {},
            'emendas': {},
            'resultados': {},
            'participacao': {}
        }
        
        # Votações de proposições
        total_votacoes_prop = db.query(Votacao).count()
        total_votos_deputados = db.query(VotoDeputado).count()
        
        analise['proposicoes']['total_votacoes'] = total_votacoes_prop
        analise['proposicoes']['total_votos'] = total_votos_deputados
        
        print(f"📋 Votações de proposições: {total_votacoes_prop}")
        print(f"🗳️ Votos de deputados: {total_votos_deputados:,}")
        
        # Resultados das votações
        resultados = db.query(
            Votacao.resultado,
            func.count(Votacao.id).label('quantidade')
        ).group_by(Votacao.resultado).all()
        
        for resultado, qtd in resultados:
            analise['resultados'][resultado] = int(qtd)
        
        print(f"\n📊 Distribuição de resultados:")
        for resultado, qtd in analise['resultados'].items():
            print(f"   {resultado}: {qtd} votações")
        
        # Votações de emendas
        total_votacoes_emendas = db.query(VotacaoEmenda).count()
        analise['emendas']['total_votacoes'] = total_votacoes_emendas
        
        print(f"\n📝 Votações de emendas: {total_votacoes_emendas}")
        
        # Participação dos deputados
        participacao = db.query(
            Deputado.nome,
            func.count(VotoDeputado.id).label('total_votos')
        ).join(VotoDeputado, VotoDeputado.deputado_id == Deputado.id)\
         .group_by(Deputado.id, Deputado.nome)\
         .order_by(func.count(VotoDeputado.id).desc())\
         .limit(10).all()
        
        analise['participacao']['top_participantes'] = [
            {'nome': nome, 'total_votos': int(total)}
            for nome, total in participacao
        ]
        
        print(f"\n🏆 Top 10 deputados por participação em votações:")
        for i, item in enumerate(analise['participacao']['top_participantes'], 1):
            print(f"   {i}. {item['nome']}: {item['total_votos']} votos")
        
        return analise
    
    def gerar_insights(self, dados: Dict[str, Any]) -> List[str]:
        """Gera insights baseados nos dados"""
        print("\n💡 GERANDO INSIGHTS PARA O HACKATHON")
        print("=" * 40)
        
        insights = []
        
        # Insight sobre deputados
        if dados['gerais']['deputados']['total'] > 0:
            percentual_exercicio = (dados['gerais']['deputados']['em_exercicio'] / 
                                 dados['gerais']['deputados']['total']) * 100
            insights.append(
                f"👥 {percentual_exercicio:.1f}% dos deputados estão em exercício ativo, "
                f"representando {dados['gerais']['deputados']['em_exercicio']} parlamentares"
            )
        
        # Insight sobre gastos
        if dados['gastos']['total_geral'] > 0:
            media_por_deputado = dados['gastos']['total_geral'] / dados['gerais']['deputados']['total']
            insights.append(
                f"💰 Gasto médio por deputado: R$ {media_por_deputado:,.2f}, "
                f"com total de R$ {dados['gastos']['total_geral']:,.2f}"
            )
        
        # Insight sobre votações
        if dados['votacoes']['proposicoes']['total_votos'] > 0:
            media_votos_por_votacao = (dados['votacoes']['proposicoes']['total_votos'] / 
                                    dados['votacoes']['proposicoes']['total_votacoes'] if 
                                    dados['votacoes']['proposicoes']['total_votacoes'] > 0 else 0)
            insights.append(
                f"🗳️ Média de {media_votos_por_votacao:.1f} votos por votação, "
                f"totalizando {dados['votacoes']['proposicoes']['total_votos']:,} votos registrados"
            )
        
        # Insight sobre estados
        if dados['deputados']['por_estado']:
            top_estado = max(dados['deputados']['por_estado'].items(), key=lambda x: x[1])
            percentual_top = (top_estado[1] / dados['gerais']['deputados']['total']) * 100
            insights.append(
                f"🗺️ {top_estado[0]} é o estado com mais deputados ({top_estado[1]}), "
                f"representando {percentual_top:.1f}% do total"
            )
        
        # Insight sobre partidos
        if dados['deputados']['por_partido']:
            top_partido = max(dados['deputados']['por_partido'].items(), key=lambda x: x[1])
            percentual_top = (top_partido[1] / dados['gerais']['deputados']['total']) * 100
            insights.append(
                f"🏛️ {top_partido[0]} é o maior partido ({top_partido[1]} deputados), "
                f"com {percentual_top:.1f}% da representação"
            )
        
        # Insight sobre categorias de gastos
        if dados['gastos']['por_categoria']:
            top_categoria = max(dados['gastos']['por_categoria'].items(), 
                              key=lambda x: x[1]['total'])
            percentual_cat = (top_categoria[1]['total'] / dados['gastos']['total_geral']) * 100
            insights.append(
                f"📊 '{top_categoria[0]}' é a maior categoria de gastos, "
                f"com R$ {top_categoria[1]['total']:,.2f} ({percentual_cat:.1f}% do total)"
            )
        
        # Mostrar insights
        for i, insight in enumerate(insights, 1):
            print(f"   {i}. {insight}")
        
        return insights
    
    def gerar_recomendacoes(self, dados: Dict[str, Any]) -> List[str]:
        """Gera recomendações para análises no hackathon"""
        print("\n🎯 RECOMENDAÇÕES PARA ANÁLISES NO HACKATHON")
        print("=" * 40)
        
        recomendacoes = [
            "📊 Análise de padrões de gastos por partido e estado",
            "🗳️ Análise de alinhamento partidário nas votações",
            "💰 Correlação entre gastos e participação em votações",
            "👥 Análise demográfica dos deputados vs desempenho",
            "🏛️ Comparação de gastos entre diferentes categorias",
            "📈 Tendências de gastos ao longo do tempo",
            "🎯 Identificação de deputados mais ativos em votações",
            "🗺️ Análise regional de padrões comportamentais",
            "📊 Análise de dispersão de gastos dentro de partidos",
            "🔍 Detecção de outliers em padrões de votação"
        ]
        
        for i, rec in enumerate(recomendacoes, 1):
            print(f"   {i}. {rec}")
        
        return recomendacoes
    
    def salvar_relatorio_completo(self, dados: Dict[str, Any]):
        """Salva o relatório completo em arquivo JSON"""
        try:
            nome_arquivo = f"relatorio_dados_hackathon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            caminho_arquivo = Path(__file__).parent / nome_arquivo
            
            relatorio = {
                'metadata': {
                    'data_geracao': self.inicio_relatorio.isoformat(),
                    'versao': 'hackathon-2025-v1.0',
                    'descricao': 'Relatório completo dos dados coletados para o hackathon Kritikos 2025'
                },
                'dados': dados,
                'insights': self.gerar_insights(dados),
                'recomendacoes': self.gerar_recomendacoes(dados)
            }
            
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Relatório completo salvo em: {caminho_arquivo}")
            return caminho_arquivo
            
        except Exception as e:
            print(f"\n❌ Erro ao salvar relatório: {e}")
            return None
    
    def gerar_relatorio_completo(self) -> Dict[str, Any]:
        """Gera o relatório completo"""
        db = next(get_db())
        
        try:
            print("🚀 INICIANDO GERAÇÃO DO RELATÓRIO COMPLETO")
            
            # Coletar dados
            dados = {
                'gerais': self.coletar_dados_gerais(db),
                'deputados': self.analisar_deputados(db),
                'gastos': self.analisar_gastos(db),
                'votacoes': self.analisar_votacoes(db)
            }
            
            # Gerar insights e recomendações
            dados['insights'] = self.gerar_insights(dados)
            dados['recomendacoes'] = self.gerar_recomendacoes(dados)
            
            # Salvar relatório
            caminho_arquivo = self.salvar_relatorio_completo(dados)
            
            # Resumo final
            fim_relatorio = datetime.now()
            duracao = (fim_relatorio - self.inicio_relatorio).total_seconds()
            
            print(f"\n{'='*60}")
            print("📋 RESUMO DO RELATÓRIO")
            print(f"{'='*60}")
            print(f"📅 Geração: {self.inicio_relatorio.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"⏱️ Duração: {duracao:.1f}s")
            print(f"📄 Arquivo: {caminho_arquivo}")
            
            print(f"\n🎯 PRINCIPAIS MÉTRICAS:")
            print(f"   👥 Deputados: {dados['gerais']['deputados']['total']}")
            print(f"   🏛️  Partidos: {dados['gerais']['partidos']['total']}")
            print(f"   💰 Gastos: R$ {dados['gastos']['total_geral']:,.2f}")
            print(f"   🗳️  Votações: {dados['votacoes']['proposicoes']['total_votacoes']}")
            print(f"   💡 Insights: {len(dados['insights'])}")
            print(f"   🎯 Recomendações: {len(dados['recomendacoes'])}")
            
            print(f"\n✅ Relatório gerado com sucesso!")
            print(f"🎯 Use os dados e insights para suas análises no hackathon!")
            
            return dados
            
        finally:
            db.close()

def main():
    """Função principal"""
    relatorio = RelatorioHackathon()
    dados = relatorio.gerar_relatorio_completo()
    
    return dados

if __name__ == "__main__":
    main()
