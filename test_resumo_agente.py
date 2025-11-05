#!/usr/bin/env python3
"""
Script de teste isolado para o SummarizerAgent.
Testa a geração de resumos com proposições reais do banco.
"""

import os
import sys
from datetime import datetime

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents', 'tools'))

# Importar ferramentas
from document_summarizer_tool import summarize_proposal_text
from models.db_utils import get_db_session
from models.proposicao_models import Proposicao

def testar_agente_resumo():
    """
    Testa o agente de resumo com algumas proposições do banco.
    """
    print("🚀 INICIANDO TESTE DO SUMMARIZERAGENT")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)
    
    try:
        # Buscar algumas proposições para teste
        session = get_db_session()
        
        # Buscar 3 proposições diferentes para teste
        props = session.query(Proposicao).filter(
            Proposicao.ano == 2025
        ).limit(3).all()
        
        if not props:
            print("❌ Nenhuma proposição encontrada para teste!")
            return False
        
        print(f"📋 Encontradas {len(props)} proposições para teste")
        print()
        
        # Testar cada proposição
        for i, prop in enumerate(props, 1):
            print(f"🔍 TESTE {i}/{len(props)} - Proposição {prop.id}")
            print(f"   Tipo: {prop.tipo}")
            print(f"   Número: {prop.numero}/{prop.ano}")
            print(f"   Ementa: {prop.ementa[:100]}...")
            print()
            
            # Montar texto completo para teste
            texto_completo = f"""
            TIPO: {prop.tipo}
            NÚMERO: {prop.numero}/{prop.ano}
            EMENTA: {prop.ementa}
            TEXTO: {prop.texto_original or 'Texto não disponível'}
            """
            
            print("📝 Gerando resumo...")
            
            # Gerar resumo
            resumo = summarize_proposal_text(texto_completo, prop.id)
            
            if resumo:
                print(f"✅ Resumo gerado com sucesso!")
                print(f"   Tamanho: {len(resumo)} caracteres")
                print(f"   Preview: {resumo[:200]}...")
                print()
            else:
                print(f"❌ Falha ao gerar resumo!")
                print()
            
            print("-" * 60)
        
        print("🎉 TESTE CONCLUÍDO!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'session' in locals():
            session.close()

def testar_conexao_gemini():
    """
    Testa a conexão com o Gemini/Vertex AI.
    """
    print("🔗 TESTANDO CONEXÃO COM GEMINI/VERTEX AI")
    print("="*50)
    
    try:
        # Configurar variável de ambiente antes de importar
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "backend", "service-account-key.json")
        
        from google import genai
        
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
        LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        print(f"Projeto: {PROJECT_ID}")
        print(f"Localização: {LOCATION}")
        print(f"Credenciais: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
        
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION
        )
        
        # Teste simples
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Responda apenas com "OK" para teste de conexão.'
        )
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"   Resposta: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TESTE DO AGENTE DE RESUMO KRITIKOS")
    print("="*60)
    
    # Testar conexão primeiro
    if not testar_conexao_gemini():
        print("❌ Falha na conexão com Gemini. Verifique as credenciais.")
        sys.exit(1)
    
    print()
    
    # Testar agente de resumo
    if testar_agente_resumo():
        print("✅ Todos os testes passaram com sucesso!")
    else:
        print("❌ Alguns testes falharam. Verifique os logs acima.")
