"""
Financial Listeners - Escutam eventos de RH e criam registros financeiros

PADRÃO:
- Na APROVAÇÃO: criar AccountPayable com status='pending'
- No PAGAMENTO: marcar AccountPayable existente como 'paid'
"""

from services.event_bus import EventBus, Events
from extensions import db
from decimal import Decimal
from datetime import datetime, date, timedelta


@EventBus.on(Events.ADVANCE_APPROVED)
def create_advance_payable(data):
    """
    Cria AccountPayable quando solicitação de adiantamento é APROVADA.
    origin_id = solicitacao_id (não employee_id)
    notes contém employee_id para rastreabilidade em relatórios
    Retorna True/False para verificação atômica na rota
    """
    from models.rh import AccountPayable, SolicitacaoAdiantamento
    try:
        solicitacao_id = data.get('solicitacao_id')
        if not solicitacao_id:
            return False

        existing = AccountPayable.query.filter_by(
            origin_type='adiantamento',
            origin_id=solicitacao_id
        ).first()
        if existing:
            return False

        due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if isinstance(data['due_date'], str) else data['due_date']
        employee_id = data.get('employee_id')
        conta = AccountPayable(
            company_id=data['company_id'],
            description=f"Adiantamento - {data['employee_name']} ({due_date.strftime('%m/%Y')})",
            category='adiantamento',
            amount=Decimal(str(data['amount'])),
            due_date=due_date,
            status='pending',
            origin_type='adiantamento',
            origin_id=solicitacao_id,
            notes=f"employee_id:{employee_id}" if employee_id else None,
            created_by=data.get('approved_by')
        )
        db.session.add(conta)
        db.session.flush()

        solicitacao = SolicitacaoAdiantamento.query.get(solicitacao_id)
        if solicitacao:
            solicitacao.status = 'integrado'

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False


@EventBus.on(Events.PAYROLL_APPROVED)
def create_payroll_payables_on_approval(data):
    """
    Cria TODOS os AccountPayables quando a folha é APROVADA (não quando é paga).
    Todos são criados com status='pending'.
    Due dates:
    - Salário: dia 5 do mês seguinte
    - FGTS: dia 7 do mês seguinte
    - INSS/GPS: dia 20 do mês seguinte
    - IRRF: dia 20 do mês seguinte
    """
    from models.rh import AccountPayable, PayrollEntry
    try:
        entry = PayrollEntry.query.get(data['payroll_id'])
        if not entry:
            return {'created': False, 'error': 'PayrollEntry not found'}

        existing = AccountPayable.query.filter_by(
            origin_type='payroll',
            origin_id=entry.id,
            category='folha_pagamento'
        ).first()
        if existing:
            return {'created': False, 'error': 'AccountPayables already exist for this payroll'}

        ref_month = entry.reference_month
        ref_year = entry.reference_year
        next_month = ref_month + 1 if ref_month < 12 else 1
        next_year = ref_year if ref_month < 12 else ref_year + 1

        salary_due_date = date(next_year, next_month, 5)
        fgts_due_date = date(next_year, next_month, 7)
        inss_due_date = date(next_year, next_month, 20)
        irrf_due_date = date(next_year, next_month, 20)

        employee_name = data.get('employee_name', 'N/A')
        company_id = data['company_id']
        created_by = data.get('approved_by')

        db.session.add(AccountPayable(
            company_id=company_id,
            description=f"Salário - {employee_name} ({ref_month:02d}/{ref_year})",
            category='folha_pagamento', amount=entry.net_salary,
            due_date=salary_due_date, status='pending',
            origin_type='payroll', origin_id=entry.id, created_by=created_by
        ))

        total_inss = float(entry.inss_employee or 0) + float(entry.inss_employer or 0) + float(entry.inss_rat or 0) + float(entry.inss_terceiros or 0)
        if total_inss > 0:
            db.session.add(AccountPayable(
                company_id=company_id,
                description=f"INSS/GPS - {employee_name} ({ref_month:02d}/{ref_year})",
                category='inss', amount=Decimal(str(total_inss)),
                due_date=inss_due_date, status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=created_by
            ))

        if entry.fgts and float(entry.fgts) > 0:
            db.session.add(AccountPayable(
                company_id=company_id,
                description=f"FGTS - {employee_name} ({ref_month:02d}/{ref_year})",
                category='fgts', amount=entry.fgts,
                due_date=fgts_due_date, status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=created_by
            ))

        if entry.irrf and float(entry.irrf) > 0:
            db.session.add(AccountPayable(
                company_id=company_id,
                description=f"IRRF - {employee_name} ({ref_month:02d}/{ref_year})",
                category='irrf', amount=entry.irrf,
                due_date=irrf_due_date, status='pending',
                origin_type='payroll', origin_id=entry.id, created_by=created_by
            ))

        entry.financial_integrated = True
        db.session.commit()
        return {'created': True}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.PAYROLL_PAID)
def mark_salary_payable_as_paid(data):
    """
    Quando a folha é PAGA, apenas marca o AccountPayable do salário como 'paid'.
    NÃO cria novos AccountPayables (eles já foram criados na aprovação).
    """
    from models.rh import AccountPayable, PayrollEntry
    try:
        entry = PayrollEntry.query.get(data['payroll_id'])
        if not entry:
            return {'updated': False, 'error': 'PayrollEntry not found'}

        salary_payable = AccountPayable.query.filter_by(
            origin_type='payroll',
            origin_id=entry.id,
            category='folha_pagamento'
        ).first()

        if not salary_payable:
            return {'updated': False, 'error': 'Salary AccountPayable not found'}

        if salary_payable.status == 'paid':
            return {'updated': False, 'error': 'Already paid'}

        salary_payable.status = 'paid'
        salary_payable.paid_at = datetime.utcnow()
        salary_payable.paid_amount = salary_payable.amount
        salary_payable.payment_method = data.get('payment_method', 'transfer')

        db.session.commit()
        return {'updated': True, 'payable_id': salary_payable.id}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}


@EventBus.on(Events.VACATION_APPROVED)
def create_vacation_payable_on_approval(data):
    """
    Quando férias são APROVADAS/AGENDADAS, cria AccountPayable com status='pending'.
    Due date = payment_date das férias (2 dias antes do início).
    """
    from models.rh import AccountPayable, VacationPeriod
    try:
        ferias = VacationPeriod.query.get(data['vacation_id'])
        if not ferias:
            return {'created': False, 'error': 'VacationPeriod not found'}

        existing = AccountPayable.query.filter_by(
            origin_type='vacation',
            origin_id=ferias.id
        ).first()
        if existing:
            return {'created': False, 'error': 'AccountPayable already exists for this vacation'}

        payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date() if isinstance(data['payment_date'], str) else data['payment_date']

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"Férias - {data['employee_name']}",
            category='ferias',
            amount=Decimal(str(data['net_value'])),
            due_date=payment_date,
            status='pending',
            origin_type='vacation',
            origin_id=ferias.id,
            created_by=data.get('approved_by')
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


@EventBus.on(Events.VACATION_PAID)
def mark_vacation_payable_as_paid(data):
    """
    Quando férias são PAGAS, marca o AccountPayable existente como 'paid'.
    NÃO cria novo AccountPayable (já foi criado na aprovação).
    """
    from models.rh import AccountPayable, VacationPeriod
    try:
        ferias = VacationPeriod.query.get(data['vacation_id'])
        if not ferias:
            return {'updated': False, 'error': 'VacationPeriod not found'}

        payable = AccountPayable.query.filter_by(
            origin_type='vacation',
            origin_id=ferias.id
        ).first()

        if not payable:
            return {'updated': False, 'error': 'Vacation AccountPayable not found'}

        if payable.status == 'paid':
            return {'updated': False, 'error': 'Already paid'}

        payable.status = 'paid'
        payable.paid_at = datetime.utcnow()
        payable.paid_amount = payable.amount
        payable.payment_method = 'transfer'

        db.session.commit()
        return {'updated': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}


@EventBus.on(Events.THIRTEENTH_APPROVED)
def create_thirteenth_payables_on_approval(data):
    """
    Quando 13º é GERADO/APROVADO, cria 2 AccountPayables com status='pending':
    - 1ª parcela: due_date = 30/Nov, category='decimo_primeira'
    - 2ª parcela: due_date = 20/Dez, category='decimo_segunda'
    """
    from models.rh import AccountPayable, ThirteenthSalary
    try:
        entry = ThirteenthSalary.query.get(data['thirteenth_id'])
        if not entry:
            return {'created': False, 'error': 'ThirteenthSalary not found'}

        existing = AccountPayable.query.filter_by(
            origin_type='thirteenth',
            origin_id=entry.id,
            category='decimo_primeira'
        ).first()
        if existing:
            return {'created': False, 'error': 'AccountPayables already exist for this thirteenth'}

        year = data['reference_year']
        employee_name = data['employee_name']
        company_id = data['company_id']
        created_by = data.get('created_by')

        first_due_date = date(year, 11, 30)
        second_due_date = date(year, 12, 20)

        first_payable = AccountPayable(
            company_id=company_id,
            description=f"13º 1ª Parcela - {employee_name} ({year})",
            category='decimo_primeira',
            amount=Decimal(str(data['first_installment_value'])),
            due_date=first_due_date,
            status='pending',
            origin_type='thirteenth',
            origin_id=entry.id,
            created_by=created_by
        )
        db.session.add(first_payable)
        db.session.flush()
        entry.first_account_payable_id = first_payable.id

        second_payable = AccountPayable(
            company_id=company_id,
            description=f"13º 2ª Parcela - {employee_name} ({year})",
            category='decimo_segunda',
            amount=Decimal(str(data['second_installment_net'])),
            due_date=second_due_date,
            status='pending',
            origin_type='thirteenth',
            origin_id=entry.id,
            created_by=created_by
        )
        db.session.add(second_payable)
        db.session.flush()
        entry.second_account_payable_id = second_payable.id

        entry.financial_integrated = True
        db.session.commit()
        return {'created': True, 'first_payable_id': first_payable.id, 'second_payable_id': second_payable.id}
    except Exception as e:
        db.session.rollback()
        return {'created': False, 'error': str(e)}


@EventBus.on(Events.THIRTEENTH_FIRST_PAID)
def mark_thirteenth_first_as_paid(data):
    """
    Quando 1ª parcela do 13º é PAGA, marca o AccountPayable existente como 'paid'.
    NÃO cria novo AccountPayable (já foi criado na aprovação).
    """
    from models.rh import AccountPayable, ThirteenthSalary
    try:
        entry = ThirteenthSalary.query.get(data['thirteenth_id'])
        if not entry:
            return {'updated': False, 'error': 'ThirteenthSalary not found'}

        payable = AccountPayable.query.filter_by(
            origin_type='thirteenth',
            origin_id=entry.id,
            category='decimo_primeira'
        ).first()

        if not payable:
            return {'updated': False, 'error': 'First installment AccountPayable not found'}

        if payable.status == 'paid':
            return {'updated': False, 'error': 'Already paid'}

        payable.status = 'paid'
        payable.paid_at = datetime.utcnow()
        payable.paid_amount = payable.amount
        payable.payment_method = 'transfer'

        db.session.commit()
        return {'updated': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}


@EventBus.on(Events.THIRTEENTH_SECOND_PAID)
def mark_thirteenth_second_as_paid(data):
    """
    Quando 2ª parcela do 13º é PAGA, marca o AccountPayable existente como 'paid'.
    NÃO cria novo AccountPayable (já foi criado na aprovação).
    """
    from models.rh import AccountPayable, ThirteenthSalary
    try:
        entry = ThirteenthSalary.query.get(data['thirteenth_id'])
        if not entry:
            return {'updated': False, 'error': 'ThirteenthSalary not found'}

        payable = AccountPayable.query.filter_by(
            origin_type='thirteenth',
            origin_id=entry.id,
            category='decimo_segunda'
        ).first()

        if not payable:
            return {'updated': False, 'error': 'Second installment AccountPayable not found'}

        if payable.status == 'paid':
            return {'updated': False, 'error': 'Already paid'}

        payable.status = 'paid'
        payable.paid_at = datetime.utcnow()
        payable.paid_amount = payable.amount
        payable.payment_method = 'transfer'

        db.session.commit()
        return {'updated': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}


@EventBus.on(Events.TERMINATION_APPROVED)
def create_termination_payable_on_approval(data):
    """
    Quando rescisão é APROVADA, cria AccountPayable com status='pending'.
    Due date = termination_date + 10 dias (prazo legal).
    """
    from models.rh import AccountPayable, Termination
    try:
        rescisao = Termination.query.get(data['termination_id'])
        if not rescisao:
            return {'created': False, 'error': 'Termination not found'}

        existing = AccountPayable.query.filter_by(
            origin_type='termination',
            origin_id=rescisao.id
        ).first()
        if existing:
            return {'created': False, 'error': 'AccountPayable already exists for this termination'}

        termination_date = datetime.strptime(data['termination_date'], '%Y-%m-%d').date() if isinstance(data['termination_date'], str) else data['termination_date']
        due_date = termination_date + timedelta(days=10)

        payable = AccountPayable(
            company_id=data['company_id'],
            description=f"Rescisão - {data['employee_name']}",
            category='rescisao',
            amount=Decimal(str(data['net_total'])),
            due_date=due_date,
            status='pending',
            origin_type='termination',
            origin_id=rescisao.id,
            created_by=data.get('approved_by')
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


@EventBus.on(Events.TERMINATION_PAID)
def mark_termination_payable_as_paid(data):
    """
    Quando rescisão é PAGA, marca o AccountPayable existente como 'paid'.
    NÃO cria novo AccountPayable (já foi criado na aprovação).
    """
    from models.rh import AccountPayable, Termination
    try:
        rescisao = Termination.query.get(data['termination_id'])
        if not rescisao:
            return {'updated': False, 'error': 'Termination not found'}

        payable = AccountPayable.query.filter_by(
            origin_type='termination',
            origin_id=rescisao.id
        ).first()

        if not payable:
            return {'updated': False, 'error': 'Termination AccountPayable not found'}

        if payable.status == 'paid':
            return {'updated': False, 'error': 'Already paid'}

        payable.status = 'paid'
        payable.paid_at = datetime.utcnow()
        payable.paid_amount = payable.amount
        payable.payment_method = data.get('payment_method', 'transfer')

        db.session.commit()
        return {'updated': True, 'payable_id': payable.id}
    except Exception as e:
        db.session.rollback()
        return {'updated': False, 'error': str(e)}


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
