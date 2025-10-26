#!/usr/bin/env python3
"""
Mapear nomes da API para nomes do banco de dados
Criar tabela de correspondência para usar na coleta
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple

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

def obter_nomes_com_emendas_api(coletor, ano: int) -> List[str]:
    """
    Obtém lista de nomes que têm emendas na API
    """
    print(f"🔍 Obtendo nomes com emendas na API - {ano}")
    
    # Buscar emendas sem filtro de nome para pegar todos os autores
    params = {
        'ano': ano,
        'pagina': 1,
        'itens': 100  # Pegar uma amostra
    }
    
    emendas_amostra = coletor.fazer_requisicao_api(params)
    if not emendas_amostra:
        return []
    
    # Extrair nomes únicos
    nomes_unicos = set()
    for emenda in emendas_amostra:
        nome_autor = emenda.get('nomeAutor') or emenda.get('autor', '')
        if nome_autor and 'BANCADA' not in nome_autor.upper():
            nomes_unicos.add(nome_autor.strip().upper())
    
    return list(nomes_unicos)

def criar_mapeamento_nomes(coletor, db_session, ano: int) -> Dict[str, int]:
    """
    Cria mapeamento entre nomes da API e IDs do banco
    """
    print(f"\n🗺️ CRIANDO MAPEAMENTO DE NOMES - {ano}")
    print("=" * 50)
    
    # Obter nomes da API
    nomes_api = obter_nomes_com_emendas_api(coletor, ano)
    print(f"📊 Encontrados {len(nomes_api)} nomes únicos na API")
    
    # Obter todos os deputados do banco
    deputados_banco = db_session.query(Deputado.id, Deputado.nome).all()
    print(f"👥 Encontrados {len(deputados_banco)} deputados no banco")
    
    # Criar dicionário de busca
    banco_por_nome = {dep.nome.upper(): dep.id for dep in deputados_banco}
    banco_por_primeiro_nome = {}
    
    for dep in deputados_banco:
        primeiro_nome = dep.nome.split()[0].upper()
        if primeiro_nome not in banco_por_primeiro_nome:
            banco_por_primeiro_nome[primeiro_nome] = []
        banco_por_primeiro_nome[primeiro_nome].append((dep.nome, dep.id))
    
    # Mapear nomes
    mapeamento = {}
    nao_mapeados = []
    
    for nome_api in nomes_api:
        # 1. Busca exata
        if nome_api in banco_por_nome:
            mapeamento[nome_api] = banco_por_nome[nome_api]
            continue
        
        # 2. Busca sem acentos/maiúsculas
        nome_normalizado = ''.join(c for c in nome_api if c.isalnum()).upper()
        for nome_banco, id_banco in banco_por_nome.items():
            nome_banco_normalizado = ''.join(c for c in nome_banco if c.isalnum()).upper()
            if nome_normalizado == nome_banco_normalizado:
                mapeamento[nome_api] = id_banco
                break
        
        if nome_api in mapeamento:
            continue
        
        # 3. Busca por primeiro nome
        primeiro_nome_api = nome_api.split()[0].upper()
        if primeiro_nome_api in banco_por_primeiro_nome:
            # Se tiver apenas uma opção, usar ela
            if len(banco_por_primeiro_nome[primeiro_nome_api]) == 1:
                nome_banco, id_banco = banco_por_primeiro_nome[primeiro_nome_api][0]
                mapeamento[nome_api] = id_banco
                print(f"   📝 Mapeado por primeiro nome: '{nome_api}' -> '{nome_banco}'")
                continue
            else:
                # Se tiver múltiplas opções, mostrar para análise
                opcoes = [nome for nome, _ in banco_por_primeiro_nome[primeiro_nome_api]]
                print(f"   ⚠️ Múltiplas opções para '{nome_api}': {opcoes}")
                nao_mapeados.append((nome_api, "Múltiplas opções"))
                continue
        
        if nome_api not in mapeamento:
            nao_mapeados.append((nome_api, "Não encontrado"))
    
    print(f"\n📊 RESULTADO DO MAPEAMENTO:")
    print(f"   ✅ Mapeados: {len(mapeamento)}")
    print(f"   ❌ Não mapeados: {len(nao_mapeados)}")
    print(f"   📈 Taxa de sucesso: {100*len(mapeamento)/len(nomes_api):.1f}%")
    
    if nao_mapeados:
        print(f"\n❌ NOMES NÃO MAPEADOS (amostra):")
        for nome, motivo in nao_mapeados[:10]:  # Mostrar apenas 10
            print(f"   📝 {nome} - {motivo}")
        if len(nao_mapeados) > 10:
            print(f"   ... e mais {len(nao_mapeados) - 10}")
    
    return mapeamento

def main():
    """
    Função principal para criar mapeamento de nomes
    """
    print("🗺️ MAPEADOR DE NOMES API vs BANCO")
    print("=" * 60)
    print("🎯 Criar correspondência entre nomes da API e IDs do banco")
    print("=" * 60)
    
    # Usar sessão do banco
    db_session = get_db_session()
    
    try:
        coletor = ColetorEmendasTransparencia()
        
        # Criar mapeamento para cada ano
        anos = [2024, 2023, 2022, 2021]
        mapeamento_completo = {}
        
        for ano in anos:
            print(f"\n{'='*60}")
            print(f"📅 PROCESSANDO ANO: {ano}")
            print(f"{'='*60}")
            
            mapeamento_ano = criar_mapeamento_nomes(coletor, db_session, ano)
            mapeamento_completo[ano] = mapeamento_ano
        
        # Salvar mapeamento completo
        print(f"\n💾 SALVANDO MAPEAMENTO COMPLETO")
        print("=" * 40)
        
        arquivo_mapeamento = f"mapeamento_nomes_api_banco_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        
        with open(arquivo_mapeamento, 'w', encoding='utf-8') as f:
            f.write('"""')
            f.write('Mapeamento entre nomes da API de emendas e IDs do banco de dados')
            f.write(f'\nGerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
            f.write('"""\n\n')
            f.write('MAPEAMENTO_NOMES_API_BANCO = {\n')
            
            for ano, mapeamento in mapeamento_completo.items():
                f.write(f'    {ano}: {{\n')
                for nome_api, id_banco in mapeamento.items():
                    f.write(f'        "{nome_api}": {id_banco},\n')
                f.write(f'    }},\n')
            
            f.write('}\n')
        
        print(f"✅ Mapeamento salvo em: {arquivo_mapeamento}")
        
        # Estatísticas finais
        total_nomes = sum(len(mapeamento) for mapeamento in mapeamento_completo.values())
        print(f"\n📊 ESTATÍSTICAS FINAIS:")
        print(f"   📅 Anos processados: {len(anos)}")
        print(f"   📝 Total de mapeamentos: {total_nomes}")
        print(f"   📈 Média por ano: {total_nomes/len(anos):.0f}")
        
        # Criar função de busca otimizada
        print(f"\n🔧 CRIANDO FUNÇÃO DE BUSCA OTIMIZADA")
        print("=" * 40)
        
        arquivo_funcao = f"busca_deputado_otimizada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        
        with open(arquivo_funcao, 'w', encoding='utf-8') as f:
            f.write('''"""
Função otimizada para buscar ID do deputado pelo nome
Usando mapeamento pré-calculado para melhor performance
"""

from sqlalchemy.orm import Session
from models.politico_models import Deputado
from sqlalchemy import func

# Importar mapeamento gerado
from mapeamento_nomes_api_banco import MAPEAMENTO_NOMES_API_BANCO

def buscar_deputado_por_nome_otimizado(nome_autor: str, ano: int, db: Session) -> int:
    """
    Busca ID do deputado usando mapeamento pré-calculado
    Fallback para busca no banco se não encontrar no mapeamento
    """
    if not nome_autor or 'BANCADA' in nome_autor.upper():
        return None
    
    # Normalizar nome
    nome_normalizado = nome_autor.strip().upper()
    
    # 1. Tentar mapeamento direto
    if ano in MAPEAMENTO_NOMES_API_BANCO:
        if nome_normalizado in MAPEAMENTO_NOMES_API_BANCO[ano]:
            return MAPEAMENTO_NOMES_API_BANCO[ano][nome_normalizado]
    
    # 2. Fallback para busca no banco (método original)
    deputado = db.query(Deputado).filter(
        func.upper(Deputado.nome) == func.upper(nome_autor.strip())
    ).first()
    
    if deputado:
        return deputado.id
    
    # 3. Busca parcial
    deputado = db.query(Deputado).filter(
        Deputado.nome.ilike(f"%{nome_autor.strip()}%")
    ).first()
    
    if deputado:
        return deputado.id
    
    # 4. Busca por primeiro nome
    partes_nome = nome_autor.strip().split()
    if len(partes_nome) >= 2:
        primeiro_nome = partes_nome[0]
        deputado = db.query(Deputado).filter(
            Deputado.nome.ilike(f"{primeiro_nome}%")
        ).first()
        
        if deputado:
            return deputado.id
    
    return None
''')
        
        print(f"✅ Função otimizada salva em: {arquivo_funcao}")
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE MAPEAMENTO: {e}")
    finally:
        db_session.close()

if __name__ == "__main__":
    from datetime import datetime
    main()
