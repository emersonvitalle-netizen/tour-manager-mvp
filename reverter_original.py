#!/usr/bin/env python3
"""
Reverte todas as mudanças de CSS/base.html ao estado original
"""

import os
import shutil

print("🔄 REVERTENDO AO ESTADO ORIGINAL")
print("=" * 60)

# 1. Remover CSS que criamos
print("\n🗑️  Removendo CSS dark cinematic criados...")

css_files = [
    'static/css/dark-cinematic-override.css',
    'static/css/dark-cinematic-FORCE.css',
    'static/css/dark-cinematic-CORES-APENAS.css'
]

for css in css_files:
    if os.path.exists(css):
        os.remove(css)
        print(f"  ✅ {css} removido")
    else:
        print(f"  ⚠️  {css} não existe")

# 2. Restaurar dark-theme.css se tiver backup
print("\n📂 Verificando backup dark-theme.css...")

if os.path.exists('static/css/dark-theme-OLD.css'):
    shutil.copy('static/css/dark-theme-OLD.css', 'static/css/dark-theme.css')
    print("  ✅ dark-theme.css restaurado do backup")
elif os.path.exists('static/css/dark-theme.css'):
    print("  ✅ dark-theme.css já existe")
else:
    print("  ❌ ATENÇÃO: dark-theme.css não encontrado!")
    print("  Você precisará restaurar manualmente")

# 3. Verificar base.html
print("\n📄 Verificando base.html...")

if os.path.exists('templates/base.html'):
    with open('templates/base.html', 'r') as f:
        conteudo = f.read()

    if 'dark-theme.css' in conteudo:
        print("  ✅ base.html está correto (chama dark-theme.css)")
    elif 'dark-cinematic' in conteudo:
        print("  ⚠️  base.html precisa correção (chama CSS errado)")
        print("\n  📝 Deve ter essa linha:")
        print('    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/dark-theme.css\') }}">')
    else:
        print("  ⚠️  base.html pode estar sem CSS!")
else:
    print("  ❌ base.html não encontrado!")

print("\n" + "=" * 60)
print("✅ PROCESSO CONCLUÍDO!")
print("=" * 60)
print("\n📋 PRÓXIMOS PASSOS:")
print("  1. Reinicie o Replit")
print("  2. Limpe cache do navegador (Ctrl+Shift+R)")
print("  3. Teste o sistema")
print("\n")