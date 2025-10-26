#!/usr/bin/env python3
"""
Testar o coletor corrigido com diferentes anos
"""

import sys
from pathlib import Path

# Adicionar src ao path
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))

from etl.coleta_emendas import ColetorEmendas
from models.db_utils import get_db_session

def testar_coletor_corrigido():
    """Testar coletor corrigido com vários anos"""
    print("🔍 TESTANDO COLETOR CORRIGIDO")
    print("=" * 50)
    
    db = get_db_session()
    coletor = ColetorEmendas()
    
    anos = [2022, 2023, 2024, 2025]
    tipos = ['EMD', 'EMP', 'EMC', 'EMR', 'EPV', 'EPL']
    
    try:
        for ano in anos:
            print(f"\n📅 Testando ano: {ano}")
            for tipo in tipos:
                print(f"   🔍 {tipo}/{ano}: ", end="")
                emendas = coletor.buscar_emendas_por_tipo(tipo, ano, limite=10)
                print(f"{len(emendas)} encontradas")
                
                if emendas:
                    print(f"      📄 Primeira: {tipo} {emendas[0].get('numero', '?')}/{emendas[0].get('ano', '?')}")
                    print(f"      📝 Ementa: {emendas[0].get('ementa', '')[:100]}...")
                    
                    # Testar salvar uma emenda
                    print(f"      💾 Testando salvar...")
                    salva = coletor.salvar_emenda(emendas[0], db)
                    if salva:
                        print(f"      ✅ Emenda salva com sucesso!")
                    else:
                        print(f"      ❌ Falha ao salvar emenda")
                    break  # Testar só o primeiro tipo que encontrar
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    testar_coletor_corrigido()
