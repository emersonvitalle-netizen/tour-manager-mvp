"""Decoradores de permissão para controle de acesso"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Apenas admin pode acessar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_or_tech_required(f):
    """Admin ou Técnico Responsável podem acessar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ['admin', 'tech_responsible']:
            flash('Acesso restrito.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def can_view_prices(f):
    """Injeta variável para templates verificarem se pode ver preços"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def hide_prices_for_non_admin():
    """Helper para templates verificarem se deve ocultar preços"""
    if not current_user.is_authenticated:
        return True
    return current_user.role != 'admin'
