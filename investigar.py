#!/usr/bin/env python3
"""
Verifica EXATAMENTE qual arquivo está sendo usado
"""

import sys
import os

# Adicionar diretório atual ao path
sys.path.insert(0, os.getcwd())

print("🔍 Investigando imports...")
print()

# Importar Flask app
from main import app

with app.app_context():
    # Importar como o código faz
    from models.separation_list import SeparationList

    # Ver de onde veio
    import inspect
    file_path = inspect.getfile(SeparationList)

    print(f"📂 SeparationList importado de:")
    print(f"   {file_path}")
    print()

    # Ler a linha tour_id
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if 'tour_id' in line and 'Column' in line:
                print(f"📋 Linha {i}:")
                print(f"   {line.strip()}")

                if 'nullable=True' in line:
                    print("   ✅ Tem nullable=True")
                elif 'nullable=False' in line:
                    print("   ❌ Tem nullable=False")
                else:
                    print("   ⚠️  Sem nullable (padrão=False)")
                break