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

        weekend_maintenances = Maintenance.query.filter(
            Maintenance.company_id == company_id,
            Maintenance.status.in_(['pending', 'in_progress']),
            Maintenance.created_at >= friday
        ).all()

        # 2. Equipamentos que precisam atencao
        equipment_alerts = Equipment.query.filter(
            Equipment.company_id == company_id,
            Equipment.status.in_(['maintenance', 'damaged'])
        ).all()

        # 3. Gerar relatorio
        report = {
            'weekend_maintenances': len(weekend_maintenances),
            'equipment_needing_attention': len(equipment_alerts),
            'generated_at': datetime.now().isoformat(),
            'details': {
                'maintenances': [{'id': m.id, 'equipment': m.equipment_id, 'type': m.maintenance_type} for m in weekend_maintenances],
                'equipment': [{'id': e.id, 'name': e.name, 'status': e.status} for e in equipment_alerts]
            }
        }

        return report

    @staticmethod
    def check_low_stock_alerts(company_id):
        """Verifica estoque baixo e gera alertas"""

        # Buscar materiais com estoque baixo
        low_stock_items = MaterialStock.query.filter(
            MaterialStock.company_id == company_id,
            MaterialStock.quantity <= MaterialStock.min_quantity
        ).all()

        alerts_created = 0
        for item in low_stock_items:
            # Verificar se ja existe alerta ativo para este item
            existing_alert = FinancialAlert.query.filter(
                FinancialAlert.company_id == company_id,
                FinancialAlert.alert_type == 'low_stock',
                FinancialAlert.reference_type == 'material_stock',
                FinancialAlert.reference_id == item.id,
                FinancialAlert.status == 'active'
            ).first()

            if not existing_alert:
                alert = FinancialAlert(
                    company_id=company_id,
                    alert_type='low_stock',
                    severity='medium',
                    title=f'Estoque baixo: {item.name}',
                    message=f'O material {item.name} esta com apenas {item.quantity} unidades. Minimo recomendado: {item.min_quantity}',
                    suggested_action=f'Solicitar compra de pelo menos {item.min_quantity - item.quantity} unidades',
                    reference_type='material_stock',
                    reference_id=item.id
                )
                db.session.add(alert)
                alerts_created += 1

        db.session.commit()
        return {'alerts_created': alerts_created}

    @staticmethod
    def generate_financial_projections(company_id):
        """Gera projecoes de fluxo de caixa para os proximos 3 meses"""
        from models.rh import AccountReceivable, AccountPayable

        today = date.today()
        projections_created = 0

        for month_offset in range(1, 4):
            projection_date = today + relativedelta(months=month_offset)
            projection_month = projection_date.month
            projection_year = projection_date.year

            # Verificar se ja existe projecao para este mes
            existing = CashFlowProjection.query.filter(
                CashFlowProjection.company_id == company_id,
                CashFlowProjection.projection_month == projection_month,
                CashFlowProjection.projection_year == projection_year
            ).first()

            if existing:
                continue

            # Calcular receitas projetadas (baseado em historico)
            # Por enquanto, usar media dos ultimos 3 meses
            tres_meses_atras = today - relativedelta(months=3)

            receitas_historico = db.session.query(db.func.avg(AccountReceivable.amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'received',
                AccountReceivable.received_at >= tres_meses_atras
            ).scalar() or 0

            despesas_historico = db.session.query(db.func.avg(AccountPayable.amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status == 'paid',
                AccountPayable.paid_at >= datetime.combine(tres_meses_atras, datetime.min.time())
            ).scalar() or 0

            projection = CashFlowProjection(
                company_id=company_id,
                projection_date=projection_date.replace(day=1),
                projection_month=projection_month,
                projection_year=projection_year,
                projected_revenue=float(receitas_historico) * 30,  # Estimativa mensal
                projected_expenses=float(despesas_historico) * 30,
                projected_balance=(float(receitas_historico) - float(despesas_historico)) * 30,
                confidence_level=60  # Confianca media para projecao baseada em historico
            )
            db.session.add(projection)
            projections_created += 1

        db.session.commit()
        return {'projections_created': projections_created}

    @staticmethod
    def suggest_lead_reactivations(company_id):
        """Sugere leads para reativacao (inativos ha mais de 30 dias)"""

        trinta_dias_atras = datetime.now() - timedelta(days=30)

        # Leads inativos
        inactive_leads = Lead.query.filter(
            Lead.company_id == company_id,
            Lead.status.in_(['cold', 'lost']),
            Lead.updated_at < trinta_dias_atras
        ).all()

        suggestions = []
        for lead in inactive_leads:
            # Verificar se ja tem sugestao ativa
            existing = FinancialAlert.query.filter(
                FinancialAlert.company_id == company_id,
                FinancialAlert.alert_type == 'lead_reactivation',
                FinancialAlert.reference_type == 'lead',
                FinancialAlert.reference_id == lead.id,
                FinancialAlert.status == 'active'
            ).first()

            if not existing:
                alert = FinancialAlert(
                    company_id=company_id,
                    alert_type='lead_reactivation',
                    severity='low',
                    title=f'Reativar lead: {lead.name}',
                    message=f'O lead {lead.name} esta inativo ha mais de 30 dias. Considere fazer contato.',
                    suggested_action='Enviar email de follow-up ou ligar',
                    reference_type='lead',
                    reference_id=lead.id
                )
                db.session.add(alert)
                suggestions.append(lead.id)

        db.session.commit()
        return {'leads_suggested': len(suggestions)}

    @staticmethod
    def run_all_automations(company_id):
        """Executa todas as automacoes"""
        results = {}

        try:
            results['stock_alerts'] = AutomationService.check_low_stock_alerts(company_id)
        except Exception as e:
            results['stock_alerts'] = {'error': str(e)}

        try:
            results['projections'] = AutomationService.generate_financial_projections(company_id)
        except Exception as e:
            results['projections'] = {'error': str(e)}

        try:
            results['lead_reactivations'] = AutomationService.suggest_lead_reactivations(company_id)
        except Exception as e:
            results['lead_reactivations'] = {'error': str(e)}

        return results

    @staticmethod
    def get_automation_report(company_id):
        """Gera relatorio completo de automacoes"""
        report = AutomationService.monday_morning_task(company_id)

        # Adicionar alertas ativos
        active_alerts = FinancialAlert.query.filter(
            FinancialAlert.company_id == company_id,
            FinancialAlert.status == 'active'
        ).count()

        report['active_alerts'] = active_alerts

        return report

    # ============================================
    # AUTOMACAO: APROVAR ORCAMENTO
    # ============================================
    @staticmethod
    def approve_quote(quote_id, company_id):
        """Aprova orcamento e retorna dados para proximos passos"""
        from models.commercial import Quote

        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orcamento nao encontrado'}

        quote.status = 'approved'
        quote.approved_at = datetime.utcnow()
        db.session.commit()

        return {
            'success': True,
            'data': {
                'quote_id': quote.id,
                'client_name': quote.client_name,
                'total': float(quote.total or 0)
            }
        }

    # ============================================
    # AUTOMACAO: CRIAR CONTRATO
    # ============================================
    @staticmethod
    def create_contract_from_quote(quote_id, company_id, user_id, contract_type='rental', duration_months=12):
        from models.commercial import Quote, Contract

        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orcamento nao encontrado'}

        # Verificar se ja existe contrato para este orcamento
        existing_contract = Contract.query.filter_by(quote_id=quote_id).first()
        if existing_contract:
            return {'success': False, 'message': 'Ja existe contrato para este orcamento'}

        start_date = date.today()
        end_date = start_date + relativedelta(months=int(duration_months))

        contract = Contract(
            company_id=company_id,
            quote_id=quote_id,
            client_name=quote.client_name,
            client_email=quote.client_email,
            client_phone=quote.client_phone,
            contract_type=contract_type,
            start_date=start_date,
            end_date=end_date,
            total_value=quote.total,
            status='active',
            created_by=user_id
        )

        db.session.add(contract)
        db.session.commit()

        return {
            'success': True,
            'data': {
                'contract_id': contract.id,
                'client_name': contract.client_name,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }

    # ============================================
    # AUTOMACAO: CRIAR CONTAS A RECEBER
    # ============================================
    @staticmethod
    def create_receivables_from_quote(quote_id, company_id, user_id, 
                                       installments=1, first_due_date=None):
        from models.commercial import Quote
        from models.rh import AccountReceivable

        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orcamento nao encontrado'}

        if first_due_date is None:
            first_due_date = date.today() + timedelta(days=30)
        elif isinstance(first_due_date, str):
            first_due_date = date.fromisoformat(first_due_date)

        total = float(quote.total or 0)
        installment_value = total / int(installments)

        created = []
        for i in range(int(installments)):
            due_date = first_due_date + relativedelta(months=i)

            receivable = AccountReceivable(
                company_id=company_id,
                description=f"{quote.client_name} - Parcela {i+1}/{installments}",
                category='locacao',
                client_name=quote.client_name,
                amount=installment_value,
                due_date=due_date,
                status='pending',
                quote_id=quote_id,
                installment_number=i+1,
                total_installments=int(installments),
                created_by=user_id
            )
            db.session.add(receivable)
            created.append(receivable)

        db.session.commit()
        return {'success': True, 'data': {'receivables_created': len(created)}}

    # ============================================
    # AUTOMACAO: DESPESAS AUTOMATICAS FUNCIONARIO
    # ============================================
    @staticmethod
    def create_employee_auto_expenses(employee_id, company_id, user_id, 
                                       auto_salary=True, auto_benefits=False,
                                       vt_value=0, vr_value=0):
        from models.rh import Employee, AccountPayable

        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
        if not employee:
            return {'success': False, 'message': 'Funcionário não encontrado'}

        # ========== VALIDAÇÃO: FUNCIONÁRIO ATIVO ==========
        if employee.status != 'active':
            return {'success': False, 'message': 'Funcionário inativo não pode ter despesas automáticas'}

        created = []
        skipped = 0
        today = date.today()

        if auto_salary and employee.salary:
            for month_offset in range(12):
                due_date = date(today.year, today.month, 5) + relativedelta(months=month_offset)

                # ========== VALIDAÇÃO: VERIFICAR DUPLICIDADE ==========
                existing = AccountPayable.query.filter(
                    AccountPayable.employee_id == employee.id,
                    AccountPayable.category == 'folha_pagamento',
                    db.func.strftime('%Y-%m', AccountPayable.due_date) == due_date.strftime('%Y-%m')
                ).first()

                if existing:
                    skipped += 1
                    continue

                payable = AccountPayable(
                    company_id=company_id,
                    description=f"Salário - {employee.name} ({due_date.strftime('%m/%Y')})",
                    category='folha_pagamento',
                    amount=float(employee.salary),
                    due_date=due_date,
                    status='pending',
                    is_recurring=True,
                    recurrence_type='monthly',
                    employee_id=employee.id,
                    created_by=user_id
                )
                db.session.add(payable)
                created.append(payable)

        if auto_benefits:
            if vt_value and float(vt_value) > 0:
                for month_offset in range(12):
                    due_date = date(today.year, today.month, 1) + relativedelta(months=month_offset)

                    # Verificar duplicidade VT
                    existing = AccountPayable.query.filter(
                        AccountPayable.employee_id == employee.id,
                        AccountPayable.category == 'beneficios',
                        AccountPayable.description.like(f'VT - {employee.name}%'),
                        db.func.strftime('%Y-%m', AccountPayable.due_date) == due_date.strftime('%Y-%m')
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    payable = AccountPayable(
                        company_id=company_id,
                        description=f"VT - {employee.name} ({due_date.strftime('%m/%Y')})",
                        category='beneficios',
                        amount=float(vt_value),
                        due_date=due_date,
                        status='pending',
                        is_recurring=True,
                        recurrence_type='monthly',
                        employee_id=employee.id,
                        created_by=user_id
                    )
                    db.session.add(payable)
                    created.append(payable)

            if vr_value and float(vr_value) > 0:
                for month_offset in range(12):
                    due_date = date(today.year, today.month, 1) + relativedelta(months=month_offset)

                    # Verificar duplicidade VR
                    existing = AccountPayable.query.filter(
                        AccountPayable.employee_id == employee.id,
                        AccountPayable.category == 'beneficios',
                        AccountPayable.description.like(f'VR - {employee.name}%'),
                        db.func.strftime('%Y-%m', AccountPayable.due_date) == due_date.strftime('%Y-%m')
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    payable = AccountPayable(
                        company_id=company_id,
                        description=f"VR - {employee.name} ({due_date.strftime('%m/%Y')})",
                        category='beneficios',
                        amount=float(vr_value),
                        due_date=due_date,
                        status='pending',
                        is_recurring=True,
                        recurrence_type='monthly',
                        employee_id=employee.id,
                        created_by=user_id
                    )
                    db.session.add(payable)
                    created.append(payable)

        db.session.commit()
        return {
            'success': True, 
            'data': {
                'expenses_created': len(created),
                'expenses_skipped': skipped,
                'message': f'{len(created)} despesas criadas, {skipped} já existiam'
            }
        }

    # ============================================
    # AUTOMACAO: CRIAR PAGAVEL FREELANCER
    # ============================================
    @staticmethod
    def create_freelancer_payable(freelancer_id, company_id, user_id, 
                                   value, event_name='', payment_date=None):
        from models.rh import Freelancer, AccountPayable

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
            amount=float(value),
            due_date=payment_date,
            status='pending',
            created_by=user_id
        )
        db.session.add(payable)
        db.session.commit()

        return {'success': True, 'data': {'payable_id': payable.id}}

    # ============================================
    # AUTOMACAO: CRIAR PARCELAS DE VEICULO
    # ============================================
    @staticmethod
    def create_vehicle_installments(company_id, user_id, vehicle_name, 
                                      total_value, installments, first_due_date=None):
        from models.rh import AccountPayable

        if first_due_date is None:
            first_due_date = date.today() + relativedelta(months=1)
        elif isinstance(first_due_date, str):
            first_due_date = date.fromisoformat(first_due_date)

        installment_value = float(total_value) / int(installments)

        created = []
        for i in range(int(installments)):
            due_date = first_due_date + relativedelta(months=i)

            payable = AccountPayable(
                company_id=company_id,
                description=f"Veículo {vehicle_name} - Parcela {i+1}/{installments}",
                category='veiculos',
                amount=installment_value,
                due_date=due_date,
                status='pending',
                installment_number=i+1,
                total_installments=int(installments),
                created_by=user_id
            )
            db.session.add(payable)
            created.append(payable)

        db.session.commit()
        return {'success': True, 'data': {'installments_created': len(created)}}

    # ============================================
    # AUTOMACAO: CRIAR WORK LIST A PARTIR DO ORCAMENTO
    # ============================================
    @staticmethod
    def create_worklist_from_quote(quote_id, company_id, user_id):
        from models.commercial import Quote
        from models.work_list import WorkList

        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orcamento não encontrado'}

        # Verificar se ja existe work list para este orcamento
        existing = WorkList.query.filter_by(quote_id=quote_id).first()
        if existing:
            return {'success': False, 'message': 'Já existe Work List para este orçamento', 'data': {'worklist_id': existing.id}}

        worklist = WorkList(
            company_id=company_id,
            quote_id=quote_id,
            title=f"WL - {quote.client_name}",
            description=f"Work List gerada a partir do orçamento #{quote_id}",
            status='pending',
            created_by=user_id
        )

        db.session.add(worklist)
        db.session.commit()

        return {'success': True, 'data': {'worklist_id': worklist.id}}

    # ============================================
    # AUTOMACAO: CRIAR EVENTO A PARTIR DO ORCAMENTO
    # ============================================
    @staticmethod
    def create_event_from_quote(quote_id, company_id, user_id, event_date=None):
        from models.commercial import Quote
        from models.tour import Tour

        quote = Quote.query.filter_by(id=quote_id, company_id=company_id).first()
        if not quote:
            return {'success': False, 'message': 'Orcamento não encontrado'}

        # Verificar se ja existe evento/tour para este orcamento
        existing = Tour.query.filter_by(quote_id=quote_id).first()
        if existing:
            return {'success': False, 'message': 'Já existe Evento para este orçamento', 'data': {'tour_id': existing.id}}

        if event_date is None:
            event_date = date.today() + timedelta(days=7)
        elif isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        tour = Tour(
            company_id=company_id,
            quote_id=quote_id,
            name=f"Evento - {quote.client_name}",
            client_name=quote.client_name,
            start_date=event_date,
            end_date=event_date,
            status='planning',
            created_by=user_id
        )

        db.session.add(tour)
        db.session.commit()

        return {'success': True, 'data': {'tour_id': tour.id}}