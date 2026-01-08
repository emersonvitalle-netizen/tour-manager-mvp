"""
Routes para modulo RH
- Dashboard com ranking de funcionarios
- Gestao de CLT
- Gestao de Freelancers
- Folhas de pagamento com calculo completo de encargos
- Adiantamento salarial
- Desligamento com limpeza de pendencias
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.rh import Employee, Freelancer, FreelancerAssignment, FreelancerReview, PayrollEntry, AccountPayable, SolicitacaoAdiantamento
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

rh_bp = Blueprint('rh', __name__, url_prefix='/rh')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# TABELAS INSS E IRRF 2025
# ============================================

INSS_TABLE_2025 = [
    # (limite, aliquota)
    (Decimal('1518.00'), Decimal('0.075')),   # 7.5%
    (Decimal('2793.88'), Decimal('0.09')),    # 9%
    (Decimal('4190.83'), Decimal('0.12')),    # 12%
    (Decimal('8157.41'), Decimal('0.14')),    # 14% (teto)
]

IRRF_TABLE_2025 = [
    # (limite, aliquota, deducao)
    (Decimal('2259.20'), Decimal('0'), Decimal('0')),           # Isento
    (Decimal('2826.65'), Decimal('0.075'), Decimal('169.44')),  # 7.5%
    (Decimal('3751.05'), Decimal('0.15'), Decimal('381.44')),   # 15%
    (Decimal('4664.68'), Decimal('0.225'), Decimal('662.77')),  # 22.5%
    (Decimal('999999.99'), Decimal('0.275'), Decimal('896.00')), # 27.5%
]

DEDUCAO_DEPENDENTE_2025 = Decimal('189.59')


def calcular_inss_funcionario(salario_bruto):
    """
    Calcula INSS do funcionario - tabela progressiva 2025
    """
    salario = Decimal(str(salario_bruto))
    inss_total = Decimal('0')
    salario_restante = salario
    faixa_anterior = Decimal('0')

    for limite, aliquota in INSS_TABLE_2025:
        if salario_restante <= 0:
            break

        faixa = min(salario_restante, limite - faixa_anterior)
        if faixa > 0:
            inss_total += faixa * aliquota
            salario_restante -= faixa

        faixa_anterior = limite

    # Teto INSS 2025
    teto_inss = Decimal('951.63')
    return min(inss_total, teto_inss).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_irrf(base_calculo, dependentes=0):
    """
    Calcula IRRF - tabela progressiva 2025
    Base = Salario Bruto - INSS - Deducao Dependentes
    """
    base = Decimal(str(base_calculo))

    # Deducao por dependente
    deducao_dep = DEDUCAO_DEPENDENTE_2025 * dependentes
    base -= deducao_dep

    if base <= 0:
        return Decimal('0')

    for limite, aliquota, deducao in IRRF_TABLE_2025:
        if base <= limite:
            irrf = (base * aliquota) - deducao
            return max(Decimal('0'), irrf).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return Decimal('0')


def calcular_encargos_empresa(salario_bruto, rat_percent=2):
    """
    Calcula encargos que a empresa paga (nao desconta do funcionario)
    """
    salario = Decimal(str(salario_bruto))

    # INSS Patronal: 20%
    inss_patronal = salario * Decimal('0.20')

    # RAT/SAT: 1% a 3% (padrao 2%)
    rat = salario * (Decimal(str(rat_percent)) / 100)

    # Sistema S (Terceiros): 5.8%
    terceiros = salario * Decimal('0.058')

    # FGTS: 8%
    fgts = salario * Decimal('0.08')

    return {
        'inss_patronal': inss_patronal.quantize(Decimal('0.01')),
        'rat': rat.quantize(Decimal('0.01')),
        'terceiros': terceiros.quantize(Decimal('0.01')),
        'fgts': fgts.quantize(Decimal('0.01'))
    }


def calcular_provisoes(salario_bruto):
    """
    Calcula provisoes mensais (1/12 de ferias e 13o)
    """
    salario = Decimal(str(salario_bruto))

    # 13o salario: 1/12
    prov_13 = salario / 12

    # Ferias: 1/12
    prov_ferias = salario / 12

    # 1/3 de ferias
    prov_ferias_bonus = prov_ferias / 3

    # FGTS sobre 13o e ferias
    fgts_13 = prov_13 * Decimal('0.08')
    fgts_ferias = (prov_ferias + prov_ferias_bonus) * Decimal('0.08')

    return {
        'prov_13': prov_13.quantize(Decimal('0.01')),
        'prov_ferias': prov_ferias.quantize(Decimal('0.01')),
        'prov_ferias_bonus': prov_ferias_bonus.quantize(Decimal('0.01')),
        'fgts_13': fgts_13.quantize(Decimal('0.01')),
        'fgts_ferias': fgts_ferias.quantize(Decimal('0.01'))
    }


def calcular_holerite_completo(employee, overtime_hours=0, bonuses=0, advances=0):
    """
    Calcula holerite completo com todos os encargos
    """
    salario_base = Decimal(str(employee.salary))

    # Hora extra (50%)
    valor_hora = salario_base / 220
    overtime_amount = Decimal(str(overtime_hours)) * valor_hora * Decimal('1.5')

    # Salario bruto
    gross = salario_base + overtime_amount + Decimal(str(bonuses))

    # === DESCONTOS FUNCIONARIO ===
    inss_func = calcular_inss_funcionario(gross)

    # Base IRRF = Bruto - INSS
    base_irrf = gross - inss_func
    irrf = calcular_irrf(base_irrf, employee.dependents_count or 0)

    # VT desconto (max 6% do salario base)
    vt_value = Decimal(str(employee.vt_value or 0))
    vt_discount = min(salario_base * Decimal('0.06'), vt_value) if vt_value > 0 else Decimal('0')

    # Total descontos
    total_descontos = inss_func + irrf + vt_discount + Decimal(str(advances))

    # Liquido
    liquido = gross - total_descontos

    # === ENCARGOS EMPRESA ===
    encargos = calcular_encargos_empresa(gross)

    # === PROVISOES ===
    provisoes = calcular_provisoes(gross)

    # === BENEFICIOS PAGOS EMPRESA ===
    vt_paid = vt_value  # Empresa paga VT integral
    vr_paid = Decimal(str(employee.vr_value or 0))
    va_paid = Decimal(str(employee.va_value or 0))
    health_paid = Decimal(str(employee.health_insurance or 0))

    # === CUSTO TOTAL EMPRESA ===
    total_encargos = (
        encargos['inss_patronal'] + 
        encargos['rat'] + 
        encargos['terceiros'] + 
        encargos['fgts']
    )

    total_provisoes = (
        provisoes['prov_13'] + 
        provisoes['prov_ferias'] + 
        provisoes['prov_ferias_bonus'] +
        provisoes['fgts_13'] +
        provisoes['fgts_ferias']
    )

    total_beneficios = vt_paid + vr_paid + va_paid + health_paid

    custo_total = gross + total_encargos + total_provisoes + total_beneficios

    return {
        # Proventos
        'base_salary': salario_base,
        'overtime_hours': Decimal(str(overtime_hours)),
        'overtime_amount': overtime_amount.quantize(Decimal('0.01')),
        'bonuses': Decimal(str(bonuses)),
        'gross_salary': gross.quantize(Decimal('0.01')),

        # Descontos funcionario
        'inss_employee': inss_func,
        'irrf': irrf,
        'vt_discount': vt_discount.quantize(Decimal('0.01')),
        'advances': Decimal(str(advances)),
        'deductions': total_descontos.quantize(Decimal('0.01')),

        # Liquido
        'net_salary': liquido.quantize(Decimal('0.01')),

        # Encargos empresa
        'inss_employer': encargos['inss_patronal'],
        'inss_rat': encargos['rat'],
        'inss_terceiros': encargos['terceiros'],
        'fgts': encargos['fgts'],

        # Provisoes
        'provision_13th': provisoes['prov_13'],
        'provision_vacation': provisoes['prov_ferias'],
        'provision_vacation_bonus': provisoes['prov_ferias_bonus'],
        'provision_fgts_13th': provisoes['fgts_13'],
        'provision_fgts_vacation': provisoes['fgts_ferias'],
        'total_provisions': total_provisoes.quantize(Decimal('0.01')),

        # Beneficios
        'vt_paid': vt_paid,
        'vr_paid': vr_paid,
        'va_paid': va_paid,
        'health_paid': health_paid,

        # Custo total
        'total_employer_cost': custo_total.quantize(Decimal('0.01'))
    }


# ============================================
# ROTAS DASHBOARD
# ============================================

@rh_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard RH com estatisticas"""
    current_month = date.today().month
    current_year = date.today().year

    # Funcionarios ativos
    employees = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).all()

    # Freelancers
    freelancers = Freelancer.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).all()

    # Folha do mes
    payroll_total = db.session.query(db.func.sum(PayrollEntry.net_salary)).filter(
        PayrollEntry.company_id == current_user.company_id,
        PayrollEntry.reference_month == current_month,
        PayrollEntry.reference_year == current_year
    ).scalar() or 0

    pending_payrolls = PayrollEntry.query.filter_by(
        company_id=current_user.company_id,
        reference_month=current_month,
        reference_year=current_year,
        status='pending'
    ).count()

    # Ranking de funcionarios
    ranking = _generate_employee_ranking(current_user.company_id, current_month, current_year)

    return render_template('rh/index.html',
                          employees=employees,
                          freelancers=freelancers,
                          payroll_total=payroll_total,
                          pending_payrolls=pending_payrolls,
                          ranking=ranking,
                          current_month=current_month,
                          current_year=current_year)


# ============================================
# ROTAS FUNCIONARIOS CLT
# ============================================

@rh_bp.route('/employees')
@login_required
@admin_required
def employees():
    """Lista de funcionarios"""
    employees = Employee.query.filter_by(
        company_id=current_user.company_id
    ).order_by(Employee.name).all()

    return render_template('rh/employees.html', employees=employees)


@rh_bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_employee():
    """Novo funcionario"""
    if request.method == 'POST':
        try:
            admission_date_str = request.form.get('admission_date', '')
            admission_date = None
            if admission_date_str:
                admission_date = datetime.strptime(admission_date_str, '%Y-%m-%d').date()

            birth_date_str = request.form.get('birth_date', '')
            birth_date = None
            if birth_date_str:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()

            employee = Employee(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                cpf=request.form.get('cpf', '').strip() or None,
                rg=request.form.get('rg', '').strip() or None,
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                address=request.form.get('address', '').strip() or None,
                birth_date=birth_date,
                admission_date=admission_date,
                position=request.form.get('position', '').strip(),
                department=request.form.get('department', '').strip() or None,
                salary=Decimal(request.form.get('salary', '0').replace(',', '.')),
                status='active'
            )

            db.session.add(employee)
            db.session.commit()

            # === EVENTBUS: EMPLOYEE_HIRED ===
            try:
                from services.event_bus import EventBus, Events
                EventBus.emit(Events.EMPLOYEE_HIRED, {
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'position': employee.position,
                    'department': employee.department,
                    'salary': float(employee.salary),
                    'admission_date': str(admission_date) if admission_date else None,
                    'company_id': current_user.company_id,
                    'created_by': current_user.id
                })
            except ImportError:
                pass

            flash('Funcionario cadastrado com sucesso!', 'success')
            return redirect(url_for('rh.employees'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar funcionario: {str(e)}', 'danger')

    return render_template('rh/employee_form.html', employee=None)


@rh_bp.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(id):
    """Editar funcionario - com limpeza de pendencias ao inativar"""
    employee = Employee.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if request.method == 'POST':
        try:
            # Guardar status anterior para verificar mudanca
            old_status = employee.status
            new_status = request.form.get('status', 'active')

            employee.name = request.form.get('name', '').strip()
            employee.cpf = request.form.get('cpf', '').strip() or None
            employee.rg = request.form.get('rg', '').strip() or None
            employee.email = request.form.get('email', '').strip() or None
            employee.phone = request.form.get('phone', '').strip() or None
            employee.address = request.form.get('address', '').strip() or None
            employee.position = request.form.get('position', '').strip()
            employee.department = request.form.get('department', '').strip() or None
            employee.salary = Decimal(request.form.get('salary', '0').replace(',', '.'))
            employee.vt_value = Decimal(request.form.get('vt_value', '0').replace(',', '.') or '0')
            employee.vr_value = Decimal(request.form.get('vr_value', '0').replace(',', '.') or '0')
            employee.va_value = Decimal(request.form.get('va_value', '0').replace(',', '.') or '0')
            employee.health_insurance = Decimal(request.form.get('health_insurance', '0').replace(',', '.') or '0')
            employee.dependents_count = int(request.form.get('dependents_count', '0') or '0')
            employee.status = new_status

            birth_date_str = request.form.get('birth_date', '')
            if birth_date_str:
                employee.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()

            # ========================================
            # DESLIGAMENTO - Limpeza de pendencias
            # ========================================
            if old_status == 'active' and new_status == 'inactive':
                # Pegar motivo e data do desligamento
                motivo_desligamento = request.form.get('motivo_desligamento', 'demissao')
                data_desligamento_str = request.form.get('data_desligamento', '')

                if data_desligamento_str:
                    data_desligamento = datetime.strptime(data_desligamento_str, '%Y-%m-%d').date()
                else:
                    data_desligamento = date.today()

                # Contar pendencias antes de excluir
                folhas_pendentes = PayrollEntry.query.filter_by(
                    employee_id=employee.id,
                    status='pending'
                ).count()

                contas_pendentes = AccountPayable.query.filter_by(
                    employee_id=employee.id,
                    status='pending'
                ).count()

                # Excluir folhas pendentes (nao pagas)
                PayrollEntry.query.filter_by(
                    employee_id=employee.id,
                    status='pending'
                ).delete()

                # Excluir contas a pagar pendentes vinculadas ao funcionario
                AccountPayable.query.filter_by(
                    employee_id=employee.id,
                    status='pending'
                ).delete()

                # Mensagem informativa
                msg = f'Funcionario {employee.name} desligado ({motivo_desligamento}) em {data_desligamento.strftime("%d/%m/%Y")}.'
                if folhas_pendentes > 0 or contas_pendentes > 0:
                    msg += f' Removidas: {folhas_pendentes} folha(s) e {contas_pendentes} conta(s) pendente(s).'
                flash(msg, 'warning')

            employee.updated_at = datetime.utcnow()
            db.session.commit()

            if new_status == 'active' or old_status == new_status:
                flash('Funcionario atualizado com sucesso!', 'success')

            return redirect(url_for('rh.employees'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar funcionario: {str(e)}', 'danger')

    return render_template('rh/employee_form.html', employee=employee)


@rh_bp.route('/employees/<int:id>')
@login_required
@admin_required
def view_employee(id):
    """Visualizar funcionario"""
    employee = Employee.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    # Calcular preview do holerite
    holerite = calcular_holerite_completo(employee)

    # Buscar adiantamentos pendentes do mes
    mes_atual = date.today().replace(day=1)
    adiantamentos = AccountPayable.query.filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.origin_type == 'adiantamento',
        AccountPayable.origin_id == employee.id,
        AccountPayable.category == 'adiantamento',
        AccountPayable.status == 'pending',
        AccountPayable.due_date >= mes_atual
    ).all()

    return render_template('rh/employee_view.html', 
                          employee=employee, 
                          holerite=holerite,
                          adiantamentos=adiantamentos)


# ============================================
# ROTAS ADIANTAMENTO SALARIAL
# ============================================

@rh_bp.route('/adiantamento', methods=['GET', 'POST'])
@login_required
@admin_required
def adiantamento():
    """Solicitar adiantamento salarial"""
    employees = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Employee.name).all()

    if request.method == 'POST':
        try:
            employee_id = int(request.form.get('employee_id', 0))
            employee = Employee.query.filter_by(
                id=employee_id,
                company_id=current_user.company_id,
                status='active'
            ).first()

            if not employee:
                flash('Funcionario nao encontrado ou inativo', 'danger')
                return redirect(url_for('rh.adiantamento'))

            # Calcular valor maximo (40% do salario)
            salario = float(employee.salary)
            max_adiantamento = salario * 0.40

            # Pegar valor do form
            tipo_valor = request.form.get('tipo_valor', 'percentual')

            if tipo_valor == 'percentual':
                percentual = float(request.form.get('percentual', '0').replace(',', '.'))
                if percentual < 0 or percentual > 40:
                    flash('Percentual deve ser entre 0% e 40%', 'danger')
                    return redirect(url_for('rh.adiantamento'))
                valor = salario * (percentual / 100)
            else:
                valor = float(request.form.get('valor', '0').replace(',', '.'))
                if valor <= 0 or valor > max_adiantamento:
                    flash(f'Valor deve ser entre R$ 0,01 e R$ {max_adiantamento:.2f} (40%)', 'danger')
                    return redirect(url_for('rh.adiantamento'))

            # Data do pagamento
            data_pagamento_str = request.form.get('data_pagamento', '')
            if data_pagamento_str:
                data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
            else:
                data_pagamento = date.today()

            # Verificar se ja tem solicitacao de adiantamento no mes (pendente, aprovado)
            mes_ref = data_pagamento.replace(day=1)
            mes_fim = (mes_ref + timedelta(days=32)).replace(day=1)

            solicitacao_existente = SolicitacaoAdiantamento.query.filter(
                SolicitacaoAdiantamento.company_id == current_user.company_id,
                SolicitacaoAdiantamento.employee_id == employee.id,
                SolicitacaoAdiantamento.status.in_(['pendente', 'aprovado']),
                SolicitacaoAdiantamento.data_pagamento >= mes_ref,
                SolicitacaoAdiantamento.data_pagamento < mes_fim
            ).first()

            if solicitacao_existente:
                status_map = {'pendente': 'pendente de aprovacao', 'aprovado': 'aprovado'}
                status_txt = status_map.get(solicitacao_existente.status, solicitacao_existente.status)
                flash(f'Ja existe adiantamento {status_txt} para {employee.name} neste mes', 'warning')
                return redirect(url_for('rh.adiantamento'))

            # Criar SolicitacaoAdiantamento (aguarda aprovacao RH)
            solicitacao = SolicitacaoAdiantamento(
                company_id=current_user.company_id,
                employee_id=employee.id,
                valor=Decimal(str(valor)),
                data_solicitacao=date.today(),
                data_pagamento=data_pagamento,
                status='pendente',
                created_by=current_user.id
            )
            db.session.add(solicitacao)
            db.session.commit()

            flash(f'Solicitacao de adiantamento de R$ {valor:.2f} criada para {employee.name}. Aguarda aprovacao.', 'success')
            return redirect(url_for('rh.adiantamento'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar adiantamento: {str(e)}', 'danger')

    # Listar solicitacoes pendentes de aprovacao
    solicitacoes_pendentes = SolicitacaoAdiantamento.query.filter(
        SolicitacaoAdiantamento.company_id == current_user.company_id,
        SolicitacaoAdiantamento.status == 'pendente'
    ).order_by(SolicitacaoAdiantamento.data_pagamento).all()

    # Listar adiantamentos aprovados (AccountPayable pendentes de pagamento)
    adiantamentos_aprovados = AccountPayable.query.filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.category == 'adiantamento',
        AccountPayable.status == 'pending'
    ).order_by(AccountPayable.due_date).all()

    return render_template('rh/adiantamento.html', 
                          employees=employees,
                          solicitacoes_pendentes=solicitacoes_pendentes,
                          adiantamentos_aprovados=adiantamentos_aprovados,
                          today=date.today().strftime('%Y-%m-%d'))


@rh_bp.route('/adiantamento/<int:id>/aprovar', methods=['POST'])
@login_required
@admin_required
def aprovar_adiantamento(id):
    """Aprovar solicitacao de adiantamento - cria AccountPayable atomicamente"""
    solicitacao = SolicitacaoAdiantamento.query.filter_by(
        id=id,
        company_id=current_user.company_id,
        status='pendente'
    ).first_or_404()

    employee_name = solicitacao.employee.name
    valor = solicitacao.valor

    solicitacao.status = 'aprovado'
    solicitacao.approved_by = current_user.id
    solicitacao.approved_at = datetime.utcnow()
    db.session.commit()

    payable_created = False
    try:
        from services.event_bus import EventBus, Events
        payable_created = EventBus.emit(Events.ADVANCE_APPROVED, {
            'solicitacao_id': solicitacao.id,
            'employee_id': solicitacao.employee_id,
            'employee_name': employee_name,
            'amount': float(valor),
            'due_date': str(solicitacao.data_pagamento),
            'company_id': current_user.company_id,
            'approved_by': current_user.id
        })
    except ImportError:
        payable_created = False

    if not payable_created:
        solicitacao.status = 'pendente'
        solicitacao.approved_by = None
        solicitacao.approved_at = None
        db.session.commit()
        flash(f'Erro ao criar conta a pagar para {employee_name}. Aprovação revertida.', 'danger')
        return redirect(url_for('rh.adiantamento'))

    flash(f'Adiantamento de R$ {valor:.2f} aprovado para {employee_name}', 'success')
    return redirect(url_for('rh.adiantamento'))


@rh_bp.route('/adiantamento/<int:id>/rejeitar', methods=['POST'])
@login_required
@admin_required
def rejeitar_adiantamento(id):
    """Rejeitar solicitacao de adiantamento"""
    solicitacao = SolicitacaoAdiantamento.query.filter_by(
        id=id,
        company_id=current_user.company_id,
        status='pendente'
    ).first_or_404()

    motivo = request.form.get('motivo', 'Solicitacao rejeitada')

    solicitacao.status = 'rejeitado'
    solicitacao.rejected_by = current_user.id
    solicitacao.rejected_at = datetime.utcnow()
    solicitacao.rejection_reason = motivo
    db.session.commit()

    flash(f'Solicitacao de adiantamento rejeitada para {solicitacao.employee.name}', 'info')
    return redirect(url_for('rh.adiantamento'))


@rh_bp.route('/adiantamento/<int:id>/pagar', methods=['POST'])
@login_required
@admin_required
def pagar_adiantamento(id):
    """Marcar adiantamento como pago"""
    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id,
        category='adiantamento'
    ).first_or_404()

    # Buscar solicitação e funcionário (origin_id agora é solicitacao_id)
    solicitacao = SolicitacaoAdiantamento.query.get(conta.origin_id) if conta.origin_id else None
    employee = solicitacao.employee if solicitacao else None

    conta.status = 'paid'
    conta.paid_at = datetime.utcnow()
    conta.paid_amount = conta.amount
    conta.payment_method = request.form.get('method', 'transfer')

    # Atualizar status da solicitação para pago
    if solicitacao:
        solicitacao.status = 'pago'

    db.session.commit()

    # === EVENTBUS: ADVANCE_PAID ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.ADVANCE_PAID, {
            'advance_id': conta.id,
            'solicitacao_id': conta.origin_id,
            'employee_id': employee.id if employee else None,
            'employee_name': employee.name if employee else 'N/A',
            'amount': float(conta.paid_amount),
            'payment_method': conta.payment_method,
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('Adiantamento pago com sucesso!', 'success')
    return redirect(url_for('rh.adiantamento'))


@rh_bp.route('/adiantamento/<int:id>/cancelar', methods=['POST'])
@login_required
@admin_required
def cancelar_adiantamento(id):
    """Cancelar adiantamento aprovado (ainda pendente de pagamento)"""
    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id,
        category='adiantamento',
        status='pending'
    ).first_or_404()

    solicitacao = SolicitacaoAdiantamento.query.get(conta.origin_id) if conta.origin_id else None
    if solicitacao:
        solicitacao.status = 'rejeitado'
        solicitacao.rejected_by = current_user.id
        solicitacao.rejected_at = datetime.utcnow()
        solicitacao.rejection_reason = 'Cancelado após aprovação'

    db.session.delete(conta)
    db.session.commit()

    flash('Adiantamento cancelado', 'info')
    return redirect(url_for('rh.adiantamento'))


# ============================================
# ROTAS FREELANCERS
# ============================================

@rh_bp.route('/freelancers')
@login_required
@admin_required
def freelancers():
    """Lista de freelancers"""
    freelancers = Freelancer.query.filter_by(
        company_id=current_user.company_id
    ).order_by(Freelancer.overall_score.desc()).all()

    return render_template('rh/freelancers.html', freelancers=freelancers)


@rh_bp.route('/freelancers/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_freelancer():
    """Novo freelancer"""
    if request.method == 'POST':
        try:
            freelancer = Freelancer(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                cpf=request.form.get('cpf', '').strip() or None,
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                specialty=request.form.get('specialty', '').strip(),
                daily_rate=Decimal(request.form.get('daily_rate', '0').replace(',', '.')),
                status='active',
                overall_score=Decimal('5.0')
            )

            db.session.add(freelancer)
            db.session.commit()

            flash('Freelancer cadastrado com sucesso!', 'success')
            return redirect(url_for('rh.freelancers'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar freelancer: {str(e)}', 'danger')

    return render_template('rh/freelancer_form.html', freelancer=None)


@rh_bp.route('/freelancers/<int:id>')
@login_required
@admin_required
def view_freelancer(id):
    """Visualizar freelancer"""
    freelancer = Freelancer.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    # Historico de trabalhos
    assignments = FreelancerAssignment.query.filter_by(
        freelancer_id=freelancer.id
    ).order_by(FreelancerAssignment.created_at.desc()).limit(10).all()

    # Avaliacoes
    reviews = FreelancerReview.query.filter_by(
        freelancer_id=freelancer.id
    ).order_by(FreelancerReview.created_at.desc()).limit(5).all()

    return render_template('rh/freelancer_view.html', 
                          freelancer=freelancer,
                          assignments=assignments,
                          reviews=reviews)


# ============================================
# ROTAS FOLHA DE PAGAMENTO
# ============================================

@rh_bp.route('/payroll')
@login_required
@admin_required
def payroll():
    """Lista de folhas de pagamento"""
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    entries = PayrollEntry.query.filter_by(
        company_id=current_user.company_id,
        reference_month=month,
        reference_year=year
    ).order_by(PayrollEntry.employee_id).all()

    # Totais
    total_liquido = sum(float(e.net_salary or 0) for e in entries)
    total_custo = sum(float(e.total_employer_cost or 0) for e in entries)
    total_pendente = len([e for e in entries if e.status == 'pending'])

    # Totais de encargos (para o template)
    total_inss = sum(
        float(e.inss_employee or 0) + float(e.inss_employer or 0) + 
        float(e.inss_rat or 0) + float(e.inss_terceiros or 0) 
        for e in entries
    )
    total_fgts = sum(float(e.fgts or 0) for e in entries)
    total_irrf = sum(float(e.irrf or 0) for e in entries)

    return render_template('rh/payroll.html',
                          entries=entries,
                          month=month,
                          year=year,
                          total_liquido=total_liquido,
                          total_custo=total_custo,
                          total_pendente=total_pendente,
                          total_inss=total_inss,
                          total_fgts=total_fgts,
                          total_irrf=total_irrf)


@rh_bp.route('/payroll/generate', methods=['POST'])
@login_required
@admin_required
def generate_payroll():
    """Gerar folhas do mes com calculo completo"""
    month = request.form.get('month', date.today().month, type=int)
    year = request.form.get('year', date.today().year, type=int)

    employees = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).all()

    created = 0
    for emp in employees:
        existing = PayrollEntry.query.filter_by(
            employee_id=emp.id,
            reference_month=month,
            reference_year=year
        ).first()

        if not existing:
            # Buscar adiantamentos do mes para descontar
            mes_ref = date(year, month, 1)
            mes_fim = (mes_ref + timedelta(days=32)).replace(day=1)

            adiantamentos = AccountPayable.query.filter(
                AccountPayable.company_id == current_user.company_id,
                AccountPayable.origin_type == 'adiantamento',
                AccountPayable.origin_id == emp.id,
                AccountPayable.category == 'adiantamento',
                AccountPayable.status == 'paid',
                AccountPayable.paid_at >= datetime.combine(mes_ref, datetime.min.time()),
                AccountPayable.paid_at < datetime.combine(mes_fim, datetime.min.time())
            ).all()

            total_adiantamentos = sum(float(a.paid_amount or 0) for a in adiantamentos)

            # Calcular holerite completo
            calc = calcular_holerite_completo(emp, advances=total_adiantamentos)

            entry = PayrollEntry(
                employee_id=emp.id,
                company_id=current_user.company_id,
                reference_month=month,
                reference_year=year,

                # Proventos
                base_salary=calc['base_salary'],
                overtime_hours=calc['overtime_hours'],
                overtime_amount=calc['overtime_amount'],
                bonuses=calc['bonuses'],
                gross_salary=calc['gross_salary'],

                # Descontos
                inss_employee=calc['inss_employee'],
                irrf=calc['irrf'],
                vt_discount=calc['vt_discount'],
                advances=calc['advances'],
                deductions=calc['deductions'],

                # Liquido
                net_salary=calc['net_salary'],

                # Encargos empresa
                inss_employer=calc['inss_employer'],
                inss_rat=calc['inss_rat'],
                inss_terceiros=calc['inss_terceiros'],
                fgts=calc['fgts'],

                # Provisoes
                provision_13th=calc['provision_13th'],
                provision_vacation=calc['provision_vacation'],
                provision_vacation_bonus=calc['provision_vacation_bonus'],
                provision_fgts_13th=calc['provision_fgts_13th'],
                provision_fgts_vacation=calc['provision_fgts_vacation'],
                total_provisions=calc['total_provisions'],

                # Beneficios
                vt_paid=calc['vt_paid'],
                vr_paid=calc['vr_paid'],
                va_paid=calc['va_paid'],
                health_paid=calc['health_paid'],

                # Custo total
                total_employer_cost=calc['total_employer_cost'],

                status='pending'
            )
            db.session.add(entry)
            created += 1

    db.session.commit()
    flash(f'{created} folhas geradas para {month}/{year} com encargos calculados', 'success')

    return redirect(url_for('rh.payroll', month=month, year=year))


@rh_bp.route('/payroll/<int:id>')
@login_required
@admin_required
def view_payroll(id):
    """Visualizar holerite completo"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('rh/payroll_view.html', entry=entry)


@rh_bp.route('/payroll/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_payroll(id):
    """Aprovar folha de pagamento"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    entry.status = 'approved'
    db.session.commit()

    # === EVENTBUS: PAYROLL_APPROVED (Listener cria AccountPayables) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.PAYROLL_APPROVED, {
            'payroll_id': entry.id,
            'employee_id': entry.employee_id,
            'employee_name': entry.employee.name if entry.employee else 'N/A',
            'net_salary': float(entry.net_salary or 0),
            'gross_salary': float(entry.gross_salary or 0),
            'inss_employee': float(entry.inss_employee or 0),
            'inss_employer': float(entry.inss_employer or 0),
            'inss_rat': float(entry.inss_rat or 0),
            'inss_terceiros': float(entry.inss_terceiros or 0),
            'fgts': float(entry.fgts or 0),
            'irrf': float(entry.irrf or 0),
            'reference_month': entry.reference_month,
            'reference_year': entry.reference_year,
            'company_id': current_user.company_id,
            'approved_by': current_user.id
        })
    except ImportError:
        pass

    flash('Folha aprovada!', 'success')
    return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))


@rh_bp.route('/payroll/<int:id>/pay', methods=['POST'])
@login_required
@admin_required
def pay_payroll(id):
    """Marcar folha como paga e integrar com financeiro"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    # Verificar se já está pago
    if entry.status == 'paid':
        flash('Esta folha já foi paga!', 'warning')
        return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))

    # Verificar se folha foi aprovada (AccountPayables devem existir)
    if entry.status != 'approved':
        flash('A folha precisa ser aprovada antes de ser paga!', 'warning')
        return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))

    entry.status = 'paid'
    entry.payment_date = date.today()
    entry.payment_method = request.form.get('method', 'transfer')

    db.session.commit()

    # === EVENTBUS: PAYROLL_PAID (listener cria AccountPayables) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.PAYROLL_PAID, {
            'payroll_id': entry.id,
            'employee_id': entry.employee_id,
            'employee_name': entry.employee.name if entry.employee else 'N/A',
            'reference_month': entry.reference_month,
            'reference_year': entry.reference_year,
            'net_salary': float(entry.net_salary or 0),
            'gross_salary': float(entry.gross_salary or 0),
            'total_employer_cost': float(entry.total_employer_cost or 0),
            'payment_method': entry.payment_method,
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('Pagamento registrado e integrado ao financeiro!', 'success')
    return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))


@rh_bp.route('/payroll/<int:id>/recalculate', methods=['POST'])
@login_required
@admin_required
def recalculate_payroll(id):
    """Recalcular holerite com novos valores"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if entry.status == 'paid':
        flash('Nao e possivel recalcular folha ja paga', 'danger')
        return redirect(url_for('rh.view_payroll', id=id))

    # Pegar valores do form
    overtime_hours = float(request.form.get('overtime_hours', '0').replace(',', '.') or '0')
    bonuses = float(request.form.get('bonuses', '0').replace(',', '.') or '0')
    advances = float(request.form.get('advances', '0').replace(',', '.') or '0')

    # Recalcular
    calc = calcular_holerite_completo(entry.employee, overtime_hours, bonuses, advances)

    # Atualizar entry
    entry.overtime_hours = calc['overtime_hours']
    entry.overtime_amount = calc['overtime_amount']
    entry.bonuses = calc['bonuses']
    entry.advances = calc['advances']
    entry.gross_salary = calc['gross_salary']
    entry.inss_employee = calc['inss_employee']
    entry.irrf = calc['irrf']
    entry.vt_discount = calc['vt_discount']
    entry.deductions = calc['deductions']
    entry.net_salary = calc['net_salary']
    entry.inss_employer = calc['inss_employer']
    entry.inss_rat = calc['inss_rat']
    entry.inss_terceiros = calc['inss_terceiros']
    entry.fgts = calc['fgts']
    entry.provision_13th = calc['provision_13th']
    entry.provision_vacation = calc['provision_vacation']
    entry.provision_vacation_bonus = calc['provision_vacation_bonus']
    entry.provision_fgts_13th = calc['provision_fgts_13th']
    entry.provision_fgts_vacation = calc['provision_fgts_vacation']
    entry.total_provisions = calc['total_provisions']
    entry.total_employer_cost = calc['total_employer_cost']

    db.session.commit()

    flash('Holerite recalculado com sucesso!', 'success')
    return redirect(url_for('rh.view_payroll', id=id))


# ============================================
# FUNCOES AUXILIARES
# ============================================

def _generate_employee_ranking(company_id, month, year):
    """Gera ranking de performance dos funcionarios"""
    employees = Employee.query.filter_by(
        company_id=company_id,
        status='active'
    ).all()

    ranking = []

    for emp in employees:
        payrolls_paid = PayrollEntry.query.filter_by(
            employee_id=emp.id,
            status='paid'
        ).count()

        score = min(100, payrolls_paid * 10 + 50)

        ranking.append({
            'employee': emp,
            'score': score,
            'payrolls_paid': payrolls_paid
        })

    ranking.sort(key=lambda x: x['score'], reverse=True)

    return ranking[:10]


# ============================================
# ROTAS DE TESTE - NOVOS TEMPLATES DE RECIBO
# ============================================

@rh_bp.route('/payroll/<int:id>/teste')
@login_required
@admin_required
def view_payroll_teste(id):
    """TESTE: Visualizar holerite com novo template modular"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('rh/recibos/holerite.html', entry=entry)


@rh_bp.route('/adiantamento/<int:id>/recibo')
@login_required
@admin_required
def recibo_adiantamento(id):
    """Visualizar recibo de adiantamento"""
    adiantamento = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id,
        category='adiantamento'
    ).first_or_404()

    # Buscar employee manualmente (AccountPayable nÃ£o tem relationship)
    employee = Employee.query.get(adiantamento.employee_id) if adiantamento.employee_id else None

    return render_template('rh/recibos/recibo_adiantamento.html', adiantamento=adiantamento, employee=employee)


# ============================================
# NOVAS CONSTANTES
# ============================================

SALARIO_MINIMO_2025 = Decimal('1518.00')
TETO_INSS_2025 = Decimal('951.63')


# ============================================
# NOVAS FUNCOES DE CALCULO - FERIAS
# ============================================

def calcular_ferias(employee, dias_gozo=30, dias_abono=0):
    """
    Calcula valores de ferias
    - dias_gozo: dias de ferias (minimo 5, maximo 30)
    - dias_abono: dias vendidos (maximo 10)
    """
    salario = Decimal(str(employee.salary))

    # Adicionar adicionais fixos ao salario base para calculo
    if hasattr(employee, 'adicional_periculosidade') and employee.adicional_periculosidade:
        salario += salario * (Decimal(str(employee.adicional_periculosidade)) / 100)
    if hasattr(employee, 'adicional_insalubridade_percent') and employee.adicional_insalubridade_percent:
        salario += SALARIO_MINIMO_2025 * (Decimal(str(employee.adicional_insalubridade_percent)) / 100)
    if hasattr(employee, 'adicional_funcao') and employee.adicional_funcao:
        salario += Decimal(str(employee.adicional_funcao))

    valor_dia = salario / 30

    # Ferias
    ferias = valor_dia * dias_gozo
    um_terco = ferias / 3

    # Abono pecuniario (venda de ferias)
    dias_abono = min(dias_abono, 10)
    abono = valor_dia * dias_abono
    abono_um_terco = abono / 3

    # Bruto total
    bruto = ferias + um_terco + abono + abono_um_terco

    # Descontos (INSS e IRRF sobre ferias + 1/3, NAO sobre abono)
    base_inss = ferias + um_terco
    inss = calcular_inss_funcionario(base_inss)
    irrf = calcular_irrf(base_inss - inss, getattr(employee, 'dependents_count', 0) or 0)

    liquido = bruto - inss - irrf

    return {
        'dias_gozo': dias_gozo,
        'dias_abono': dias_abono,
        'salario_base': Decimal(str(employee.salary)),
        'salario_calculo': salario.quantize(Decimal('0.01')),
        'valor_dia': valor_dia.quantize(Decimal('0.01')),
        'ferias': ferias.quantize(Decimal('0.01')),
        'um_terco': um_terco.quantize(Decimal('0.01')),
        'abono': abono.quantize(Decimal('0.01')),
        'abono_um_terco': abono_um_terco.quantize(Decimal('0.01')),
        'bruto': bruto.quantize(Decimal('0.01')),
        'inss': inss.quantize(Decimal('0.01')),
        'irrf': irrf.quantize(Decimal('0.01')),
        'liquido': liquido.quantize(Decimal('0.01'))
    }


# ============================================
# NOVAS FUNCOES DE CALCULO - 13o SALARIO
# ============================================

def calcular_13_salario(employee, meses_trabalhados=12, adiantamento_pago=Decimal('0')):
    """
    Calcula 13o salario
    - meses_trabalhados: meses no ano (1-12)
    - adiantamento_pago: valor ja pago na 1a parcela
    """
    salario = Decimal(str(employee.salary))

    # Adicionar adicionais fixos
    if hasattr(employee, 'adicional_periculosidade') and employee.adicional_periculosidade:
        salario += salario * (Decimal(str(employee.adicional_periculosidade)) / 100)
    if hasattr(employee, 'adicional_insalubridade_percent') and employee.adicional_insalubridade_percent:
        salario += SALARIO_MINIMO_2025 * (Decimal(str(employee.adicional_insalubridade_percent)) / 100)
    if hasattr(employee, 'adicional_funcao') and employee.adicional_funcao:
        salario += Decimal(str(employee.adicional_funcao))

    # Proporcional
    proporcional = salario * meses_trabalhados / 12

    # 1a parcela (50%, sem descontos)
    primeira_parcela = proporcional / 2

    # 2a parcela (50%, com descontos)
    segunda_parcela_bruta = proporcional - primeira_parcela

    # Descontos na 2a parcela (sobre total)
    inss = calcular_inss_funcionario(proporcional)
    irrf = calcular_irrf(proporcional - inss, getattr(employee, 'dependents_count', 0) or 0)

    segunda_parcela_liquida = segunda_parcela_bruta - inss - irrf

    # Descontar adiantamento se houver
    if adiantamento_pago > 0:
        segunda_parcela_liquida -= Decimal(str(adiantamento_pago))

    return {
        'meses_trabalhados': meses_trabalhados,
        'salario_base': Decimal(str(employee.salary)),
        'salario_calculo': salario.quantize(Decimal('0.01')),
        'proporcional': proporcional.quantize(Decimal('0.01')),
        'primeira_parcela': primeira_parcela.quantize(Decimal('0.01')),
        'segunda_parcela_bruta': segunda_parcela_bruta.quantize(Decimal('0.01')),
        'inss': inss.quantize(Decimal('0.01')),
        'irrf': irrf.quantize(Decimal('0.01')),
        'adiantamento': Decimal(str(adiantamento_pago)).quantize(Decimal('0.01')),
        'segunda_parcela_liquida': segunda_parcela_liquida.quantize(Decimal('0.01')),
        'total_bruto': proporcional.quantize(Decimal('0.01')),
        'total_liquido': (primeira_parcela + segunda_parcela_liquida).quantize(Decimal('0.01'))
    }


# ============================================
# NOVAS FUNCOES DE CALCULO - RESCISAO
# ============================================

def calcular_rescisao(employee, termination_type, termination_date, 
                      notice_type='indenizado', fgts_balance=Decimal('0')):
    """
    Calcula rescisao trabalhista

    termination_type: 
        - 'sem_justa_causa': demissao sem justa causa
        - 'justa_causa': demissao por justa causa
        - 'pedido_demissao': funcionario pediu demissao
        - 'acordo_mutuo': acordo entre partes (reforma trabalhista)

    notice_type:
        - 'indenizado': aviso previo indenizado
        - 'trabalhado': aviso previo trabalhado
        - 'dispensado': aviso previo dispensado pelo empregador
    """
    from dateutil.relativedelta import relativedelta

    salario = Decimal(str(employee.salary))

    # Adicionar adicionais fixos
    if hasattr(employee, 'adicional_periculosidade') and employee.adicional_periculosidade:
        salario += salario * (Decimal(str(employee.adicional_periculosidade)) / 100)
    if hasattr(employee, 'adicional_insalubridade_percent') and employee.adicional_insalubridade_percent:
        salario += SALARIO_MINIMO_2025 * (Decimal(str(employee.adicional_insalubridade_percent)) / 100)
    if hasattr(employee, 'adicional_funcao') and employee.adicional_funcao:
        salario += Decimal(str(employee.adicional_funcao))

    admission = employee.admission_date
    valor_dia = salario / 30

    # Tempo de servico
    delta = relativedelta(termination_date, admission)
    anos = delta.years
    meses_ano = termination_date.month
    dias_mes = termination_date.day

    # Aviso previo proporcional (30 dias + 3 dias por ano, max 90)
    dias_aviso = min(30 + (anos * 3), 90)

    # ========== VERBAS RESCISORIAS ==========

    # Saldo de salario
    saldo_salario = valor_dia * dias_mes

    # 13o proporcional (exceto justa causa)
    decimo_terceiro = Decimal('0')
    if termination_type != 'justa_causa':
        decimo_terceiro = salario / 12 * meses_ano

    # Aviso previo
    aviso_valor = Decimal('0')
    if termination_type == 'sem_justa_causa' and notice_type == 'indenizado':
        aviso_valor = valor_dia * dias_aviso
    elif termination_type == 'acordo_mutuo' and notice_type == 'indenizado':
        aviso_valor = (valor_dia * dias_aviso) / 2  # 50% no acordo

    # Ferias proporcionais (exceto justa causa)
    ferias_prop = Decimal('0')
    ferias_um_terco = Decimal('0')
    if termination_type != 'justa_causa':
        ultima_ferias = getattr(employee, 'ultima_ferias_fim', None) or admission
        meses_ferias = relativedelta(termination_date, ultima_ferias).months
        meses_ferias += relativedelta(termination_date, ultima_ferias).years * 12
        ferias_prop = salario / 12 * min(meses_ferias, 12)
        ferias_um_terco = ferias_prop / 3

    # Ferias vencidas
    ferias_vencidas = Decimal('0')
    ferias_vencidas_bonus = Decimal('0')
    if hasattr(employee, 'ferias_vencidas') and employee.ferias_vencidas:
        ferias_vencidas = salario
        ferias_vencidas_bonus = salario / 3

    # ========== FGTS ==========
    fgts_balance = Decimal(str(fgts_balance))
    fgts_multa = Decimal('0')
    fgts_percent = 0
    fgts_saque = Decimal('0')

    if termination_type == 'sem_justa_causa':
        fgts_multa = fgts_balance * Decimal('0.40')  # 40%
        fgts_percent = 40
        fgts_saque = fgts_balance
    elif termination_type == 'acordo_mutuo':
        fgts_multa = fgts_balance * Decimal('0.20')  # 20%
        fgts_percent = 20
        fgts_saque = fgts_balance * Decimal('0.80')  # Saca 80%

    # ========== TOTAIS ==========
    bruto = (saldo_salario + aviso_valor + decimo_terceiro + 
             ferias_vencidas + ferias_vencidas_bonus + 
             ferias_prop + ferias_um_terco)

    # Base INSS/IRRF (saldo + 13o + aviso trabalhado)
    base_inss = saldo_salario + decimo_terceiro
    if notice_type == 'trabalhado':
        base_inss += salario

    inss = calcular_inss_funcionario(base_inss)
    irrf = calcular_irrf(base_inss - inss, getattr(employee, 'dependents_count', 0) or 0)

    liquido = bruto - inss - irrf

    return {
        'termination_type': termination_type,
        'notice_type': notice_type,
        'admission_date': admission,
        'termination_date': termination_date,
        'anos_trabalhados': anos,
        'dias_aviso': dias_aviso,
        'salario_base': Decimal(str(employee.salary)),
        'salario_calculo': salario.quantize(Decimal('0.01')),
        'saldo_salario': saldo_salario.quantize(Decimal('0.01')),
        'aviso_previo': aviso_valor.quantize(Decimal('0.01')),
        'decimo_terceiro': decimo_terceiro.quantize(Decimal('0.01')),
        'ferias_vencidas': ferias_vencidas.quantize(Decimal('0.01')),
        'ferias_vencidas_bonus': ferias_vencidas_bonus.quantize(Decimal('0.01')),
        'ferias_proporcionais': ferias_prop.quantize(Decimal('0.01')),
        'ferias_um_terco': ferias_um_terco.quantize(Decimal('0.01')),
        'fgts_saldo': fgts_balance.quantize(Decimal('0.01')),
        'fgts_multa': fgts_multa.quantize(Decimal('0.01')),
        'fgts_percent': fgts_percent,
        'fgts_saque': fgts_saque.quantize(Decimal('0.01')),
        'inss': inss.quantize(Decimal('0.01')),
        'irrf': irrf.quantize(Decimal('0.01')),
        'bruto': bruto.quantize(Decimal('0.01')),
        'liquido': liquido.quantize(Decimal('0.01')),
        'tem_seguro_desemprego': termination_type == 'sem_justa_causa'
    }


# ============================================
# FUNCAO AUXILIAR - GERAR PERIODOS DE FERIAS
# ============================================

def _gerar_periodos_ferias(employee):
    """Gera periodos aquisitivos de ferias para funcionario"""
    try:
        from models.rh import VacationPeriod
    except ImportError:
        return  # VacationPeriod nao existe ainda

    if not employee.admission_date:
        return

    hoje = date.today()
    admission = employee.admission_date

    # Calcular quantos periodos aquisitivos completos
    anos = (hoje - admission).days // 365

    for i in range(anos + 1):
        acq_start = admission + timedelta(days=365 * i)
        acq_end = acq_start + timedelta(days=364)

        # Verificar se ja existe
        existing = VacationPeriod.query.filter_by(
            employee_id=employee.id,
            acquisition_start=acq_start
        ).first()

        if not existing and acq_end <= hoje:
            period = VacationPeriod(
                employee_id=employee.id,
                company_id=employee.company_id,
                acquisition_start=acq_start,
                acquisition_end=acq_end,
                concession_start=acq_end + timedelta(days=1),
                concession_end=acq_end + timedelta(days=365),
                status='pending'
            )
            db.session.add(period)

    try:
        db.session.commit()
    except:
        db.session.rollback()


# ============================================
# NOVAS ROTAS - FERIAS
# ============================================

@rh_bp.route('/ferias')
@login_required
@admin_required
def ferias_list():
    """Lista de ferias"""
    try:
        from models.rh import VacationPeriod
    except ImportError:
        flash('Modulo de ferias nao disponivel', 'warning')
        return redirect(url_for('rh.index'))

    status_filter = request.args.get('status', 'all')

    query = VacationPeriod.query.filter_by(company_id=current_user.company_id)

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    ferias = query.order_by(VacationPeriod.concession_end.asc()).all()

    # Estatisticas
    hoje = date.today()
    total_pendentes = VacationPeriod.query.filter_by(
        company_id=current_user.company_id, status='pending'
    ).count()

    total_vencidas = VacationPeriod.query.filter(
        VacationPeriod.company_id == current_user.company_id,
        VacationPeriod.status == 'pending',
        VacationPeriod.concession_end < hoje
    ).count()

    total_agendadas = VacationPeriod.query.filter_by(
        company_id=current_user.company_id, status='scheduled'
    ).count()

    return render_template('rh/ferias_list.html',
                          ferias=ferias,
                          status_filter=status_filter,
                          total_pendentes=total_pendentes,
                          total_vencidas=total_vencidas,
                          total_agendadas=total_agendadas)


@rh_bp.route('/ferias/<int:id>')
@login_required
@admin_required
def ferias_view(id):
    """Visualizar periodo de ferias"""
    try:
        from models.rh import VacationPeriod
    except ImportError:
        abort(404)

    ferias = VacationPeriod.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    # Calcular valores se ainda nao calculado
    if not ferias.net_value and ferias.employee:
        calc = calcular_ferias(ferias.employee, ferias.days_taken or 30, ferias.days_sold or 0)
        ferias.vacation_value = calc['ferias']
        ferias.bonus_value = calc['um_terco']
        ferias.sold_value = calc['abono']
        ferias.sold_bonus = calc['abono_um_terco']
        ferias.gross_value = calc['bruto']
        ferias.inss_discount = calc['inss']
        ferias.irrf_discount = calc['irrf']
        ferias.net_value = calc['liquido']

    return render_template('rh/ferias_view.html', ferias=ferias)


@rh_bp.route('/ferias/<int:id>/agendar', methods=['GET', 'POST'])
@login_required
@admin_required
def ferias_agendar(id):
    """Agendar ferias"""
    try:
        from models.rh import VacationPeriod
    except ImportError:
        abort(404)

    ferias = VacationPeriod.query.filter_by(
        id=id, company_id=current_user.company_id, status='pending'
    ).first_or_404()

    if request.method == 'POST':
        try:
            vacation_start = datetime.strptime(request.form.get('vacation_start'), '%Y-%m-%d').date()
            days_taken = int(request.form.get('days_taken', '30'))
            days_sold = int(request.form.get('days_sold', '0'))

            # Validacoes
            if days_taken < 5:
                flash('Minimo de 5 dias de ferias', 'danger')
                return redirect(url_for('rh.ferias_agendar', id=id))

            if days_taken + days_sold > 30:
                flash('Total de dias nao pode exceder 30', 'danger')
                return redirect(url_for('rh.ferias_agendar', id=id))

            if days_sold > 10:
                flash('Maximo de 10 dias podem ser vendidos', 'danger')
                return redirect(url_for('rh.ferias_agendar', id=id))

            # Calcular data fim
            vacation_end = vacation_start + timedelta(days=days_taken - 1)

            # Calcular valores
            calc = calcular_ferias(ferias.employee, days_taken, days_sold)

            # Atualizar periodo
            ferias.vacation_start = vacation_start
            ferias.vacation_end = vacation_end
            ferias.days_taken = days_taken
            ferias.days_sold = days_sold
            ferias.base_salary = ferias.employee.salary
            ferias.vacation_value = calc['ferias']
            ferias.bonus_value = calc['um_terco']
            ferias.sold_value = calc['abono']
            ferias.sold_bonus = calc['abono_um_terco']
            ferias.gross_value = calc['bruto']
            ferias.inss_discount = calc['inss']
            ferias.irrf_discount = calc['irrf']
            ferias.net_value = calc['liquido']
            ferias.payment_date = vacation_start - timedelta(days=2)  # 2 dias antes
            ferias.status = 'scheduled'

            db.session.commit()

            # === EVENTBUS: VACATION_APPROVED (listener cria AccountPayable pendente) ===
            try:
                from services.event_bus import EventBus, Events
                EventBus.emit(Events.VACATION_APPROVED, {
                    'vacation_id': ferias.id,
                    'employee_id': ferias.employee_id,
                    'employee_name': ferias.employee.name if ferias.employee else 'N/A',
                    'net_value': float(ferias.net_value or 0),
                    'payment_date': str(ferias.payment_date),
                    'company_id': current_user.company_id,
                    'approved_by': current_user.id
                })
            except ImportError:
                pass

            flash('Ferias agendadas com sucesso!', 'success')
            return redirect(url_for('rh.ferias_view', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao agendar ferias: {str(e)}', 'danger')

    return render_template('rh/ferias_form.html', ferias=ferias)


@rh_bp.route('/ferias/<int:id>/pagar', methods=['POST'])
@login_required
@admin_required
def ferias_pagar(id):
    """Pagar ferias"""
    try:
        from models.rh import VacationPeriod
    except ImportError:
        abort(404)

    ferias = VacationPeriod.query.filter_by(
        id=id, company_id=current_user.company_id, status='scheduled'
    ).first_or_404()

    ferias.status = 'paid'
    ferias.paid_at = datetime.utcnow()

    # Atualizar funcionario
    ferias.employee.ultima_ferias_inicio = ferias.vacation_start
    ferias.employee.ultima_ferias_fim = ferias.vacation_end

    db.session.commit()

    # === EVENTBUS: VACATION_PAID (listener cria AccountPayable) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.VACATION_PAID, {
            'vacation_id': ferias.id,
            'employee_id': ferias.employee_id,
            'employee_name': ferias.employee.name if ferias.employee else 'N/A',
            'days_taken': ferias.days_taken,
            'days_sold': ferias.days_sold,
            'vacation_start': str(ferias.vacation_start),
            'vacation_end': str(ferias.vacation_end),
            'net_value': float(ferias.net_value or 0),
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('Ferias pagas com sucesso!', 'success')
    return redirect(url_for('rh.ferias_view', id=id))


# ============================================
# NOVAS ROTAS - 13o SALARIO
# ============================================

@rh_bp.route('/decimo-terceiro')
@login_required
@admin_required
def decimo_terceiro_list():
    """Lista de 13o salario"""
    try:
        from models.rh import ThirteenthSalary
    except ImportError:
        flash('Modulo de 13o nao disponivel', 'warning')
        return redirect(url_for('rh.index'))

    year = request.args.get('year', date.today().year, type=int)

    entries = ThirteenthSalary.query.filter_by(
        company_id=current_user.company_id,
        reference_year=year
    ).all()

    # Totais
    total_primeira = sum(float(e.first_installment_value or 0) for e in entries)
    total_segunda = sum(float(e.second_installment_net or 0) for e in entries)
    pendentes = len([e for e in entries if e.status == 'pending'])

    return render_template('rh/decimo_terceiro_list.html',
                          entries=entries,
                          year=year,
                          total_primeira=total_primeira,
                          total_segunda=total_segunda,
                          pendentes=pendentes)


@rh_bp.route('/decimo-terceiro/gerar', methods=['POST'])
@login_required
@admin_required
def decimo_terceiro_gerar():
    """Gerar 13o para todos funcionarios"""
    try:
        from models.rh import ThirteenthSalary
    except ImportError:
        flash('Modulo de 13o nao disponivel', 'warning')
        return redirect(url_for('rh.index'))

    year = request.form.get('year', date.today().year, type=int)

    employees = Employee.query.filter_by(
        company_id=current_user.company_id, status='active'
    ).all()

    created = 0
    for emp in employees:
        existing = ThirteenthSalary.query.filter_by(
            employee_id=emp.id, reference_year=year
        ).first()

        if not existing:
            # Calcular meses trabalhados no ano
            if emp.admission_date and emp.admission_date.year == year:
                meses = 13 - emp.admission_date.month
            else:
                meses = 12

            calc = calcular_13_salario(emp, meses)

            entry = ThirteenthSalary(
                employee_id=emp.id,
                company_id=current_user.company_id,
                reference_year=year,
                months_worked=meses,
                base_salary=emp.salary,
                first_installment_value=calc['primeira_parcela'],
                second_installment_gross=calc['segunda_parcela_bruta'],
                second_installment_inss=calc['inss'],
                second_installment_irrf=calc['irrf'],
                second_installment_net=calc['segunda_parcela_liquida'],
                total_gross=calc['total_bruto'],
                total_inss=calc['inss'],
                total_irrf=calc['irrf'],
                total_net=calc['total_liquido'],
                status='pending',
                created_by=current_user.id
            )
            db.session.add(entry)
            db.session.flush()

            # === EVENTBUS: THIRTEENTH_APPROVED (listener cria 2 AccountPayables pendentes) ===
            try:
                from services.event_bus import EventBus, Events
                EventBus.emit(Events.THIRTEENTH_APPROVED, {
                    'thirteenth_id': entry.id,
                    'employee_id': emp.id,
                    'employee_name': emp.name,
                    'reference_year': year,
                    'first_installment_value': float(entry.first_installment_value or 0),
                    'second_installment_net': float(entry.second_installment_net or 0),
                    'company_id': current_user.company_id,
                    'created_by': current_user.id
                })
            except ImportError:
                pass

            created += 1

    db.session.commit()
    flash(f'{created} registros de 13o gerados!', 'success')
    return redirect(url_for('rh.decimo_terceiro_list', year=year))


@rh_bp.route('/decimo-terceiro/<int:id>/pagar-primeira', methods=['POST'])
@login_required
@admin_required
def decimo_terceiro_pagar_primeira(id):
    """Pagar 1a parcela do 13o"""
    try:
        from models.rh import ThirteenthSalary
    except ImportError:
        abort(404)

    entry = ThirteenthSalary.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    if entry.first_installment_paid:
        flash('1a parcela ja foi paga!', 'warning')
        return redirect(url_for('rh.decimo_terceiro_list', year=entry.reference_year))

    entry.first_installment_paid = True
    entry.first_installment_paid_at = datetime.utcnow()
    entry.first_installment_date = date.today()
    entry.first_installment_method = request.form.get('method', 'transfer')
    entry.status = 'first_paid'

    db.session.commit()

    # === EVENTBUS: THIRTEENTH_FIRST_PAID (listener cria AccountPayable) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.THIRTEENTH_FIRST_PAID, {
            'thirteenth_id': entry.id,
            'employee_id': entry.employee_id,
            'employee_name': entry.employee.name if entry.employee else 'N/A',
            'reference_year': entry.reference_year,
            'amount': float(entry.first_installment_value or 0),
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('1a parcela do 13o paga!', 'success')
    return redirect(url_for('rh.decimo_terceiro_list', year=entry.reference_year))


@rh_bp.route('/decimo-terceiro/<int:id>/pagar-segunda', methods=['POST'])
@login_required
@admin_required
def decimo_terceiro_pagar_segunda(id):
    """Pagar 2a parcela do 13o"""
    try:
        from models.rh import ThirteenthSalary
    except ImportError:
        abort(404)

    entry = ThirteenthSalary.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    if entry.second_installment_paid:
        flash('2a parcela ja foi paga!', 'warning')
        return redirect(url_for('rh.decimo_terceiro_list', year=entry.reference_year))

    entry.second_installment_paid = True
    entry.second_installment_paid_at = datetime.utcnow()
    entry.second_installment_date = date.today()
    entry.second_installment_method = request.form.get('method', 'transfer')
    entry.status = 'completed'

    db.session.commit()

    # === EVENTBUS: THIRTEENTH_SECOND_PAID (listener cria AccountPayable) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.THIRTEENTH_SECOND_PAID, {
            'thirteenth_id': entry.id,
            'employee_id': entry.employee_id,
            'employee_name': entry.employee.name if entry.employee else 'N/A',
            'reference_year': entry.reference_year,
            'amount': float(entry.second_installment_net or 0),
            'total_paid': float((entry.first_installment_value or 0) + (entry.second_installment_net or 0)),
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('2a parcela do 13o paga!', 'success')
    return redirect(url_for('rh.decimo_terceiro_list', year=entry.reference_year))


# ============================================
# NOVAS ROTAS - RESCISAO
# ============================================

@rh_bp.route('/rescisoes')
@login_required
@admin_required
def rescisoes_list():
    """Lista de rescisoes"""
    try:
        from models.rh import Termination
    except ImportError:
        flash('Modulo de rescisao nao disponivel', 'warning')
        return redirect(url_for('rh.index'))

    rescisoes = Termination.query.filter_by(
        company_id=current_user.company_id
    ).order_by(Termination.created_at.desc()).all()

    return render_template('rh/rescisoes_list.html', rescisoes=rescisoes)


@rh_bp.route('/rescisoes/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def rescisao_nova():
    """Nova rescisao"""
    try:
        from models.rh import Termination
    except ImportError:
        flash('Modulo de rescisao nao disponivel', 'warning')
        return redirect(url_for('rh.index'))

    employees = Employee.query.filter_by(
        company_id=current_user.company_id, status='active'
    ).order_by(Employee.name).all()

    if request.method == 'POST':
        try:
            employee_id = int(request.form.get('employee_id'))
            employee = Employee.query.filter_by(
                id=employee_id, company_id=current_user.company_id
            ).first_or_404()

            termination_date = datetime.strptime(
                request.form.get('termination_date'), '%Y-%m-%d'
            ).date()
            termination_type = request.form.get('termination_type')
            notice_type = request.form.get('notice_type', 'indenizado')
            fgts_balance = Decimal(
                request.form.get('fgts_balance', '0').replace(',', '.') or '0'
            )

            # Calcular rescisao
            calc = calcular_rescisao(
                employee, termination_type, termination_date, 
                notice_type, fgts_balance
            )

            rescisao = Termination(
                employee_id=employee.id,
                company_id=current_user.company_id,
                termination_date=termination_date,
                termination_type=termination_type,
                notice_type=notice_type,
                notice_days=calc['dias_aviso'],
                base_salary=employee.salary,
                admission_date=employee.admission_date,
                years_worked=calc['anos_trabalhados'],
                salary_balance=calc['saldo_salario'],
                notice_value=calc['aviso_previo'],
                thirteenth_prop=calc['decimo_terceiro'],
                vacation_overdue=calc['ferias_vencidas'],
                vacation_overdue_bonus=calc['ferias_vencidas_bonus'],
                vacation_prop=calc['ferias_proporcionais'],
                vacation_prop_bonus=calc['ferias_um_terco'],
                gross_total=calc['bruto'],
                inss_discount=calc['inss'],
                irrf_discount=calc['irrf'],
                fgts_balance=fgts_balance,
                fgts_fine=calc['fgts_multa'],
                fgts_fine_percent=calc['fgts_percent'],
                fgts_total_withdraw=calc['fgts_saque'],
                net_total=calc['liquido'],
                seguro_desemprego=calc['tem_seguro_desemprego'],
                status='calculated',
                reason=request.form.get('reason', '').strip() or None,
                created_by=current_user.id
            )

            db.session.add(rescisao)
            db.session.commit()

            flash('Rescisao calculada com sucesso!', 'success')
            return redirect(url_for('rh.rescisao_view', id=rescisao.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar rescisao: {str(e)}', 'danger')

    return render_template('rh/rescisao_form.html', employees=employees, rescisao=None)


@rh_bp.route('/rescisoes/<int:id>')
@login_required
@admin_required
def rescisao_view(id):
    """Visualizar rescisao"""
    try:
        from models.rh import Termination
    except ImportError:
        abort(404)

    rescisao = Termination.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    return render_template('rh/rescisao_view.html', rescisao=rescisao)


@rh_bp.route('/rescisoes/<int:id>/aprovar', methods=['POST'])
@login_required
@admin_required
def rescisao_aprovar(id):
    """Aprovar rescisao"""
    try:
        from models.rh import Termination
    except ImportError:
        abort(404)

    rescisao = Termination.query.filter_by(
        id=id, company_id=current_user.company_id, status='calculated'
    ).first_or_404()

    rescisao.status = 'approved'
    rescisao.approved_by = current_user.id
    rescisao.approved_at = datetime.utcnow()

    db.session.commit()

    # === EVENTBUS: TERMINATION_APPROVED (listener cria AccountPayable pendente) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.TERMINATION_APPROVED, {
            'termination_id': rescisao.id,
            'employee_id': rescisao.employee_id,
            'employee_name': rescisao.employee.name if rescisao.employee else 'N/A',
            'net_total': float(rescisao.net_total or 0),
            'fgts_fine': float(rescisao.fgts_fine or 0),
            'termination_date': str(rescisao.termination_date),
            'company_id': current_user.company_id,
            'approved_by': current_user.id
        })
    except ImportError:
        pass

    flash('Rescisao aprovada!', 'success')
    return redirect(url_for('rh.rescisao_view', id=id))


@rh_bp.route('/rescisoes/<int:id>/pagar', methods=['POST'])
@login_required
@admin_required
def rescisao_pagar(id):
    """Pagar rescisao"""
    try:
        from models.rh import Termination
    except ImportError:
        abort(404)

    rescisao = Termination.query.filter_by(
        id=id, company_id=current_user.company_id, status='approved'
    ).first_or_404()

    rescisao.status = 'paid'
    rescisao.payment_date = date.today()
    rescisao.payment_method = request.form.get('method', 'transfer')
    rescisao.paid_at = datetime.utcnow()

    # Inativar funcionario
    rescisao.employee.status = 'inactive'
    rescisao.employee.dismissal_date = rescisao.termination_date

    db.session.commit()

    # === EVENTBUS: TERMINATION_PAID (listener cria AccountPayable) ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.TERMINATION_PAID, {
            'termination_id': rescisao.id,
            'employee_id': rescisao.employee_id,
            'employee_name': rescisao.employee.name if rescisao.employee else 'N/A',
            'termination_type': rescisao.termination_type,
            'termination_date': str(rescisao.termination_date),
            'net_total': float(rescisao.net_total or 0),
            'fgts_fine': float(rescisao.fgts_fine or 0),
            'years_worked': rescisao.years_worked,
            'company_id': current_user.company_id,
            'paid_by': current_user.id
        })
    except ImportError:
        pass

    flash('Rescisao paga e funcionario desligado!', 'success')
    return redirect(url_for('rh.rescisao_view', id=id))


# ============================================
# RELATORIO CUSTO TOTAL POR FUNCIONARIO
# ============================================

@rh_bp.route('/relatorio/custo-funcionario')
@login_required
@admin_required
def relatorio_custo_funcionario():
    """Relatorio completo de custo total por funcionario"""
    from sqlalchemy import func
    from dateutil.relativedelta import relativedelta

    employees = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Employee.name).all()

    # Periodo de analise (ultimos 12 meses)
    hoje = date.today()
    inicio_periodo = (hoje - relativedelta(months=12)).replace(day=1)

    relatorio = []
    totais = {
        'salarios': Decimal('0'),
        'inss_patronal': Decimal('0'),
        'fgts': Decimal('0'),
        'provisao_ferias': Decimal('0'),
        'provisao_13': Decimal('0'),
        'beneficios': Decimal('0'),
        'custo_total': Decimal('0')
    }

    for emp in employees:
        salario = Decimal(str(emp.salary or 0))

        # Calcular encargos mensais
        inss_patronal = salario * Decimal('0.20')  # 20% INSS patronal
        fgts = salario * Decimal('0.08')  # 8% FGTS

        # Provisoes mensais (1/12 do salario + encargos)
        provisao_ferias = (salario + (salario / Decimal('3'))) / Decimal('12')  # 1/12 de salario + 1/3
        provisao_13 = salario / Decimal('12')  # 1/12 do 13o

        # Beneficios (usando campos corretos do modelo)
        vale_transporte = Decimal(str(emp.vt_value or 0))
        vale_alimentacao = Decimal(str(emp.va_value or 0)) + Decimal(str(emp.vr_value or 0))
        plano_saude = Decimal(str(emp.health_insurance or 0))
        outros_beneficios = Decimal(str(emp.other_benefits or 0))
        total_beneficios = vale_transporte + vale_alimentacao + plano_saude + outros_beneficios

        # Custo total mensal
        custo_mensal = salario + inss_patronal + fgts + provisao_ferias + provisao_13 + total_beneficios

        # Buscar folhas pagas no periodo (Ãºltimos 12 meses)
        folhas_pagas = PayrollEntry.query.filter(
            PayrollEntry.employee_id == emp.id,
            PayrollEntry.company_id == current_user.company_id,
            PayrollEntry.status == 'paid',
            PayrollEntry.payment_date >= inicio_periodo,
            PayrollEntry.payment_date <= hoje
        ).count()

        # Buscar total pago em folhas no perÃ­odo
        total_pago_folhas = db.session.query(func.coalesce(func.sum(PayrollEntry.net_salary), 0)).filter(
            PayrollEntry.employee_id == emp.id,
            PayrollEntry.company_id == current_user.company_id,
            PayrollEntry.status == 'paid',
            PayrollEntry.payment_date >= inicio_periodo,
            PayrollEntry.payment_date <= hoje
        ).scalar() or Decimal('0')

        # Buscar adiantamentos pagos (origin_type=adiantamento usa employee.id em origin_id)
        adiantamentos_pagos = db.session.query(func.coalesce(func.sum(AccountPayable.amount), 0)).filter(
            AccountPayable.company_id == current_user.company_id,
            AccountPayable.origin_type == 'adiantamento',
            AccountPayable.origin_id == emp.id,
            AccountPayable.status == 'paid',
            AccountPayable.paid_at >= inicio_periodo
        ).scalar() or Decimal('0')

        item = {
            'funcionario': emp,
            'salario': salario,
            'inss_patronal': inss_patronal,
            'fgts': fgts,
            'provisao_ferias': provisao_ferias,
            'provisao_13': provisao_13,
            'beneficios': total_beneficios,
            'custo_mensal': custo_mensal,
            'custo_anual': custo_mensal * 12,
            'folhas_pagas': folhas_pagas,
            'total_pago_periodo': total_pago_folhas,
            'adiantamentos_periodo': adiantamentos_pagos
        }

        relatorio.append(item)

        # Acumular totais
        totais['salarios'] += salario
        totais['inss_patronal'] += inss_patronal
        totais['fgts'] += fgts
        totais['provisao_ferias'] += provisao_ferias
        totais['provisao_13'] += provisao_13
        totais['beneficios'] += total_beneficios
        totais['custo_total'] += custo_mensal

    return render_template('rh/relatorio_custo_funcionario.html',
                          relatorio=relatorio,
                          totais=totais,
                          periodo_inicio=inicio_periodo,
                          periodo_fim=hoje)