#!/usr/bin/env python3
"""
Script para limpar completamente o banco de dados do Kritikos.
Remove todos os registros permitindo uma repopulação limpa.
"""

import sys
from pathlib import Path

# Adicionar o diretório src ao sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.append(str(SRC_DIR))

from models.db_utils import get_db_session
from models.database import get_db
from models.politico_models import Deputado, Mandato
from models.base_models import Partido, Estado, Legislatura
from models.financeiro_models import GastoParlamentar
from sqlalchemy import text

def confirmar_limpeza():
    """Solicita confirmação do usuário antes de limpar o banco."""
    print("ATENCAO: Este script ira APAGAR TODOS os dados do banco!")
    print("Esta operacao é IRREVERSIVEL!")
    print("\nDados que serao removidos:")
    print("   • Todos os gastos parlamentares")
    print("   • Todos os mandatos")
    print("   • Todos os deputados")
    print("   • Todos os partidos")
    print("   • Todos os estados")
    print("   • Todas as legislaturas")
    print("\nDigite 'LIMPAR' em maiusculas para confirmar:")
    
    confirmacao = input("> ").strip()
    
    if confirmacao == "LIMPAR":
        return True
    else:
        print("Operacao cancelada pelo usuario.")
        return False

def contar_registros_antes(db):
    """Contagem de registros antes da limpeza."""
    print("\nREGISTROS ANTES DA LIMPEZA")
    print("=" * 40)
    
    try:
        partidos = db.query(Partido).count()
        deputados = db.query(Deputado).count()
        mandatos = db.query(Mandato).count()
        estados = db.query(Estado).count()
        legislaturas = db.query(Legislatura).count()
        gastos = db.query(GastoParlamentar).count()
        
        print(f"Partidos: {partidos}")
        print(f"Deputados: {deputados}")
        print(f"Mandatos: {mandatos}")
        print(f"Estados: {estados}")
        print(f"Legislaturas: {legislaturas}")
        print(f"Gastos Parlamentares: {gastos}")
        
        total = partidos + deputados + mandatos + estados + legislaturas + gastos
        print(f"\nTotal de registros: {total:,}")
        
        return total
        
    except Exception as e:
        print(f"Erro ao contar registros: {e}")
        return 0

def limpar_tabelas_em_ordem(db):
    """Limpa as tabelas na ordem correta para respeitar as foreign keys."""
    print("\nLIMPANDO TABELAS...")
    print("=" * 40)
    
    # Ordem reversa das dependências (filhos antes dos pais)
    tabelas = [
        ("Gastos Parlamentares", GastoParlamentar),
        ("Mandatos", Mandato),
        ("Deputados", Deputado),
        ("Legislaturas", Legislatura),
        ("Estados", Estado),
        ("Partidos", Partido)
    ]
    
    total_removido = 0
    
    for nome_tabela, modelo in tabelas:
        try:
            contador = db.query(modelo).count()
            if contador > 0:
                db.query(modelo).delete()
                db.commit()
                print(f"   OK {nome_tabela}: {contador:,} registros removidos")
                total_removido += contador
            else:
                print(f"   PULAR {nome_tabela}: ja estava vazia")
                
        except Exception as e:
            print(f"   ERRO ao limpar {nome_tabela}: {e}")
            db.rollback()
            return False
    
    print(f"\nTotal de registros removidos: {total_removido:,}")
    return True

def resetar_sequencias(db):
    """Reseta as sequências auto-increment do banco."""
    print("\nRESETANDO SEQUENCIAS...")
    print("=" * 40)
    
    try:
        # Resetar sequências das tabelas principais
        sequencias = [
            "ALTER SEQUENCE deputados_id_seq RESTART WITH 1",
            "ALTER SEQUENCE partidos_id_seq RESTART WITH 1", 
            "ALTER SEQUENCE estados_id_seq RESTART WITH 1",
            "ALTER SEQUENCE legislaturas_id_seq RESTART WITH 1",
            "ALTER SEQUENCE mandatos_id_seq RESTART WITH 1",
            "ALTER SEQUENCE gastos_parlamentares_id_seq RESTART WITH 1"
        ]
        
        for seq in sequencias:
            try:
                db.execute(text(seq))
                print(f"   OK {seq.split()[2]} resetada")
            except Exception as e:
                # Algumas sequências podem não existir, ignorar
                print(f"   AVISO Sequencia nao encontrada: {e}")
        
        db.commit()
        print("   OK Sequencias resetadas com sucesso!")
        
    except Exception as e:
        print(f"   AVISO Erro ao resetar sequencias: {e}")
        # Não é crítico, continue

def contar_registros_depois(db):
    """Contagem de registros após a limpeza."""
    print("\nREGISTROS APOS A LIMPEZA")
    print("=" * 40)
    
    try:
        partidos = db.query(Partido).count()
        deputados = db.query(Deputado).count()
        mandatos = db.query(Mandato).count()
        estados = db.query(Estado).count()
        legislaturas = db.query(Legislatura).count()
        gastos = db.query(GastoParlamentar).count()
        
        print(f"Partidos: {partidos}")
        print(f"Deputados: {deputados}")
        print(f"Mandatos: {mandatos}")
        print(f"Estados: {estados}")
        print(f"Legislaturas: {legislaturas}")
        print(f"Gastos Parlamentares: {gastos}")
        
        total = partidos + deputados + mandatos + estados + legislaturas + gastos
        print(f"\nTotal de registros: {total}")
        
        return total
        
    except Exception as e:
        print(f"Erro ao contar registros: {e}")
        return 0

def main():
    """Função principal do script."""
    print("LIMPEZA COMPLETA DO BANCO DE DADOS KRITIKOS")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Conectar ao banco
    try:
        db = next(get_db())
        print("OK Conexao com o banco estabelecida!")
    except Exception as e:
        print(f"ERRO na conexao com o banco: {e}")
        return
    
    try:
        # Mostrar estado atual
        total_antes = contar_registros_antes(db)
        
        if total_antes == 0:
            print("\nOK O banco ja esta vazio!")
            return
        
        # Solicitar confirmação
        if not confirmar_limpeza():
            return
        
        # Executar limpeza
        print("\nIniciando limpeza do banco...")
        
        if limpar_tabelas_em_ordem(db):
            resetar_sequencias(db)
            
            # Verificar resultado
            total_depois = contar_registros_depois(db)
            
            print("\nRESUMO DA OPERACAO")
            print("=" * 30)
            print(f"Registros antes: {total_antes:,}")
            print(f"Registros depois: {total_depois:,}")
            print(f"Registros removidos: {total_antes - total_depois:,}")
            
            if total_depois == 0:
                print("\nOK Banco de dados limpo com sucesso!")
                print("Agora voce pode repopular usando o script de coleta.")
            else:
                print(f"\nAVISO Ainda existem {total_depois} registros no banco.")
        else:
            print("\nERRO Falha durante a limpeza do banco.")
            
    except Exception as e:
        print(f"\nERRO Erro durante a limpeza: {e}")
        db.rollback()
        
    finally:
        db.close()
        print("\nOperacao finalizada.")

if __name__ == "__main__":
    from datetime import datetime
    main()
