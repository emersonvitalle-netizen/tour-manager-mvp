from flask import Flask, render_template, redirect, url_for
from flask_login import current_user
from config import Config
from extensions import db, login_manager, bcrypt, migrate
import os


def create_models():
    """Importa todos os models na ordem correta - ORDEM BASEADA EM DEPENDENCIAS"""

    # NIVEL 1 - Base (sem dependencias externas)
    from models.company import Company
    from models.category import Category

    # NIVEL 2 - Dependem so de Nivel 1
    from models.user import User, TourAccess
    from models.equipment_type import EquipmentType
    from models.material_stock import MaterialStock, MaterialMovement

    # NIVEL 3 - Dependem de Nivel 1 e 2
    from models.equipment_model import EquipmentModel

    # NIVEL 4 - Dependem de niveis anteriores
    from models.equipment import Equipment
    from models.tour import Tour, Show, TourRequirement, TourEquipment, EquipmentCheckpoint, EquipmentTransfer, EquipmentReplacement
    from models.commercial import Lead, LeadInteraction, LeadReactivation
    from models.rh import (Employee, Freelancer, FreelancerAssignment, FreelancerReview, PayrollEntry,
                           AccountPayable, FreelancerPayment, BankAccount, CostCenter, AccountReceivable,
                           Supplier, Client, Vehicle, Consumable, ContractTemplate, CashRegister, CashEntry)

    # NIVEL 5 - Dependem de Equipment/Tour
    from models.maintenance import Maintenance
    from models.kit import Kit, KitRequirement
    from models.separation_list import SeparationList, SeparationListItem
    from models.work_list import WorkList, WorkListItem
    from models.financial import Quote, QuoteItem, Contract, Invoice, Payment

    # NIVEL 6 - Dependem de Quote/Invoice/Payment
    from models.financial_expanded import FinancialProvision, PaymentStrategy, CashFlowProjection, TaxCalculation, FinancialAlert

    # NIVEL 7 - Fabricacao
    from models.fabrication import FabricationTemplate, FabricationRecord


def ensure_columns():
    """
    Rede de seguranca: garante que TODAS as colunas dos models existem no banco.
    Roda SEMPRE na inicializacao, antes de qualquer query.
    Se a coluna ja existe, ignora silenciosamente.

    FLUXO DE DESENVOLVIMENTO:
    ─────────────────────────
    1. Adiciona campo no model (.py)
    2. Adiciona ALTER TABLE aqui (seguranca imediata)
    3. Gera migracao Alembic:  flask db migrate -m "descricao"
    4. Commita migrations/ no Git

    FLUXO DE DEPLOY/TESTES:
    ───────────────────────
    1. Git pull (traz migrations/ atualizadas)
    2. App inicia → ensure_columns() corrige qualquer gap
    3. flask db upgrade aplica migracoes formais
    4. Sistema funciona sem erros
    """
    from sqlalchemy import text

    migrations = [
        # ============================================
        # COMPANY
        # ============================================
        'ALTER TABLE company ADD COLUMN logo_url VARCHAR(500)',
        'ALTER TABLE company ADD COLUMN email VARCHAR(120)',
        'ALTER TABLE company ADD COLUMN phone VARCHAR(20)',
        'ALTER TABLE company ADD COLUMN address TEXT',
        'ALTER TABLE company ADD COLUMN cellphone VARCHAR(20)',
        'ALTER TABLE company ADD COLUMN website VARCHAR(200)',
        'ALTER TABLE company ADD COLUMN inscricao_estadual VARCHAR(20)',
        'ALTER TABLE company ADD COLUMN street VARCHAR(200)',
        'ALTER TABLE company ADD COLUMN number VARCHAR(20)',
        'ALTER TABLE company ADD COLUMN complement VARCHAR(100)',
        'ALTER TABLE company ADD COLUMN neighborhood VARCHAR(100)',
        'ALTER TABLE company ADD COLUMN city VARCHAR(100)',
        'ALTER TABLE company ADD COLUMN state VARCHAR(2)',
        'ALTER TABLE company ADD COLUMN zipcode VARCHAR(10)',
        'ALTER TABLE company ADD COLUMN api_key VARCHAR(64)',
        'ALTER TABLE company ADD COLUMN asaas_api_key VARCHAR(200)',
        'ALTER TABLE company ADD COLUMN asaas_sandbox BOOLEAN DEFAULT 1',
        'ALTER TABLE company ADD COLUMN asaas_webhook_token VARCHAR(64)',
        'ALTER TABLE company ADD COLUMN asaas_enabled BOOLEAN DEFAULT 0',

        # ============================================
        # EQUIPMENT
        # ============================================
        'ALTER TABLE equipment ADD COLUMN qr_code_url VARCHAR(500)',
        'ALTER TABLE equipment ADD COLUMN type_id INTEGER',
        'ALTER TABLE equipment ADD COLUMN nfc_tag_id VARCHAR(64)',
        'ALTER TABLE equipment ADD COLUMN rfid_uhf_tag VARCHAR(128)',
        'ALTER TABLE equipment ADD COLUMN tag_associated_at DATETIME',
        'ALTER TABLE equipment ADD COLUMN tag_associated_by INTEGER',

        # ============================================
        # MAINTENANCE
        # ============================================
        'ALTER TABLE maintenance ADD COLUMN created_at DATETIME',

        # ============================================
        # SEPARATION LIST
        # ============================================
        'ALTER TABLE separation_list ADD COLUMN client_name VARCHAR(200)',
        'ALTER TABLE separation_list ADD COLUMN client_phone VARCHAR(20)',
        'ALTER TABLE separation_list ADD COLUMN client_email VARCHAR(120)',
        'ALTER TABLE separation_list ADD COLUMN client_address TEXT',
        'ALTER TABLE separation_list ADD COLUMN event_name VARCHAR(200)',
        'ALTER TABLE separation_list ADD COLUMN event_date DATE',
        'ALTER TABLE separation_list ADD COLUMN event_time VARCHAR(10)',
        'ALTER TABLE separation_list ADD COLUMN event_location TEXT',
        'ALTER TABLE separation_list ADD COLUMN validity_date DATE',
        'ALTER TABLE separation_list ADD COLUMN observations TEXT',
        'ALTER TABLE separation_list ADD COLUMN discount_percent DECIMAL(5,2)',
        'ALTER TABLE separation_list ADD COLUMN discount_value DECIMAL(10,2)',
        'ALTER TABLE separation_list_item ADD COLUMN item_description VARCHAR(500)',

        # ============================================
        # QUOTE
        # ============================================
        'ALTER TABLE quote ADD COLUMN client_id INTEGER',

        # ============================================
        # ACCOUNT PAYABLE
        # ============================================
        'ALTER TABLE account_payable ADD COLUMN custom_category VARCHAR(100)',
        'ALTER TABLE account_payable ADD COLUMN payment_method VARCHAR(50)',
        'ALTER TABLE account_payable ADD COLUMN installment_number INTEGER',
        'ALTER TABLE account_payable ADD COLUMN total_installments INTEGER',
        'ALTER TABLE account_payable ADD COLUMN bank_account_id INTEGER',
        'ALTER TABLE account_payable ADD COLUMN cost_center_id INTEGER',
        'ALTER TABLE account_payable ADD COLUMN receipt_url VARCHAR(500)',
        'ALTER TABLE account_payable ADD COLUMN origin_type VARCHAR(50)',
        'ALTER TABLE account_payable ADD COLUMN origin_id INTEGER',

        # ============================================
        # ACCOUNT RECEIVABLE
        # ============================================
        'ALTER TABLE account_receivable ADD COLUMN category VARCHAR(50)',
        'ALTER TABLE account_receivable ADD COLUMN client_id INTEGER',
        'ALTER TABLE account_receivable ADD COLUMN received_amount DECIMAL(10,2)',
        'ALTER TABLE account_receivable ADD COLUMN received_at DATETIME',
        'ALTER TABLE account_receivable ADD COLUMN payment_method VARCHAR(50)',
        'ALTER TABLE account_receivable ADD COLUMN bank_account_id INTEGER',
        'ALTER TABLE account_receivable ADD COLUMN origin_type VARCHAR(50)',
        'ALTER TABLE account_receivable ADD COLUMN origin_id INTEGER',
        'ALTER TABLE account_receivable ADD COLUMN notes TEXT',
        'ALTER TABLE account_receivable ADD COLUMN created_by INTEGER',
        'ALTER TABLE account_receivable ADD COLUMN asaas_payment_id VARCHAR(100)',
        'ALTER TABLE account_receivable ADD COLUMN asaas_invoice_url VARCHAR(500)',
        'ALTER TABLE account_receivable ADD COLUMN asaas_pix_qrcode TEXT',
        'ALTER TABLE account_receivable ADD COLUMN asaas_pix_payload TEXT',
        'ALTER TABLE account_receivable ADD COLUMN asaas_boleto_url VARCHAR(500)',

        # ============================================
        # CLIENT
        # ============================================
        'ALTER TABLE client ADD COLUMN cnpj_cpf VARCHAR(18)',
        'ALTER TABLE client ADD COLUMN email VARCHAR(120)',
        'ALTER TABLE client ADD COLUMN phone VARCHAR(20)',
        'ALTER TABLE client ADD COLUMN address TEXT',
        'ALTER TABLE client ADD COLUMN contact_name VARCHAR(100)',
        'ALTER TABLE client ADD COLUMN contact_phone VARCHAR(20)',
        'ALTER TABLE client ADD COLUMN asaas_customer_id VARCHAR(100)',
        'ALTER TABLE client ADD COLUMN notes TEXT',
        'ALTER TABLE client ADD COLUMN is_active BOOLEAN DEFAULT 1',
        'ALTER TABLE client ADD COLUMN created_at DATETIME',

        # ============================================
        # SUPPLIER
        # ============================================
        'ALTER TABLE supplier ADD COLUMN cnpj_cpf VARCHAR(18)',
        'ALTER TABLE supplier ADD COLUMN email VARCHAR(120)',
        'ALTER TABLE supplier ADD COLUMN phone VARCHAR(20)',
        'ALTER TABLE supplier ADD COLUMN address TEXT',
        'ALTER TABLE supplier ADD COLUMN category VARCHAR(50)',
        'ALTER TABLE supplier ADD COLUMN contact_name VARCHAR(100)',
        'ALTER TABLE supplier ADD COLUMN contact_phone VARCHAR(20)',
        'ALTER TABLE supplier ADD COLUMN notes TEXT',
        'ALTER TABLE supplier ADD COLUMN is_active BOOLEAN DEFAULT 1',
        'ALTER TABLE supplier ADD COLUMN created_at DATETIME',

        # ============================================
        # BANK ACCOUNT
        # ============================================
        'ALTER TABLE bank_account ADD COLUMN bank_name VARCHAR(100)',
        'ALTER TABLE bank_account ADD COLUMN bank_code VARCHAR(10)',
        'ALTER TABLE bank_account ADD COLUMN agency VARCHAR(20)',
        'ALTER TABLE bank_account ADD COLUMN account_number VARCHAR(30)',
        'ALTER TABLE bank_account ADD COLUMN account_type VARCHAR(20)',
        'ALTER TABLE bank_account ADD COLUMN initial_balance DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE bank_account ADD COLUMN current_balance DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE bank_account ADD COLUMN is_active BOOLEAN DEFAULT 1',
        'ALTER TABLE bank_account ADD COLUMN is_default BOOLEAN DEFAULT 0',
        'ALTER TABLE bank_account ADD COLUMN created_at DATETIME',

        # ============================================
        # VEHICLE
        # ============================================
        'ALTER TABLE vehicle ADD COLUMN plate VARCHAR(10)',
        'ALTER TABLE vehicle ADD COLUMN brand VARCHAR(50)',
        'ALTER TABLE vehicle ADD COLUMN model VARCHAR(100)',
        'ALTER TABLE vehicle ADD COLUMN year INTEGER',
        'ALTER TABLE vehicle ADD COLUMN color VARCHAR(30)',
        'ALTER TABLE vehicle ADD COLUMN vehicle_type VARCHAR(30)',
        'ALTER TABLE vehicle ADD COLUMN fuel_type VARCHAR(20)',
        'ALTER TABLE vehicle ADD COLUMN capacity VARCHAR(50)',
        'ALTER TABLE vehicle ADD COLUMN status VARCHAR(20)',
        'ALTER TABLE vehicle ADD COLUMN notes TEXT',

        # ============================================
        # CONSUMABLE
        # ============================================
        'ALTER TABLE consumable ADD COLUMN category VARCHAR(50)',
        'ALTER TABLE consumable ADD COLUMN unit VARCHAR(20)',
        'ALTER TABLE consumable ADD COLUMN quantity DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE consumable ADD COLUMN min_quantity DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE consumable ADD COLUMN unit_cost DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE consumable ADD COLUMN supplier_id INTEGER',

        # ============================================
        # CONTRACT TEMPLATE
        # ============================================
        'ALTER TABLE contract_template ADD COLUMN contract_type VARCHAR(50)',
        'ALTER TABLE contract_template ADD COLUMN content TEXT',
        'ALTER TABLE contract_template ADD COLUMN is_active BOOLEAN DEFAULT 1',
        'ALTER TABLE contract_template ADD COLUMN created_at DATETIME',

        # ============================================
        # CASH REGISTER
        # ============================================
        'ALTER TABLE cash_register ADD COLUMN current_balance DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE cash_register ADD COLUMN is_open BOOLEAN DEFAULT 0',
        'ALTER TABLE cash_register ADD COLUMN opened_at DATETIME',
        'ALTER TABLE cash_register ADD COLUMN opened_by INTEGER',
        'ALTER TABLE cash_register ADD COLUMN opening_balance DECIMAL(10,2) DEFAULT 0',
        'ALTER TABLE cash_register ADD COLUMN created_at DATETIME',

        # ============================================
        # CASH ENTRY
        # ============================================
        'ALTER TABLE cash_entry ADD COLUMN entry_type VARCHAR(20)',
        'ALTER TABLE cash_entry ADD COLUMN description VARCHAR(200)',
        'ALTER TABLE cash_entry ADD COLUMN category VARCHAR(50)',
        'ALTER TABLE cash_entry ADD COLUMN reference_type VARCHAR(50)',
        'ALTER TABLE cash_entry ADD COLUMN reference_id INTEGER',

        # ============================================
        # COST CENTER
        # ============================================
        'ALTER TABLE cost_center ADD COLUMN code VARCHAR(20)',
        'ALTER TABLE cost_center ADD COLUMN description TEXT',
        'ALTER TABLE cost_center ADD COLUMN is_active BOOLEAN DEFAULT 1',
        'ALTER TABLE cost_center ADD COLUMN created_at DATETIME',

        # ============================================
        # INVOICE - NFSe
        # ============================================
        'ALTER TABLE invoice ADD COLUMN nfse_id VARCHAR(100)',
        'ALTER TABLE invoice ADD COLUMN nfse_number VARCHAR(50)',
        'ALTER TABLE invoice ADD COLUMN nfse_status VARCHAR(30)',
        'ALTER TABLE invoice ADD COLUMN nfse_url VARCHAR(500)',
        'ALTER TABLE invoice ADD COLUMN nfse_xml_url VARCHAR(500)',

        # ============================================
        # PAYMENT - Asaas
        # ============================================
        'ALTER TABLE payment ADD COLUMN external_id VARCHAR(100)',
        'ALTER TABLE payment ADD COLUMN provider VARCHAR(30)',
        'ALTER TABLE payment ADD COLUMN provider_data TEXT',
    ]

    added = 0
    for m in migrations:
        try:
            db.session.execute(text(m))
            db.session.commit()
            added += 1
        except Exception:
            db.session.rollback()

    if added > 0:
        print(f'[ensure_columns] {added} colunas adicionadas')


def apply_migrations():
    """
    Aplica migracoes Alembic pendentes.
    NAO gera migracoes novas - apenas aplica as que ja existem em migrations/.

    Para gerar novas migracoes (somente em DEV):
        flask db migrate -m "descricao da mudanca"
        flask db upgrade
        git add migrations/
        git commit -m "nova migracao"
    """
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')

    if not os.path.exists(migrations_dir):
        # Primeira execucao: inicializa e marca estado atual
        try:
            from flask_migrate import init, stamp
            print('[Alembic] Inicializando migrations/...')
            init()
            stamp(revision='head')
            print('[Alembic] Inicializado e marcado como HEAD')
        except Exception as e:
            print(f'[Alembic] Init: {e}')
        return

    try:
        from flask_migrate import upgrade
        upgrade()
        print('[Alembic] Migracoes aplicadas')
    except Exception as e:
        print(f'[Alembic] Upgrade: {e}')


def regenerate_all_qr_codes():
    """Regenera QR Codes de todos os equipamentos"""
    from models.equipment import Equipment

    try:
        equipments = Equipment.query.all()

        if not equipments:
            return

        print(f'Regenerando {len(equipments)} QR Codes...')

        for eq in equipments:
            try:
                eq.generate_qr_code()
            except Exception as e:
                print(f'Erro em {eq.code}: {e}')

        db.session.commit()
        print('QR Codes regenerados!')

    except Exception as e:
        db.session.rollback()
        print(f'Erro ao regenerar QR Codes: {e}')


def register_event_listeners():
    """Registra listeners do EventBus"""
    try:
        from services.event_bus import EventBus
        import services.listeners

        listeners = EventBus.get_listeners()
        total = sum(len(v) for v in listeners.values())
        print(f'[EventBus] {total} listeners em {len(listeners)} eventos')
    except ImportError as e:
        print(f'[EventBus] Nao disponivel: {e}')
    except Exception as e:
        print(f'[EventBus] Erro: {e}')


# ============================================
# APP
# ============================================

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)
migrate.init_app(app, db)  # Flask-Migrate / Alembic

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faca login para acessar.'

from utils.permissions import inject_permissions
app.context_processor(inject_permissions)

os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/uploads/logos', exist_ok=True)
os.makedirs('static/qr/access', exist_ok=True)
os.makedirs('static/qr', exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))


# Registrar blueprints
from routes.auth import auth_bp
from routes.equipment import equipment_bp
from routes.kit import kit_bp
from routes.company import company_bp
from routes.tour import tour_bp
from routes.separation import separation_bp
from routes.work_list import work_list_bp
from routes.users import users_bp
from routes.financial import financial_bp
from routes.orcamento import orcamento_bp
from routes.scanner import scanner_bp
from routes.api_rfid import api_rfid_bp
from routes.leads import leads_bp
from routes.rh import rh_bp
from routes.maintenance import maintenance_bp
from routes.automation_api import automation_api
from routes.relatorios import relatorios_bp

app.register_blueprint(auth_bp)
app.register_blueprint(equipment_bp)
app.register_blueprint(kit_bp)
app.register_blueprint(company_bp)
app.register_blueprint(tour_bp)
app.register_blueprint(separation_bp)
app.register_blueprint(work_list_bp)
app.register_blueprint(users_bp)
app.register_blueprint(financial_bp)
app.register_blueprint(orcamento_bp)
app.register_blueprint(scanner_bp)
app.register_blueprint(api_rfid_bp)
app.register_blueprint(leads_bp)
app.register_blueprint(rh_bp)
app.register_blueprint(maintenance_bp)
app.register_blueprint(automation_api)
app.register_blueprint(relatorios_bp)


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))


@app.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    alert_count = 0
    try:
        from models.financial_expanded import FinancialAlert
        alert_count = FinancialAlert.query.filter_by(
            company_id=current_user.company_id,
            status='active'
        ).count()
    except:
        pass

    url_map = {rule.endpoint for rule in app.url_map.iter_rules()}

    return render_template('dashboard.html',
                          alert_count=alert_count,
                          url_map=url_map)


@app.route('/docs/project')
def project_docs():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return render_template('docs/project_overview.html')


# ============================================
# INICIALIZACAO
# ============================================

with app.app_context():
    create_models()
    db.create_all()

    # 1. Rede de seguranca: garante colunas ANTES de qualquer query
    ensure_columns()

    # 2. Alembic: aplica migracoes formais (so upgrade, nunca gera)
    apply_migrations()

    regenerate_all_qr_codes()
    register_event_listeners()
    print("Sistema pronto!")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)