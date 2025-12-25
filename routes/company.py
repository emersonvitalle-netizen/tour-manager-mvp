from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models.company import Company
import os

company_bp = Blueprint('company', __name__, url_prefix='/company')

ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_logo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS

@company_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash('Apenas administradores podem acessar as configurações da empresa.', 'danger')
        return redirect(url_for('dashboard'))

    company = Company.query.get(current_user.company_id)

    if request.method == 'POST':
        # Dados básicos
        company.name = request.form.get('name')
        company.cnpj = request.form.get('cnpj', '').strip() or None
        company.inscricao_estadual = request.form.get('inscricao_estadual', '').strip() or None
        
        # Endereço
        company.street = request.form.get('street', '').strip() or None
        company.number = request.form.get('number', '').strip() or None
        company.complement = request.form.get('complement', '').strip() or None
        company.neighborhood = request.form.get('neighborhood', '').strip() or None
        company.city = request.form.get('city', '').strip() or None
        company.state = request.form.get('state', '').strip() or None
        company.zipcode = request.form.get('zipcode', '').strip() or None
        
        # Contato
        company.phone = request.form.get('phone', '').strip() or None
        company.cellphone = request.form.get('cellphone', '').strip() or None
        company.email = request.form.get('email', '').strip() or None
        company.website = request.form.get('website', '').strip() or None

        # Upload do logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename != '' and allowed_logo(file.filename):
                filename = secure_filename(f"logo_company_{company.id}_{file.filename}")
                filepath = os.path.join('static', 'uploads', 'logos', filename)

                os.makedirs('static/uploads/logos', exist_ok=True)

                file.save(filepath)
                company.logo_url = f"/static/uploads/logos/{filename}"

        db.session.commit()
        flash('Configurações da empresa atualizadas com sucesso!', 'success')
        return redirect(url_for('company.settings'))

    return render_template('company/settings.html', company=company)
