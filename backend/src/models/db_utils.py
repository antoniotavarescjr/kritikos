from . import database

def get_db_session():
    """
    Função auxiliar para obter uma sessão de banco de dados.
    
    Returns:
        Session: Uma sessão do banco de dados SQLAlchemy
    """
    return database.SessionLocal()
