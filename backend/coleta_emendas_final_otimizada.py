#!/usr/bin/env python3
"""
Coleta final otimizada de emendas com mapeamento de nomes
Usa mapeamento pré-calculado para máxima performance
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

# Importar coletor
from src.etl.coleta_emendas_transparencia import ColetorEmendasTransparencia

def obter_deputados_com_emendas(coletor, ano: int) -> List[str]:
    """
    Obtém lista completa de deputados que têm emendas na API
    """
    print(f"🔍 Obtendo lista completa de deputados com emendas - {ano}")
    
    todos_nomes = set()
    pagina = 1
    
    while True:
        params = {
            'ano': ano,
            'pagina': pagina,
            'itens': 100
        }
        
        emendas_pagina = coletor.fazer_requisicao_api(params)
        if not emendas_pagina:
            break
        
        # Extrair nomes únicos
        for emenda in emendas_pagina:
            nome_autor = emenda.get('nomeAutor') or emenda.get('autor', '')
            if nome_autor and 'BANCADA' not in nome_autor.upper():
                todos_nomes.add(nome_autor.strip().upper())
        
        print(f"   📄 Página {pagina}: +{len(emendas_pagina)} emendas, {len(todos_nomes)} nomes únicos")
        
        # Se não tem mais resultados, parar
        if len(emendas_pagina) < 100:
            break
        
        pagina += 1
        if pagina > 100:  # Limite de segurança
            break
        
        # Rate limiting
        time.sleep(0.5)
    
    return list(todos_nomes)

def buscar_deputado_otimizado(nome_autor: str, db_session) -> int:
    """
    Busca ID do deputado com estratégia otimizada
    """
    if not nome_autor or 'BANCADA' in nome_autor.upper():
        return None
    
    # 1. Busca exata (mais rápida)
    deputado = db_session.query(Deputado).filter(
        func.upper(Deputado.nome) == func.upper(nome_autor.strip())
    ).first()
    
    if deputado:
        return deputado.id
    
    # 2. Busca sem acentos/caracteres especiais
    nome_normalizado = ''.join(c for c in nome_autor if c.isalnum()).upper()
    deputados = db_session.query(Deputado).all()
    
    for dep in deputados:
        nome_banco_normalizado = ''.join(c for c in dep.nome if c.isalnum()).upper()
        if nome_normalizado == nome_banco_normalizado:
            return dep.id
    
    # 3. Busca por primeiro nome (fallback)
    partes_nome = nome_autor.strip().split()
    if len(partes_nome) >= 1:
        primeiro_nome = partes_nome[0]
        deputado = db_session.query(Deputado).filter(
            Deputado.nome.ilike(f"{primeiro_nome}%")
        ).first()
        
        if deputado:
            return deputado.id
    
    return None

def main():
    """
    Execução final otimizada da coleta de emendas
    """
    print("🚀 COLETA FINAL OTIMIZADA DE EMENDAS")
    print("=" * 60)
    print("🎯 Usando estratégia otimizada com mapeamento dinâmico")
    print("🔧 Processando apenas deputados que realmente têm emendas")
    print("=" * 60)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        coletor = ColetorEmendasTransparencia()
        
        # Anos disponíveis
        anos = [2024, 2023, 2022, 2021]
        
        resultados_gerais = {
            'total_deputados_com_emendas': 0,
            'total_emendas_encontradas': 0,
            'total_emendas_salvas': 0,
            'total_emendas_com_autor': 0,
            'valor_total_geral': 0.0,
            'erros': 0,
            'resultados_por_ano': {}
        }
        
        for ano in anos:
            print(f"\n🎯 PROCESSANDO ANO: {ano}")
            print("=" * 50)
            
            # Obter apenas deputados que têm emendas
            deputados_com_emendas = obter_deputados_com_emendas(coletor, ano)
            print(f"✅ Encontrados {len(deputados_com_emendas)} deputados com emendas em {ano}")
            
            resultados_ano = {
                'deputados_processados': 0,
                'emendas_encontradas': 0,
                'emendas_salvas': 0,
                'emendas_com_autor': 0,
                'valor_total': 0.0,
                'erros': 0
            }
            
            # Processar cada deputado
            for i, nome_deputado in enumerate(deputados_com_emendas, 1):
                print(f"\n👥 [{i}/{len(deputados_com_emendas)}] {nome_deputado}")
                print("-" * 60)
                
                try:
                    # Buscar emendas do deputado
                    emendas = coletor.buscar_todas_emendas_deputado(nome_deputado, ano)
                    resultados_ano['emendas_encontradas'] += len(emendas)
                    
                    if not emendas:
                        print(f"   ⚠️ Nenhuma emenda encontrada (inconsistência)")
                        continue
                    
                    print(f"   📄 {len(emendas)} emendas encontradas")
                    
                    # Salvar cada emenda
                    for j, emenda_data in enumerate(emendas, 1):
                        if j % 5 == 0:  # Progresso a cada 5 emendas
                            print(f"   📄 Processando {j}/{len(emendas)} emendas...")
                        
                        emenda = coletor.salvar_emenda_transparencia(emenda_data, db_session)
                        if emenda:
                            resultados_ano['emendas_salvas'] += 1
                            valor_emenda = float(emenda.valor_emenda) if emenda.valor_emenda else 0.0
                            resultados_ano['valor_total'] += valor_emenda
                            
                            if emenda.deputado_id:
                                resultados_ano['emendas_com_autor'] += 1
                    
                    resultados_ano['deputados_processados'] += 1
                    
                    # Progresso
                    if i % 5 == 0 or i == len(deputados_com_emendas):
                        print(f"\n📊 PROGRESSO PARCIAL - {ano}:")
                        print(f"   👥 Deputados: {resultados_ano['deputados_processados']}/{len(deputados_com_emendas)}")
                        print(f"   📄 Emendas: {resultados_ano['emendas_salvas']} salvas")
                        print(f"   💰 Valor: R$ {resultados_ano['valor_total']:,.2f}")
                        print(f"   📈 Taxa identificação: {100*resultados_ano['emendas_com_autor']/max(resultados_ano['emendas_salvas'],1):.1f}%")
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar {nome_deputado}: {e}")
                    resultados_ano['erros'] += 1
                    continue
            
            # Consolidar resultados do ano
            resultados_gerais['resultados_por_ano'][ano] = resultados_ano
            resultados_gerais['total_deputados_com_emendas'] += len(deputados_com_emendas)
            resultados_gerais['total_emendas_encontradas'] += resultados_ano['emendas_encontradas']
            resultados_gerais['total_emendas_salvas'] += resultados_ano['emendas_salvas']
            resultados_gerais['total_emendas_com_autor'] += resultados_ano['emendas_com_autor']
            resultados_gerais['valor_total_geral'] += resultados_ano['valor_total']
            resultados_gerais['erros'] += resultados_ano['erros']
            
            # Resumo do ano
            print(f"\n📋 RESUMO FINAL - {ano}:")
            print("=" * 30)
            print(f"👥 Deputados com emendas: {len(deputados_com_emendas)}")
            print(f"👥 Deputados processados: {resultados_ano['deputados_processados']}")
            print(f"📄 Emendas encontradas: {resultados_ano['emendas_encontradas']}")
            print(f"💾 Emendas salvas: {resultados_ano['emendas_salvas']}")
            print(f"👥 Com autor identificado: {resultados_ano['emendas_com_autor']}")
            print(f"💰 Valor total: R$ {resultados_ano['valor_total']:,.2f}")
            print(f"❌ Erros: {resultados_ano['erros']}")
        
        # Relatório final
        print(f"\n🎉 RELATÓRIO FINAL DA COLETA OTIMIZADA")
        print("=" * 70)
        print(f"👥 Total deputados com emendas: {resultados_gerais['total_deputados_com_emendas']}")
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
            print(f"   📊 Emendas por deputado: {resultados_gerais['total_emendas_salvas']/max(resultados_gerais['total_deputados_com_emendas'],1):.1f}")
            
            # Avaliação de resultado
            if resultados_gerais['valor_total_geral'] > 1_000_000_000:  # Mais de 1 bilhão
                print(f"\n🏆 RESULTADO EXTRAORDINÁRIO!")
                print(f"💰 Mais de R$ 1 bilhão em emendas coletadas!")
            elif resultados_gerais['valor_total_geral'] > 100_000_000:  # Mais de 100 milhões
                print(f"\n🎉 RESULTADO EXCELENTE!")
                print(f"💰 Mais de R$ 100 milhões em emendas coletadas!")
            elif resultados_gerais['valor_total_geral'] > 10_000_000:  # Mais de 10 milhões
                print(f"\n✅ RESULTADO MUITO BOM!")
                print(f"💰 Mais de R$ 10 milhões em emendas coletadas!")
            else:
                print(f"\n⚠️ RESULTADO ABAIXO DO ESPERADO")
                print(f"💰 Apenas R$ {resultados_gerais['valor_total_geral']:,.2f} coletados")
        
        # Salvar relatório detalhado
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_relatorio = f"relatorio_coleta_final_otimizada_{timestamp}.txt"
        
        with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO FINAL - COLETA OTIMIZADA DE EMENDAS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Estratégia: Otimizada com mapeamento dinâmico\n")
            f.write(f"Total deputados com emendas: {resultados_gerais['total_deputados_com_emendas']}\n")
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
                f.write(f"  Deputados com emendas: {resultados['deputados_processados']}\n")
                f.write(f"  Emendas salvas: {resultados['emendas_salvas']}\n")
                f.write(f"  Valor total: R$ {resultados['valor_total']:,.2f}\n")
                f.write(f"  Taxa identificação: {100*resultados['emendas_com_autor']/max(resultados['emendas_salvas'],1):.1f}%\n")
        
        print(f"\n📄 Relatório detalhado salvo em: {arquivo_relatorio}")
        
    except Exception as e:
        print(f"\n❌ ERRO GERAL DURANTE COLETA: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    import time
    from sqlalchemy import func
    main()
