from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from services.automation_service import AutomationService

automation_api = Blueprint('automation_api', __name__, url_prefix='/api/automation')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        return f(*args, **kwargs)
    return decorated_function


@automation_api.route('/quote/<int:quote_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_quote(quote_id):
    result = AutomationService.approve_quote(quote_id, current_user.company_id)
    return jsonify(result)


@automation_api.route('/quote/<int:quote_id>/contract', methods=['POST'])
@login_required
@admin_required
def create_contract_from_quote(quote_id):
    result = AutomationService.create_contract_from_quote(
        quote_id, 
        current_user.company_id, 
        current_user.id
    )
    return jsonify(result)


@automation_api.route('/quote/<int:quote_id>/receivables', methods=['POST'])
@login_required
@admin_required
def create_receivables_from_quote(quote_id):
    data = request.get_json() or {}
    installments = int(data.get('installments', 1))
    first_due_date = data.get('first_due_date')
    
    result = AutomationService.create_receivables_from_quote(
        quote_id,
        current_user.company_id,
        current_user.id,
        installments=installments,
        first_due_date=first_due_date
    )
    return jsonify(result)


@automation_api.route('/employee/<int:employee_id>/auto-expenses', methods=['POST'])
@login_required
@admin_required
def create_employee_auto_expenses(employee_id):
    data = request.get_json() or {}
    
    result = AutomationService.create_employee_auto_expenses(
        employee_id,
        current_user.company_id,
        current_user.id,
        auto_salary=data.get('auto_salary', True),
        auto_benefits=data.get('auto_benefits', False),
        vt_value=data.get('vt_value', 0),
        vr_value=data.get('vr_value', 0)
    )
    return jsonify(result)


@automation_api.route('/freelancer/<int:freelancer_id>/payable', methods=['POST'])
@login_required
@admin_required
def create_freelancer_payable(freelancer_id):
    data = request.get_json() or {}
    
    result = AutomationService.create_freelancer_payable(
        freelancer_id,
        current_user.company_id,
        current_user.id,
        value=data.get('value', 0),
        event_name=data.get('event_name', ''),
        payment_date=data.get('payment_date')
    )
    return jsonify(result)


@automation_api.route('/vehicle/installments', methods=['POST'])
@login_required
@admin_required
def create_vehicle_installments():
    data = request.get_json() or {}
    
    result = AutomationService.create_vehicle_installments(
        data.get('vehicle_id'),
        current_user.company_id,
        current_user.id,
        total_value=data.get('total_value', 0),
        installments=int(data.get('installments', 1)),
        first_due_date=data.get('first_due_date')
    )
    return jsonify(result)


@automation_api.route('/quote/<int:quote_id>/worklist', methods=['POST'])
@login_required
@admin_required
def create_worklist_from_quote(quote_id):
    """Cria WorkList a partir do orçamento aprovado (sem preços)"""
    data = request.get_json() or {}
    
    result = AutomationService.create_worklist_from_quote(
        quote_id,
        current_user.company_id,
        current_user.id,
        event_date=data.get('event_date'),
        event_location=data.get('event_location'),
        assigned_to=data.get('assigned_to')
    )
    return jsonify(result)


@automation_api.route('/quote/<int:quote_id>/create-event', methods=['POST'])
@login_required
@admin_required
def create_event_from_quote(quote_id):
    """Cria evento/tour a partir do orçamento aprovado"""
    data = request.get_json() or {}
    
    result = AutomationService.create_event_from_quote(
        quote_id,
        current_user.company_id,
        current_user.id,
        name=data.get('name'),
        artist=data.get('artist'),
        start_date=data.get('start_date')
    )
    return jsonify(result)
