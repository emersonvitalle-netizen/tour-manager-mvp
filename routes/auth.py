from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, current_user
from extensions import db, bcrypt
from models.company import Company
from models.user import User, TechnicianAccess, TourAccess
from models.category import Category
from models.equipment_type import EquipmentType
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

DEFAULT_CATEGORIES = {
    'Som': ['Caixa Ativa', 'Caixa Passiva', 'Microfone', 'Mesa de Som', 'Amplificador'],
    'Luz': ['Moving Head', 'PAR LED', 'Fresnel', 'Elipsoidal', 'Strobo'],
    'Materiais': ['Cabo XLR', 'Cabo P10', 'Praticável', 'DI Box', 'Pedestal'],
    'Instrumentos': ['Guitarra', 'Baixo', 'Bateria', 'Teclado', 'Violão']
}

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'danger')
            return redirect(url_for('auth.register'))

        company = Company(name=f'Empresa de {name}')
        db.session.add(company)
        db.session.flush()

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            role='admin',
            company_id=company.id
        )
        db.session.add(user)

        for cat_name, type_list in DEFAULT_CATEGORIES.items():
            category = Category(
                name=cat_name,
                company_id=company.id,
                is_system=True
            )
            db.session.add(category)
            db.session.flush()

            for type_name in type_list:
                eq_type = EquipmentType(
                    name=type_name,
                    category_id=category.id,
                    company_id=company.id,
                    is_system=True
                )
                db.session.add(eq_type)

        db.session.commit()

        login_user(user, remember=True)
        flash('Conta criada com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Conta desativada.', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user, remember=True)
            flash('Login realizado com sucesso!', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha incorretos.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/invite/<token>')
def invite(token):
    """Página de onboarding quando técnico/tour escaneia QR de convite"""
    tech_access = TechnicianAccess.query.filter_by(access_token=token).first()
    if tech_access:
        if tech_access.status == 'active':
            flash('Este convite já foi utilizado. Faça login normalmente.', 'info')
            return redirect(url_for('auth.login'))
        if tech_access.status == 'revoked':
            return render_template('auth/invite_expired.html', reason='revoked')
        if tech_access.is_expired:
            return render_template('auth/invite_expired.html', reason='expired')
        return render_template('auth/invite_technician.html', access=tech_access, token=token)
    
    tour_access = TourAccess.query.filter_by(access_token=token).first()
    if tour_access:
        if tour_access.status == 'active':
            flash('Este convite já foi utilizado. Faça login normalmente.', 'info')
            return redirect(url_for('auth.login'))
        if tour_access.status == 'revoked':
            return render_template('auth/invite_expired.html', reason='revoked')
        if tour_access.is_expired:
            return render_template('auth/invite_expired.html', reason='expired')
        return render_template('auth/invite_tour.html', access=tour_access, token=token)
    
    return render_template('auth/invite_expired.html', reason='not_found')


@auth_bp.route('/invite/<token>/complete', methods=['POST'])
def complete_invite(token):
    """Finaliza o cadastro do técnico/tour após preencher dados"""
    name = request.form.get('name')
    phone = request.form.get('phone')
    pin = request.form.get('pin')
    
    tech_access = TechnicianAccess.query.filter_by(access_token=token).first()
    if tech_access and tech_access.is_pending:
        user = User(
            name=name,
            phone=phone,
            role='tech_responsible',
            company_id=tech_access.company_id,
            pending_setup=False
        )
        if pin:
            user.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')
        
        db.session.add(user)
        db.session.flush()
        
        tech_access.user_id = user.id
        tech_access.status = 'active'
        tech_access.activated_at = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        flash('Cadastro realizado com sucesso! Bem-vindo!', 'success')
        return redirect(url_for('dashboard'))
    
    tour_access = TourAccess.query.filter_by(access_token=token).first()
    if tour_access and tour_access.is_pending:
        user = User(
            name=name,
            phone=phone,
            role='tech_tour',
            company_id=tour_access.company_id,
            pending_setup=False
        )
        if pin:
            user.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')
        
        db.session.add(user)
        db.session.flush()
        
        tour_access.user_id = user.id
        tour_access.status = 'active'
        tour_access.activated_at = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        flash('Cadastro realizado com sucesso! Bem-vindo!', 'success')
        return redirect(url_for('dashboard'))
    
    flash('Convite inválido ou já utilizado.', 'danger')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login/qr', methods=['POST'])
def login_qr():
    """Login via QR Code (para técnico e tour já cadastrados)"""
    token = request.json.get('token') if request.is_json else request.form.get('token')
    
    if not token:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Token não informado'}), 400
        flash('QR Code inválido.', 'danger')
        return redirect(url_for('auth.login'))
    
    tech_access = TechnicianAccess.query.filter_by(access_token=token).first()
    if tech_access:
        if tech_access.is_pending:
            if request.is_json:
                return jsonify({
                    'success': False, 
                    'redirect': url_for('auth.invite', token=token),
                    'message': 'Complete seu cadastro primeiro'
                })
            return redirect(url_for('auth.invite', token=token))
        
        if not tech_access.is_valid:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Acesso expirado ou revogado'}), 403
            flash('Acesso expirado ou revogado.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = tech_access.user
        if user and user.is_active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            return redirect(url_for('dashboard'))
    
    tour_access = TourAccess.query.filter_by(access_token=token).first()
    if tour_access:
        if tour_access.is_pending:
            if request.is_json:
                return jsonify({
                    'success': False, 
                    'redirect': url_for('auth.invite', token=token),
                    'message': 'Complete seu cadastro primeiro'
                })
            return redirect(url_for('auth.invite', token=token))
        
        if not tour_access.is_valid:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Acesso expirado ou revogado'}), 403
            flash('Acesso expirado ou a tour foi finalizada.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = tour_access.user
        if user and user.is_active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            return redirect(url_for('dashboard'))
    
    if request.is_json:
        return jsonify({'success': False, 'error': 'QR Code não reconhecido'}), 404
    flash('QR Code não reconhecido.', 'danger')
    return redirect(url_for('auth.login'))