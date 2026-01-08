"""
EventBus - Sistema Central de Eventos do TOUR Manager

Permite comunicacao desacoplada entre modulos.
Modulos emitem eventos, outros escutam e reagem.

Uso:
    # Registrar listener
    @EventBus.on('payroll.approved')
    def minha_funcao(data):
        print(f"Folha aprovada: {data}")

    # Emitir evento
    EventBus.emit('payroll.approved', {'payroll_id': 123})
"""

from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)


class EventBus:
    """Sistema central de eventos - Padrao Observer/Pub-Sub"""

    _listeners: Dict[str, List[Callable]] = {}
    _event_history: List[Dict] = []
    _max_history: int = 100

    @classmethod
    def on(cls, event_name: str):
        """
        Decorator para registrar listener de evento

        Uso:
            @EventBus.on('payroll.approved')
            def handle_payroll(data):
                # processar evento
                pass
        """
        def decorator(func: Callable) -> Callable:
            if event_name not in cls._listeners:
                cls._listeners[event_name] = []

            # Evitar duplicatas
            if func not in cls._listeners[event_name]:
                cls._listeners[event_name].append(func)
                logger.info(f"[EventBus] Listener registrado: {func.__name__} -> {event_name}")

            return func
        return decorator

    @classmethod
    def register(cls, event_name: str, callback: Callable) -> None:
        """
        Registra listener programaticamente (sem decorator)

        Uso:
            EventBus.register('payroll.approved', minha_funcao)
        """
        if event_name not in cls._listeners:
            cls._listeners[event_name] = []

        if callback not in cls._listeners[event_name]:
            cls._listeners[event_name].append(callback)
            logger.info(f"[EventBus] Listener registrado: {callback.__name__} -> {event_name}")

    @classmethod
    def unregister(cls, event_name: str, callback: Callable) -> bool:
        """
        Remove listener de um evento

        Retorna True se removeu, False se nao encontrou
        """
        if event_name in cls._listeners and callback in cls._listeners[event_name]:
            cls._listeners[event_name].remove(callback)
            logger.info(f"[EventBus] Listener removido: {callback.__name__} <- {event_name}")
            return True
        return False

    @classmethod
    def emit(cls, event_name: str, data: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Dispara evento para todos os listeners registrados

        Args:
            event_name: Nome do evento (ex: 'payroll.approved')
            data: Dados do evento (dict)

        Returns:
            Lista com resultados de cada listener

        Uso:
            EventBus.emit('payroll.approved', {
                'payroll_id': 123,
                'total': 5000.00
            })
        """
        data = data or {}
        timestamp = datetime.utcnow()

        # Registrar no historico
        event_record = {
            'event': event_name,
            'data': data,
            'timestamp': timestamp.isoformat(),
            'listeners_count': len(cls._listeners.get(event_name, []))
        }

        cls._event_history.append(event_record)

        # Limitar tamanho do historico
        if len(cls._event_history) > cls._max_history:
            cls._event_history = cls._event_history[-cls._max_history:]

        logger.info(f"[EventBus] Evento emitido: {event_name}")

        listeners = cls._listeners.get(event_name, [])

        if not listeners:
            logger.warning(f"[EventBus] Nenhum listener para: {event_name}")
            return []

        results = []
        for listener in listeners:
            try:
                logger.debug(f"[EventBus] Executando: {listener.__name__}")
                result = listener(data)
                results.append({
                    'listener': listener.__name__,
                    'success': True,
                    'result': result
                })
            except Exception as e:
                error_msg = f"Erro em {listener.__name__}: {str(e)}"
                logger.error(f"[EventBus] {error_msg}")
                logger.debug(traceback.format_exc())
                results.append({
                    'listener': listener.__name__,
                    'success': False,
                    'error': str(e)
                })

        return results

    @classmethod
    def emit_async(cls, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emite evento de forma assincrona (fire-and-forget)
        Erros sao logados mas nao propagados

        Util para eventos que nao precisam de resposta imediata
        """
        try:
            cls.emit(event_name, data)
        except Exception as e:
            logger.error(f"[EventBus] Erro async em {event_name}: {e}")

    @classmethod
    def get_listeners(cls, event_name: str = None) -> Dict[str, List[str]]:
        """
        Retorna listeners registrados

        Args:
            event_name: Se informado, retorna apenas deste evento

        Returns:
            Dict com nomes dos eventos e funcoes registradas
        """
        if event_name:
            listeners = cls._listeners.get(event_name, [])
            return {event_name: [f.__name__ for f in listeners]}

        return {
            event: [f.__name__ for f in funcs]
            for event, funcs in cls._listeners.items()
        }

    @classmethod
    def get_history(cls, event_name: str = None, limit: int = 20) -> List[Dict]:
        """
        Retorna historico de eventos emitidos

        Args:
            event_name: Filtrar por evento especifico
            limit: Quantidade maxima de registros
        """
        history = cls._event_history

        if event_name:
            history = [e for e in history if e['event'] == event_name]

        return history[-limit:]

    @classmethod
    def clear_listeners(cls, event_name: str = None) -> None:
        """
        Remove todos os listeners (util para testes)

        Args:
            event_name: Se informado, limpa apenas deste evento
        """
        if event_name:
            cls._listeners[event_name] = []
        else:
            cls._listeners = {}

        logger.info(f"[EventBus] Listeners limpos: {event_name or 'TODOS'}")

    @classmethod
    def clear_history(cls) -> None:
        """Limpa historico de eventos"""
        cls._event_history = []


class Events:
    """
    Constantes de eventos do sistema

    Usar estas constantes ao inves de strings para evitar typos:
        EventBus.emit(Events.PAYROLL_APPROVED, data)
    """

    # ============================================
    # RH - Recursos Humanos
    # ============================================
    PAYROLL_CREATED = 'payroll.created'
    PAYROLL_APPROVED = 'payroll.approved'
    PAYROLL_PAID = 'payroll.paid'
    PAYROLL_CANCELLED = 'payroll.cancelled'

    EMPLOYEE_HIRED = 'employee.hired'
    EMPLOYEE_UPDATED = 'employee.updated'
    EMPLOYEE_FIRED = 'employee.fired'

    VACATION_REQUESTED = 'vacation.requested'
    VACATION_APPROVED = 'vacation.approved'
    VACATION_PAID = 'vacation.paid'

    THIRTEENTH_FIRST_PAID = 'thirteenth.first_paid'
    THIRTEENTH_SECOND_PAID = 'thirteenth.second_paid'

    TERMINATION_CREATED = 'termination.created'
    TERMINATION_PAID = 'termination.paid'

    ADVANCE_CREATED = 'advance.created'
    ADVANCE_APPROVED = 'advance.approved'
    ADVANCE_PAID = 'advance.paid'

    # ============================================
    # FINANCEIRO
    # ============================================
    PAYMENT_RECEIVED = 'payment.received'
    PAYMENT_OVERDUE = 'payment.overdue'
    PAYMENT_CANCELLED = 'payment.cancelled'

    INVOICE_CREATED = 'invoice.created'
    INVOICE_SENT = 'invoice.sent'
    INVOICE_PAID = 'invoice.paid'

    ACCOUNT_PAYABLE_CREATED = 'account_payable.created'
    ACCOUNT_PAYABLE_PAID = 'account_payable.paid'
    ACCOUNT_PAYABLE_OVERDUE = 'account_payable.overdue'

    ACCOUNT_RECEIVABLE_CREATED = 'account_receivable.created'
    ACCOUNT_RECEIVABLE_RECEIVED = 'account_receivable.received'

    PIX_GENERATED = 'pix.generated'
    BOLETO_GENERATED = 'boleto.generated'
    NFSE_EMITTED = 'nfse.emitted'

    # ============================================
    # ORCAMENTO / COMERCIAL
    # ============================================
    QUOTE_CREATED = 'quote.created'
    QUOTE_SENT = 'quote.sent'
    QUOTE_APPROVED = 'quote.approved'
    QUOTE_REJECTED = 'quote.rejected'
    QUOTE_EXPIRED = 'quote.expired'

    LEAD_CREATED = 'lead.created'
    LEAD_CONVERTED = 'lead.converted'
    LEAD_LOST = 'lead.lost'

    # ============================================
    # TOUR / EVENTO
    # ============================================
    TOUR_CREATED = 'tour.created'
    TOUR_STARTED = 'tour.started'
    TOUR_FINISHED = 'tour.finished'
    TOUR_CANCELLED = 'tour.cancelled'

    SHOW_CREATED = 'show.created'
    SHOW_COMPLETED = 'show.completed'

    # ============================================
    # EQUIPAMENTO
    # ============================================
    EQUIPMENT_CREATED = 'equipment.created'
    EQUIPMENT_ALLOCATED = 'equipment.allocated'
    EQUIPMENT_RETURNED = 'equipment.returned'
    EQUIPMENT_DAMAGED = 'equipment.damaged'
    EQUIPMENT_MAINTENANCE = 'equipment.maintenance'
    EQUIPMENT_REPAIRED = 'equipment.repaired'

    CHECKPOINT_LOAD_TRUCK = 'checkpoint.load_truck'
    CHECKPOINT_UNLOAD_SHOW = 'checkpoint.unload_show'
    CHECKPOINT_LOAD_RETURN = 'checkpoint.load_return'
    CHECKPOINT_UNLOAD_COMPANY = 'checkpoint.unload_company'

    # ============================================
    # MANUTENCAO
    # ============================================
    MAINTENANCE_CREATED = 'maintenance.created'
    MAINTENANCE_STARTED = 'maintenance.started'
    MAINTENANCE_COMPLETED = 'maintenance.completed'
    MAINTENANCE_EXTERNAL = 'maintenance.external'

    # ============================================
    # SISTEMA
    # ============================================
    USER_REGISTERED = 'user.registered'
    USER_LOGIN = 'user.login'
    TECHNICIAN_INVITED = 'technician.invited'
    TECHNICIAN_ACTIVATED = 'technician.activated'

    LOW_STOCK_ALERT = 'alert.low_stock'
    PAYMENT_OVERDUE_ALERT = 'alert.payment_overdue'