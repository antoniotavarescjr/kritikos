#!/usr/bin/env python3
"""
Investigar detalhes de uma emenda específica para entender estrutura dos dados
"""

import requests
import json

def investigar_emenda_especifica(emenda_id=2541270):
    """Investigar detalhes completos de uma emenda"""
    print(f"🔍 INVESTIGANDO EMENDA ID: {emenda_id}")
    print("=" * 60)
    
    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    
