#!/usr/bin/env python3
"""
Investigar por que CSS não está aplicando
"""

import os

print("🔍 INVESTIGAÇÃO - CSS DARK CINEMATIC")
print("=" * 60)

# 1. Verificar se arquivo existe
css_path = 'static/css/dark-cinematic-override.css'

print(f"\n📂 Verificando arquivo: {css_path}")

if os.path.exists(css_path):
    print(f"  ✅ Arquivo existe!")

    # Tamanho
    size = os.path.getsize(css_path)
    print(f"  📏 Tamanho: {size} bytes")

    # Primeiras linhas
    with open(css_path, 'r') as f:
        linhas = f.readlines()[:10]

    print(f"\n📄 Primeiras linhas:")
    for i, linha in enumerate(linhas, 1):
        print(f"  {i}: {linha.rstrip()}")
else:
    print(f"  ❌ Arquivo NÃO encontrado!")
    print(f"\n📂 Arquivos em static/css/:")

    if os.path.exists('static/css'):
        for arquivo in os.listdir('static/css'):
            print(f"    - {arquivo}")
    else:
        print("    ❌ Pasta static/css/ não existe!")

# 2. Verificar base.html
print(f"\n📄 Verificando base.html...")

base_path = 'templates/base.html'

if os.path.exists(base_path):
    with open(base_path, 'r') as f:
        conteudo = f.read()

    if 'dark-cinematic-override.css' in conteudo:
        print("  ✅ base.html referencia o CSS!")

        # Mostrar linha
        linhas = conteudo.split('\n')
        for i, linha in enumerate(linhas, 1):
            if 'dark-cinematic-override' in linha:
                print(f"\n  Linha {i}:")
                print(f"    {linha.strip()}")
    else:
        print("  ❌ base.html NÃO referencia o CSS!")
        print("\n  🔍 CSS encontrados em base.html:")

        linhas = conteudo.split('\n')
        for i, linha in enumerate(linhas, 1):
            if '.css' in linha and 'link' in linha:
                print(f"    Linha {i}: {linha.strip()}")
else:
    print("  ❌ base.html não encontrado!")

# 3. Verificar permissões
print(f"\n🔐 Verificando permissões...")

if os.path.exists(css_path):
    import stat
    perms = oct(os.stat(css_path).st_mode)[-3:]
    print(f"  Permissões: {perms}")

    if perms >= '644':
        print(f"  ✅ Permissões OK (leitura permitida)")
    else:
        print(f"  ⚠️  Permissões podem estar bloqueando leitura")

print("\n" + "=" * 60)
print("🎯 DIAGNÓSTICO COMPLETO!")
print("=" * 60)