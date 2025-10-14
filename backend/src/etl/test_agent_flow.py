# /backend/src/etl/test_agent_flow.py

import asyncio
import os
import json
from pathlib import Path

# --- Bloco de Configuração de Caminho (sem alterações) ---
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

# Classe simples para representar uma parte do conteúdo
class Part:
    def __init__(self, text: str):
        self.text = text

# Classe simples para representar uma mensagem com role
class Content:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.parts = [Part(text=content)]  # ADK espera que parts seja uma lista de objetos

# Textos de exemplo (sem alterações)
PROPOSAL_TEXT_COMPLEX = """
PROJETO DE LEI Nº 1234, DE 2025
(Do Sr. Deputado Ciclano de Tal)
Institui a Política Nacional de Incentivo à Agricultura Urbana Sustentável e estabelece diretrizes para o aproveitamento de espaços ociosos em centros urbanos para a produção de alimentos...
""" # (O resto do texto está oculto para brevidade)
PROPOSAL_TEXT_TRIVIAL = """
PROJETO DE LEI Nº 5678, DE 2025
(Do Sr. Deputado Beltrano de Tal)
Denomina "Viaduto Vereador José da Silva" o complexo viário localizado no cruzamento da Avenida Brasil com a Avenida Principal na cidade de Curitiba, Estado do Paraná...
""" # (O resto do texto está oculto para brevidade)


async def main():
    print("--- INICIANDO TESTE DO FLUXO DE AGENTES KRITIKOS ---")
    
    # Configurar variáveis de ambiente para o Vertex AI
    import os
    os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'true'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'kritikos-474618'
    os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'
    
    # Tentar configurar credenciais do Vertex AI explicitamente
    try:
        from google.cloud import aiplatform
        aiplatform.init(project='kritikos-474618', location='us-central1')
        print("Vertex AI inicializado com sucesso!")
        
        # Tentar configurar credenciais para o ADK
        import google.auth
        credentials, project = google.auth.default()
        print(f"Credenciais carregadas para o projeto: {project}")
        
    except Exception as e:
        print(f"Aviso: Não foi possível inicializar Vertex AI: {e}")
        print("NOTA: O teste continuará, mas os agentes LLM não funcionarão sem credenciais.")
        print("Para resolver: execute 'gcloud auth application-default login'")
    
    print("Configurações do GCP:")
    print(f"  Projeto: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"  Location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")
    print(f"  Usando Vertex AI: {os.environ.get('GOOGLE_GENAI_USE_VERTEXAI')}")
    
    agent_configs_dir = PROJECT_ROOT / "agents" / "configs"
    root_agent_filename = "root_agent.yaml"
    
    # --- WORKAROUND PARA O BUG DE CAMINHO DO ADK NO WINDOWS ---
    print(f"Carregando agente de '{root_agent_filename}'...")
    # Usa o caminho absoluto para evitar problemas de resolução de caminho
    root_agent_path = agent_configs_dir / root_agent_filename
    root_agent = from_config(config_path=str(root_agent_path))
    # --- FIM DO WORKAROUND ---
    
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="KritikosTest",
        agent=root_agent,
        session_service=session_service
    )
    
    print(f"\n[ETAPA 1/2] Testando proposta COMPLEXA...")
    try:
        session = await session_service.create_session(
            app_name="KritikosTest",
            user_id="test_user"
        )
        
        result_generator = runner.run(
            session_id=session.id,
            user_id="test_user",
            new_message=Content(role="user", content=PROPOSAL_TEXT_COMPLEX),
        )
        
        # Itera sobre o generator para obter os resultados
        final_result_complex = None
        for event in result_generator:
            if hasattr(event, 'content'):
                final_result_complex = event.content
                if final_result_complex:  # Para quando receber conteúdo válido
                    break
        
        print("\n--- RESULTADO FINAL (COMPLEXA) ---")
        
        if final_result_complex:
            # O resultado do ADK pode ser uma string JSON, então vamos tentar parseá-la
            try:
                parsed_result = json.loads(final_result_complex)
                print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, TypeError):
                print(final_result_complex) # Se não for JSON, imprime como está
        else:
            print("Nenhum resultado foi retornado pelo agente.")

    except Exception as e:
        import traceback
        print(f"\nERRO AO PROCESSAR PROPOSTA COMPLEXA: {e}")
        traceback.print_exc()

    print("\n" + "="*50 + "\n")

    print(f"[ETAPA 2/2] Testando proposta TRIVIAL...")
    try:
        session = await session_service.create_session(
            app_name="KritikosTest",
            user_id="test_user"
        )
        
        result_generator = runner.run(
            session_id=session.id,
            user_id="test_user",
            new_message=Content(role="user", content=PROPOSAL_TEXT_TRIVIAL),
        )
        
        # Itera sobre o generator para obter os resultados
        final_result_trivial = None
        for event in result_generator:
            if hasattr(event, 'content'):
                final_result_trivial = event.content
                if final_result_trivial:  # Para quando receber conteúdo válido
                    break
        
        print("\n--- RESULTADO FINAL (TRIVIAL) ---")
        if final_result_trivial:
            print(f"Resultado recebido: {final_result_trivial}")
        else:
            print("Nenhum resultado foi retornado pelo agente.")
        print("NOTA: O fluxo para a proposta trivial ainda não foi implementado com a lógica condicional.")
        
    except Exception as e:
        import traceback
        print(f"\nERRO AO PROCESSAR PROPOSTA TRIVIAL: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    backend_src_path = str(PROJECT_ROOT / "backend" / "src")
    if backend_src_path not in os.sys.path:
        os.sys.path.insert(0, backend_src_path)

    asyncio.run(main())
