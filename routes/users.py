from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db, bcrypt
from models.user import User, TourAccess
from models.tour import Tour
from datetime import datetime
import secrets
import qrcode
import os

users_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required(f):
    """Decorator para rotas apenas admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@users_bp.route('/')
@login_required
@admin_required
def index():
    """Lista usuários da empresa"""
    users = User.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(User.name).all()
    
    return render_template('users/list.html', users=users)


@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Criar novo usuário"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'tech_responsible')
        
        if not email or not name or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('users.new'))
        
        if User.query.filter_by(email=email).first():
            flash('Este email já está em uso.', 'danger')
            return redirect(url_for('users.new'))
        
        if role not in ['admin', 'tech_responsible', 'tech_tour']:
            role = 'tech_responsible'
        
        user = User(
            email=email,
            name=name,
            phone=phone,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            role=role,
            company_id=current_user.company_id
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuário {name} criado com sucesso!', 'success')
        
        if role == 'tech_tour':
            flash('Para técnico tour, configure o acesso temporário.', 'info')
            return redirect(url_for('users.tour_access', user_id=user.id))
        
        return redirect(url_for('users.index'))
    
    return render_template('users/new.html')


@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Editar usuário"""
    user = User.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        user.name = request.form.get('name', user.name).strip()
        user.phone = request.form.get('phone', '').strip()
        user.role = request.form.get('role', user.role)
        
        new_password = request.form.get('password', '').strip()
        if new_password:
            user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        db.session.commit()
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/edit.html', user=user)


@users_bp.route('/<int:id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate(id):
    """Desativar usuário"""
    user = User.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if user.id == current_user.id:
        flash('Você não pode desativar a si mesmo.', 'danger')
        return redirect(url_for('users.index'))
    
    user.is_active = False
    db.session.commit()
    
    flash(f'Usuário {user.name} desativado.', 'warning')
    return redirect(url_for('users.index'))


@users_bp.route('/<int:user_id>/tour-access', methods=['GET', 'POST'])
@login_required
@admin_required
def tour_access(user_id):
    """Gerenciar acesso temporário para técnico tour"""
    user = User.query.filter_by(
        id=user_id,
        company_id=current_user.company_id,
        role='tech_tour'
    ).first_or_404()
    
    if request.method == 'POST':
        tour_id = request.form.get('tour_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not tour_id or not start_date or not end_date:
            flash('Preencha todos os campos.', 'danger')
            return redirect(url_for('users.tour_access', user_id=user_id))
        
        tour = Tour.query.get(tour_id)
        if not tour:
            flash('Tour não encontrada.', 'danger')
            return redirect(url_for('users.tour_access', user_id=user_id))
        
        access_code = secrets.token_urlsafe(32)
        
        access = TourAccess(
            user_id=user.id,
            tour_id=tour.id,
            tour_name=tour.name,
            access_code=access_code,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            created_by=current_user.id,
            company_id=current_user.company_id
        )
        
        qr = qrcode.make(access_code)
        qr_dir = 'static/qr/access'
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = f'{qr_dir}/{access_code[:16]}.png'
        qr.save(qr_path)
        access.qr_code_url = '/' + qr_path
        
        db.session.add(access)
        db.session.commit()
        
        flash(f'Acesso temporário criado para {user.name}!', 'success')
        return redirect(url_for('users.view_access', access_id=access.id))
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.start_date.desc()).all()
    
    accesses = TourAccess.query.filter_by(
        user_id=user.id,
        company_id=current_user.company_id
    ).order_by(TourAccess.created_at.desc()).all()
    
    return render_template('users/tour_access.html', 
                          user=user, 
                          tours=tours,
                          accesses=accesses)


@users_bp.route('/access/<int:access_id>')
@login_required
@admin_required
def view_access(access_id):
    """Ver QR Code de acesso"""
    access = TourAccess.query.filter_by(
        id=access_id,
        company_id=current_user.company_id
    ).first_or_404()
    
    user = User.query.get(access.user_id)
    
    return render_template('users/view_access.html', access=access, user=user)


@users_bp.route('/access/<int:access_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_access(access_id):
    """Revogar acesso temporário"""
    access = TourAccess.query.filter_by(
        id=access_id,
        company_id=current_user.company_id
    ).first_or_404()
    
    access.is_active = False
    access.revoked_at = datetime.utcnow()
    access.revoked_by = current_user.id
    
    db.session.commit()
    
    flash('Acesso revogado.', 'warning')
    return redirect(url_for('users.tour_access', user_id=access.user_id))
