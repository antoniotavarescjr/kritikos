#!/usr/bin/env python3
"""
Execução completa da coleta de emendas com o coletor corrigido
Coleta todos os deputados para todos os anos disponíveis
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Importar modelos
from models.db_utils import get_db_session
from models.politico_models import Deputado

# Importar coletor corrigido
from src.etl.coleta_emendas_transparencia import ColetorEmendasTransparencia

def obter_todos_deputados(db_session) -> List[str]:
    """
    Obtém lista de todos os deputados ativos no banco
    """
    try:
        deputados = db_session.query(Deputado.nome).filter(
            Deputado.nome.isnot(None),
            Deputado.id.isnot(None)
        ).distinct().all()
        
        return [dep[0] for dep in deputados if dep[0] and 'BANCADA' not in dep[0].upper()]
        
    except Exception as e:
        print(f"❌ Erro ao obter lista de deputados: {e}")
        return []

def main():
    """
    Execução completa da coleta de emendas corrigida
    """
    print("🚀 EXECUÇÃO COMPLETA DA COLETA DE EMENDAS - VERSÃO CORRIGIDA")
    print("=" * 80)
    print("🎯 Coletando TODOS os deputados para TODOS os anos disponíveis")
    print("🔧 Com as correções validadas: tratamento de valores + mapeamento de nomes")
    print("=" * 80)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        # Inicializar coletor
        coletor = ColetorEmendasTransparencia()
        
        # Obter lista de todos os deputados
        print("\n👥 OBTENDO LISTA COMPLETA DE DEPUTADOS")
        print("=" * 50)
        
        deputados = obter_todos_deputados(db_session)
        print(f"✅ Encontrados {len(deputados)} deputados no banco")
        
        if not deputados:
            print("❌ Nenhum deputado encontrado no banco!")
            return
        
        # Anos disponíveis na API
        anos_disponiveis = [2024, 2023, 2022, 2021]
        
        print(f"\n📅 ANOS DISPONÍVEIS PARA COLETA")
        print("=" * 40)
        for ano in anos_disponiveis:
            print(f"   📅 {ano}")
        
        # Resultados gerais
        resultados_gerais = {
            'total_deputados': len(deputados),
            'deputados_processados': 0,
            'total_emendas_encontradas': 0,
            'total_emendas_salvas': 0,
            'total_emendas_com_autor': 0,
            'valor_total_geral': 0.0,
            'erros': 0,
            'resultados_por_ano': {}
        }
        
        # Processar cada ano
        for ano in anos_disponiveis:
            print(f"\n🎯 COLETANDO EMENDAS DE {ano}")
            print("=" * 50)
            
            resultados_ano = {
                'deputados_processados': 0,
                'emendas_encontradas': 0,
                'emendas_salvas': 0,
                'emendas_com_autor': 0,
                'valor_total': 0.0,
                'erros': 0
            }
            
            # Processar cada deputado
            for i, nome_deputado in enumerate(deputados, 1):
                print(f"\n👥 [{i}/{len(deputados)}] {nome_deputado} - {ano}")
                print("-" * 60)
                
                try:
                    # Buscar todas as emendas do deputado no ano
                    emendas = coletor.buscar_todas_emendas_deputado(nome_deputado, ano)
                    resultados_ano['emendas_encontradas'] += len(emendas)
                    
                    if not emendas:
                        print(f"   ⚠️ Nenhuma emenda encontrada")
                        resultados_ano['deputados_processados'] += 1
                        continue
                    
                    print(f"   📄 {len(emendas)} emendas encontradas")
                    
                    # Salvar cada emenda
                    for j, emenda_data in enumerate(emendas, 1):
                        if j % 10 == 0:  # Progresso a cada 10 emendas
                            print(f"   📄 Processando {j}/{len(emendas)} emendas...")
                        
                        emenda = coletor.salvar_emenda_transparencia(emenda_data, db_session)
                        if emenda:
                            resultados_ano['emendas_salvas'] += 1
                            valor_emenda = float(emenda.valor_emenda) if emenda.valor_emenda else 0.0
                            resultados_ano['valor_total'] += valor_emenda
                            
                            if emenda.deputado_id:
                                resultados_ano['emendas_com_autor'] += 1
                    
                    resultados_ano['deputados_processados'] += 1
                    
                    # Progresso geral
                    if i % 10 == 0 or i == len(deputados):
                        print(f"\n📊 PROGRESSO PARCIAL - {ano}:")
                        print(f"   👥 Deputados: {resultados_ano['deputados_processados']}/{len(deputados)}")
                        print(f"   📄 Emendas: {resultados_ano['emendas_salvas']} salvas")
                        print(f"   💰 Valor: R$ {resultados_ano['valor_total']:,.2f}")
                        print(f"   📈 Taxa identificação: {100*resultados_ano['emendas_com_autor']/max(resultados_ano['emendas_salvas'],1):.1f}%")
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar {nome_deputado}: {e}")
                    resultados_ano['erros'] += 1
                    continue
            
            # Consolidar resultados do ano
            resultados_gerais['resultados_por_ano'][ano] = resultados_ano
            resultados_gerais['deputados_processados'] += resultados_ano['deputados_processados']
            resultados_gerais['total_emendas_encontradas'] += resultados_ano['emendas_encontradas']
            resultados_gerais['total_emendas_salvas'] += resultados_ano['emendas_salvas']
            resultados_gerais['total_emendas_com_autor'] += resultados_ano['emendas_com_autor']
            resultados_gerais['valor_total_geral'] += resultados_ano['valor_total']
            resultados_gerais['erros'] += resultados_ano['erros']
            
            # Resumo do ano
            print(f"\n📋 RESUMO FINAL - {ano}:")
            print("=" * 30)
            print(f"👥 Deputados processados: {resultados_ano['deputados_processados']}")
            print(f"📄 Emendas encontradas: {resultados_ano['emendas_encontradas']}")
            print(f"💾 Emendas salvas: {resultados_ano['emendas_salvas']}")
            print(f"👥 Com autor identificado: {resultados_ano['emendas_com_autor']}")
            print(f"💰 Valor total: R$ {resultados_ano['valor_total']:,.2f}")
            print(f"❌ Erros: {resultados_ano['erros']}")
        
        # Relatório final
        print(f"\n🎉 RELATÓRIO FINAL DA COLETA COMPLETA")
        print("=" * 60)
        print(f"👥 Total deputados: {resultados_gerais['total_deputados']}")
        print(f"👥 Deputados processados: {resultados_gerais['deputados_processados']}")
        print(f"📄 Total emendas encontradas: {resultados_gerais['total_emendas_encontradas']}")
        print(f"💾 Total emendas salvas: {resultados_gerais['total_emendas_salvas']}")
        print(f"👥 Com autor identificado: {resultados_gerais['total_emendas_com_autor']}")
        print(f"💰 Valor total geral: R$ {resultados_gerais['valor_total_geral']:,.2f}")
        print(f"❌ Total erros: {resultados_gerais['erros']}")
        
        # Métricas de sucesso
        if resultados_gerais['total_emendas_salvas'] > 0:
            taxa_identificacao = 100 * resultados_gerais['total_emendas_com_autor'] / resultados_gerais['total_emendas_salvas']
            valor_medio = resultados_gerais['valor_total_geral'] / resultados_gerais['total_emendas_salvas']
            
            print(f"\n📈 MÉTRICAS DE SUCESSO:")
            print(f"   📊 Taxa de identificação de autores: {taxa_identificacao:.1f}%")
            print(f"   💰 Valor médio por emenda: R$ {valor_medio:,.2f}")
            print(f"   📊 Emendas por deputado: {resultados_gerais['total_emendas_salvas']/max(resultados_gerais['deputados_processados'],1):.1f}")
            
            if resultados_gerais['valor_total_geral'] > 1_000_000_000:  # Mais de 1 bilhão
                print(f"\n🏆 RESULTADO EXTRAORDINÁRIO!")
                print(f"💰 Mais de R$ 1 bilhão em emendas coletadas!")
            elif resultados_gerais['valor_total_geral'] > 100_000_000:  # Mais de 100 milhões
                print(f"\n🎉 RESULTADO EXCELENTE!")
                print(f"💰 Mais de R$ 100 milhões em emendas coletadas!")
        
        # Salvar relatório em arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_relatorio = f"relatorio_coleta_completa_corrigida_{timestamp}.txt"
        
        with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO FINAL - COLETA COMPLETA DE EMENDAS CORRIGIDA\n")
            f.write("=" * 60 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total deputados: {resultados_gerais['total_deputados']}\n")
            f.write(f"Deputados processados: {resultados_gerais['deputados_processados']}\n")
            f.write(f"Total emendas encontradas: {resultados_gerais['total_emendas_encontradas']}\n")
            f.write(f"Total emendas salvas: {resultados_gerais['total_emendas_salvas']}\n")
            f.write(f"Com autor identificado: {resultados_gerais['total_emendas_com_autor']}\n")
            f.write(f"Valor total geral: R$ {resultados_gerais['valor_total_geral']:,.2f}\n")
            f.write(f"Total erros: {resultados_gerais['erros']}\n")
            f.write(f"Taxa de identificação: {taxa_identificacao:.1f}%\n")
            f.write(f"Valor médio por emenda: R$ {valor_medio:,.2f}\n")
            
            f.write("\n\nRESULTADOS POR ANO:\n")
            f.write("-" * 30 + "\n")
            for ano, resultados in resultados_gerais['resultados_por_ano'].items():
                f.write(f"\n{ano}:\n")
                f.write(f"  Emendas salvas: {resultados['emendas_salvas']}\n")
                f.write(f"  Valor total: R$ {resultados['valor_total']:,.2f}\n")
                f.write(f"  Taxa identificação: {100*resultados['emendas_com_autor']/max(resultados['emendas_salvas'],1):.1f}%\n")
        
        print(f"\n📄 Relatório salvo em: {arquivo_relatorio}")
        
    except Exception as e:
        print(f"\n❌ ERRO GERAL DURANTE COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
