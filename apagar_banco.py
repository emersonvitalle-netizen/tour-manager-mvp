#!/usr/bin/env python3
"""
Apaga banco - depois REINICIE o app
"""

import shutil
import os

print("🗑️  Apagando banco...")

if os.path.exists('instance'):
    shutil.rmtree('instance')
    print("✅ instance/ apagada")

if os.path.exists('models/__pycache__'):
    shutil.rmtree('models/__pycache__')
    print("✅ cache limpo")

print()
print("=" * 60)
print("✅ PRONTO!")
print("=" * 60)
print()
print("🚀 AGORA:")
print("   1. REINICIE o Replit (Stop → Run)")
print("   2. Teste criar e aprovar lista")
print()