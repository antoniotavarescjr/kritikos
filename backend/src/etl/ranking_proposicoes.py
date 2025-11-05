"""
Ranking de Deputados por Proposições

Gera ranking dos deputados com mais proposições por tipo e total.
"""

import logging
from sqlalchemy import text
from models.db_utils import get_db_session
from utils.common_utils import setup_logging

logger = logging.getLogger(__name__)


class RankingProposicoes:
    """
    Gera rankings de deputados baseados nas proposições.
    """
    
    def __init__(self):
        self.session = get_db_session()
    
    def gerar_ranking_top_10(self) -> list:
        """
        Gera ranking dos top 10 deputados com mais proposições.
        
        Returns:
            Lista de dicionários com dados do ranking
        """
        try:
            logger.info("🏆 Gerando ranking dos top 10 deputados...")
            
            # Query para contar proposições por deputado e tipo
            query = """
            SELECT 
                d.nome as nome_deputado,
                pa.sigla as sigla_partido,
                e.sigla as uf,
                p.tipo,
                COUNT(*) as quantidade
            FROM deputados d
            JOIN autorias a ON d.id = a.deputado_id
            JOIN proposicoes p ON a.proposicao_id = p.id
            JOIN mandatos m ON d.id = m.deputado_id AND m.data_fim IS NULL
            JOIN partidos pa ON m.partido_id = pa.id
            JOIN estados e ON m.estado_id = e.id
            WHERE p.ano = 2025
            GROUP BY d.id, d.nome, pa.sigla, e.sigla, p.tipo
            ORDER BY quantidade DESC
            """
            
            resultados = self.session.execute(text(query)).fetchall()
            
            # Agrupar por deputado
            deputados_dict = {}
            for row in resultados:
                nome = row[0]
                partido = row[1]
                uf = row[2]
                tipo = row[3]
                quantidade = row[4]
                
                if nome not in deputados_dict:
                    deputados_dict[nome] = {
                        'nome': nome,
                        'partido': partido,
                        'uf': uf,
                        'total': 0,
                        'tipos': {}
                    }
                
                deputados_dict[nome]['total'] += quantidade
                deputados_dict[nome]['tipos'][tipo] = quantidade
            
            # Converter para lista e ordenar por total
            ranking = list(deputados_dict.values())
            ranking.sort(key=lambda x: x['total'], reverse=True)
            
            # Pegar top 10
            top_10 = ranking[:10]
            
            # Exibir ranking
            self._exibir_ranking(top_10)
            
            return top_10
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar ranking: {e}")
            return []
        finally:
            self.session.close()
    
    def _exibir_ranking(self, ranking: list):
        """
        Exibe o ranking de forma formatada.
        
        Args:
            ranking: Lista com dados do ranking
        """
        print("\n" + "="*80)
        print("🏆 TOP 10 DEPUTADOS COM MAIS PROPOSIÇÕES (2025)")
        print("="*80)
        
        for i, dep in enumerate(ranking, 1):
            print(f"\n{i:2d}. {dep['nome']} ({dep['partido']}-{dep['uf']})")
            print(f"    📊 TOTAL: {dep['total']} proposições")
            
            # Exibir detalhes por tipo
            tipos_ordenados = sorted(dep['tipos'].items(), key=lambda x: x[1], reverse=True)
            for tipo, qtd in tipos_ordenados:
                print(f"       • {tipo}: {qtd}")
        
        print("\n" + "="*80)
        
        # Estatísticas adicionais
        total_proposicoes = sum(dep['total'] for dep in ranking)
        print(f"📈 ESTATÍSTICAS:")
        print(f"   • Total de proposições (top 10): {total_proposicoes}")
        print(f"   • Média por deputado: {total_proposicoes / 10:.1f}")
        
        # Tipo mais comum
        todos_tipos = {}
        for dep in ranking:
            for tipo, qtd in dep['tipos'].items():
                todos_tipos[tipo] = todos_tipos.get(tipo, 0) + qtd
        
        tipo_mais_comum = max(todos_tipos.items(), key=lambda x: x[1])
        print(f"   • Tipo mais comum: {tipo_mais_comum[0]} ({tipo_mais_comum[1]} proposições)")
    
    def gerar_ranking_por_tipo(self, tipo: str, limite: int = 10) -> list:
        """
        Gera ranking para um tipo específico de proposição.
        
        Args:
            tipo: Tipo da proposição (PL, PEC, etc.)
            limite: Limite de deputados no ranking
            
        Returns:
            Lista de dicionários com dados do ranking
        """
        try:
            logger.info(f"🏆 Gerando ranking de {tipo}s...")
            
            query = """
            SELECT 
                d.nome as nome_deputado,
                pa.sigla as sigla_partido,
                e.sigla as uf,
                COUNT(*) as quantidade
            FROM deputados d
            JOIN autorias a ON d.id = a.deputado_id
            JOIN proposicoes p ON a.proposicao_id = p.id
            JOIN mandatos m ON d.id = m.deputado_id AND m.data_fim IS NULL
            JOIN partidos pa ON m.partido_id = pa.id
            JOIN estados e ON m.estado_id = e.id
            WHERE p.ano = 2025 AND p.tipo = :tipo
            GROUP BY d.id, d.nome, pa.sigla, e.sigla
            ORDER BY quantidade DESC
            LIMIT :limite
            """
            
            resultados = self.session.execute(
                text(query), 
                {'tipo': tipo, 'limite': limite}
            ).fetchall()
            
            ranking = []
            for row in resultados:
                ranking.append({
                    'nome': row[0],
                    'partido': row[1],
                    'uf': row[2],
                    'quantidade': row[3]
                })
            
            # Exibir ranking específico
            print(f"\n🏆 TOP {limite} DEPUTADOS COM MAIS {tipo}S (2025)")
            print("="*60)
            
            for i, dep in enumerate(ranking, 1):
                print(f"{i:2d}. {dep['nome']} ({dep['partido']}-{dep['uf']}) - {dep['quantidade']} {tipo}s")
            
            return ranking
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar ranking por tipo: {e}")
            return []
        finally:
            self.session.close()
    
    def exibir_estatisticas_gerais(self):
        """
        Exibe estatísticas gerais das proposições de 2025.
        """
        try:
            logger.info("📊 Gerando estatísticas gerais...")
            
            # Total de proposições por tipo
            query_tipos = """
            SELECT tipo, COUNT(*) as quantidade
            FROM proposicoes
            WHERE ano = 2025
            GROUP BY tipo
            ORDER BY quantidade DESC
            """
            
            tipos_result = self.session.execute(text(query_tipos)).fetchall()
            
            print("\n📊 ESTATÍSTICAS GERAIS DE PROPOSIÇÕES (2025)")
            print("="*60)
            print("TIPO     QUANTIDADE  PERCENTUAL")
            print("-" * 40)
            
            total_geral = sum(row[1] for row in tipos_result)
            
            for tipo, quantidade in tipos_result:
                percentual = (quantidade / total_geral) * 100
                print(f"{tipo:<8} {quantidade:>9}   {percentual:>7.1f}%")
            
            print("-" * 40)
            print(f"{'TOTAL':<8} {total_geral:>9}  100.0%")
            
            # Total de deputados com proposições
            query_deputados = """
            SELECT COUNT(DISTINCT d.id)
            FROM deputados d
            JOIN autorias a ON d.id = a.deputado_id
            JOIN proposicoes p ON a.proposicao_id = p.id
            WHERE p.ano = 2025
            """
            
            total_deputados = self.session.execute(text(query_deputados)).scalar()
            
            print(f"\n👥 Deputados com proposições: {total_deputados}")
            print(f"📈 Média por deputado: {total_geral / total_deputados:.1f} proposições")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar estatísticas: {e}")
        finally:
            self.session.close()


def main():
    """
    Função principal para executar os rankings.
    """
    setup_logging()
    
    ranking = RankingProposicoes()
    
    print("🏆 GERANDO RANKINGS DE PROPOSIÇÕES")
    print("="*50)
    
    # Ranking geral top 10
    ranking.gerar_ranking_top_10()
    
    # Rankings por tipo principais
    tipos_principais = ['PL', 'PEC', 'PLP', 'MPV']
    
    for tipo in tipos_principais:
        ranking.gerar_ranking_por_tipo(tipo, limite=5)
    
    # Estatísticas gerais
    ranking.exibir_estatisticas_gerais()


if __name__ == "__main__":
    main()
