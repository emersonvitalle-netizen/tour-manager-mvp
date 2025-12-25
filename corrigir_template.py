#!/usr/bin/env python3
"""
Corrige erro AppenderQuery no template detail.html
"""

import os
import re

arquivo = 'templates/separation/detail.html'

print(f"🔧 Corrigindo {arquivo}...")

if not os.path.exists(arquivo):
    print(f"❌ Arquivo não encontrado: {arquivo}")
    exit(1)

# Ler arquivo
with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Trocar todas as ocorrências
# De: sep_list.items|length
# Para: sep_list.items.count()
conteudo_novo = conteudo.replace(
    'sep_list.items|length',
    'sep_list.items.count()'
)

# Também trocar variação com espaços
conteudo_novo = conteudo_novo.replace(
    'sep_list.items | length',
    'sep_list.items.count()'
)

if conteudo != conteudo_novo:
    # Salvar
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo_novo)
    print("✅ Arquivo corrigido!")
else:
    print("⚠️  Nenhuma alteração necessária")

print()
print("🚀 Tente acessar a lista novamente!")