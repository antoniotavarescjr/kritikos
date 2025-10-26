#!/usr/bin/env python3
"""
Verificação do Estado Atual das Emendas no Banco
Testa hipóteses sobre o que está acontecendo com os dados
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

def verificar_estado_banco():
    """
    Verifica o estado atual das emendas no banco de dados
    """
    print("🔍 VERIFICAÇÃO DO ESTADO ATUAL DAS EMENDAS")
    print("=" * 60)
    
    try:
        # Importar modelos do banco
        from models.db_utils import get_db_session
        from models.emenda_models import EmendaParlamentar
        from models.politico_models import Deputado
        from sqlalchemy import func, and_
        
        db_session = get_db_session()
        
        print("\n📊 ESTATÍSTICAS GERAIS DE EMENDAS:")
        print("-" * 40)
        
        # Total de emendas
        total_emendas = db_session.query(func.count(EmendaParlamentar.id)).scalar()
        print(f"📄 Total de emendas no banco: {total_emendas}")
        
        if total_emendas == 0:
            print("\n❌ BANCO ESTÁ VAZIO DE EMENDAS!")
            print("🔍 Isso explica por que o teste encontrou R$ 0,00")
            print("🎯 O coletor do Portal da Transparência nunca foi executado")
            return "banco_vazio"
        
        # Emendas com deputado_id NULL
        emendas_sem_deputado = db_session.query(func.count(EmendaParlamentar.id)).filter(
            EmendaParlamentar.deputado_id.is_(None)
        ).scalar()
        
        print(f"👥 Emendas sem deputado (NULL): {emendas_sem_deputado}")
        
        # Emendas com valor = 0
        emendas_valor_zero = db_session.query(func.count(EmendaParlamentar.id)).filter(
            EmendaParlamentar.valor_emenda == 0
        ).scalar()
        
        print(f"💰 Emendas com valor = 0: {emendas_valor_zero}")
        
        # Emendas com valor > 0
        emendas_valor_positivo = db_session.query(func.count(EmendaParlamentar.id)).filter(
            EmendaParlamentar.valor_emenda > 0
        ).scalar()
        
        print(f"💰 Emendas com valor > 0: {emendas_valor_positivo}")
        
        # Soma total de valores
        soma_valores = db_session.query(func.sum(EmendaParlamentar.valor_emenda)).scalar() or 0
        print(f"💰 Soma total de valores: R$ {soma_valores:,.2f}")
        
        # Anos disponíveis
        anos_disponiveis = db_session.query(EmendaParlamentar.ano).distinct().all()
        anos = [ano[0] for ano in anos_disponiveis if ano[0]]
        print(f"📅 Anos disponíveis: {sorted(anos)}")
        
        # Fontes dos dados
        fontes = db_session.query(
            EmendaParlamentar.api_camara_id,
            func.count(EmendaParlamentar.id)
        ).group_by(EmendaParlamentar.api_camara_id).limit(10).all()
        
        print(f"\n🔍 AMOSTRA DE FONTES (API IDs):")
        for api_id, count in fontes:
            print(f"   {api_id}: {count} emendas")
        
        # Top deputados (se houver)
        if emendas_valor_positivo > 0:
            top_deputados = db_session.query(
                Deputado.nome,
                func.count(EmendaParlamentar.id).label('quantidade'),
                func.sum(EmendaParlamentar.valor_emenda).label('valor_total')
            ).join(
                EmendaParlamentar, Deputado.id == EmendaParlamentar.deputado_id
            ).filter(
                EmendaParlamentar.valor_emenda > 0
            ).group_by(
                Deputado.id, Deputado.nome
            ).order_by(
                func.sum(EmendaParlamentar.valor_emenda).desc()
            ).limit(5).all()
            
            print(f"\n🏆 TOP 5 DEPUTADOS (se houver dados):")
            for nome, qtd, valor in top_deputados:
                print(f"   {nome}: {qtd} emendas, R$ {valor:,.2f}")
        
        db_session.close()
        
        # Análise do estado
        if total_emendas > 0 and soma_valores == 0:
            return "dados_sem_valor"
        elif total_emendas > 0 and emendas_sem_deputado > 0:
            return "dados_sem_deputado"
        elif total_emendas > 0 and soma_valores > 0:
            return "dados_existentes"
        else:
            return "estado_desconhecido"
            
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        return "erro_verificacao"

def verificar_deputados_teste():
    """
    Verifica se os deputados do teste existem no banco
    """
    print("\n👥 VERIFICAÇÃO DE DEPUTADOS DO TESTE:")
    print("-" * 40)
    
    try:
        from models.db_utils import get_db_session
        from models.politico_models import Deputado
        from models.emenda_models import EmendaParlamentar
        from sqlalchemy import func
        
        db_session = get_db_session()
        
        # Deputados do teste
        deputados_teste = [
            "NIKOLAS FERREIRA",
            "TABATA AMARAL", 
            "KIM KATAGUIRI",
            "CARLA ZAMBELLI"
        ]
        
        for nome_deputado in deputados_teste:
            print(f"\n🔍 Verificando: {nome_deputado}")
            
            # Buscar deputado
            deputado = db_session.query(Deputado).filter(
                func.upper(Deputado.nome) == func.upper(nome_deputado)
            ).first()
            
            if deputado:
                print(f"   ✅ Deputado encontrado: ID {deputado.id}")
                
                # Buscar emendas deste deputado
                emendas = db_session.query(func.count(EmendaParlamentar.id)).filter(
                    EmendaParlamentar.deputado_id == deputado.id
                ).scalar()
                
                valor_total = db_session.query(func.sum(EmendaParlamentar.valor_emenda)).filter(
                    EmendaParlamentar.deputado_id == deputado.id
                ).scalar() or 0
                
                print(f"   📄 Emendas: {emendas}")
                print(f"   💰 Valor total: R$ {valor_total:,.2f}")
                
            else:
                print(f"   ❌ Deputado NÃO encontrado no banco")
                
                # Tentar busca aproximada
                deputado_aprox = db_session.query(Deputado).filter(
                    Deputado.nome.ilike(f"%{nome_deputado}%")
                ).first()
                
                if deputado_aprox:
                    print(f"   ⚠️ Nome similar encontrado: {deputado_aprox.nome}")
                else:
                    print(f"   ❌ Nenhum nome similar encontrado")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Erro ao verificar deputados: {e}")

def analisar_fonte_dados():
    """
    Analisa a fonte dos dados existentes
    """
    print("\n🔍 ANÁLISE DA FONTE DOS DADOS:")
    print("-" * 40)
    
    try:
        from models.db_utils import get_db_session
        from models.emenda_models import EmendaParlamentar
        from sqlalchemy import func
        
        db_session = get_db_session()
        
        # Verificar padrão dos IDs
        emendas_amostra = db_session.query(
            EmendaParlamentar.api_camara_id,
            EmendaParlamentar.ano,
            EmendaParlamentar.valor_emenda,
            EmendaParlamentar.deputado_id
        ).limit(10).all()
        
        print(f"\n📋 AMOSTRA DE EMENDAS (primeiras 10):")
        for i, (api_id, ano, valor, dep_id) in enumerate(emendas_amostra, 1):
            print(f"   {i}. API ID: {api_id} | Ano: {ano} | Valor: R$ {valor or 0:,.2f} | Dep ID: {dep_id}")
        
        # Verificar se são números (API Câmara) ou strings (Portal Transparência)
        ids_numericos = db_session.query(func.count(EmendaParlamentar.id)).filter(
            EmendaParlamentar.api_camara_id.regexp('^[0-9]+$')
        ).scalar()
        
        ids_texto = db_session.query(func.count(EmendaParlamentar.id)).filter(
            ~EmendaParlamentar.api_camara_id.regexp('^[0-9]+$')
        ).scalar()
        
        print(f"\n🔊 ANÁLISE DOS API IDs:")
        print(f"   📊 IDs numéricos (API Câmara): {ids_numericos}")
        print(f"   📝 IDs texto (Portal Transparência): {ids_texto}")
        
        db_session.close()
        
        if ids_numericos > 0 and ids_texto == 0:
            return "apenas_api_camara"
        elif ids_texto > 0 and ids_numericos == 0:
            return "apenas_portal_transparencia"
        else:
            return "fontes_mistas"
            
    except Exception as e:
        print(f"❌ Erro ao analisar fonte: {e}")
        return "erro_analise"

def main():
    """
    Função principal
    """
    print("🔍 VERIFICAÇÃO COMPLETA DO ESTADO ATUAL")
    print("=" * 60)
    print("🎯 Objetivo: Identificar o que está acontecendo com os dados de emendas")
    print("🔧 Método: Análise detalhada do banco de dados")
    print("=" * 60)
    
    try:
        # Verificar estado geral
        estado = verificar_estado_banco()
        
        # Verificar deputados do teste
        verificar_deputados_teste()
        
        # Analisar fonte dos dados
        fonte = analisar_fonte_dados()
        
        # Conclusão
        print(f"\n🎯 CONCLUSÃO DA ANÁLISE:")
        print("=" * 30)
        print(f"📊 Estado do banco: {estado}")
        print(f"🔊 Fonte dos dados: {fonte}")
        
        if estado == "banco_vazio":
            print(f"\n✅ DIAGNÓSTICO CLARO:")
            print(f"   ❌ O banco está vazio de emendas do Portal da Transparência")
            print(f"   🔧 Solução: Executar o coletor do Portal da Transparência")
            print(f"   📋 Próximo passo: Implementar correções no coletor")
            
        elif estado == "dados_sem_valor":
            print(f"\n✅ DIAGNÓSTICO CLARO:")
            print(f"   ❌ Dados existem mas com valores zerados")
            print(f"   🔧 Solução: Corrigir tratamento de valores no coletor")
            print(f"   📋 Próximo passo: Reexecutar coleta com valores corrigidos")
            
        elif estado == "dados_sem_deputado":
            print(f"\n✅ DIAGNÓSTICO CLARO:")
            print(f"   ❌ Dados existem mas sem vincular com deputados")
            print(f"   🔧 Solução: Corrigir mapeamento de nomes")
            print(f"   📋 Próximo passo: Melhorar busca de deputados")
            
        elif estado == "dados_existentes":
            print(f"\n✅ DIAGNÓSTICO CLARO:")
            print(f"   ✅ Dados existentes e válidos")
            print(f"   🔍 Problema pode estar na consulta do teste")
            print(f"   📋 Próximo passo: Verificar lógica de consulta")
        
        print(f"\n🎉 VERIFICAÇÃO CONCLUÍDA!")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE VERIFICAÇÃO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
