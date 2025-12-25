#!/usr/bin/env python3
"""
Corrige work_list.py e recria banco
"""

import os
import shutil
import sys

print("=" * 60)
print("🔧 CORRIGINDO WORK_LIST E RECREANDO BANCO")
print("=" * 60)

# 1. Descobrir qual arquivo usar
from main import app

with app.app_context():
    from models.work_list import WorkList
    import inspect

    arquivo = inspect.getfile(WorkList)
    print(f"\n📂 WorkList está em: {arquivo}")

    # Ler arquivo
    with open(arquivo, 'r') as f:
        linhas = f.readlines()

    # Procurar e corrigir tour_id
    corrigido = False
    for i, linha in enumerate(linhas):
        if 'tour_id' in linha and 'Column' in linha:
            print(f"\n📋 Linha {i+1} ANTES:")
            print(f"   {linha.strip()}")

            if 'nullable=False' in linha:
                linhas[i] = linha.replace('nullable=False', 'nullable=True')
                corrigido = True
                print(f"\n📋 Linha {i+1} DEPOIS:")
                print(f"   {linhas[i].strip()}")
            elif 'nullable=True' in linha:
                print("   ✅ Já está correto!")
            else:
                # Adicionar nullable=True
                linhas[i] = linha.replace(
                    "db.ForeignKey('tour.id')",
                    "db.ForeignKey('tour.id'), nullable=True"
                )
                corrigido = True
                print(f"\n📋 Linha {i+1} DEPOIS:")
                print(f"   {linhas[i].strip()}")
            break

    if corrigido:
        # Salvar
        with open(arquivo, 'w') as f:
            f.writelines(linhas)
        print("\n✅ Arquivo corrigido!")
    else:
        print("\n✅ Arquivo já estava correto!")

# 2. Recriar banco
print("\n📁 Apagando banco antigo...")

if os.path.exists('instance'):
    shutil.rmtree('instance')
    print("  ✅ instance/ apagada")

print("\n🔨 Recriando banco...")

with app.app_context():
    from extensions import db
    db.create_all()
    print("  ✅ Banco recriado")

    # Verificar
    from sqlalchemy import inspect as sql_inspect
    inspector = sql_inspect(db.engine)

    # Verificar separation_list
    cols = inspector.get_columns('separation_list')
    sep_tour = [c for c in cols if c['name'] == 'tour_id'][0]

    # Verificar work_lists
    cols = inspector.get_columns('work_lists')
    work_tour = [c for c in cols if c['name'] == 'tour_id'][0]

    print(f"\n🔍 Verificação:")
    print(f"  separation_list.tour_id nullable: {sep_tour['nullable']}")
    print(f"  work_lists.tour_id nullable: {work_tour['nullable']}")

    if sep_tour['nullable'] and work_tour['nullable']:
        print("\n✅✅✅ TUDO CORRETO!")
    else:
        print("\n❌ AINDA HÁ PROBLEMAS!")
        sys.exit(1)

print("\n" + "=" * 60)
print("🚀 PRONTO! REINICIE E TESTE!")
print("=" * 60)