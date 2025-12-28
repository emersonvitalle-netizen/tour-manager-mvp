"""Decoradores de permissão para controle de acesso"""
from functools import wraps
from flask import flash, redirect, url_for, g
from flask_login import current_user


def get_user_permissions():
    """Retorna as permissões do usuário atual baseado no role e TechnicianAccess"""
    if not current_user.is_authenticated:
        return {
            'can_equipment': False,
            'can_maintenance': False,
            'can_separation': False,
            'can_tours': False,
            'can_scanner': False,
            'can_financial': False,
            'can_users': False,
            'can_view_prices': False
        }
    
    if current_user.role == 'admin':
        return {
            'can_equipment': True,
            'can_maintenance': True,
            'can_separation': True,
            'can_tours': True,
            'can_scanner': True,
            'can_financial': True,
            'can_users': True,
            'can_view_prices': True
        }
    
    if current_user.role == 'tech_responsible':
        from models.user import TechnicianAccess
        tech_access = TechnicianAccess.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).first()
        
        if tech_access and tech_access.is_valid:
            return {
                'can_equipment': tech_access.can_equipment,
                'can_maintenance': tech_access.can_maintenance,
                'can_separation': tech_access.can_separation,
                'can_tours': tech_access.can_tours,
                'can_scanner': tech_access.can_scanner,
                'can_financial': False,
                'can_users': False,
                'can_view_prices': False
            }
        return {
            'can_equipment': True,
            'can_maintenance': True,
            'can_separation': True,
            'can_tours': True,
            'can_scanner': True,
            'can_financial': False,
            'can_users': False,
            'can_view_prices': False
        }
    
    if current_user.role == 'tech_tour':
        return {
            'can_equipment': False,
            'can_maintenance': False,
            'can_separation': False,
            'can_tours': True,
            'can_scanner': True,
            'can_financial': False,
            'can_users': False,
            'can_view_prices': False
        }
    
    return {
        'can_equipment': False,
        'can_maintenance': False,
        'can_separation': False,
        'can_tours': False,
        'can_scanner': False,
        'can_financial': False,
        'can_users': False,
        'can_view_prices': False
    }


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


def permission_required(permission_name):
    """Decorator genérico para verificar permissão específica"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            permissions = get_user_permissions()
            if not permissions.get(permission_name, False):
                flash('Voce nao tem permissao para acessar esta funcionalidade.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


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


def inject_permissions():
    """Context processor para injetar permissões em todos os templates"""
    if current_user.is_authenticated:
        return {'user_permissions': get_user_permissions()}
    return {'user_permissions': get_user_permissions()}
