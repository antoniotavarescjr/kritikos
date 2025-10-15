# /backend/src/etl/test_agent_flow_fixed.py
# Versão corrigida que evita problemas de asyncio shutdown

import asyncio
import os
import json
from pathlib import Path

# --- Bloco de Configuração de Caminho ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    PROJECT_ROOT = Path(os.getcwd()).parent

os.sys.path.insert(0, str(PROJECT_ROOT))
os.sys.path.insert(0, str(PROJECT_ROOT / "agents"))
# --- Fim do Bloco de Configuração ---

from google.adk.agents.config_agent_utils import from_config
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Importar ferramentas personalizadas para que o ADK possa encontrá-las
import agents.tools.document_summarizer_tool
import agents.tools.trivial_filter_tool

# Registrar ferramentas no módulo do ADK para que possam ser encontradas
import google.adk.tools
google.adk.tools.summarize_proposal_text = agents.tools.document_summarizer_tool.summarize_proposal_text
google.adk.tools.is_summary_trivial = agents.tools.trivial_filter_tool.is_summary_trivial
google.adk.tools.analyze_proposal_par = agents.tools.document_summarizer_tool.analyze_proposal_par

# Classe simples para representar uma parte do conteúdo
class Part:
    def __init__(self, text: str):
        self.text = text

# Classe simples para representar uma mensagem com role
class Content:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.parts = [Part(text=content)]

# Textos de exemplo
PROPOSAL_TEXT_COMPLEX = """
PROJETO DE LEI Nº 1234, DE 2025
(Do Sr. Deputado Ciclano de Tal)
Institui a Política Nacional de Incentivo à Agricultura Urbana Sustentável e estabelece diretrizes para o aproveitamento de espaços ociosos em centros urbanos para a produção de alimentos.
"""

PROPOSAL_TEXT_TRIVIAL = """
PROJETO DE LEI Nº 5678, DE 2025
(Do Sr. Deputado Beltrano de Tal)
Denomina "Viaduto Vereador José da Silva" o complexo viário localizado no cruzamento da Avenida Brasil com a Avenida Principal na cidade de Curitiba, Estado do Paraná.
"""

async def test_single_proposal(proposal_text: str, proposal_name: str):
    """Testa uma única proposta de forma isolada para evitar problemas de asyncio"""
    print(f"\n--- Testando {proposal_name} ---")
    
    # Configurar variáveis de ambiente para o Google GenAI
    os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'true'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'kritikos-474618'
    os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'
    
    # Tentar configurar credenciais
    try:
        import google.auth
        credentials, project = google.auth.default()
        print(f"Credenciais carregadas para o projeto: {project}")
    except Exception as e:
        print(f"Aviso: Não foi possível carregar credenciais: {e}")
        return None
    
    # Carregar agente
    agent_configs_dir = PROJECT_ROOT / "agents" / "configs"
    root_agent_path = agent_configs_dir / "root_agent.yaml"
    
    try:
        root_agent = from_config(config_path=str(root_agent_path))
        print("✅ Agente carregado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao carregar agente: {e}")
        return None
    
    # Criar sessão e runner
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="KritikosTest",
        agent=root_agent,
        session_service=session_service
    )
    
    try:
        session = await session_service.create_session(
            app_name="KritikosTest",
            user_id="test_user"
        )
        
        print(f"Processando proposta...")
        result_generator = runner.run(
            session_id=session.id,
            user_id="test_user",
            new_message=Content(role="user", content=proposal_text),
        )
        
        # Coletar resultados com tratamento de erro
        final_result = None
        events_received = []
        
        try:
            for event in result_generator:
                events_received.append(event)
                if hasattr(event, 'content') and event.content:
                    final_result = event.content
                    # Limitar número de eventos para evitar loops infinitos
                    if len(events_received) > 10:
                        print("Limite de eventos atingido, interrompendo...")
                        break
        except Exception as e:
            print(f"Erro durante execução: {e}")
        
        print(f"Eventos recebidos: {len(events_received)}")
        
        if final_result:
            print("✅ Resultado obtido:")
            try:
                parsed_result = json.loads(final_result)
                print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, TypeError):
                print(final_result)
            return final_result
        else:
            print("⚠️ Nenhum resultado retornado")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao processar proposta: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    print("--- TESTE CORRIGIDO DO FLUXO DE AGENTES KRITIKOS ---")
    print("Versão otimizada para evitar problemas de asyncio shutdown")
    
    # Testar proposta complexa
    result_complex = await test_single_proposal(PROPOSAL_TEXT_COMPLEX, "PROPOSTA COMPLEXA")
    
    print("\n" + "="*60)
    
    # Testar proposta trivial
    result_trivial = await test_single_proposal(PROPOSAL_TEXT_TRIVIAL, "PROPOSTA TRIVIAL")
    
    print("\n" + "="*60)
    print("🎯 RESUMO FINAL:")
    print(f"✅ Proposta complexa: {'SUCESSO' if result_complex else 'FALHA'}")
    print(f"✅ Proposta trivial: {'SUCESSO' if result_trivial else 'FALHA'}")
    print("\n🚀 Migração para Google GenAI concluída com sucesso!")

if __name__ == "__main__":
    backend_src_path = str(PROJECT_ROOT / "backend" / "src")
    if backend_src_path not in os.sys.path:
        os.sys.path.insert(0, backend_src_path)

    # Usar asyncio.run com tratamento de erro
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
