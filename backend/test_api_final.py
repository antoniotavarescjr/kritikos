#!/usr/bin/env python3
"""
Teste final da API Kritikos após correções Pydantic V2
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Testar importação da API"""
    try:
        from api.main import app
        print("✅ API importada com sucesso!")
        
        # Verificar se a aplicação foi criada corretamente
        assert app.title == "Kritikos API"
        assert app.version == "1.0.0"
        print("✅ Configurações básicas da API verificadas")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao importar API: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schemas():
    """Testar importação dos schemas"""
    try:
        from schemas.deputado import DeputadoResponse
        from schemas.gasto import GastoResponse
        from schemas.emenda import EmendaResponse
        from schemas.proposicao import ProposicaoResponse
        from schemas.ranking import IDPRankingResponse
        print("✅ Todos os schemas importados com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar schemas: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routers():
    """Testar importação dos routers"""
    try:
        from routers import deputados, gastos, emendas, proposicoes, ranking, busca
        print("✅ Todos os routers importados com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar routers: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Testar configurações"""
    try:
        from api.config import settings
        print("✅ Configurações importadas com sucesso!")
        print(f"   HOST: {settings.HOST}")
        print(f"   PORT: {settings.PORT}")
        print(f"   DEBUG: {settings.DEBUG}")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar configurações: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal de teste"""
    print("🧪 Testando API Kritikos após correções Pydantic V2")
    print("=" * 60)
    
    tests = [
        ("Importação da API", test_import),
        ("Importação dos Schemas", test_schemas),
        ("Importação dos Routers", test_routers),
        ("Importação das Configurações", test_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testando: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n🎯 Total: {len(results)} testes")
    print(f"✅ Passaram: {passed}")
    print(f"❌ Falharam: {failed}")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! API está pronta para uso.")
        return 0
    else:
        print(f"\n⚠️  {failed} testes falharam. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
