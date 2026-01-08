"""
Notification Listeners - Escuta eventos e envia notificacoes

Futuramente pode integrar com:
- WhatsApp (Twilio, Z-API, Evolution API)
- Email (SendGrid, SES)
- Push Notifications
- Slack/Discord
"""

from services.event_bus import EventBus, Events
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================
# HELPERS DE NOTIFICACAO
# ============================================

def send_notification(channel: str, recipient: str, message: str, data: dict = None):
    """
    Helper para enviar notificacoes

    Por enquanto apenas loga, mas pode ser expandido para:
    - WhatsApp
    - Email
    - Push
    - SMS
    """
    logger.info(f"[Notification] [{channel}] Para: {recipient}")
    logger.info(f"[Notification] Mensagem: {message[:100]}...")

    # TODO: Implementar integracao real
    # if channel == 'whatsapp':
    #     whatsapp_service.send(recipient, message)
    # elif channel == 'email':
    #     email_service.send(recipient, message)

    return {
        'sent': True,
        'channel': channel,
        'recipient': recipient,
        'timestamp': datetime.utcnow().isoformat()
    }


# ============================================
# NOTIFICACOES DE RH
# ============================================

@EventBus.on(Events.PAYROLL_PAID)
def notify_payroll_paid(data):
    """Notifica quando folha e paga"""
    employee_name = data.get('employee_name', 'Funcionario')
    net_salary = data.get('net_salary', 0)
    month = data.get('reference_month', '')
    year = data.get('reference_year', '')

    message = f"""
💰 PAGAMENTO REALIZADO

Funcionario: {employee_name}
Competencia: {month}/{year}
Valor Liquido: R$ {net_salary:,.2f}

Obrigado pelo seu trabalho!
    """.strip()

    # Por enquanto so loga
    logger.info(f"[Notify] Folha paga - {employee_name}")

    return {'notified': True}


@EventBus.on(Events.VACATION_APPROVED)
def notify_vacation_approved(data):
    """Notifica quando ferias sao aprovadas"""
    employee_name = data.get('employee_name', 'Funcionario')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')

    message = f"""
🏖️ FERIAS APROVADAS

Funcionario: {employee_name}
Periodo: {start_date} a {end_date}

Boas ferias!
    """.strip()

    logger.info(f"[Notify] Ferias aprovadas - {employee_name}")

    return {'notified': True}


@EventBus.on(Events.EMPLOYEE_HIRED)
def notify_employee_hired(data):
    """Notifica equipe quando novo funcionario e contratado"""
    employee_name = data.get('employee_name', 'Funcionario')
    position = data.get('position', '')
    department = data.get('department', '')

    message = f"""
👋 NOVO MEMBRO NA EQUIPE

Nome: {employee_name}
Cargo: {position}
Departamento: {department}

Bem-vindo(a) ao time!
    """.strip()

    logger.info(f"[Notify] Novo funcionario - {employee_name}")

    return {'notified': True}


# ============================================
# NOTIFICACOES COMERCIAIS
# ============================================

@EventBus.on(Events.QUOTE_APPROVED)
def notify_quote_approved(data):
    """Notifica equipe quando orcamento e aprovado"""
    client_name = data.get('client_name', 'Cliente')
    event_name = data.get('event_name', 'Evento')
    total_value = data.get('total_value', 0)

    message = f"""
✅ ORCAMENTO APROVADO!

Cliente: {client_name}
Evento: {event_name}
Valor: R$ {total_value:,.2f}

Parabens pela venda!
    """.strip()

    logger.info(f"[Notify] Orcamento aprovado - {client_name} - R$ {total_value:,.2f}")

    return {'notified': True}


@EventBus.on(Events.QUOTE_REJECTED)
def notify_quote_rejected(data):
    """Notifica quando orcamento e rejeitado"""
    client_name = data.get('client_name', 'Cliente')
    reason = data.get('reason', 'Nao informado')

    message = f"""
❌ ORCAMENTO RECUSADO

Cliente: {client_name}
Motivo: {reason}

Analisar para proximas oportunidades.
    """.strip()

    logger.info(f"[Notify] Orcamento rejeitado - {client_name}")

    return {'notified': True}


@EventBus.on(Events.PAYMENT_RECEIVED)
def notify_payment_received(data):
    """Notifica quando pagamento e recebido"""
    client_name = data.get('client_name', 'Cliente')
    amount = data.get('amount', 0)
    payment_method = data.get('payment_method', 'N/A')

    message = f"""
💵 PAGAMENTO CONFIRMADO!

Cliente: {client_name}
Valor: R$ {amount:,.2f}
Forma: {payment_method}
    """.strip()

    logger.info(f"[Notify] Pagamento recebido - {client_name} - R$ {amount:,.2f}")

    return {'notified': True}


# ============================================
# NOTIFICACOES DE TOUR/EVENTO
# ============================================

@EventBus.on(Events.TOUR_STARTED)
def notify_tour_started(data):
    """Notifica equipe quando tour comeca"""
    tour_name = data.get('tour_name', 'Tour')
    start_date = data.get('start_date', '')

    message = f"""
🎸 TOUR INICIADA!

Nome: {tour_name}
Inicio: {start_date}

Boa tour a todos!
    """.strip()

    logger.info(f"[Notify] Tour iniciada - {tour_name}")

    return {'notified': True}


@EventBus.on(Events.TOUR_FINISHED)
def notify_tour_finished(data):
    """Notifica quando tour termina"""
    tour_name = data.get('tour_name', 'Tour')

    message = f"""
🏁 TOUR FINALIZADA!

Nome: {tour_name}

Conferir equipamentos devolvidos.
    """.strip()

    logger.info(f"[Notify] Tour finalizada - {tour_name}")

    return {'notified': True}


# ============================================
# NOTIFICACOES DE EQUIPAMENTO
# ============================================

@EventBus.on(Events.EQUIPMENT_DAMAGED)
def notify_equipment_damaged(data):
    """Notifica URGENTE quando equipamento e danificado"""
    equipment_name = data.get('equipment_name', 'Equipamento')
    equipment_code = data.get('equipment_code', '')
    damage_level = data.get('damage_level', 'unknown')
    description = data.get('description', '')
    reported_by = data.get('reported_by', '')

    urgency = "🔴 URGENTE" if damage_level == 'critical' else "⚠️"

    message = f"""
{urgency} EQUIPAMENTO DANIFICADO

Equipamento: {equipment_name} ({equipment_code})
Nivel: {damage_level.upper()}
Descricao: {description}
Reportado por: {reported_by}

Acionar manutencao imediatamente!
    """.strip()

    logger.warning(f"[Notify] DANO - {equipment_name} - {damage_level}")

    return {'notified': True, 'urgency': damage_level}


@EventBus.on(Events.MAINTENANCE_COMPLETED)
def notify_maintenance_completed(data):
    """Notifica quando manutencao e concluida"""
    equipment_name = data.get('equipment_name', 'Equipamento')

    message = f"""
✅ MANUTENCAO CONCLUIDA

Equipamento: {equipment_name}
Status: Disponivel para uso
    """.strip()

    logger.info(f"[Notify] Manutencao concluida - {equipment_name}")

    return {'notified': True}


# ============================================
# ALERTAS DO SISTEMA
# ============================================

@EventBus.on(Events.LOW_STOCK_ALERT)
def notify_low_stock(data):
    """Notifica quando estoque esta baixo"""
    item_name = data.get('item_name', 'Item')
    quantity = data.get('quantity', 0)
    min_quantity = data.get('min_quantity', 0)

    message = f"""
⚠️ ESTOQUE BAIXO

Material: {item_name}
Quantidade atual: {quantity}
Minimo recomendado: {min_quantity}

Solicitar reposicao!
    """.strip()

    logger.warning(f"[Notify] Estoque baixo - {item_name}: {quantity}/{min_quantity}")

    return {'notified': True}


@EventBus.on(Events.PAYMENT_OVERDUE_ALERT)
def notify_payment_overdue(data):
    """Notifica quando pagamento esta vencido"""
    description = data.get('description', 'Conta')
    amount = data.get('amount', 0)
    days_overdue = data.get('days_overdue', 0)

    message = f"""
🔴 PAGAMENTO VENCIDO

Descricao: {description}
Valor: R$ {amount:,.2f}
Dias em atraso: {days_overdue}

Regularizar urgente!
    """.strip()

    logger.warning(f"[Notify] Pagamento vencido - {description} - {days_overdue} dias")

    return {'notified': True}