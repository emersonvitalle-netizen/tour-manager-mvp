"""
Audit Listeners - Registra eventos para auditoria e historico

Todos os eventos importantes sao logados para:
- Rastreabilidade
- Compliance
- Debug
- Relatorios
"""

from services.event_bus import EventBus, Events
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


# ============================================
# AUDIT LOG HELPER
# ============================================

def audit_log(event_type: str, data: dict, user_id: int = None):
    """
    Registra evento no log de auditoria

    Futuramente pode salvar em:
    - Tabela AuditLog no banco
    - Elasticsearch
    - CloudWatch
    - Arquivo de log separado
    """
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event': event_type,
        'user_id': user_id,
        'data': data
    }

    # Por enquanto loga como JSON
    logger.info(f"[AUDIT] {json.dumps(log_entry, ensure_ascii=False, default=str)}")

    return log_entry


# ============================================
# AUDITORIA DE RH
# ============================================

@EventBus.on(Events.EMPLOYEE_HIRED)
def audit_employee_hired(data):
    """Audita contratacao de funcionario"""
    return audit_log('EMPLOYEE_HIRED', {
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'position': data.get('position'),
        'salary': data.get('salary'),
        'admission_date': data.get('admission_date')
    }, data.get('created_by'))


@EventBus.on(Events.EMPLOYEE_FIRED)
def audit_employee_fired(data):
    """Audita desligamento de funcionario"""
    return audit_log('EMPLOYEE_FIRED', {
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'termination_type': data.get('termination_type'),
        'termination_date': data.get('termination_date'),
        'total_value': data.get('total_value')
    }, data.get('approved_by'))


@EventBus.on(Events.PAYROLL_PAID)
def audit_payroll_paid(data):
    """Audita pagamento de folha"""
    return audit_log('PAYROLL_PAID', {
        'payroll_id': data.get('payroll_id'),
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'reference_month': data.get('reference_month'),
        'reference_year': data.get('reference_year'),
        'gross_salary': data.get('gross_salary'),
        'net_salary': data.get('net_salary'),
        'inss': data.get('inss'),
        'irrf': data.get('irrf'),
        'fgts': data.get('fgts')
    }, data.get('paid_by'))


@EventBus.on(Events.VACATION_PAID)
def audit_vacation_paid(data):
    """Audita pagamento de ferias"""
    return audit_log('VACATION_PAID', {
        'vacation_id': data.get('vacation_id'),
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'days_taken': data.get('days_taken'),
        'days_sold': data.get('days_sold'),
        'total_value': data.get('total_value')
    }, data.get('paid_by'))


@EventBus.on(Events.TERMINATION_PAID)
def audit_termination_paid(data):
    """Audita pagamento de rescisao"""
    return audit_log('TERMINATION_PAID', {
        'termination_id': data.get('termination_id'),
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'termination_type': data.get('termination_type'),
        'total_value': data.get('total_value'),
        'fgts_fine': data.get('fgts_fine')
    }, data.get('paid_by'))


# ============================================
# AUDITORIA FINANCEIRA
# ============================================

@EventBus.on(Events.PAYMENT_RECEIVED)
def audit_payment_received(data):
    """Audita recebimento de pagamento"""
    return audit_log('PAYMENT_RECEIVED', {
        'payment_id': data.get('payment_id'),
        'invoice_id': data.get('invoice_id'),
        'client_name': data.get('client_name'),
        'amount': data.get('amount'),
        'payment_method': data.get('payment_method'),
        'transaction_id': data.get('transaction_id')
    })


@EventBus.on(Events.INVOICE_CREATED)
def audit_invoice_created(data):
    """Audita criacao de fatura"""
    return audit_log('INVOICE_CREATED', {
        'invoice_id': data.get('invoice_id'),
        'invoice_code': data.get('invoice_code'),
        'client_name': data.get('client_name'),
        'total_amount': data.get('total_amount')
    }, data.get('created_by'))


@EventBus.on(Events.NFSE_EMITTED)
def audit_nfse_emitted(data):
    """Audita emissao de NFSe"""
    return audit_log('NFSE_EMITTED', {
        'nfse_id': data.get('nfse_id'),
        'nfse_number': data.get('nfse_number'),
        'invoice_id': data.get('invoice_id'),
        'value': data.get('value'),
        'service_description': data.get('service_description')
    }, data.get('emitted_by'))


# ============================================
# AUDITORIA COMERCIAL
# ============================================

@EventBus.on(Events.QUOTE_CREATED)
def audit_quote_created(data):
    """Audita criacao de orcamento"""
    return audit_log('QUOTE_CREATED', {
        'quote_id': data.get('quote_id'),
        'client_name': data.get('client_name'),
        'event_name': data.get('event_name'),
        'total_value': data.get('total_value')
    }, data.get('created_by'))


@EventBus.on(Events.QUOTE_APPROVED)
def audit_quote_approved(data):
    """Audita aprovacao de orcamento"""
    return audit_log('QUOTE_APPROVED', {
        'quote_id': data.get('quote_id'),
        'client_name': data.get('client_name'),
        'total_value': data.get('total_value'),
        'signal_amount': data.get('signal_amount')
    }, data.get('approved_by'))


@EventBus.on(Events.QUOTE_REJECTED)
def audit_quote_rejected(data):
    """Audita rejeicao de orcamento"""
    return audit_log('QUOTE_REJECTED', {
        'quote_id': data.get('quote_id'),
        'client_name': data.get('client_name'),
        'reason': data.get('reason')
    })


@EventBus.on(Events.LEAD_CONVERTED)
def audit_lead_converted(data):
    """Audita conversao de lead"""
    return audit_log('LEAD_CONVERTED', {
        'lead_id': data.get('lead_id'),
        'lead_name': data.get('lead_name'),
        'quote_id': data.get('quote_id'),
        'converted_value': data.get('converted_value')
    }, data.get('converted_by'))


# ============================================
# AUDITORIA DE TOUR/EVENTO
# ============================================

@EventBus.on(Events.TOUR_CREATED)
def audit_tour_created(data):
    """Audita criacao de tour"""
    return audit_log('TOUR_CREATED', {
        'tour_id': data.get('tour_id'),
        'tour_name': data.get('tour_name'),
        'client_name': data.get('client_name'),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date')
    }, data.get('created_by'))


@EventBus.on(Events.TOUR_FINISHED)
def audit_tour_finished(data):
    """Audita finalizacao de tour"""
    return audit_log('TOUR_FINISHED', {
        'tour_id': data.get('tour_id'),
        'tour_name': data.get('tour_name'),
        'equipment_returned': data.get('equipment_returned'),
        'equipment_damaged': data.get('equipment_damaged')
    }, data.get('finished_by'))


# ============================================
# AUDITORIA DE EQUIPAMENTO
# ============================================

@EventBus.on(Events.EQUIPMENT_CREATED)
def audit_equipment_created(data):
    """Audita cadastro de equipamento"""
    return audit_log('EQUIPMENT_CREATED', {
        'equipment_id': data.get('equipment_id'),
        'equipment_code': data.get('equipment_code'),
        'equipment_name': data.get('equipment_name'),
        'value': data.get('value')
    }, data.get('created_by'))


@EventBus.on(Events.EQUIPMENT_DAMAGED)
def audit_equipment_damaged(data):
    """Audita dano em equipamento"""
    return audit_log('EQUIPMENT_DAMAGED', {
        'equipment_id': data.get('equipment_id'),
        'equipment_code': data.get('equipment_code'),
        'equipment_name': data.get('equipment_name'),
        'damage_level': data.get('damage_level'),
        'description': data.get('description'),
        'tour_id': data.get('tour_id')
    }, data.get('reported_by_id'))


@EventBus.on(Events.MAINTENANCE_COMPLETED)
def audit_maintenance_completed(data):
    """Audita conclusao de manutencao"""
    return audit_log('MAINTENANCE_COMPLETED', {
        'maintenance_id': data.get('maintenance_id'),
        'equipment_id': data.get('equipment_id'),
        'equipment_name': data.get('equipment_name'),
        'cost': data.get('cost'),
        'duration_days': data.get('duration_days')
    }, data.get('completed_by'))


# ============================================
# AUDITORIA DE CHECKPOINTS
# ============================================

@EventBus.on(Events.CHECKPOINT_LOAD_TRUCK)
def audit_checkpoint_load_truck(data):
    """Audita carregamento no caminhao"""
    return audit_log('CHECKPOINT_LOAD_TRUCK', {
        'tour_id': data.get('tour_id'),
        'equipment_id': data.get('equipment_id'),
        'equipment_code': data.get('equipment_code'),
        'scanned_by': data.get('scanned_by')
    })


@EventBus.on(Events.CHECKPOINT_UNLOAD_SHOW)
def audit_checkpoint_unload_show(data):
    """Audita descarregamento no show"""
    return audit_log('CHECKPOINT_UNLOAD_SHOW', {
        'tour_id': data.get('tour_id'),
        'show_id': data.get('show_id'),
        'equipment_id': data.get('equipment_id'),
        'equipment_code': data.get('equipment_code'),
        'scanned_by': data.get('scanned_by')
    })


@EventBus.on(Events.CHECKPOINT_UNLOAD_COMPANY)
def audit_checkpoint_unload_company(data):
    """Audita devolucao na empresa"""
    return audit_log('CHECKPOINT_UNLOAD_COMPANY', {
        'tour_id': data.get('tour_id'),
        'equipment_id': data.get('equipment_id'),
        'equipment_code': data.get('equipment_code'),
        'condition': data.get('condition'),
        'scanned_by': data.get('scanned_by')
    })


# ============================================
# AUDITORIA DE ACESSO
# ============================================

@EventBus.on(Events.USER_LOGIN)
def audit_user_login(data):
    """Audita login de usuario"""
    return audit_log('USER_LOGIN', {
        'user_id': data.get('user_id'),
        'user_email': data.get('user_email'),
        'ip_address': data.get('ip_address'),
        'user_agent': data.get('user_agent')
    })


@EventBus.on(Events.TECHNICIAN_ACTIVATED)
def audit_technician_activated(data):
    """Audita ativacao de tecnico via QR"""
    return audit_log('TECHNICIAN_ACTIVATED', {
        'access_id': data.get('access_id'),
        'technician_name': data.get('technician_name'),
        'permissions': data.get('permissions')
    })