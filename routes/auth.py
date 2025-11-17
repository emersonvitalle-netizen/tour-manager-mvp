from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from main import db, bcrypt
from models.company import Company
from models.user import User
from models.category import Category
from models.equipment_type import EquipmentType

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