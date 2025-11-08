#!/usr/bin/env python3
"""
Script de exemplo para testar a Kritikos API
"""

import asyncio
import httpx
import json
from typing import Dict, Any

class KritikosAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Testa health check básico"""
        print("🔍 Testando health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_database_health(self) -> Dict[str, Any]:
        """Testa health check do banco de dados"""
        print("🗄️ Testando conexão com banco de dados...")
        try:
            response = await self.client.get(f"{self.base_url}/health/db")
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_list_deputados(self) -> Dict[str, Any]:
        """Testa listagem de deputados"""
        print("👥 Testando listagem de deputados...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/deputados",
                params={"page": 1, "per_page": 5}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_deputado_especifico(self, deputado_id: int = 745) -> Dict[str, Any]:
        """Testa busca de deputado específico"""
        print(f"👤 Testando busca do deputado {deputado_id}...")
        try:
            response = await self.client.get(f"{self.base_url}/api/deputados/{deputado_id}")
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_ranking_idp(self) -> Dict[str, Any]:
        """Testa ranking por IDP"""
        print("🏆 Testando ranking por IDP...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/ranking/idp",
                params={"page": 1, "per_page": 10}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_busca_proposicoes(self) -> Dict[str, Any]:
        """Testa busca de proposições"""
        print("📜 Testando busca de proposições...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/busca/proposicoes",
                params={"ementa": "educação", "page": 1, "per_page": 5}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_gastos_deputado(self, deputado_id: int = 745) -> Dict[str, Any]:
        """Testa gastos de um deputado"""
        print(f"💰 Testando gastos do deputado {deputado_id}...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/deputados/{deputado_id}/gastos",
                params={"ano": 2025, "page": 1, "per_page": 5}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_emendas_deputado(self, deputado_id: int = 745) -> Dict[str, Any]:
        """Testa emendas de um deputado"""
        print(f"📋 Testando emendas do deputado {deputado_id}...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/deputados/{deputado_id}/emendas",
                params={"ano": 2025, "page": 1, "per_page": 5}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def test_proposicoes_deputado(self, deputado_id: int = 745) -> Dict[str, Any]:
        """Testa proposições de um deputado"""
        print(f"📄 Testando proposições do deputado {deputado_id}...")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/deputados/{deputado_id}/proposicoes",
                params={"page": 1, "per_page": 5}
            )
            return {
                "status": "✅ Sucesso",
                "data": response.json(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "❌ Erro",
                "error": str(e),
                "status_code": None
            }
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("🚀 Iniciando testes da Kritikos API")
        print("=" * 50)
        
        tests = [
            self.test_health_check,
            self.test_database_health,
            self.test_list_deputados,
            self.test_deputado_especifico,
            self.test_ranking_idp,
            self.test_busca_proposicoes,
            self.test_gastos_deputado,
            self.test_emendas_deputado,
            self.test_proposicoes_deputado,
        ]
        
        results = []
        
        for test in tests:
            try:
                result = await test()
                results.append(result)
                print(f"Resultado: {result['status']}")
                if result.get('status_code'):
                    print(f"Status Code: {result['status_code']}")
                print("-" * 30)
            except Exception as e:
                print(f"❌ Erro ao executar teste: {e}")
                print("-" * 30)
        
        # Resumo final
        print("\n" + "=" * 50)
        print("📊 RESUMO DOS TESTES")
        print("=" * 50)
        
        success_count = sum(1 for r in results if "✅" in r["status"])
        total_count = len(results)
        
        print(f"✅ Testes bem-sucedidos: {success_count}/{total_count}")
        print(f"❌ Testes com erro: {total_count - success_count}/{total_count}")
        print(f"📈 Taxa de sucesso: {(success_count/total_count)*100:.1f}%")
        
        # Detalhes dos erros
        failed_tests = [r for r in results if "❌" in r["status"]]
        if failed_tests:
            print("\n❌ TESTES COM ERRO:")
            for i, test in enumerate(failed_tests, 1):
                print(f"{i}. {test.get('error', 'Erro desconhecido')}")
        
        await self.client.aclose()
        return results

async def main():
    """Função principal"""
    import sys
    
    # Verifica se a URL base foi passada como argumento
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🌐 Testando API em: {base_url}")
    
    tester = KritikosAPITester(base_url)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
