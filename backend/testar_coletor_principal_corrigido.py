#!/usr/bin/env python3
"""
Teste do coletor principal corrigido
Valida se as correções aplicadas funcionam corretamente
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

# Importar modelos
from models.db_utils import get_db_session
from models.politico_models import Deputado

# Importar coletor corrigido
from src.etl.coleta_emendas_transparencia import ColetorEmendasTransparencia

def main():
    """
    Teste do coletor principal com as correções aplicadas
    """
    print("🧪 TESTE DO COLETOR PRINCIPAL CORRIGIDO")
    print("=" * 60)
    print("🎯 Validando se as correções funcionam no coletor principal")
    print("=" * 60)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        # Inicializar coletor
        coletor = ColetorEmendasTransparencia()
        
        # Testar com deputados conhecidos
        deputados_teste = [
            "NIKOLAS FERREIRA",
            "TABATA AMARAL"
        ]
        
        ano_teste = 2024
        
        print(f"\n🎯 TESTE COM DEPUTADOS CONHECIDOS - {ano_teste}")
        print("=" * 50)
        
        resultados_teste = {
            'deputados_processados': 0,
            'emendas_encontradas': 0,
            'emendas_salvas': 0,
            'emendas_com_autor': 0,
            'valor_total': 0.0,
            'erros': 0
        }
        
        for i, nome_deputado in enumerate(deputados_teste, 1):
            print(f"\n🎯 PROCESSANDO DEPUTADO {i}/{len(deputados_teste)}: {nome_deputado}")
            print("-" * 50)
            
            try:
                # Usar o novo método de coleta por deputado
                emendas = coletor.buscar_todas_emendas_deputado(nome_deputado, ano_teste)
                resultados_teste['emendas_encontradas'] += len(emendas)
                
                if not emendas:
                    print(f"   ⚠️ Nenhuma emenda encontrada para {nome_deputado} em {ano_teste}")
                    resultados_teste['deputados_processados'] += 1
                    continue
                
                print(f"   📄 {len(emendas)} emendas encontradas")
                
                # Salvar cada emenda
                for j, emenda_data in enumerate(emendas[:5], 1):  # Limitar para teste
                    print(f"   📄 Salvando emenda {j}/{min(5, len(emendas))}: {emenda_data.get('codigoEmenda', 'N/A')}")
                    
                    emenda = coletor.salvar_emenda_transparencia(emenda_data, db_session)
                    if emenda:
                        resultados_teste['emendas_salvas'] += 1
                        valor_emenda = float(emenda.valor_emenda) if emenda.valor_emenda else 0.0
                        resultados_teste['valor_total'] += valor_emenda
                        
                        if emenda.deputado_id:
                            resultados_teste['emendas_com_autor'] += 1
                            print(f"      ✅ Autor identificado: {emenda.autor}")
                        else:
                            print(f"      ⚠️ Autor não identificado: {emenda_data.get('nomeAutor', 'N/A')}")
                
                resultados_teste['deputados_processados'] += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao processar deputado {nome_deputado}: {e}")
                resultados_teste['erros'] += 1
                continue
        
        print(f"\n📋 RESUMO DO TESTE:")
        print("=" * 30)
        print(f"👥 Deputados processados: {resultados_teste['deputados_processados']}")
        print(f"📄 Emendas encontradas: {resultados_teste['emendas_encontradas']}")
        print(f"💾 Emendas salvas: {resultados_teste['emendas_salvas']}")
        print(f"👥 Com autor identificado: {resultados_teste['emendas_com_autor']}")
        print(f"💰 Valor total: R$ {resultados_teste['valor_total']:,.2f}")
        print(f"❌ Erros: {resultados_teste['erros']}")
        
        # Avaliação do resultado
        if resultados_teste['valor_total'] > 0:
            print(f"\n🎉 SUCESSO! Coletor principal corrigido funcionando!")
            print(f"💰 Valores reais sendo salvos: R$ {resultados_teste['valor_total']:,.2f}")
            print(f"📈 Taxa de identificação de autores: {resultados_teste['emendas_com_autor']}/{resultados_teste['emendas_salvas']} ({100*resultados_teste['emendas_com_autor']/max(resultados_teste['emendas_salvas'],1):.1f}%)")
            
            # Verificar se as correções principais funcionaram
            if resultados_teste['emendas_com_autor'] > 0:
                print(f"✅ Correção de mapeamento de deputados: FUNCIONANDO")
            else:
                print(f"❌ Correção de mapeamento de deputados: FALHOU")
                
            if resultados_teste['valor_total'] > 1000:  # Pelo menos R$ 1.000
                print(f"✅ Correção de tratamento de valores: FUNCIONANDO")
            else:
                print(f"❌ Correção de tratamento de valores: FALHOU")
                
        else:
            print(f"\n⚠️ Ainda há problemas a investigar")
            print(f"🔍 Possíveis causas:")
            print(f"   - Problema na API")
            print(f"   - Mudança no formato dos dados")
            print(f"   - Erro nas correções aplicadas")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
