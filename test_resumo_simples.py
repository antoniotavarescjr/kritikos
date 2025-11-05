#!/usr/bin/env python3
"""
Script de teste simples para o SummarizerAgent usando API Gemini direta.
"""

import os
import sys
from datetime import datetime

# Adicionar paths necessários
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

def testar_gemini_api():
    """
    Testa a API Gemini diretamente sem Vertex AI.
    """
    print("🔗 TESTANDO CONEXÃO COM GEMINI API DIRETA")
    print("="*50)
    
    try:
        import google.generativeai as genai
        
        # Tentar usar API key se disponível
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            print("Usando API Key do Gemini...")
            genai.configure(api_key=api_key)
        else:
            print("Tentando usar Application Default Credentials...")
            # Tentar usar credenciais padrão
            genai.configure()
        
        # Teste simples
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content('Responda apenas com "OK" para teste de conexão.')
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"   Resposta: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def testar_resumo_manual():
    """
    Testa geração de resumo com texto manual.
    """
    print("\n📝 TESTANDO GERAÇÃO DE RESUMO")
    print("="*50)
    
    try:
        import google.generativeai as genai
        
        # Configurar
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            genai.configure()
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Texto de exemplo
        texto_exemplo = """
        PROJETO DE LEI Nº 1.234/2025
        
        EMENTA: Institui o Programa Nacional de Incentivo à Educação Ambiental nas escolas de ensino fundamental e médio, 
        estabelece diretrizes para implementação de atividades de conscientização ambiental e dá outras providências.
        
        TEXTO: Art. 1º Fica instituído o Programa Nacional de Incentivo à Educação Ambiental (PNIEA), 
        com o objetivo de promover a conscientização ambiental nas escolas brasileiras.
        
        Art. 2º O programa será implementado em todas as escolas públicas e privadas de ensino fundamental 
        e médio do território nacional.
        
        Art. 3º As atividades do programa incluirão:
        I - Aulas práticas de jardinagem e reciclagem;
        II - Visitas a áreas de conservação ambiental;
        III - Campanhas de redução do consumo de plástico;
        IV - Competências escolares de projetos sustentáveis.
        
        Art. 4º Os recursos para implementação do programa serão provenientes de dotações orçamentárias 
        da União, complementados por parcerias com o setor privado.
        """
        
        prompt = f"""
        Você é um assistente especializado em análise legislativa para o projeto Kritikos.
        Gere um resumo conciso e objetivo em português focado em:
        - Propósito Central
        - Escopo e Impacto
        - Mecanismo de Ação
        - Sustentabilidade Fiscal
        
        Não ultrapasse 250 palavras.
        
        Texto da proposta:
        {texto_exemplo}
        """
        
        print("Gerando resumo...")
        response = model.generate_content(prompt)
        
        if response and response.text:
            print(f"✅ Resumo gerado com sucesso!")
            print(f"   Tamanho: {len(response.text)} caracteres")
            print(f"   Preview: {response.text[:300]}...")
            return True
        else:
            print("❌ Falha ao gerar resumo!")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao gerar resumo: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTE SIMPLES DO AGENTE DE RESUMO")
    print("="*60)
    
    # Testar conexão
    if not testar_gemini_api():
        print("❌ Falha na conexão. Verifique as credenciais.")
        sys.exit(1)
    
    # Testar resumo
    if testar_resumo_manual():
        print("\n✅ Teste de resumo concluído com sucesso!")
    else:
        print("\n❌ Teste de resumo falhou.")
