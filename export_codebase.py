#!/usr/bin/env python3
"""
EXPORTADOR DE CÓDIGO BASE - TOUR Manager
==========================================
Rode no Shell do Replit:
    python export_codebase.py

Gera: CODEBASE_EXPORT.md (arquivo único com todo o código organizado)
Para subir como base de conhecimento no Claude Projects.
"""

import os
from datetime import datetime

# Configuração de pastas e extensões
FOLDERS = {
    'models': {'ext': ['.py'], 'desc': 'Modelos SQLAlchemy (banco de dados)'},
    'routes': {'ext': ['.py'], 'desc': 'Blueprints Flask (endpoints)'},
    'services': {'ext': ['.py'], 'desc': 'Lógica de negócio'},
    'utils': {'ext': ['.py'], 'desc': 'Utilitários'},
    'templates/auth': {'ext': ['.html'], 'desc': 'Templates - Autenticação'},
    'templates/company': {'ext': ['.html'], 'desc': 'Templates - Empresa'},
    'templates/equipment': {'ext': ['.html'], 'desc': 'Templates - Equipamentos'},
    'templates/financial': {'ext': ['.html'], 'desc': 'Templates - Financeiro'},
    'templates/kit': {'ext': ['.html'], 'desc': 'Templates - Kits'},
    'templates/leads': {'ext': ['.html'], 'desc': 'Templates - Leads/CRM'},
    'templates/maintenance': {'ext': ['.html'], 'desc': 'Templates - Manutenção'},
    'templates/orcamento': {'ext': ['.html'], 'desc': 'Templates - Orçamentos'},
    'templates/orcamento/pdf': {'ext': ['.html'], 'desc': 'Templates - Orçamento PDF'},
    'templates/relatorios': {'ext': ['.html'], 'desc': 'Templates - Relatórios'},
    'templates/rh': {'ext': ['.html'], 'desc': 'Templates - RH'},
    'templates/scanner': {'ext': ['.html'], 'desc': 'Templates - Scanners'},
    'templates/tour': {'ext': ['.html'], 'desc': 'Templates - Tours'},
    'templates/users': {'ext': ['.html'], 'desc': 'Templates - Usuários'},
    'templates/work_list': {'ext': ['.html'], 'desc': 'Templates - Work Lists'},
    'templates/docs': {'ext': ['.html'], 'desc': 'Templates - Documentação'},
    'templates/components': {'ext': ['.html'], 'desc': 'Templates - Componentes'},
    'static/js': {'ext': ['.js'], 'desc': 'JavaScript'},
    'static/css': {'ext': ['.css'], 'desc': 'CSS'},
}

# Arquivos raiz importantes
ROOT_FILES = [
    'main.py',
    'config.py',
    'extensions.py',
    'requirements.txt',
    'pyproject.toml',
]

# Templates na raiz de templates/
TEMPLATE_ROOT = {
    'templates': {'ext': ['.html'], 'desc': 'Templates - Raiz (base, dashboard)'}
}

OUTPUT_FILE = 'CODEBASE_EXPORT.md'

def get_file_content(filepath):
    """Lê conteúdo do arquivo com tratamento de encoding."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                return f.read()
        except:
            return f"[ERRO: Não foi possível ler {filepath}]"
    except Exception as e:
        return f"[ERRO: {str(e)}]"

def list_files_in_folder(folder, extensions):
    """Lista arquivos com extensões específicas numa pasta (sem recursão)."""
    files = []
    if not os.path.exists(folder):
        return files
    for f in sorted(os.listdir(folder)):
        filepath = os.path.join(folder, f)
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(f)
            if ext.lower() in extensions:
                files.append(filepath)
    return files

def count_lines(content):
    """Conta linhas do conteúdo."""
    return len(content.strip().split('\n')) if content.strip() else 0

def main():
    print(f"🚀 Exportando código base do TOUR Manager...")
    print(f"   Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    lines = []
    total_files = 0
    total_lines = 0

    # Header
    lines.append("# TOUR Manager - CÓDIGO BASE COMPLETO")
    lines.append(f"# Exportado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"# Use como base de conhecimento no Claude Projects")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Índice
    lines.append("## 📋 ÍNDICE")
    lines.append("")
    lines.append("### Arquivos Raiz")
    for f in ROOT_FILES:
        if os.path.exists(f):
            lines.append(f"- `{f}`")
    lines.append("")

    lines.append("### Por Pasta")
    all_folders = {**FOLDERS, **TEMPLATE_ROOT}
    for folder, info in all_folders.items():
        files = list_files_in_folder(folder, info['ext'])
        if files:
            names = [os.path.basename(f) for f in files]
            lines.append(f"- **{folder}/** ({len(files)} arquivos) — {info['desc']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ===== ARQUIVOS RAIZ =====
    lines.append("## 🏠 ARQUIVOS RAIZ")
    lines.append("")

    for filename in ROOT_FILES:
        if not os.path.exists(filename):
            print(f"   ⚠️  {filename} não encontrado, pulando...")
            continue

        content = get_file_content(filename)
        num_lines = count_lines(content)
        total_files += 1
        total_lines += num_lines

        lines.append(f"### 📄 {filename}")
        lines.append(f"**Caminho:** `{filename}` | **Linhas:** {num_lines}")
        lines.append("")
        ext = os.path.splitext(filename)[1]
        lang = 'python' if ext == '.py' else 'toml' if ext == '.toml' else 'text'
        lines.append(f"```{lang}")
        lines.append(content.rstrip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

        print(f"   ✅ {filename} ({num_lines} linhas)")

    # ===== PASTAS =====
    all_folders_ordered = dict(sorted({**FOLDERS, **TEMPLATE_ROOT}.items()))

    current_section = None
    for folder, info in all_folders_ordered.items():
        # Determinar seção
        if folder.startswith('models'):
            section = "MODELS"
            section_emoji = "🗄️"
        elif folder.startswith('routes'):
            section = "ROUTES"
            section_emoji = "🔀"
        elif folder.startswith('services'):
            section = "SERVICES"
            section_emoji = "⚙️"
        elif folder.startswith('utils'):
            section = "UTILS"
            section_emoji = "🔧"
        elif folder.startswith('templates'):
            section = "TEMPLATES"
            section_emoji = "📝"
        elif folder.startswith('static'):
            section = "STATIC"
            section_emoji = "🎨"
        else:
            section = "OTHER"
            section_emoji = "📁"

        if section != current_section:
            current_section = section
            lines.append(f"## {section_emoji} {section}")
            lines.append("")

        files = list_files_in_folder(folder, info['ext'])
        if not files:
            continue

        lines.append(f"### 📁 {folder}/ — {info['desc']}")
        lines.append("")

        for filepath in files:
            content = get_file_content(filepath)
            num_lines = count_lines(content)
            total_files += 1
            total_lines += num_lines

            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1]

            if ext == '.py':
                lang = 'python'
            elif ext == '.html':
                lang = 'html'
            elif ext == '.js':
                lang = 'javascript'
            elif ext == '.css':
                lang = 'css'
            else:
                lang = 'text'

            lines.append(f"#### 📄 {folder}/{filename}")
            lines.append(f"**Caminho completo:** `{filepath}` | **Linhas:** {num_lines}")
            lines.append("")
            lines.append(f"```{lang}")
            lines.append(content.rstrip())
            lines.append("```")
            lines.append("")

            print(f"   ✅ {filepath} ({num_lines} linhas)")

        lines.append("---")
        lines.append("")

    # Resumo final
    lines.append("## 📊 RESUMO DA EXPORTAÇÃO")
    lines.append("")
    lines.append(f"- **Total de arquivos:** {total_files}")
    lines.append(f"- **Total de linhas de código:** {total_lines:,}")
    lines.append(f"- **Data de exportação:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("*Gerado automaticamente por export_codebase.py*")

    # Escrever arquivo
    output = '\n'.join(lines)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

    file_size = os.path.getsize(OUTPUT_FILE)
    size_mb = file_size / (1024 * 1024)

    print()
    print(f"{'='*50}")
    print(f"✅ EXPORTAÇÃO COMPLETA!")
    print(f"   📄 Arquivo: {OUTPUT_FILE}")
    print(f"   📊 {total_files} arquivos | {total_lines:,} linhas")
    print(f"   💾 Tamanho: {size_mb:.1f} MB")
    print(f"{'='*50}")
    print()

    if size_mb > 10:
        print(f"⚠️  AVISO: Arquivo com {size_mb:.1f}MB pode ser grande")
        print(f"   para base de conhecimento do Claude.")
        print(f"   Considere dividir em partes menores.")
        print()

    print("📋 PRÓXIMOS PASSOS:")
    print("   1. Baixe o arquivo CODEBASE_EXPORT.md")
    print("   2. No Claude Projects → Base de Conhecimento")
    print("   3. Remova os arquivos antigos desorganizados")
    print("   4. Suba o CODEBASE_EXPORT.md")
    print()

if __name__ == '__main__':
    main()