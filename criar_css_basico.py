#!/usr/bin/env python3
"""
Cria estrutura CSS básica para voltar ao funcionamento
"""

import os

print("📂 Criando estrutura CSS...")

# Criar pasta
os.makedirs('static/css', exist_ok=True)
print("✅ Pasta static/css/ criada")

# Criar CSS básico
css_content = """/* DARK THEME - Básico Funcional */

:root {
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    --bottom-nav-height: 70px;
}

body {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.alert {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
}

.alert-success { background: #d4edda; color: #155724; }
.alert-danger { background: #f8d7da; color: #721c24; }
.alert-warning { background: #fff3cd; color: #856404; }

.alert-close {
    background: none;
    border: none;
    cursor: pointer;
    float: right;
}

.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 70px;
    background: #fff;
    border-top: 1px solid #ddd;
    display: flex;
    justify-content: space-around;
    z-index: 1000;
}

.bottom-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: #666;
    flex: 1;
}

.bottom-nav-item.active {
    color: #007bff;
}

.bottom-nav-icon {
    font-size: 24px;
    margin-bottom: 4px;
}

.fab {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 56px;
    height: 56px;
    background: #007bff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    text-decoration: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 999;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 16px;
}
"""

with open('static/css/dark-theme.css', 'w') as f:
    f.write(css_content)

print("✅ dark-theme.css criado")
print("\n🚀 Pronto! Reinicie o Replit!")