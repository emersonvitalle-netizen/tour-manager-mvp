#!/usr/bin/env python3
"""
Corrige nullable=False para nullable=True no arquivo correto
"""

import os

arquivo = 'models/separation_list.py'

print(f"🔧 Corrigindo {arquivo}...")

# Ler arquivo
with open(arquivo, 'r') as f:
    conteudo = f.read()

# Trocar
conteudo_novo = conteudo.replace(
    "tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)",
    "tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=True)"
)

# Salvar
with open(arquivo, 'w') as f:
    f.write(conteudo_novo)

print("✅ Arquivo corrigido!")
print()
print("🚀 AGORA execute:")
print("   python3 reset_banco.py")