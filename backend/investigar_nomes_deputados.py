#!/usr/bin/env python3
"""
Investigar diferença entre nomes no banco e na API
"""

import sys
import os
from pathlib import Path

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "src"))
# --- Fim do Bloco ---

# Importar modelos
from models.db_utils import get_db_session
from models.politico_models import Deputado
from sqlalchemy import func

# Importar coletor
from src.etl.coleta_emendas_transparencia import ColetorEmendasTransparencia

def main():
    """
    Investigar nomes de deputados que funcionam no teste
    """
    print("🔍 INVESTIGANDO NOMES DE DEPUTADOS")
    print("=" * 50)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        coletor = ColetorEmendasTransparencia()
        
        # Nomes que funcionaram no teste
        nomes_teste = ["NIKOLAS FERREIRA", "TABATA AMARAL"]
        
        print("\n🎯 VERIFICANDO NOMES QUE FUNCIONARAM NO TESTE:")
        print("=" * 50)
        
        for nome_teste in nomes_teste:
            print(f"\n👥 Testando: {nome_teste}")
            
            # Buscar no banco
            deputado = db_session.query(Deputado).filter(
                Deputado.nome.ilike(f"%{nome_teste}%")
            ).first()
            
            if deputado:
                print(f"   ✅ Encontrado no banco: {deputado.nome}")
                print(f"   🆔 ID: {deputado.id}")
            else:
                print(f"   ❌ NÃO encontrado no banco")
            
            # Testar na API
            emendas = coletor.buscar_todas_emendas_deputado(nome_teste, 2024)
            print(f"   📄 Emendas na API: {len(emendas)}")
            
            if emendas:
                print(f"   💰 Primeira emenda: {emendas[0].get('codigoEmenda', 'N/A')}")
                print(f"   👤 Nome na API: {emendas[0].get('nomeAutor', 'N/A')}")
        
        print(f"\n🔍 VERIFICANDO NOMES SIMILARES NO BANCO:")
        print("=" * 50)
        
        # Buscar nomes similares
        for nome_teste in nomes_teste:
            print(f"\n👥 Buscando similares para: {nome_teste}")
            
            similares = db_session.query(Deputado).filter(
                Deputado.nome.ilike(f"%{nome_teste.split()[0]}%")
            ).limit(5).all()
            
            for dep in similares:
                print(f"   📝 {dep.nome} (ID: {dep.id})")
        
        print(f"\n🔍 TESTANDO VARIAÇÕES DOS NOMES:")
        print("=" * 50)
        
        # Testar variações
        variacoes = {
            "NIKOLAS FERREIRA": [
                "NIKOLAS FERREIRA",
                "Nikolas Ferreira", 
                "NIKOLAS FERREIRA DE OLIVEIRA",
                "Nikolas Ferreira de Oliveira"
            ],
            "TABATA AMARAL": [
                "TABATA AMARAL",
                "Tabata Amaral",
                "TABATA AMARAL DE PONTES",
                "Tabata Amaral de Pontes"
            ]
        }
        
        for nome_original, lista_variacoes in variacoes.items():
            print(f"\n👥 Testando variações para: {nome_original}")
            
            for variacao in lista_variacoes:
                print(f"\n   📝 Testando: '{variacao}'")
                
                # Buscar no banco
                deputado = db_session.query(Deputado).filter(
                    func.upper(Deputado.nome) == func.upper(variacao.strip())
                ).first()
                
                if deputado:
                    print(f"      ✅ Encontrado no banco: {deputado.nome}")
                else:
                    print(f"      ❌ NÃO encontrado no banco")
                
                # Testar na API
                emendas = coletor.buscar_todas_emendas_deputado(variacao, 2024)
                print(f"      📄 Emendas na API: {len(emendas)}")
                
                if emendas:
                    print(f"      💰 Primeira emenda: {emendas[0].get('codigoEmenda', 'N/A')}")
                    print(f"      👤 Nome na API: {emendas[0].get('nomeAutor', 'N/A')}")
        
        print(f"\n🎯 CONCLUSÕES:")
        print("=" * 30)
        print(f"1. Verificar diferença entre nomes no banco vs API")
        print(f"2. Identificar formato correto para busca")
        print(f"3. Ajustar estratégia de matching")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE INVESTIGAÇÃO: {e}")
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
