#!/usr/bin/env python3
"""
Script para executar a coleta de emendas com integração GCS
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar src ao path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

def main():
    print("🚀 EXECUTANDO COLETA DE EMENDAS COM GCS")
    print("=" * 60)
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    try:
        from etl.coleta_emendas import ColetorEmendas
        from models.db_utils import get_db_session
        
        # Inicializar coletor
        coletor = ColetorEmendas()
        db_session = get_db_session()
        
        print("✅ Coletor inicializado")
        print("✅ Conexão com banco estabelecida")
        print("✅ GCS disponível para uploads")
        
        # Anos para coleta
        anos = [2024, 2025]
        tipos_emenda = ['EMD', 'EMP']  # Emenda e Emenda de Plenário
        
        print(f"\n📅 Anos para coleta: {anos}")
        print(f"📄 Tipos de emenda: {tipos_emenda}")
        
        resultados_totais = {
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'emendas_com_gcs': 0,
            'votacoes_salvas': 0,
            'erros': 0
        }
        
        for ano in anos:
            print(f"\n" + "="*50)
            print(f"📄 COLETANDO EMENDAS - {ano}")
            print("="*50)
            
            resultados = coletor.coletar_emendas_periodo(ano, tipos_emenda, db_session)
            
            # Acumular resultados
            for key in resultados_totais:
                resultados_totais[key] += resultados[key]
            
            print(f"\n📋 RESUMO PARCIAL - {ano}")
            print(f"📄 Emendas encontradas: {resultados['emendas_encontradas']}")
            print(f"💾 Emendas salvas: {resultados['emendas_salvas']}")
            print(f"👥 Com autor identificado: {resultados['emendas_com_autor']}")
            print(f"📁 Uploads GCS realizados: {resultados['emendas_com_gcs']}")
            print(f"🗳️ Votações salvas: {resultados['votacoes_salvas']}")
            print(f"❌ Erros: {resultados['erros']}")
        
        # Gerar ranking final
        print(f"\n" + "="*50)
        print("🏆 GERANDO RANKING FINAL")
        print("="*50)
        
        for ano in anos:
            print(f"\n📊 Ranking {ano}:")
            coletor.gerar_ranking_emendas(ano, db_session)
        
        # Resumo final
        print(f"\n" + "="*60)
        print("🎉 RESUMO FINAL DA COLETA")
        print("="*60)
        print(f"📄 Total emendas encontradas: {resultados_totais['emendas_encontradas']}")
        print(f"💾 Total emendas salvas: {resultados_totais['emendas_salvas']}")
        print(f"👥 Total com autor identificado: {resultados_totais['emendas_com_autor']}")
        print(f"📁 Total uploads GCS: {resultados_totais['emendas_com_gcs']}")
        print(f"🗳️ Total votações salvas: {resultados_totais['votacoes_salvas']}")
        print(f"❌ Total erros: {resultados_totais['erros']}")
        
        if resultados_totais['emendas_salvas'] > 0:
            print(f"\n✅ Coleta realizada com sucesso!")
            print(f"📊 Taxa de sucesso: {(resultados_totais['emendas_salvas']/resultados_totais['emendas_encontradas']*100):.1f}%")
            print(f"📁 Taxa de upload GCS: {(resultados_totais['emendas_com_gcs']/resultados_totais['emendas_salvas']*100):.1f}%")
        else:
            print(f"\n⚠️ Nenhuma emenda foi salva. Verifique os logs acima.")
        
        db_session.close()
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE A COLETA: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
