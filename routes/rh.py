"""
Routes para modulo RH
- Dashboard com ranking de funcionarios
- Gestao de CLT
- Gestao de Freelancers
- Folhas de pagamento
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.rh import Employee, Freelancer, FreelancerAssignment, FreelancerReview, PayrollEntry
from datetime import datetime, date, timedelta
from decimal import Decimal

rh_bp = Blueprint('rh', __name__, url_prefix='/rh')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@rh_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard RH com ranking e KPIs"""
    employees = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).all()
    
    freelancers = Freelancer.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Freelancer.overall_score.desc()).all()
    
    current_month = date.today().month
    current_year = date.today().year
    
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
    
    ranking = _generate_employee_ranking(current_user.company_id, current_month, current_year)
    
    return render_template('rh/index.html',
                          employees=employees,
                          freelancers=freelancers,
                          payroll_total=payroll_total,
                          pending_payrolls=pending_payrolls,
                          ranking=ranking,
                          current_month=current_month,
                          current_year=current_year)


@rh_bp.route('/employees')
@login_required
@admin_required
def employees():
    """Lista de funcionarios CLT"""
    employees = Employee.query.filter_by(
        company_id=current_user.company_id
    ).order_by(Employee.name).all()
    
    return render_template('rh/employees.html', employees=employees)


@rh_bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_employee():
    """Cadastrar novo funcionario CLT"""
    if request.method == 'POST':
        try:
            admission_date_str = request.form.get('admission_date', '')
            admission_date = datetime.strptime(admission_date_str, '%Y-%m-%d').date() if admission_date_str else date.today()
            
            birth_date = None
            birth_date_str = request.form.get('birth_date', '')
            if birth_date_str:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            
            employee = Employee(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                cpf=request.form.get('cpf', '').strip() or None,
                rg=request.form.get('rg', '').strip() or None,
                birth_date=birth_date,
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                address=request.form.get('address', '').strip() or None,
                position=request.form.get('position', '').strip(),
                department=request.form.get('department', '').strip() or None,
                admission_date=admission_date,
                salary=Decimal(request.form.get('salary', '0').replace(',', '.')),
                salary_type='monthly',
                status='active'
            )
            
            db.session.add(employee)
            db.session.commit()
            
            flash(f'Funcionario "{employee.name}" cadastrado com sucesso!', 'success')
            return redirect(url_for('rh.employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar funcionario: {str(e)}', 'danger')
    
    return render_template('rh/employee_form.html', employee=None)


@rh_bp.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(id):
    """Editar funcionario"""
    employee = Employee.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            employee.name = request.form.get('name', '').strip()
            employee.cpf = request.form.get('cpf', '').strip() or None
            employee.rg = request.form.get('rg', '').strip() or None
            employee.email = request.form.get('email', '').strip() or None
            employee.phone = request.form.get('phone', '').strip() or None
            employee.address = request.form.get('address', '').strip() or None
            employee.position = request.form.get('position', '').strip()
            employee.department = request.form.get('department', '').strip() or None
            employee.salary = Decimal(request.form.get('salary', '0').replace(',', '.'))
            employee.status = request.form.get('status', 'active')
            
            birth_date_str = request.form.get('birth_date', '')
            if birth_date_str:
                employee.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            
            employee.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Funcionario atualizado com sucesso!', 'success')
            return redirect(url_for('rh.employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar funcionario: {str(e)}', 'danger')
    
    return render_template('rh/employee_form.html', employee=employee)


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
    """Cadastrar novo freelancer"""
    if request.method == 'POST':
        try:
            freelancer = Freelancer(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                cpf_cnpj=request.form.get('cpf_cnpj', '').strip() or None,
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                role=request.form.get('role', '').strip() or None,
                hourly_rate=Decimal(request.form.get('hourly_rate', '0').replace(',', '.')) if request.form.get('hourly_rate') else None,
                daily_rate=Decimal(request.form.get('daily_rate', '0').replace(',', '.')) if request.form.get('daily_rate') else None,
                notes=request.form.get('notes', '').strip() or None,
                status='active',
                performance_score=50,
                reliability_score=50,
                technical_score=50,
                overall_score=50
            )
            
            db.session.add(freelancer)
            db.session.commit()
            
            flash(f'Freelancer "{freelancer.name}" cadastrado com sucesso!', 'success')
            return redirect(url_for('rh.freelancers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar freelancer: {str(e)}', 'danger')
    
    return render_template('rh/freelancer_form.html', freelancer=None)


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
    ).all()
    
    total = sum(e.net_salary for e in entries if e.net_salary)
    
    return render_template('rh/payroll.html',
                          entries=entries,
                          month=month,
                          year=year,
                          total=total)


@rh_bp.route('/payroll/generate', methods=['POST'])
@login_required
@admin_required
def generate_payroll():
    """Gerar folhas do mes"""
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
            entry = PayrollEntry(
                employee_id=emp.id,
                company_id=current_user.company_id,
                reference_month=month,
                reference_year=year,
                base_salary=emp.salary,
                overtime_hours=Decimal('0'),
                overtime_amount=Decimal('0'),
                bonuses=Decimal('0'),
                deductions=Decimal('0'),
                net_salary=emp.salary,
                status='pending'
            )
            db.session.add(entry)
            created += 1
    
    db.session.commit()
    flash(f'{created} folhas geradas para {month}/{year}', 'success')
    
    return redirect(url_for('rh.payroll', month=month, year=year))


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
    entry.approved_by = current_user.id
    db.session.commit()
    
    flash('Folha aprovada!', 'success')
    return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))


@rh_bp.route('/payroll/<int:id>/pay', methods=['POST'])
@login_required
@admin_required
def pay_payroll(id):
    """Marcar folha como paga"""
    entry = PayrollEntry.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    entry.status = 'paid'
    entry.payment_date = date.today()
    entry.payment_method = request.form.get('method', 'transfer')
    db.session.commit()
    
    flash('Pagamento registrado!', 'success')
    return redirect(url_for('rh.payroll', month=entry.reference_month, year=entry.reference_year))


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
