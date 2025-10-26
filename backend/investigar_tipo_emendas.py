#!/usr/bin/env python3
"""
Investigar que tipo de emendas estão no banco de dados
"""

import sys
from pathlib import Path

# --- Bloco de Configuração de Caminho ---
SRC_DIR = Path(__file__).resolve().parent / 'src'
sys.path.append(str(SRC_DIR))
# --- Fim do Bloco ---

from models.database import get_db
from models.emenda_models import EmendaParlamentar

def investigar_emendas_banco():
    """Investigar detalhes das emendas no banco"""
    print("🔍 INVESTIGANDO EMENDAS NO BANCO DE DADOS")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Total de emendas
        total_emendas = db.query(EmendaParlamentar).count()
        print(f"📄 Total de emendas no banco: {total_emendas}")
        
        if total_emendas == 0:
            print("❌ Nenhuma emenda encontrada no banco!")
            return
        
        # Distribuição por tipo
        print(f"\n📊 DISTRIBUIÇÃO POR TIPO:")
        tipos = db.query(
            EmendaParlamentar.tipo_emenda,
            EmendaParlamentar.api_camara_id,
            EmendaParlamentar.numero,
            EmendaParlamentar.ano,
            EmendaParlamentar.emenda,
            EmendaParlamentar.valor_emenda,
            EmendaParlamentar.beneficiario_principal,
            EmendaParlamentar.autor
        ).all()
        
        if tipos:
            for i, (tipo, api_id, numero, ano, emenda_texto, valor, beneficiario, autor) in enumerate(tipos[:10], 1):
                print(f"\n📄 Emenda #{i}:")
                print(f"   Tipo: {tipo}")
                print(f"   ID API: {api_id}")
                print(f"   Número: {numero}")
                print(f"   Ano: {ano}")
                print(f"   Valor: R$ {valor if valor else 0.00}")
                print(f"   Beneficiário: {beneficiario or 'N/A'}")
                print(f"   Autor: {autor or 'N/A'}")
                print(f"   Texto: {emenda_texto[:100]}..." if emenda_texto else "   Texto: N/A")
        
        # Verificar se alguma tem valor
        com_valor = db.query(EmendaParlamentar).filter(
            EmendaParlamentar.valor_emenda.isnot(None),
            EmendaParlamentar.valor_emenda > 0
        ).count()
        
        print(f"\n💰 EMENDAS COM VALOR MONETÁRIO:")
        print(f"   Com valor > 0: {com_valor}")
        print(f"   Sem valor: {total_emendas - com_valor}")
        
        # Análise dos tipos
        print(f"\n📈 ANÁLISE DOS TIPOS:")
        from sqlalchemy import func
        tipos_contagem = db.query(
            EmendaParlamentar.tipo_emenda,
            func.count(EmendaParlamentar.id).label('quantidade')
        ).group_by(EmendaParlamentar.tipo_emenda).all()
        
        for tipo, quantidade in tipos_contagem:
            print(f"   {tipo}: {quantidade} emendas")
            
            # Verificar se em algum tipo tem valores
            valores_tipo = db.query(
                func.sum(EmendaParlamentar.valor_emenda)
            ).filter(
                EmendaParlamentar.tipo_emenda == tipo,
                EmendaParlamentar.valor_emenda.isnot(None)
            ).scalar()
            
            print(f"      Valor total: R$ {valores_tipo or 0.00}")
        
        # Exemplos de textos para entender natureza
        print(f"\n📝 EXEMPLOS DE TEXTOS DAS EMENDAS:")
        exemplos = db.query(
            EmendaParlamentar.tipo_emenda,
            EmendaParlamentar.emenda
        ).limit(5).all()
        
        for i, (tipo, texto) in enumerate(exemplos, 1):
            print(f"\n📄 Exemplo #{i} ({tipo}):")
            print(f"   {texto[:200]}..." if texto else "   Sem texto")
        
        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if com_valor == 0:
            print("   ❌ NENHUMA emenda tem valor monetário!")
            print("   🔍 São emendas LEGISLATIVAS (modificam textos)")
            print("   💡 Precisamos de emendas ORÇAMENTÁRIAS (alocam recursos)")
        else:
            print(f"   ✅ {com_valor} emendas têm valores monetários")
        
    except Exception as e:
        print(f"❌ Erro na investigação: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    investigar_emendas_banco()
