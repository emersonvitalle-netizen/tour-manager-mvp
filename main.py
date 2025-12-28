from flask import Flask, render_template, redirect, url_for
from flask_login import current_user
from config import Config
from extensions import db, login_manager, bcrypt
import os

def create_models():
    """Importa todos os models na ordem correta - ORDEM BASEADA EM DEPENDÊNCIAS"""

    # NÍVEL 1 - Base (sem dependências externas)
    from models.company import Company
    from models.category import Category

    # NÍVEL 2 - Dependem só de Nível 1
    from models.user import User, TourAccess
    from models.equipment_type import EquipmentType
    from models.material_stock import MaterialStock, MaterialMovement

    # NÍVEL 3 - Dependem de Nível 1 e 2
    from models.equipment_model import EquipmentModel

    # NÍVEL 4 - Dependem de níveis anteriores
    from models.equipment import Equipment
    from models.tour import Tour, Show, TourRequirement, TourEquipment, EquipmentCheckpoint, EquipmentTransfer, EquipmentReplacement
    from models.commercial import Lead, LeadInteraction, LeadReactivation
    from models.rh import (Employee, Freelancer, FreelancerAssignment, FreelancerReview, PayrollEntry,
                           AccountPayable, FreelancerPayment, BankAccount, CostCenter, AccountReceivable,
                           Supplier, Client, Vehicle, Consumable, ContractTemplate, CashRegister, CashEntry)

    # NÍVEL 5 - Dependem de Equipment/Tour
    from models.maintenance import Maintenance
    from models.kit import Kit, KitRequirement
    from models.separation_list import SeparationList, SeparationListItem
    from models.work_list import WorkList, WorkListItem
    from models.financial import Quote, QuoteItem, Contract, Invoice, Payment

    # NÍVEL 6 - Dependem de Quote/Invoice/Payment
    from models.financial_expanded import FinancialProvision, PaymentStrategy, CashFlowProjection, TaxCalculation, FinancialAlert

    # NÍVEL 7 - Fabricação
    from models.fabrication import FabricationTemplate, FabricationRecord

def migrate_database():
    """Adiciona colunas que podem estar faltando sem quebrar"""
    from sqlalchemy import text

    migrations = [
        # Company - campos originais
        'ALTER TABLE company ADD COLUMN logo_url VARCHAR(500)',
        'ALTER TABLE company ADD COLUMN email VARCHAR(120)',
        'ALTER TABLE company ADD COLUMN phone VARCHAR(20)',
        'ALTER TABLE company ADD COLUMN address TEXT',
        # Company - novos campos de endereco
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
        # Maintenance
        'ALTER TABLE maintenance ADD COLUMN created_at DATETIME',
        # Equipment
        'ALTER TABLE equipment ADD COLUMN qr_code_url VARCHAR(500)',
        'ALTER TABLE equipment ADD COLUMN type_id INTEGER',
        # SeparationList - dados do cliente
        'ALTER TABLE separation_list ADD COLUMN client_name VARCHAR(200)',
        'ALTER TABLE separation_list ADD COLUMN client_phone VARCHAR(20)',
        'ALTER TABLE separation_list ADD COLUMN client_email VARCHAR(120)',
        'ALTER TABLE separation_list ADD COLUMN client_address TEXT',
        # SeparationList - dados do evento
        'ALTER TABLE separation_list ADD COLUMN event_name VARCHAR(200)',
        'ALTER TABLE separation_list ADD COLUMN event_date DATE',
        'ALTER TABLE separation_list ADD COLUMN event_time VARCHAR(10)',
        'ALTER TABLE separation_list ADD COLUMN event_location TEXT',
        # SeparationList - outros
        'ALTER TABLE separation_list ADD COLUMN validity_date DATE',
        'ALTER TABLE separation_list ADD COLUMN observations TEXT',
        'ALTER TABLE separation_list ADD COLUMN discount_percent DECIMAL(5,2)',
        'ALTER TABLE separation_list ADD COLUMN discount_value DECIMAL(10,2)',
        # SeparationListItem
        'ALTER TABLE separation_list_item ADD COLUMN item_description VARCHAR(500)',
        # Equipment - RFID/NFC
        'ALTER TABLE equipment ADD COLUMN nfc_tag_id VARCHAR(64)',
        'ALTER TABLE equipment ADD COLUMN rfid_uhf_tag VARCHAR(128)',
        'ALTER TABLE equipment ADD COLUMN tag_associated_at DATETIME',
        'ALTER TABLE equipment ADD COLUMN tag_associated_by INTEGER',
        # Company - API Key
        'ALTER TABLE company ADD COLUMN api_key VARCHAR(64)',
        # Quote - client_id
        'ALTER TABLE quote ADD COLUMN client_id INTEGER',
        # AccountPayable - novos campos
        'ALTER TABLE account_payable ADD COLUMN custom_category VARCHAR(100)',
        'ALTER TABLE account_payable ADD COLUMN payment_method VARCHAR(50)',
        'ALTER TABLE account_payable ADD COLUMN installment_number INTEGER',
        'ALTER TABLE account_payable ADD COLUMN total_installments INTEGER',
        'ALTER TABLE account_payable ADD COLUMN bank_account_id INTEGER',
        'ALTER TABLE account_payable ADD COLUMN cost_center_id INTEGER',
        'ALTER TABLE account_payable ADD COLUMN receipt_url VARCHAR(500)',
        'ALTER TABLE account_payable ADD COLUMN origin_type VARCHAR(50)',
        'ALTER TABLE account_payable ADD COLUMN origin_id INTEGER',
    ]

    for migration in migrations:
        try:
            db.session.execute(text(migration))
            db.session.commit()
        except Exception:
            db.session.rollback()

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

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faca login para acessar.'

os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/uploads/logos', exist_ok=True)
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

# COMENTADO TEMPORARIAMENTE PARA RODAR MIGRATION
# DESCOMENTAR DEPOIS DE RODAR migrate_all.py
with app.app_context():
    create_models()
    db.create_all()
    migrate_database()
    regenerate_all_qr_codes()
    print("Sistema pronto!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)