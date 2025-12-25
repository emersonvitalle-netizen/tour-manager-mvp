#!/usr/bin/env python3
"""
RESET COMPLETO DO BANCO DE DADOS
Apaga tudo e recria com models corretos
"""

import os
import shutil
import sys

print("=" * 60)
print("🔥 RESET COMPLETO DO BANCO DE DADOS")
print("=" * 60)

# 1. APAGAR TUDO
print("\n📁 Apagando arquivos antigos...")

if os.path.exists('instance'):
    shutil.rmtree('instance')
    print("  ✅ instance/ apagada")

if os.path.exists('migrations'):
    shutil.rmtree('migrations')
    print("  ✅ migrations/ apagada")

# Limpar cache Python
for root, dirs, files in os.walk('.'):
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'))
        print(f"  ✅ {root}/__pycache__/ apagada")

print("\n🔨 Recriando banco de dados...")

# 2. IMPORTAR E RECRIAR
try:
    from main import app, db

    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        print("  ✅ Tabelas criadas")

        # Verificar separation_list.tour_id
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        columns = inspector.get_columns('separation_list')
        tour_id_col = [c for c in columns if c['name'] == 'tour_id'][0]

        print(f"\n🔍 Verificando tour_id:")
        print(f"  - nullable: {tour_id_col['nullable']}")

        if tour_id_col['nullable']:
            print("\n✅✅✅ SUCESSO!")
            print("  tour_id aceita NULL corretamente")
        else:
            print("\n❌ ERRO!")
            print("  tour_id ainda está NOT NULL")
            print("  Verifique o model separation_list.py")
            sys.exit(1)

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🚀 BANCO RECRIADO COM SUCESSO!")
print("=" * 60)
print("\n📋 PRÓXIMOS PASSOS:")
print("  1. Reinicie o Replit")
print("  2. Teste criar lista de separação")
print("  3. Deixe campo Tour vazio")
print("\n")