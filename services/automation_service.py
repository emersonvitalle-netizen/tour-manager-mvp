"""
Automation Service - Cronjobs e Automacoes
- Tarefa segunda-feira (manutencoes do fim de semana)
- Alertas de estoque baixo
- Projecoes financeiras
- Reativacao de leads
"""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from extensions import db
from models.maintenance import Maintenance
from models.material_stock import MaterialStock
from models.commercial import Lead
from models.financial_expanded import FinancialAlert, CashFlowProjection
import json

class AutomationService:
    
    @staticmethod
    def monday_morning_task(company_id):
        """
        Executa domingo 23:00
        Envia notificacao segunda 07:00
        """
        from models.equipment import Equipment
        
        # 1. Manutencoes do fim de semana
        friday = datetime.now() - timedelta(days=3)
        
        maintenances = Maintenance.query.filter(
            Maintenance.company_id == company_id,
            Maintenance.reported_at >= friday,
            Maintenance.status.in_(['pending', 'in_progress'])
        ).all()
        
        # 2. Verificar estoque
        low_stock_items = MaterialStock.query.filter(
            MaterialStock.company_id == company_id,
            MaterialStock.quantity < MaterialStock.minimum_quantity,
            MaterialStock.is_active == True
        ).all()
        
        # 3. Fabricacoes pendentes (buscar do historico de requisicoes)
        pending_fabrications = []  # TODO: Implementar logica
        
        # 4. Manutencoes preventivas vencidas
        # TODO: Consultar MaintenanceSchedule
        
        # Montar relatorio
        report = {
            'maintenances': {
                'total': len(maintenances),
                'urgent': len([m for m in maintenances if m.priority == 'urgent']),
                'items': [
                    {
                        'equipment_code': m.equipment.code,
                        'priority': m.priority,
                        'problem': m.problem_description[:100]
                    }
                    for m in maintenances[:10]  # Top 10
                ]
            },
            'low_stock': {
                'total': len(low_stock_items),
                'items': [
                    {
                        'name': item.name,
                        'current': float(item.quantity),
                        'minimum': float(item.minimum_quantity),
                        'unit': item.unit
                    }
                    for item in low_stock_items
                ]
            },
            'fabrications': pending_fabrications
        }
        
        return report
    
    @staticmethod
    def check_low_stock_alerts(company_id):
        """Verifica estoque baixo e cria alertas"""
        low_items = MaterialStock.query.filter(
            MaterialStock.company_id == company_id,
            MaterialStock.quantity < MaterialStock.minimum_quantity,
            MaterialStock.is_active == True
        ).all()
        
        for item in low_items:
            # Verifica se ja existe alerta ativo
            existing = FinancialAlert.query.filter_by(
                company_id=company_id,
                alert_type='low_stock',
                reference_type='material_stock',
                reference_id=item.id,
                status='active'
            ).first()
            
            if not existing:
                alert = FinancialAlert(
                    company_id=company_id,
                    alert_type='low_stock',
                    severity='medium' if item.quantity > 0 else 'high',
                    title=f'Estoque baixo: {item.name}',
                    message=f'Estoque de {item.name} está em {item.quantity}{item.unit}. Mínimo: {item.minimum_quantity}{item.unit}',
                    suggested_action=f'Realizar pedido de {item.name}',
                    reference_type='material_stock',
                    reference_id=item.id
                )
                db.session.add(alert)
        
        db.session.commit()
    
    @staticmethod
    def generate_financial_projections(company_id):
        """Gera projecoes financeiras para proximos 6 meses"""
        from models.quote import Quote
        from models.invoice import Invoice
        from models.financial import Payment
        
        today = datetime.now().date()
        
        for months_ahead in range(1, 7):
            target_date = today + timedelta(days=30 * months_ahead)
            month = target_date.month
            year = target_date.year
            
            # Verificar se ja existe projecao
            existing = CashFlowProjection.query.filter_by(
                company_id=company_id,
                projection_month=month,
                projection_year=year
            ).first()
            
            if existing:
                continue
            
            # Calcular receitas projetadas (quotes aprovados)
            projected_revenue = db.session.query(
                db.func.sum(Quote.total_amount)
            ).filter(
                Quote.company_id == company_id,
                Quote.status == 'approved',
                Quote.event_date >= target_date,
                Quote.event_date < target_date + timedelta(days=30)
            ).scalar() or 0
            
            # Calcular despesas projetadas
            projected_expenses = 0  # TODO: Somar custos fixos + variaveis
            
            projection = CashFlowProjection(
                company_id=company_id,
                projection_date=target_date,
                projection_month=month,
                projection_year=year,
                projected_revenue=projected_revenue,
                projected_expenses=projected_expenses,
                projected_balance=projected_revenue - projected_expenses,
                confidence_level=70  # TODO: Calcular com IA
            )
            
            db.session.add(projection)
        
        db.session.commit()
    
    @staticmethod
    def suggest_lead_reactivations(company_id):
        """Sugere reativacoes de leads inativos (IA)"""
        from models.commercial import LeadReactivation
        
        # Buscar leads inativos ha mais de 30 dias
        cutoff_date = datetime.now() - timedelta(days=30)
        
        inactive_leads = Lead.query.filter(
            Lead.company_id == company_id,
            Lead.status == 'active',
            Lead.stage.in_(['contacted', 'qualified']),
            Lead.last_contact_at < cutoff_date
        ).all()
        
        for lead in inactive_leads:
            # Verificar se ja tem sugestao pendente
            existing = LeadReactivation.query.filter_by(
                lead_id=lead.id,
                status='pending'
            ).first()
            
            if existing:
                continue
            
            # Definir estrategia (simplificado - depois usar IA)
            days_inactive = (datetime.now() - lead.last_contact_at).days
            
            if days_inactive > 90:
                strategy = 'discount'
                message = f"Olá {lead.name}! Temos uma oferta especial para você..."
                confidence = 60
            elif days_inactive > 60:
                strategy = 'new_service'
                message = f"Oi {lead.name}! Lançamos novos serviços que podem te interessar..."
                confidence = 70
            else:
                strategy = 'event_reminder'
                message = f"{lead.name}, seu evento está se aproximando?"
                confidence = 80
            
            reactivation = LeadReactivation(
                lead_id=lead.id,
                company_id=company_id,
                strategy=strategy,
                message_suggestion=message,
                confidence_score=confidence
            )
            
            db.session.add(reactivation)
        
        db.session.commit()
    
    @staticmethod
    def run_daily_automations(company_id):
        """Executa todas as automacoes diarias"""
        print(f"[{datetime.now()}] Iniciando automações para company {company_id}")
        
        try:
            # 1. Alertas de estoque
            AutomationService.check_low_stock_alerts(company_id)
            print("  ✓ Alertas de estoque verificados")
            
            # 2. Projeções financeiras
            AutomationService.generate_financial_projections(company_id)
            print("  ✓ Projeções financeiras atualizadas")
            
            # 3. Sugestões de reativação de leads
            AutomationService.suggest_lead_reactivations(company_id)
            print("  ✓ Sugestões de reativação geradas")
            
            print(f"[{datetime.now()}] Automações concluídas")
            
        except Exception as e:
            print(f"  ✗ Erro nas automações: {e}")
            db.session.rollback()
    
    @staticmethod
    def run_monday_morning(company_id):
        """Executa tarefa especifica de segunda-feira"""
        report = AutomationService.monday_morning_task(company_id)
        
        # TODO: Enviar push notification
        # TODO: Enviar email
        
        return report
    
    @staticmethod
    def approve_quote(quote_id, company_id):
        from models.financial import Quote
        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orçamento não encontrado'}
        
        quote.status = 'approved'
        db.session.commit()
        return {'success': True, 'data': {'quote_id': quote.id}}
    
    @staticmethod
    def create_contract_from_quote(quote_id, company_id, user_id):
        from models.financial import Quote, Contract
        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orçamento não encontrado'}
        
        contract = Contract(
            quote_id=quote.id,
            client_id=quote.client_id,
            company_id=company_id,
            title=f"Contrato - {quote.title}",
            value=quote.total,
            status='draft',
            created_by=user_id
        )
        db.session.add(contract)
        db.session.commit()
        return {'success': True, 'data': {'contract_id': contract.id}}
    
    @staticmethod
    def create_receivables_from_quote(quote_id, company_id, user_id, installments=1, first_due_date=None):
        from models.financial import Quote, AccountReceivable
        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orçamento não encontrado'}
        
        if first_due_date is None:
            first_due_date = date.today() + timedelta(days=30)
        elif isinstance(first_due_date, str):
            first_due_date = date.fromisoformat(first_due_date)
        
        total = float(quote.total or 0)
        installment_value = total / installments
        
        created = []
        for i in range(installments):
            due_date = first_due_date + relativedelta(months=i)
            
            receivable = AccountReceivable(
                company_id=company_id,
                client_id=quote.client_id,
                quote_id=quote.id,
                description=f"{quote.title} - Parcela {i+1}/{installments}",
                value=installment_value,
                due_date=due_date,
                status='pending',
                installment_number=i+1,
                total_installments=installments,
                created_by=user_id
            )
            db.session.add(receivable)
            created.append(receivable)
        
        db.session.commit()
        return {'success': True, 'data': {'receivables_created': len(created)}}
    
    @staticmethod
    def create_employee_auto_expenses(employee_id, company_id, user_id, 
                                       auto_salary=True, auto_benefits=False,
                                       vt_value=0, vr_value=0):
        from models.rh import Employee
        from models.financial import AccountPayable
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
        if not employee:
            return {'success': False, 'message': 'Funcionário não encontrado'}
        
        created = []
        today = date.today()
        
        if auto_salary and employee.salary:
            for month_offset in range(12):
                due_date = date(today.year, today.month, 5) + relativedelta(months=month_offset)
                
                payable = AccountPayable(
                    company_id=company_id,
                    description=f"Salário - {employee.name} ({due_date.strftime('%m/%Y')})",
                    category='folha_pagamento',
                    value=float(employee.salary),
                    due_date=due_date,
                    status='pending',
                    recurrence='monthly',
                    employee_id=employee.id,
                    created_by=user_id
                )
                db.session.add(payable)
                created.append(payable)
        
        if auto_benefits:
            if vt_value and float(vt_value) > 0:
                for month_offset in range(12):
                    due_date = date(today.year, today.month, 1) + relativedelta(months=month_offset)
                    payable = AccountPayable(
                        company_id=company_id,
                        description=f"VT - {employee.name} ({due_date.strftime('%m/%Y')})",
                        category='beneficios',
                        value=float(vt_value),
                        due_date=due_date,
                        status='pending',
                        recurrence='monthly',
                        employee_id=employee.id,
                        created_by=user_id
                    )
                    db.session.add(payable)
                    created.append(payable)
            
            if vr_value and float(vr_value) > 0:
                for month_offset in range(12):
                    due_date = date(today.year, today.month, 1) + relativedelta(months=month_offset)
                    payable = AccountPayable(
                        company_id=company_id,
                        description=f"VR - {employee.name} ({due_date.strftime('%m/%Y')})",
                        category='beneficios',
                        value=float(vr_value),
                        due_date=due_date,
                        status='pending',
                        recurrence='monthly',
                        employee_id=employee.id,
                        created_by=user_id
                    )
                    db.session.add(payable)
                    created.append(payable)
        
        db.session.commit()
        return {'success': True, 'data': {'expenses_created': len(created)}}
    
    @staticmethod
    def create_freelancer_payable(freelancer_id, company_id, user_id, 
                                   value, event_name='', payment_date=None):
        from models.rh import Freelancer
        from models.financial import AccountPayable
        freelancer = Freelancer.query.filter_by(id=freelancer_id, company_id=company_id).first()
        if not freelancer:
            return {'success': False, 'message': 'Freelancer não encontrado'}
        
        if payment_date is None:
            payment_date = date.today()
        elif isinstance(payment_date, str):
            payment_date = date.fromisoformat(payment_date)
        
        payable = AccountPayable(
            company_id=company_id,
            description=f"Freelancer - {freelancer.name}" + (f" ({event_name})" if event_name else ""),
            category='freelancer',
            value=float(value),
            due_date=payment_date,
            status='pending',
            freelancer_id=freelancer.id,
            created_by=user_id
        )
        db.session.add(payable)
        db.session.commit()
        
        return {'success': True, 'data': {'payable_id': payable.id}}
    
    @staticmethod
    def create_vehicle_installments(vehicle_id, company_id, user_id,
                                     total_value, installments, first_due_date=None):
        from models.financial import AccountPayable
        if first_due_date is None:
            first_due_date = date.today()
        elif isinstance(first_due_date, str):
            first_due_date = date.fromisoformat(first_due_date)
        
        installment_value = float(total_value) / installments
        created = []
        
        for i in range(installments):
            due_date = first_due_date + relativedelta(months=i)
            
            payable = AccountPayable(
                company_id=company_id,
                description=f"Aluguel Veículo - Parcela {i+1}/{installments}",
                category='veiculos',
                value=installment_value,
                due_date=due_date,
                status='pending',
                installment_number=i+1,
                total_installments=installments,
                created_by=user_id
            )
            db.session.add(payable)
            created.append(payable)
        
        db.session.commit()
        return {'success': True, 'data': {'installments_created': len(created)}}
    
    @staticmethod
    def create_worklist_from_quote(quote_id, company_id, user_id, 
                                    event_date=None, event_location=None, assigned_to=None):
        """Cria WorkList a partir do orçamento aprovado (sem preços)"""
        import secrets
        from models.financial import Quote, QuoteItem
        from models.work_list import WorkList, WorkListItem
        
        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orçamento não encontrado ou não pertence à sua empresa'}
        
        if quote.company_id != company_id:
            return {'success': False, 'message': 'Acesso negado'}
        
        if quote.status != 'approved':
            return {'success': False, 'message': 'Orçamento precisa estar aprovado'}
        
        if event_date and isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        
        share_token = secrets.token_urlsafe(32)
        
        work_list = WorkList(
            company_id=company_id,
            quote_id=quote.id,
            name=f"Separação - {quote.title}",
            description=f"Lista de separação para {quote.client_name}",
            client_name=quote.client_name,
            event_date=event_date,
            event_location=event_location,
            share_token=share_token,
            status='pending',
            created_by=user_id,
            assigned_to=assigned_to
        )
        db.session.add(work_list)
        db.session.flush()
        
        for item in quote.items:
            work_item = WorkListItem(
                work_list_id=work_list.id,
                item_name=item.description,
                quantity=item.quantity,
                separated=False
            )
            db.session.add(work_item)
        
        db.session.commit()
        
        return {
            'success': True, 
            'data': {
                'work_list_id': work_list.id,
                'items_count': len(quote.items),
                'share_token': share_token
            }
        }
