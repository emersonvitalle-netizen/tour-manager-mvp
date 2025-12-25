#!/usr/bin/env python3
"""
Corrige work_list.py COM reload correto
"""

import os
import shutil
import sys
import importlib

print("=" * 60)
print("🔧 CORREÇÃO FINAL - WORK_LIST")
print("=" * 60)

# 1. Corrigir arquivo PRIMEIRO
print("\n📝 Corrigindo arquivo...")

arquivo_path = 'models/work_list.py'

with open(arquivo_path, 'r') as f:
    conteudo = f.read()

# Corrigir linha do tour_id
conteudo_novo = conteudo.replace(
    'tour_id = db.Column(db.Integer, nullable=False)',
    'tour_id = db.Column(db.Integer, nullable=True)'
)

# Também caso não tenha nullable
conteudo_novo = conteudo_novo.replace(
    'tour_id = db.Column(db.Integer)',
    'tour_id = db.Column(db.Integer, nullable=True)'
)

with open(arquivo_path, 'w') as f:
    f.write(conteudo_novo)

print("✅ Arquivo corrigido!")

# 2. Apagar banco
print("\n📁 Apagando banco...")

if os.path.exists('instance'):
    shutil.rmtree('instance')
    print("✅ instance/ apagada")

# 3. Limpar cache Python
print("\n🗑️  Limpando cache...")

if os.path.exists('models/__pycache__'):
    shutil.rmtree('models/__pycache__')
    print("✅ Cache limpo")

# 4. AGORA importar (vai ler arquivo corrigido)
print("\n🔄 Importando models...")

from main import app

with app.app_context():
    # Importar fresh
    import models.work_list
    import models.separation_list

    # Recarregar
    importlib.reload(models.work_list)
    importlib.reload(models.separation_list)

    print("✅ Models recarregados")

    # Criar banco
    print("\n🔨 Criando banco...")
    from extensions import db
    db.create_all()
    print("✅ Banco criado")

    # Verificar
    from sqlalchemy import inspect as sql_inspect
    inspector = sql_inspect(db.engine)

    cols_sep = inspector.get_columns('separation_list')
    sep_tour = [c for c in cols_sep if c['name'] == 'tour_id'][0]

    cols_work = inspector.get_columns('work_lists')
    work_tour = [c for c in cols_work if c['name'] == 'tour_id'][0]

    print(f"\n🔍 Verificação Final:")
    print(f"  separation_list.tour_id → nullable: {sep_tour['nullable']}")
    print(f"  work_lists.tour_id → nullable: {work_tour['nullable']}")

    if sep_tour['nullable'] and work_tour['nullable']:
        print("\n" + "=" * 60)
        print("✅✅✅ PERFEITO! TUDO CORRETO!")
        print("=" * 60)
        print("\n🚀 REINICIE O APP E TESTE!")
    else:
        print("\n❌ Ainda com problema")
        if not sep_tour['nullable']:
            print("  - separation_list.tour_id NOT NULL")
        if not work_tour['nullable']:
            print("  - work_lists.tour_id NOT NULL")
        sys.exit(1)