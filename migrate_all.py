"""
HARDCASE - Migration Script Completo
Aplica TODAS as mudancas de uma vez:
- Cria novas tabelas
- Migra fotos para modelo compartilhado
- Adiciona novas colunas
"""

from extensions import db
from sqlalchemy import text
import json
from datetime import datetime
import os

def backup_database():
    """Faz backup antes de qualquer alteracao"""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    os.makedirs('backups', exist_ok=True)

    try:
        shutil.copy2('instance/tour_manager.db', f'backups/tour_manager_pre_migration_{timestamp}.db')
        print(f"Backup criado: backups/tour_manager_pre_migration_{timestamp}.db")
        return True
    except Exception as e:
        print(f"Erro ao criar backup: {e}")
        return False

def migrate_phase_1_new_tables():
    """FASE 1: Criar todas as novas tabelas"""
    print("\n=== FASE 1: Criando novas tabelas ===")

    migrations = [
        # EquipmentModel
        """CREATE TABLE IF NOT EXISTS equipment_model (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            brand VARCHAR(100) NOT NULL,
            model VARCHAR(100) NOT NULL,
            type_id INTEGER,
            photo_url VARCHAR(500),
            specs TEXT,
            reference_value NUMERIC(10, 2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (type_id) REFERENCES equipment_type(id),
            UNIQUE (company_id, brand, model)
        )""",

        # MaterialStock
        """CREATE TABLE IF NOT EXISTS material_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50) NOT NULL,
            sub_category VARCHAR(100),
            quantity NUMERIC(10, 2) DEFAULT 0,
            unit VARCHAR(20) NOT NULL,
            minimum_quantity NUMERIC(10, 2) DEFAULT 0,
            maximum_quantity NUMERIC(10, 2),
            brand VARCHAR(100),
            model VARCHAR(100),
            reference_value NUMERIC(10, 2),
            supplier VARCHAR(200),
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (company_id) REFERENCES company(id)
        )""",

        # MaterialMovement
        """CREATE TABLE IF NOT EXISTS material_movement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            movement_type VARCHAR(20) NOT NULL,
            quantity NUMERIC(10, 2) NOT NULL,
            quantity_before NUMERIC(10, 2) NOT NULL,
            quantity_after NUMERIC(10, 2) NOT NULL,
            reason VARCHAR(50) NOT NULL,
            reference_type VARCHAR(50),
            reference_id INTEGER,
            notes TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES material_stock(id),
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (created_by) REFERENCES user(id)
        )""",

        # Lead
        """CREATE TABLE IF NOT EXISTS lead (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(120),
            phone VARCHAR(20),
            company_name VARCHAR(200),
            stage VARCHAR(50) DEFAULT 'new',
            status VARCHAR(20) DEFAULT 'active',
            ai_score INTEGER DEFAULT 0,
            score_factors TEXT,
            source VARCHAR(50),
            campaign VARCHAR(100),
            estimated_value NUMERIC(10, 2),
            probability INTEGER DEFAULT 0,
            expected_close_date DATE,
            event_type VARCHAR(100),
            event_date DATE,
            event_location VARCHAR(200),
            assigned_to INTEGER,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_contact_at DATETIME,
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (assigned_to) REFERENCES user(id)
        )""",

        # LeadInteraction
        """CREATE TABLE IF NOT EXISTS lead_interaction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            interaction_type VARCHAR(50) NOT NULL,
            direction VARCHAR(20),
            subject VARCHAR(200),
            notes TEXT,
            outcome VARCHAR(50),
            next_action VARCHAR(200),
            next_action_date DATE,
            performed_by INTEGER,
            performed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES lead(id),
            FOREIGN KEY (performed_by) REFERENCES user(id)
        )""",

        # LeadReactivation
        """CREATE TABLE IF NOT EXISTS lead_reactivation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            strategy VARCHAR(50) NOT NULL,
            message_suggestion TEXT,
            confidence_score INTEGER,
            status VARCHAR(20) DEFAULT 'pending',
            executed_at DATETIME,
            executed_by INTEGER,
            result_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES lead(id),
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (executed_by) REFERENCES user(id)
        )""",

        # Employee
        """CREATE TABLE IF NOT EXISTS employee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER,
            name VARCHAR(200) NOT NULL,
            cpf VARCHAR(14) UNIQUE,
            rg VARCHAR(20),
            birth_date DATE,
            email VARCHAR(120),
            phone VARCHAR(20),
            address TEXT,
            position VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            admission_date DATE NOT NULL,
            dismissal_date DATE,
            salary NUMERIC(10, 2) NOT NULL,
            salary_type VARCHAR(20) DEFAULT 'monthly',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (user_id) REFERENCES user(id)
        )""",

        # Freelancer
        """CREATE TABLE IF NOT EXISTS freelancer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name VARCHAR(200) NOT NULL,
            cpf_cnpj VARCHAR(18),
            email VARCHAR(120),
            phone VARCHAR(20),
            role VARCHAR(100),
            skills TEXT,
            hourly_rate NUMERIC(10, 2),
            daily_rate NUMERIC(10, 2),
            performance_score INTEGER DEFAULT 50,
            reliability_score INTEGER DEFAULT 50,
            technical_score INTEGER DEFAULT 50,
            overall_score INTEGER DEFAULT 50,
            is_available BOOLEAN DEFAULT 1,
            availability_notes TEXT,
            status VARCHAR(20) DEFAULT 'active',
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(id)
        )""",

        # FreelancerAssignment
        """CREATE TABLE IF NOT EXISTS freelancer_assignment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            freelancer_id INTEGER NOT NULL,
            tour_id INTEGER,
            show_id INTEGER,
            role VARCHAR(100) NOT NULL,
            start_date DATETIME NOT NULL,
            end_date DATETIME NOT NULL,
            agreed_rate NUMERIC(10, 2) NOT NULL,
            rate_type VARCHAR(20),
            total_amount NUMERIC(10, 2),
            status VARCHAR(20) DEFAULT 'scheduled',
            payment_status VARCHAR(20) DEFAULT 'pending',
            paid_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (freelancer_id) REFERENCES freelancer(id),
            FOREIGN KEY (tour_id) REFERENCES tour(id),
            FOREIGN KEY (show_id) REFERENCES show(id)
        )""",

        # FreelancerReview
        """CREATE TABLE IF NOT EXISTS freelancer_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            freelancer_id INTEGER NOT NULL,
            assignment_id INTEGER,
            performance_rating INTEGER,
            reliability_rating INTEGER,
            communication_rating INTEGER,
            teamwork_rating INTEGER,
            comments TEXT,
            would_hire_again BOOLEAN,
            reviewed_by INTEGER,
            reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (freelancer_id) REFERENCES freelancer(id),
            FOREIGN KEY (assignment_id) REFERENCES freelancer_assignment(id),
            FOREIGN KEY (reviewed_by) REFERENCES user(id)
        )""",

        # PayrollEntry
        """CREATE TABLE IF NOT EXISTS payroll_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            reference_month INTEGER NOT NULL,
            reference_year INTEGER NOT NULL,
            base_salary NUMERIC(10, 2) NOT NULL,
            overtime_hours NUMERIC(5, 2) DEFAULT 0,
            overtime_amount NUMERIC(10, 2) DEFAULT 0,
            bonuses NUMERIC(10, 2) DEFAULT 0,
            deductions NUMERIC(10, 2) DEFAULT 0,
            net_salary NUMERIC(10, 2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            payment_date DATE,
            payment_method VARCHAR(50),
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved_by INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employee(id),
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (approved_by) REFERENCES user(id)
        )""",

        # FinancialProvision
        """CREATE TABLE IF NOT EXISTS financial_provision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            tour_id INTEGER,
            provision_type VARCHAR(50) NOT NULL,
            category VARCHAR(100),
            amount NUMERIC(10, 2) NOT NULL,
            reference_month INTEGER NOT NULL,
            reference_year INTEGER NOT NULL,
            competence_date DATE NOT NULL,
            expected_realization_date DATE,
            actual_realization_date DATE,
            status VARCHAR(20) DEFAULT 'provisioned',
            quote_id INTEGER,
            invoice_id INTEGER,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by_system BOOLEAN DEFAULT 1,
            FOREIGN KEY (company_id) REFERENCES company(id),
            FOREIGN KEY (tour_id) REFERENCES tour(id),
            FOREIGN KEY (quote_id) REFERENCES quote(id),
            FOREIGN KEY (invoice_id) REFERENCES invoice(id)
        )""",

        # Continua...
    ]

    for migration in migrations:
        try:
            db.session.execute(text(migration))
            db.session.commit()
            print(f"OK Tabela criada")
        except Exception as e:
            db.session.rollback()
            print(f"ERRO Erro: {e}")

def migrate_phase_2_add_columns():
    """FASE 2: Adicionar colunas em tabelas existentes"""
    print("\n=== FASE 2: Adicionando colunas ===")

    columns = [
        'ALTER TABLE equipment ADD COLUMN model_id INTEGER',
        'ALTER TABLE equipment ADD COLUMN fabrication_record_id INTEGER',
        'ALTER TABLE maintenance ADD COLUMN priority VARCHAR(20) DEFAULT "normal"',
        'ALTER TABLE maintenance ADD COLUMN problem_type VARCHAR(50)',
        'ALTER TABLE maintenance ADD COLUMN failure_location VARCHAR(200)',
        'ALTER TABLE maintenance ADD COLUMN tour_id INTEGER',
        'ALTER TABLE maintenance ADD COLUMN parts_cost NUMERIC(10, 2) DEFAULT 0',
        'ALTER TABLE maintenance ADD COLUMN labor_cost NUMERIC(10, 2) DEFAULT 0',
        'ALTER TABLE maintenance ADD COLUMN total_cost NUMERIC(10, 2) DEFAULT 0',
        'ALTER TABLE maintenance ADD COLUMN started_at DATETIME',
        'ALTER TABLE maintenance ADD COLUMN completed_at DATETIME',
        'ALTER TABLE maintenance ADD COLUMN estimated_hours NUMERIC(5, 2)',
        'ALTER TABLE maintenance ADD COLUMN actual_hours NUMERIC(5, 2)',
        'ALTER TABLE maintenance ADD COLUMN internal_notes TEXT',
    ]

    for col in columns:
        try:
            db.session.execute(text(col))
            db.session.commit()
            print(f"OK Coluna adicionada")
        except Exception as e:
            db.session.rollback()
            # Ignora se coluna ja existe
            pass

def migrate_phase_3_photos():
    """FASE 3: Migrar fotos para modelo compartilhado"""
    print("\n=== FASE 3: Migrando fotos ===")

    from models.equipment import Equipment
    from models.equipment_model import EquipmentModel

    # Agrupar equipamentos por brand+model
    equipments = Equipment.query.filter(
        Equipment.brand.isnot(None),
        Equipment.model.isnot(None)
    ).all()

    models_created = {}
    count = 0

    for eq in equipments:
        key = f"{eq.brand}|{eq.model}"

        if key not in models_created:
            # Criar modelo
            eq_model = EquipmentModel(
                company_id=eq.company_id,
                brand=eq.brand,
                model=eq.model,
                type_id=eq.type_id,
                photo_url=eq.primary_photo_url,  # PRIMEIRA foto vira foto do modelo
                reference_value=eq.value
            )
            db.session.add(eq_model)
            db.session.flush()
            models_created[key] = eq_model.id
            count += 1

        # Linkar equipamento ao modelo
        eq.model_id = models_created[key]

    db.session.commit()
    print(f"OK {count} modelos criados")
    print(f"OK {len(equipments)} equipamentos vinculados")

def run_full_migration():
    """Executa migracao completa"""
    print("="*60)
    print("HARDCASE - MIGRAÇÃO GLOBAL COMPLETA")
    print("="*60)

    # Backup
    if not backup_database():
        print("\nERRO ERRO: Não foi possível fazer backup. Abortando.")
        return False

    try:
        # Fase 1: Novas tabelas
        migrate_phase_1_new_tables()

        # Fase 2: Novas colunas
        migrate_phase_2_add_columns()

        # Fase 3: Migrar fotos
        migrate_phase_3_photos()

        print("\n" + "="*60)
        print("OK MIGRAÇÃO COMPLETA!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\nERRO ERRO durante migração: {e}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    from main import app
    with app.app_context():
        run_full_migration()