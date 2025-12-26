"""
Automation Service - Cronjobs e Automacoes
- Tarefa segunda-feira (manutencoes do fim de semana)
- Alertas de estoque baixo
- Projecoes financeiras
- Reativacao de leads
"""

from datetime import datetime, timedelta
from extensions import db
from models.maintenance import Maintenance
from models.material_stock import MaterialStock
from models.lead import Lead
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
