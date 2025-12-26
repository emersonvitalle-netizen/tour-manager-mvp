#!/usr/bin/env python3
"""
HARDCASE - Limpeza de Residuos
Limpa QR codes, fotos, assets, cache, logs e arquivos temporarios

SEMPRE faz backup antes de deletar!
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def backup_completo():
    """Faz backup completo antes de qualquer limpeza"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'backups/cleanup_{timestamp}'
    os.makedirs(backup_dir, exist_ok=True)

    print("Fazendo backup completo...")

    # Backup banco
    if os.path.exists('tour_manager.db'):
        shutil.copy2('tour_manager.db', f'{backup_dir}/tour_manager.db')
        print(f"  BD: {backup_dir}/tour_manager.db")

    # Backup static + assets
    for pasta in ['static', 'assets']:
        if os.path.exists(pasta):
            shutil.copytree(pasta, f'{backup_dir}/{pasta}', dirs_exist_ok=True)
            print(f"  {pasta.title()}: {backup_dir}/{pasta}")

    return backup_dir

def analisar_residuos():
    """Analisa todos os residuos que podem ser limpos"""

    print("\nANALISANDO RESIDUOS...\n")

    residuos = {
        'qr_codes': [],
        'fotos': [],
        'assets': [],
        'cache': [],
        'logs': [],
        'temp': [],
        'db_backups': []
    }

    # 1. QR Codes em TODAS as pastas possiveis
    qr_paths = [
        'static/qrcodes',
        'static/qr_codes', 
        'static/uploads/qr',
        'assets/qrcodes',
        'assets/qr_codes',
        'qrcodes',
        'qr_codes'
    ]

    for path in qr_paths:
        if os.path.exists(path):
            qr_files = []
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f.lower().endswith(('.png', '.jpg', '.svg', '.jpeg')):
                        full_path = os.path.join(root, f)
                        try:
                            size = os.path.getsize(full_path)
                            qr_files.append({
                                'path': full_path,
                                'size': size,
                                'name': f
                            })
                        except (OSError, IOError):
                            pass

            if qr_files:
                residuos['qr_codes'].extend(qr_files)
                print(f"QR Codes em {path}: {len(qr_files)} arquivos")

    # 2. Fotos em uploads (exceto QR codes)
    uploads_path = 'static/uploads'
    if os.path.exists(uploads_path):
        for root, dirs, files in os.walk(uploads_path):
            for f in files:
                # Ignorar QR codes (ja contados acima)
                if 'qr' in f.lower():
                    continue

                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    full_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(full_path)
                        residuos['fotos'].append({
                            'path': full_path,
                            'size': size,
                            'name': f
                        })
                    except (OSError, IOError):
                        pass
        print(f"Fotos em uploads: {len(residuos['fotos'])} arquivos")

    # 3. ASSETS (imagens, css, js antigos)
    assets_path = 'assets'
    if os.path.exists(assets_path):
        asset_files = []
        for root, dirs, files in os.walk(assets_path):
            for f in files:
                # Ignorar QR codes (ja contados)
                if 'qr' in f.lower():
                    continue

                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                    ext = os.path.splitext(f)[1].lower()

                    asset_files.append({
                        'path': full_path,
                        'size': size,
                        'name': f,
                        'ext': ext
                    })
                except (OSError, IOError):
                    pass

        residuos['assets'] = asset_files
        print(f"Assets: {len(asset_files)} arquivos")

        # Estatisticas por tipo
        exts = {}
        for item in asset_files:
            ext = item['ext']
            exts[ext] = exts.get(ext, 0) + 1

        if exts:
            print("   Tipos:")
            for ext, count in sorted(exts.items(), key=lambda x: -x[1])[:5]:
                print(f"     - {ext}: {count}")

    # 4. Cache Python
    cache_dirs = []
    for root, dirs, files in os.walk('.'):
        # Ignorar backups
        if 'backup' in root.lower():
            continue

        if '__pycache__' in dirs:
            cache_path = os.path.join(root, '__pycache__')
            cache_dirs.append(cache_path)

            try:
                pyc_count = len([f for f in os.listdir(cache_path) if f.endswith('.pyc')])
                residuos['cache'].append({
                    'path': cache_path,
                    'count': pyc_count
                })
            except (OSError, IOError):
                pass

    if cache_dirs:
        print(f"Cache Python: {len(cache_dirs)} diretorios")

    # 5. Logs
    log_extensions = ['.log', '.txt']
    for ext in log_extensions:
        for f in Path('.').rglob(f'*{ext}'):
            if 'backup' in str(f).lower():
                continue

            if 'log' in str(f).lower() or 'error' in str(f).lower():
                try:
                    residuos['logs'].append({
                        'path': str(f),
                        'size': os.path.getsize(f),
                        'name': os.path.basename(str(f))
                    })
                except (OSError, IOError):
                    pass

    if residuos['logs']:
        print(f"Logs: {len(residuos['logs'])} arquivos")

    # 6. Arquivos temporarios
    temp_patterns = ['*.tmp', '*.temp', '*~', '.DS_Store', 'Thumbs.db']
    for pattern in temp_patterns:
        for f in Path('.').rglob(pattern):
            if 'backup' in str(f).lower():
                continue

            try:
                residuos['temp'].append({
                    'path': str(f),
                    'size': os.path.getsize(f),
                    'name': os.path.basename(str(f))
                })
            except (OSError, IOError):
                pass

    if residuos['temp']:
        print(f"Temp: {len(residuos['temp'])} arquivos")

    # 7. Backups antigos de banco (*.db.bak, *.db.old, *.db-*)
    for pattern in ['*.db.bak', '*.db.old', '*.db-*']:
        for f in Path('.').rglob(pattern):
            if os.path.basename(str(f)) != 'tour_manager.db':
                try:
                    residuos['db_backups'].append({
                        'path': str(f),
                        'size': os.path.getsize(f),
                        'name': os.path.basename(str(f))
                    })
                except (OSError, IOError):
                    pass

    if residuos['db_backups']:
        print(f"DB Backups antigos: {len(residuos['db_backups'])} arquivos")

    return residuos

def calcular_totais(residuos):
    """Calcula tamanho total por categoria"""
    totais = {}

    for categoria, items in residuos.items():
        if categoria == 'cache':
            totais[categoria] = {
                'count': sum(item['count'] for item in items),
                'size_mb': 0
            }
        else:
            total_size = sum(item.get('size', 0) for item in items)
            totais[categoria] = {
                'count': len(items),
                'size_mb': total_size / (1024 * 1024)
            }

    return totais

def mostrar_relatorio(residuos, totais):
    """Mostra relatorio detalhado dos residuos encontrados"""

    print("\n" + "="*60)
    print("RELATORIO DE RESIDUOS")
    print("="*60)

    total_geral_mb = 0
    total_geral_arquivos = 0

    categorias_ordem = ['qr_codes', 'fotos', 'assets', 'cache', 'logs', 'db_backups', 'temp']

    for categoria in categorias_ordem:
        if categoria not in totais:
            continue

        info = totais[categoria]
        count = info['count']
        size_mb = info.get('size_mb', 0)

        if count > 0:
            nome_categoria = categoria.upper().replace('_', ' ')
            print(f"\n{nome_categoria}:")
            print(f"  Arquivos: {count}")
            if size_mb > 0:
                print(f"  Tamanho: {size_mb:.2f} MB")
                total_geral_mb += size_mb
            total_geral_arquivos += count

            # Mostrar exemplos (primeiros 3)
            if categoria != 'cache':
                items = residuos[categoria][:3]
                for item in items:
                    name = item.get('name', os.path.basename(item['path']))
                    print(f"     - {name}")

                if len(residuos[categoria]) > 3:
                    resto = len(residuos[categoria]) - 3
                    print(f"     ... e mais {resto}")

    print("\n" + "-"*60)
    print(f"TOTAL: {total_geral_arquivos} arquivos - {total_geral_mb:.2f} MB")
    print("="*60)

def limpar_categoria(residuos, categoria):
    """Limpa uma categoria especifica de residuos"""

    items = residuos.get(categoria, [])

    if not items:
        print(f"Nada para limpar em {categoria}")
        return 0

    deletados = 0
    erros = 0

    if categoria == 'cache':
        # Deletar diretorios __pycache__
        for item in items:
            try:
                shutil.rmtree(item['path'])
                deletados += 1
            except (OSError, IOError) as e:
                print(f"Erro em {item['path']}: {e}")
                erros += 1

    elif categoria == 'assets':
        # Assets: deletar TODA a pasta (cuidado!)
        if os.path.exists('assets'):
            try:
                shutil.rmtree('assets')
                deletados = len(items)
                # Recriar vazia
                os.makedirs('assets', exist_ok=True)
                print("   Pasta assets/ recriada vazia")
            except (OSError, IOError) as e:
                print(f"Erro ao deletar assets/: {e}")
                erros += 1

    else:
        # Deletar arquivos individuais
        for item in items:
            try:
                os.remove(item['path'])
                deletados += 1
            except (OSError, IOError) as e:
                nome = item.get('name', item['path'])
                print(f"Erro em {nome}: {e}")
                erros += 1

    if erros > 0:
        print(f"   {erros} erro(s) durante limpeza")

    return deletados

def menu_limpeza(residuos, totais):
    """Menu interativo de limpeza"""

    while True:
        print("\n" + "="*40)
        print("   LIMPEZA DE RESIDUOS - MENU")
        print("="*40)
        print()
        print("1. Limpar QR Codes antigos")
        print("2. Limpar Fotos (uploads)")
        print("3. Limpar Assets (TODA pasta)")
        print("4. Limpar Cache Python")
        print("5. Limpar Logs")
        print("6. Limpar DB Backups antigos")
        print("7. Limpar Arquivos Temp")
        print()
        print("9. LIMPAR TUDO")
        print("0. Sair")
        print()

        opcao = input("Escolha: ")

        if opcao == '0':
            print("\nSaindo...")
            break

        elif opcao == '1':
            info = totais.get('qr_codes', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} QR codes ({info['size_mb']:.2f} MB)")
            confirm = input("Deletar? (s/N): ")
            if confirm.lower() == 's':
                count = limpar_categoria(residuos, 'qr_codes')
                print(f"OK - {count} QR codes deletados")

        elif opcao == '2':
            info = totais.get('fotos', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} fotos ({info['size_mb']:.2f} MB)")
            print("   ATENCAO: Isso vai deletar TODAS as fotos de equipamentos!")
            confirm = input("Deletar? (digite 'SIM DELETAR FOTOS'): ")
            if confirm == 'SIM DELETAR FOTOS':
                count = limpar_categoria(residuos, 'fotos')
                print(f"OK - {count} fotos deletadas")

        elif opcao == '3':
            info = totais.get('assets', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} arquivos em assets/ ({info['size_mb']:.2f} MB)")
            print("   ATENCAO: Isso vai deletar TODA a pasta assets/!")
            confirm = input("Deletar? (digite 'DELETAR ASSETS'): ")
            if confirm == 'DELETAR ASSETS':
                count = limpar_categoria(residuos, 'assets')
                print(f"OK - Pasta assets/ deletada ({count} arquivos)")

        elif opcao == '4':
            info = totais.get('cache', {'count': 0})
            print(f"\n{info['count']} arquivos de cache Python")
            confirm = input("Deletar? (s/N): ")
            if confirm.lower() == 's':
                count = limpar_categoria(residuos, 'cache')
                print(f"OK - {count} diretorios __pycache__ deletados")

        elif opcao == '5':
            info = totais.get('logs', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} logs ({info['size_mb']:.2f} MB)")
            confirm = input("Deletar? (s/N): ")
            if confirm.lower() == 's':
                count = limpar_categoria(residuos, 'logs')
                print(f"OK - {count} logs deletados")

        elif opcao == '6':
            info = totais.get('db_backups', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} DB backups antigos ({info['size_mb']:.2f} MB)")
            confirm = input("Deletar? (s/N): ")
            if confirm.lower() == 's':
                count = limpar_categoria(residuos, 'db_backups')
                print(f"OK - {count} backups deletados")

        elif opcao == '7':
            info = totais.get('temp', {'count': 0, 'size_mb': 0})
            print(f"\n{info['count']} arquivos temp ({info['size_mb']:.2f} MB)")
            confirm = input("Deletar? (s/N): ")
            if confirm.lower() == 's':
                count = limpar_categoria(residuos, 'temp')
                print(f"OK - {count} arquivos temp deletados")

        elif opcao == '9':
            print("\nLIMPAR TUDO")
            for cat, info in totais.items():
                if info['count'] > 0:
                    size_txt = f" ({info['size_mb']:.2f} MB)" if info.get('size_mb', 0) > 0 else ""
                    nome_cat = cat.replace('_', ' ')
                    print(f"   - {nome_cat}: {info['count']}{size_txt}")
            print()
            confirm = input("Digite 'DELETAR TUDO' para confirmar: ")

            if confirm == 'DELETAR TUDO':
                total = 0
                for categoria in residuos.keys():
                    if totais.get(categoria, {}).get('count', 0) > 0:
                        print(f"\n  Limpando {categoria}...")
                        count = limpar_categoria(residuos, categoria)
                        total += count
                        if count > 0:
                            print(f"     OK - {count} itens")

                print(f"\nTOTAL: {total} itens deletados!")
                break

        else:
            print("Opcao invalida")

def main():
    """Execucao principal do script"""

    print("="*40)
    print("  LIMPEZA DE RESIDUOS - HARDCASE")
    print("="*40 + "\n")

    # 1. Fazer backup
    backup_dir = backup_completo()
    print(f"\nBackup salvo em: {backup_dir}\n")

    # 2. Analisar residuos
    residuos = analisar_residuos()

    # 3. Calcular totais
    totais = calcular_totais(residuos)

    # 4. Mostrar relatorio
    mostrar_relatorio(residuos, totais)

    # 5. Menu interativo
    menu_limpeza(residuos, totais)

    print("\nLimpeza concluida!")
    print(f"Backup disponivel em: {backup_dir}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuario")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()