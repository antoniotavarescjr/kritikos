#!/usr/bin/env python3
"""
Script de Validação do Pipeline de Coletas
Valida o funcionamento de todas as coletas para o período 06/2025+
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

# Importar configurações e modelos
from config import get_coleta_config, get_data_inicio_coleta, coleta_habilitada, get_tipos_coleta_habilitados, get_votacoes_fallback_config, deve_usar_fallback_votacoes
from models.database import get_db
from models.politico_models import Deputado
from models.base_models import Partido, BlocoPartidario
from models.financeiro_models import GastoParlamentar
from models.emenda_models import EmendaParlamentar
from models.proposicao_models import Votacao, VotoDeputado, VotacaoObjeto, VotacaoProposicao, OrientacaoBancada

class ValidadorPipeline:
    """
    Classe responsável por validar o funcionamento do pipeline de coletas
    """

    def __init__(self):
        """Inicializa o validador"""
        self.data_inicio = get_data_inicio_coleta()
        self.tipos_habilitados = get_tipos_coleta_habilitados()
        
        print(f"🔍 Validador de Pipeline inicializado")
        print(f"📅 Período de validação: {self.data_inicio} até hoje")
        print(f"🔧 Tipos habilitados: {', '.join(self.tipos_habilitados)}")
        print(f"🗳️ Fallback votações: {'Habilitado' if deve_usar_fallback_votacoes() else 'Desabilitado'}")

    def validar_coleta_referencia(self, db: Session) -> Dict[str, Any]:
        """Valida coleta de dados de referência"""
        print("\n📋 VALIDANDO COLETA DE REFERÊNCIA")
        print("=" * 50)
        
        resultado = {
            'tipo': 'referencia',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Contar deputados
            deputados_count = db.query(Deputado).count()
            deputados_ativos = db.query(Deputado).filter(
                Deputado.situacao == 'Exercício'
            ).count()
            
            # Contar partidos
            partidos_count = db.query(Partido).count()
            partidos_ativos = db.query(Partido).filter(
                Partido.status == 'Ativo'
            ).count()
            
            # Contar blocos partidários
            blocos_count = db.query(BlocoPartidario).count()
            
            resultado['dados'] = {
                'deputados_total': deputados_count,
                'deputados_ativos': deputados_ativos,
                'partidos_total': partidos_count,
                'partidos_ativos': partidos_ativos,
                'blocos_total': blocos_count
            }
            
            # Validar quantidades mínimas
            if deputados_ativos >= 500:  # Espera-se pelo menos 500 deputados
                resultado['status'] = 'sucesso'
                print(f"   ✅ Deputados: {deputados_ativos} ativos")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append(f"Poucos deputados ativos: {deputados_ativos}")
                print(f"   ⚠️ Deputados: {deputados_ativos} ativos (abaixo do esperado)")
            
            if partidos_ativos >= 20:  # Espera-se pelo menos 20 partidos
                print(f"   ✅ Partidos: {partidos_ativos} ativos")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append(f"Poucos partidos ativos: {partidos_ativos}")
                print(f"   ⚠️ Partidos: {partidos_ativos} ativos (abaixo do esperado)")
            
            if blocos_count >= 1:  # Espera-se pelo menos 1 bloco
                print(f"   ✅ Blocos: {blocos_count} cadastrados")
            else:
                print(f"   ℹ️ Blocos: {blocos_count} cadastrados (pode ser normal)")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def validar_coleta_gastos(self, db: Session) -> Dict[str, Any]:
        """Valida coleta de gastos parlamentares"""
        print("\n💰 VALIDANDO COLETA DE GASTOS")
        print("=" * 50)
        
        resultado = {
            'tipo': 'gastos',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Contar gastos a partir de 06/2025
            gastos_count = db.query(GastoParlamentar).filter(
                and_(
                    GastoParlamentar.ano >= 2025,
                    GastoParlamentar.mes >= 6
                )
            ).count()
            
            # Valor total de gastos
            valor_total = db.query(func.sum(GastoParlamentar.valor_liquido)).filter(
                and_(
                    GastoParlamentar.ano >= 2025,
                    GastoParlamentar.mes >= 6
                )
            ).scalar() or 0
            
            # Gastos por mês
            gastos_por_mes = db.query(
                GastoParlamentar.ano,
                GastoParlamentar.mes,
                func.count(GastoParlamentar.id).label('quantidade'),
                func.sum(GastoParlamentar.valor_liquido).label('valor_total')
            ).filter(
                and_(
                    GastoParlamentar.ano >= 2025,
                    GastoParlamentar.mes >= 6
                )
            ).group_by(GastoParlamentar.ano, GastoParlamentar.mes).all()
            
            resultado['dados'] = {
                'gastos_total': gastos_count,
                'valor_total': float(valor_total),
                'gastos_por_mes': [
                    {
                        'ano': row.ano,
                        'mes': row.mes,
                        'quantidade': row.quantidade,
                        'valor_total': float(row.valor_total or 0)
                    } for row in gastos_por_mes
                ]
            }
            
            # Validar quantidades mínimas
            if gastos_count >= 1000:  # Espera-se pelo menos 1000 registros
                resultado['status'] = 'sucesso'
                print(f"   ✅ Gastos: {gastos_count} registros")
                print(f"   💰 Valor total: R$ {valor_total:,.2f}")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append(f"Poucos registros de gastos: {gastos_count}")
                print(f"   ⚠️ Gastos: {gastos_count} registros (abaixo do esperado)")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def validar_coleta_emendas(self, db: Session) -> Dict[str, Any]:
        """Valida coleta de emendas"""
        print("\n📝 VALIDANDO COLETA DE EMENDAS")
        print("=" * 50)
        
        resultado = {
            'tipo': 'emendas',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Contar emendas dos anos disponíveis (2021-2024) - API não tem 2025
            emendas_count = db.query(EmendaParlamentar).filter(
                EmendaParlamentar.ano.between(2021, 2024)
            ).count()
            
            # Valor total de emendas
            valor_total = db.query(func.sum(EmendaParlamentar.valor_emenda)).filter(
                EmendaParlamentar.ano.between(2021, 2024)
            ).scalar() or 0
            
            # Emendas por tipo
            emendas_por_tipo = db.query(
                EmendaParlamentar.tipo_emenda,
                func.count(EmendaParlamentar.id).label('quantidade')
            ).filter(
                EmendaParlamentar.ano.between(2021, 2024)
            ).group_by(EmendaParlamentar.tipo_emenda).all()
            
            resultado['dados'] = {
                'emendas_total': emendas_count,
                'valor_total': float(valor_total),
                'emendas_por_tipo': [
                    {
                        'tipo': row.tipo_emenda,
                        'quantidade': row.quantidade
                    } for row in emendas_por_tipo
                ]
            }
            
            # Validar quantidades mínimas
            if emendas_count >= 50:  # Espera-se pelo menos 50 emendas
                resultado['status'] = 'sucesso'
                print(f"   ✅ Emendas: {emendas_count} registros")
                print(f"   💰 Valor total: R$ {valor_total:,.2f}")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append(f"Poucas emendas encontradas: {emendas_count}")
                print(f"   ⚠️ Emendas: {emendas_count} registros (abaixo do esperado)")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def validar_coleta_votacoes(self, db: Session) -> Dict[str, Any]:
        """Valida coleta de votações (API + Fallback)"""
        print("\n🗳️ VALIDANDO COLETA DE VOTAÇÕES")
        print("=" * 50)
        
        resultado = {
            'tipo': 'votacoes',
            'status': 'desconhecido',
            'dados': {},
            'erros': [],
            'fonte': 'desconhecida'
        }
        
        try:
            # Contar votações (tentar período 06/2025+, depois anos anteriores)
            votacoes_count = db.query(Votacao).filter(
                Votacao.data_votacao >= datetime(2025, 6, 1).date()
            ).count()
            
            # Se não tiver votações recentes, verificar anos anteriores (fallback)
            if votacoes_count == 0:
                votacoes_count = db.query(Votacao).filter(
                    Votacao.data_votacao >= datetime(2022, 1, 1).date()
                ).count()
                resultado['fonte'] = 'fallback'
                print(f"   🔄 Usando dados de fallback (anos anteriores)")
            else:
                resultado['fonte'] = 'api'
                print(f"   📡 Usando dados da API (período recente)")
            
            # Contar votos de deputados
            votos_count = db.query(VotoDeputado).count()
            
            # Contar objetos de votação
            objetos_count = db.query(VotacaoObjeto).count()
            
            # Contar proposições afetadas
            proposicoes_count = db.query(VotacaoProposicao).count()
            
            # Contar orientações de bancada
            orientacoes_count = db.query(OrientacaoBancada).count()
            
            # Votações por resultado
            votacoes_por_resultado = db.query(
                Votacao.resultado,
                func.count(Votacao.id).label('quantidade')
            ).filter(
                Votacao.data_votacao >= datetime(2022, 1, 1).date()
            ).group_by(Votacao.resultado).all()
            
            resultado['dados'] = {
                'votacoes_total': votacoes_count,
                'votos_total': votos_count,
                'objetos_total': objetos_count,
                'proposicoes_afetadas': proposicoes_count,
                'orientacoes_total': orientacoes_count,
                'votacoes_por_resultado': [
                    {
                        'resultado': row.resultado,
                        'quantidade': row.quantidade
                    } for row in votacoes_por_resultado
                ]
            }
            
            # Validar quantidades mínimas
            if votacoes_count >= 100:  # Espera-se pelo menos 100 votações
                resultado['status'] = 'sucesso'
                print(f"   ✅ Votações: {votacoes_count} registros")
                print(f"   👥 Votos: {votos_count} registros")
                print(f"   📋 Objetos: {objetos_count} registros")
                print(f"   📄 Proposições afetadas: {proposicoes_count} registros")
                print(f"   🏛️ Orientações: {orientacoes_count} registros")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append(f"Poucas votações encontradas: {votacoes_count}")
                print(f"   ⚠️ Votações: {votacoes_count} registros (abaixo do esperado)")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def validar_configuracoes_fallback(self) -> Dict[str, Any]:
        """Valida configurações do fallback de votações"""
        print("\n🔧 VALIDANDO CONFIGURAÇÕES DE FALLBACK")
        print("=" * 50)
        
        resultado = {
            'tipo': 'config_fallback',
            'status': 'desconhecido',
            'dados': {},
            'erros': []
        }
        
        try:
            # Verificar configurações
            fallback_habilitado = deve_usar_fallback_votacoes()
            anos_config = get_votacoes_fallback_config('anos_para_coletar')
            limite_config = get_votacoes_fallback_config('limite_registros')
            tipos_arquivos = get_votacoes_fallback_config('tipos_arquivos')
            
            resultado['dados'] = {
                'fallback_habilitado': fallback_habilitado,
                'anos_configurados': anos_config,
                'limite_registros': limite_config,
                'tipos_arquivos': tipos_arquivos,
                'quantidade_tipos': len(tipos_arquivos) if tipos_arquivos else 0
            }
            
            # Validar configurações
            if fallback_habilitado and anos_config and len(anos_config) >= 1:
                resultado['status'] = 'sucesso'
                print(f"   ✅ Fallback: {'Habilitado' if fallback_habilitado else 'Desabilitado'}")
                print(f"   📅 Anos configurados: {', '.join(map(str, anos_config))}")
                print(f"   🎯 Limite de registros: {limite_config}")
                print(f"   📁 Tipos de arquivos: {len(tipos_arquivos)} configurados")
            else:
                resultado['status'] = 'alerta'
                resultado['erros'].append("Configurações de fallback incompletas")
                print(f"   ⚠️ Configurações de fallback podem estar incompletas")
                
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            print(f"   ❌ Erro: {e}")
        
        return resultado

    def executar_validacao_completa(self) -> Dict[str, Any]:
        """Executa validação completa de todas as coletas"""
        print("🔍 INICIANDO VALIDAÇÃO COMPLETA DO PIPELINE")
        print("=" * 60)
        
        db = next(get_db())
        resultados = {
            'data_validacao': datetime.now().isoformat(),
            'periodo_validado': f"{self.data_inicio} até hoje",
            'tipos_habilitados': self.tipos_habilitados,
            'validacoes': {},
            'resumo_geral': {
                'total_validacoes': 0,
                'sucessos': 0,
                'alertas': 0,
                'erros': 0
            }
        }
        
        try:
            # Executar validações para cada tipo habilitado
            if coleta_habilitada('referencia'):
                resultados['validacoes']['referencia'] = self.validar_coleta_referencia(db)
                resultados['resumo_geral']['total_validacoes'] += 1
            
            if coleta_habilitada('gastos'):
                resultados['validacoes']['gastos'] = self.validar_coleta_gastos(db)
                resultados['resumo_geral']['total_validacoes'] += 1
            
            if coleta_habilitada('emendas'):
                resultados['validacoes']['emendas'] = self.validar_coleta_emendas(db)
                resultados['resumo_geral']['total_validacoes'] += 1
            
            if coleta_habilitada('votacoes'):
                resultados['validacoes']['votacoes'] = self.validar_coleta_votacoes(db)
                resultados['resumo_geral']['total_validacoes'] += 1
            
            # Validar configurações do fallback
            if deve_usar_fallback_votacoes():
                resultados['validacoes']['config_fallback'] = self.validar_configuracoes_fallback()
                resultados['resumo_geral']['total_validacoes'] += 1
            
            # Compilar resumo geral
            for tipo, validacao in resultados['validacoes'].items():
                status = validacao.get('status', 'desconhecido')
                if status == 'sucesso':
                    resultados['resumo_geral']['sucessos'] += 1
                elif status == 'alerta':
                    resultados['resumo_geral']['alertas'] += 1
                elif status == 'erro':
                    resultados['resumo_geral']['erros'] += 1
            
        except Exception as e:
            print(f"❌ Erro geral na validação: {e}")
            resultados['erro_geral'] = str(e)
        finally:
            db.close()
        
        return resultados

def main():
    """Função principal para execução da validação"""
    print("🔍 VALIDAÇÃO DO PIPELINE DE COLETAS")
    print("=" * 60)
    
    validador = ValidadorPipeline()
    resultados = validador.executar_validacao_completa()
    
    # Exibir resumo final
    print("\n📋 RESUMO FINAL DA VALIDAÇÃO")
    print("=" * 50)
    
    resumo = resultados['resumo_geral']
    print(f"📅 Data da validação: {resultados['data_validacao']}")
    print(f"📅 Período validado: {resultados['periodo_validado']}")
    print(f"🔧 Tipos habilitados: {', '.join(resultados['tipos_habilitados'])}")
    print(f"\n📊 Resumo das Validações:")
    print(f"   ✅ Sucessos: {resumo['sucessos']}")
    print(f"   ⚠️ Alertas: {resumo['alertas']}")
    print(f"   ❌ Erros: {resumo['erros']}")
    print(f"   📋 Total: {resumo['total_validacoes']}")
    
    # Detalhes por tipo
    print(f"\n📋 Detalhes por Tipo:")
    for tipo, validacao in resultados['validacoes'].items():
        status = validacao.get('status', 'desconhecido')
        icone = "✅" if status == 'sucesso' else "⚠️" if status == 'alerta' else "❌"
        print(f"   {icone} {tipo.title()}: {status}")
        
        # Mostrar fonte para votações
        if tipo == 'votacoes' and 'fonte' in validacao:
            fonte = validacao['fonte']
            print(f"      📡 Fonte: {fonte}")
        
        # Mostrar dados específicos
        dados = validacao.get('dados', {})
        if tipo == 'votacoes' and dados:
            print(f"      🗳️ Votações: {dados.get('votacoes_total', 0)}")
            print(f"      👥 Votos: {dados.get('votos_total', 0)}")
            print(f"      📋 Objetos: {dados.get('objetos_total', 0)}")
        
        erros = validacao.get('erros', [])
        if erros:
            for erro in erros:
                print(f"      - {erro}")
    
    # Conclusão
    total_sucessos = resumo['sucessos']
    total_validacoes = resumo['total_validacoes']
    
    if total_validacoes > 0 and total_sucessos == total_validacoes:
        print(f"\n🎉 TODAS AS COLETAS ESTÃO FUNCIONANDO PERFEITAMENTE!")
        print(f"✅ Pipeline validado com sucesso para o período {resultados['periodo_validado']}")
    elif total_sucessos >= total_validacoes * 0.8:  # 80% de sucesso
        print(f"\n👍 MAIORIA DAS COLETAS ESTÁ FUNCIONANDO BEM!")
        print(f"⚠️ Algumas melhorias podem ser necessárias")
    else:
        print(f"\n⚠️ PROBLEMAS ENCONTRADOS NAS COLETAS!")
        print(f"🔧 Verifique os erros listados acima")

if __name__ == "__main__":
    main()
