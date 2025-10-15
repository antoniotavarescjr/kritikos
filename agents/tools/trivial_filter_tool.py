# /agents/tools/trivial_filter_tool.py


# Palavras-chave que indicam uma proposição de baixo impacto
TRIVIAL_KEYWORDS = [
    "denomina", "logradouro", "homenagem", "batiza", "nomeia",
    "data comemorativa", "calendário oficial", "símbolo nacional",
    "cidadão honorário", "título de", "capital nacional de"
]

def is_summary_trivial(summary: str) -> bool:
    """
    Analisa o resumo de uma proposta para determinar se ela é trivial.
    Retorna True se a proposta for considerada de baixo impacto (ex: nome de rua, homenagem),
    caso contrário, retorna False.
    """
    texto_lower = summary.lower()
    
    # Verifica se alguma das palavras-chave triviais está presente no resumo
    for keyword in TRIVIAL_KEYWORDS:
        if keyword in texto_lower:
            print(f"DEBUG: Proposta trivial identificada (palavra-chave: '{keyword}').")
            return True
    
    print("DEBUG: Proposta não é trivial. Análise completa necessária.")
    return False
