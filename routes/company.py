from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models.company import Company
import os
import secrets

company_bp = Blueprint('company', __name__, url_prefix='/company')

ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_logo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


@company_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash('Apenas administradores podem acessar as configuracoes da empresa.', 'danger')
        return redirect(url_for('dashboard'))

    company = Company.query.get(current_user.company_id)

    if request.method == 'POST':
        # Dados basicos
        company.name = request.form.get('name')
        company.cnpj = request.form.get('cnpj', '').strip() or None
        company.inscricao_estadual = request.form.get('inscricao_estadual', '').strip() or None

        # Endereco
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
        flash('Configuracoes da empresa atualizadas com sucesso!', 'success')
        return redirect(url_for('company.settings'))

    return render_template('company/settings.html', company=company)


@company_bp.route('/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    """Gera ou regenera chave API para leitores RFID"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    company = Company.query.get(current_user.company_id)
    company.api_key = secrets.token_hex(32)  # 64 caracteres hex
    db.session.commit()

    return jsonify({
        'success': True,
        'api_key': company.api_key,
        'message': 'Chave API gerada com sucesso'
    })


@company_bp.route('/revoke-api-key', methods=['POST'])
@login_required
def revoke_api_key():
    """Revoga chave API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    company = Company.query.get(current_user.company_id)
    company.api_key = None
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Chave API revogada'
    })


# ============================================
# CONFIGURACOES ASAAS
# ============================================

@company_bp.route('/asaas/config', methods=['GET', 'POST'])
@login_required
def asaas_config():
    """Configurar integracao com Asaas"""
    if current_user.role != 'admin':
        flash('Apenas administradores podem configurar integracoes.', 'danger')
        return redirect(url_for('dashboard'))

    company = Company.query.get(current_user.company_id)

    if request.method == 'POST':
        # Salva configuracoes
        company.asaas_api_key = request.form.get('asaas_api_key', '').strip() or None
        company.asaas_sandbox = request.form.get('asaas_sandbox') == 'on'
        company.asaas_enabled = request.form.get('asaas_enabled') == 'on'

        # Gera token webhook se nao existir
        if company.asaas_enabled and not company.asaas_webhook_token:
            company.asaas_webhook_token = secrets.token_hex(32)

        db.session.commit()
        flash('Configuracoes Asaas salvas!', 'success')
        return redirect(url_for('company.settings'))

    return render_template('company/asaas_config.html', company=company)


@company_bp.route('/asaas/test', methods=['POST'])
@login_required
def asaas_test():
    """Testa conexao com API Asaas"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    company = Company.query.get(current_user.company_id)

    if not company.asaas_api_key:
        return jsonify({'success': False, 'error': 'API Key nao configurada'})

    try:
        from services.payment_adapter import AsaasProvider

        provider = AsaasProvider(
            api_key=company.asaas_api_key,
            sandbox=company.asaas_sandbox
        )

        # Testa listando clientes (endpoint simples)
        result = provider._make_request("GET", "customers?limit=1")

        if result.get("error"):
            return jsonify({
                'success': False,
                'error': result.get('message', 'Erro na API'),
                'sandbox': company.asaas_sandbox
            })

        return jsonify({
            'success': True,
            'message': 'Conexao OK!',
            'sandbox': company.asaas_sandbox,
            'ambiente': 'Sandbox (Teste)' if company.asaas_sandbox else 'Producao'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@company_bp.route('/asaas/generate-webhook-token', methods=['POST'])
@login_required
def generate_webhook_token():
    """Gera novo token para validacao de webhooks"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    company = Company.query.get(current_user.company_id)
    company.asaas_webhook_token = secrets.token_hex(32)
    db.session.commit()

    return jsonify({
        'success': True,
        'token': company.asaas_webhook_token,
        'message': 'Token regenerado'
    })


# ============================================
# CONFIGURACOES IA (Groq / Gemini)
# ============================================

@company_bp.route('/ai/config', methods=['POST'])
@login_required
def ai_config():
    """Configurar integracao com IA (Groq / Gemini)"""
    if current_user.role != 'admin':
        flash('Apenas administradores podem configurar integracoes.', 'danger')
        return redirect(url_for('dashboard'))

    company = Company.query.get(current_user.company_id)

    # Salva configuracoes
    company.ai_provider = request.form.get('ai_provider', 'groq').strip()
    company.groq_api_key = request.form.get('groq_api_key', '').strip() or None
    company.gemini_api_key = request.form.get('gemini_api_key', '').strip() or None
    company.google_cse_cx = request.form.get('google_cse_cx', '').strip() or None
    company.ai_enabled = request.form.get('ai_enabled') == 'on'

    db.session.commit()
    flash('Configuracoes de IA salvas!', 'success')
    return redirect(url_for('company.settings'))


@company_bp.route('/ai/test', methods=['POST'])
@login_required
def ai_test():
    """Testa conexao com provedor de IA"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

    company = Company.query.get(current_user.company_id)

    provider = company.ai_provider or 'groq'
    api_key = company.ai_api_key

    if not api_key:
        return jsonify({'success': False, 'error': f'API Key do {provider.upper()} nao configurada'})

    try:
        from services.ai_vision_service import test_ai_connection
        result = test_ai_connection(provider=provider, api_key=api_key)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })