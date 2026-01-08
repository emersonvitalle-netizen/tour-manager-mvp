"""
Financial Listeners - Escutam eventos de RH e criam registros financeiros
"""

from services.event_bus import EventBus, Events
from extensions import db
from decimal import Decimal
from datetime import datetime, date, timedelta


@EventBus.on(Events.ADVANCE_APPROVED)
def create_advance_payable(data):
    from models.rh import AccountPayable
    try:
        due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if isinstance(data['due_date'], str) else data['due_date']
        conta = AccountPayable(
            company_id=data['company_id'],
            description=f"Adiantamento - {data['employee_name']} ({due_date.strftime('%m/%Y')})",
            category='adiantamento',
            amount=Decimal(str(data['amount'])),
            due_date=due_date,
            status='pending',
            origin_type='adiantamento',
            origin_id=data['employee_id'],
            created_by=data.get('approved_by')
        )
        db.session.add(conta)
        db.session.commit()
        return {'created': True, 'payable_id': conta.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.PAYROLL_PAID)
def create_payroll_payables(data):
    from models.rh import AccountPayable, PayrollEntry
    try:
        entry = PayrollEntry.query.get(data['payroll_id'])
        if not entry or entry.financial_integrated:
            return {'created': False}

        ref_date = date(entry.reference_year, entry.reference_month, 1)

        # Salário
        db.session.add(AccountPayable(
            company_id=data['company_id'],
            description=f"Salário - {data['employee_name']} ({entry.reference_month:02d}/{entry.reference_year})",
            category='folha_pagamento', amount=entry.net_salary,
            due_date=date.today(), status='paid', paid_at=datetime.utcnow(),
            paid_amount=entry.net_salary, payment_method=data.get('payment_method', 'transfer'),
            origin_type='payroll', origin_id=entry.id, created_by=data.get('paid_by')
        ))

        # INSS
        total_inss = float(entry.inss_employee or 0) + float(entry.inss_employer or 0) + float(entry.inss_rat or 0) + float(entry.inss_terceiros or 0)
        if total_inss > 0:
            db.session.add(AccountPayable(
                company_id=data['company_id'],
                description=f"INSS/GPS - {data['employee_name']} ({entry.reference_month:02d}/{entry.reference_year})",
                category='inss', amount=Decimal(str(total_inss)),
                due_date=ref_date + timedelta(days=50), status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=data.get('paid_by')
            ))

        # FGTS
        if entry.fgts and float(entry.fgts) > 0:
            db.session.add(AccountPayable(
                company_id=data['company_id'],
                description=f"FGTS - {data['employee_name']} ({entry.reference_month:02d}/{entry.reference_year})",
                category='fgts', amount=entry.fgts,
                due_date=ref_date + timedelta(days=37), status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=data.get('paid_by')
            ))

        # IRRF
        if entry.irrf and float(entry.irrf) > 0:
            db.session.add(AccountPayable(
                company_id=data['company_id'],
                description=f"IRRF - {data['employee_name']} ({entry.reference_month:02d}/{entry.reference_year})",
                category='irrf', amount=entry.irrf,
                due_date=ref_date + timedelta(days=50), status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=data.get('paid_by')
            ))

        entry.financial_integrated = True
        db.session.commit()
        return {'created': True}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.VACATION_PAID)
def create_vacation_payable(data):
    from models.rh import AccountPayable, VacationPeriod
    try:
        ferias = VacationPeriod.query.get(data['vacation_id'])
        if not ferias or ferias.financial_integrated:
            return {'created': False}

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"Férias - {data['employee_name']}",
            category='ferias', amount=Decimal(str(data['net_value'])),
            due_date=date.today(), status='paid',
            paid_amount=Decimal(str(data['net_value'])), paid_at=datetime.utcnow(),
            payment_method='transfer', origin_type='vacation', origin_id=ferias.id,
            created_by=data.get('paid_by')
        )
        db.session.add(payable)
        db.session.flush()
        ferias.account_payable_id = payable.id
        ferias.financial_integrated = True
        db.session.commit()
        return {'created': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.THIRTEENTH_FIRST_PAID)
def create_thirteenth_first_payable(data):
    from models.rh import AccountPayable, ThirteenthSalary
    try:
        entry = ThirteenthSalary.query.get(data['thirteenth_id'])
        if not entry or entry.first_account_payable_id:
            return {'created': False}

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"13º 1ª Parcela - {data['employee_name']} ({data['reference_year']})",
            category='13o_salario', amount=Decimal(str(data['amount'])),
            due_date=date.today(), status='paid',
            paid_amount=Decimal(str(data['amount'])), paid_at=datetime.utcnow(),
            payment_method='transfer', origin_type='thirteenth', origin_id=entry.id,
            created_by=data.get('paid_by')
        )
        db.session.add(payable)
        db.session.flush()
        entry.first_account_payable_id = payable.id
        db.session.commit()
        return {'created': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.THIRTEENTH_SECOND_PAID)
def create_thirteenth_second_payable(data):
    from models.rh import AccountPayable, ThirteenthSalary
    try:
        entry = ThirteenthSalary.query.get(data['thirteenth_id'])
        if not entry or entry.second_account_payable_id:
            return {'created': False}

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"13º 2ª Parcela - {data['employee_name']} ({data['reference_year']})",
            category='13o_salario', amount=Decimal(str(data['amount'])),
            due_date=date.today(), status='paid',
            paid_amount=Decimal(str(data['amount'])), paid_at=datetime.utcnow(),
            payment_method='transfer', origin_type='thirteenth', origin_id=entry.id,
            created_by=data.get('paid_by')
        )
        db.session.add(payable)
        db.session.flush()
        entry.second_account_payable_id = payable.id
        entry.financial_integrated = True
        db.session.commit()
        return {'created': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.TERMINATION_PAID)
def create_termination_payable(data):
    from models.rh import AccountPayable, Termination
    try:
        rescisao = Termination.query.get(data['termination_id'])
        if not rescisao or rescisao.financial_integrated:
            return {'created': False}

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"Rescisão - {data['employee_name']}",
            category='rescisao', amount=Decimal(str(data['net_total'])),
            due_date=date.today(), status='paid',
            paid_amount=Decimal(str(data['net_total'])), paid_at=datetime.utcnow(),
            payment_method='transfer', origin_type='termination', origin_id=rescisao.id,
            created_by=data.get('paid_by')
        )
        db.session.add(payable)
        db.session.flush()
        rescisao.account_payable_id = payable.id
        rescisao.financial_integrated = True
        db.session.commit()
        return {'created': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.ADVANCE_PAID)
def update_advance_paid(data):
    from models.rh import AccountPayable
    try:
        conta = AccountPayable.query.get(data['advance_id'])
        if not conta or conta.status == 'paid':
            return {'updated': False}
        conta.status = 'paid'
        conta.paid_at = datetime.utcnow()
        conta.paid_amount = conta.amount
        conta.payment_method = data.get('payment_method', 'transfer')
        db.session.commit()
        return {'updated': True}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}