"""
Quote Automation Service - Automacao central quando orcamento e aprovado
Dispara automaticamente:
1. Cria Invoice (Fatura)
2. Cria Evento (antigo Tour) 
3. Aloca Equipamentos (status: available -> reserved)
4. Atualiza Lead para ganho
5. Gera PIX/Boleto (via payment_adapter)
6. Notifica equipe
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from extensions import db


class QuoteAutomation:
    """Automacao central: Orcamento Aprovado -> Tudo automatico"""
    
    @staticmethod
    def on_quote_approved(separation_list_id, signal_amount=None, user_id=None):
        """
        Executa todas as automacoes quando orcamento e aprovado
        
        Args:
            separation_list_id: ID do SeparationList (orcamento)
            signal_amount: Valor do sinal (opcional)
            user_id: ID do usuario que aprovou
            
        Returns:
            dict com resultados de cada automacao
        """
        from models.separation_list import SeparationList
        from models.financial import Invoice
        from models.tour import Tour, TourEquipment
        from models.equipment import Equipment
        
        results = {
            'success': True,
            'invoice_created': False,
            'event_created': False,
            'equipment_allocated': 0,
            'lead_updated': False,
            'pix_generated': False,
            'errors': []
        }
        
        try:
            sep_list = SeparationList.query.get(separation_list_id)
            if not sep_list:
                results['success'] = False
                results['errors'].append('Orcamento nao encontrado')
                return results
            
            invoice = None
            event = None
            
            # 1. CRIAR INVOICE (Fatura)
            try:
                invoice = QuoteAutomation._create_invoice_safe(sep_list, signal_amount, user_id)
                if invoice:
                    results['invoice_created'] = True
                    results['invoice_id'] = invoice.id
                    results['invoice_code'] = invoice.code
            except Exception as e:
                results['errors'].append(f'Erro ao criar invoice: {str(e)}')
            
            # 2. CRIAR EVENTO (antigo Tour)
            try:
                event = QuoteAutomation._create_event_safe(sep_list, user_id)
                if event:
                    results['event_created'] = True
                    results['event_id'] = event.id
                    results['event_name'] = event.name
                    
                    if invoice:
                        invoice.tour_id = event.id
            except Exception as e:
                results['errors'].append(f'Erro ao criar evento: {str(e)}')
            
            # 3. ALOCAR EQUIPAMENTOS
            try:
                allocated = QuoteAutomation._allocate_equipment_safe(sep_list, event)
                results['equipment_allocated'] = allocated
            except Exception as e:
                results['errors'].append(f'Erro ao alocar equipamentos: {str(e)}')
            
            # 4. ATUALIZAR LEAD (se existir)
            try:
                lead_updated = QuoteAutomation._update_lead_to_won(sep_list)
                results['lead_updated'] = lead_updated
            except Exception as e:
                results['errors'].append(f'Erro ao atualizar lead: {str(e)}')
            
            # 5. GERAR PIX (opcional)
            if invoice and signal_amount and signal_amount > 0:
                try:
                    pix_result = QuoteAutomation._generate_pix(invoice, signal_amount)
                    results['pix_generated'] = pix_result.get('success', False)
                except Exception as e:
                    results['errors'].append(f'Erro ao gerar PIX: {str(e)}')
            
            # Commit final de todas as operacoes
            db.session.commit()
            
            # 6. NOTIFICAR EQUIPE (em try separado para nao afetar commit)
            try:
                QuoteAutomation._notify_team(sep_list, results)
            except:
                pass
            
            return results
            
        except Exception as e:
            db.session.rollback()
            results['success'] = False
            results['errors'].append(str(e))
            return results
    
    @staticmethod
    def _create_invoice_safe(sep_list, signal_amount=None, user_id=None):
        """Cria Invoice baseado no orcamento (sem commit)"""
        from models.financial import Invoice
        
        total = Decimal('0')
        for item in sep_list.items:
            if item.total_price:
                total += Decimal(str(item.total_price))
        
        if total == 0 and hasattr(sep_list, 'total_value') and sep_list.total_value:
            total = Decimal(str(sep_list.total_value))
        
        if total == 0:
            return None
        
        code = QuoteAutomation._generate_invoice_code(sep_list.company_id)
        
        invoice = Invoice(
            code=code,
            company_id=sep_list.company_id,
            client_name=sep_list.client_name or 'Cliente',
            client_email=getattr(sep_list, 'client_email', None),
            client_document=None,
            description=f'Ref: Orcamento #{sep_list.id} - {sep_list.name}',
            subtotal=total,
            discount=Decimal('0'),
            total=total,
            due_date=date.today() + timedelta(days=7),
            status='pending',
            created_by=user_id or sep_list.created_by
        )
        
        db.session.add(invoice)
        db.session.flush()
        
        return invoice
    
    @staticmethod
    def _create_invoice(sep_list, signal_amount=None, user_id=None):
        """Wrapper para compatibilidade"""
        return QuoteAutomation._create_invoice_safe(sep_list, signal_amount, user_id)
    
    @staticmethod
    def _create_event_safe(sep_list, user_id=None):
        """Cria Evento (Tour) baseado no orcamento (sem commit)"""
        from models.tour import Tour
        
        event_date = getattr(sep_list, 'event_date', None) or date.today() + timedelta(days=30)
        event_name = getattr(sep_list, 'event_name', None) or sep_list.name
        client_name = getattr(sep_list, 'client_name', None) or 'Cliente'
        
        event = Tour(
            name=event_name,
            artist=client_name,
            description=f'Evento criado automaticamente do orcamento #{sep_list.id}',
            start_date=event_date,
            end_date=event_date,
            status='confirmed',
            company_id=sep_list.company_id,
            created_by=user_id or sep_list.created_by
        )
        
        db.session.add(event)
        db.session.flush()
        
        sep_list.tour_id = event.id
        
        return event
    
    @staticmethod
    def _create_event(sep_list, user_id=None):
        """Wrapper para compatibilidade"""
        return QuoteAutomation._create_event_safe(sep_list, user_id)
    
    @staticmethod
    def _allocate_equipment_safe(sep_list, event):
        """Aloca equipamentos do orcamento para o evento (sem commit)"""
        from models.equipment import Equipment
        from models.tour import TourEquipment
        
        allocated_count = 0
        
        for item in sep_list.items:
            if not hasattr(item, 'equipment_type_id') or not item.equipment_type_id:
                continue
            
            # Buscar apenas equipamentos realmente disponiveis
            available_equipments = Equipment.query.filter_by(
                type_id=item.equipment_type_id,
                company_id=sep_list.company_id,
                status='available',
                is_active=True
            ).limit(item.quantity).all()
            
            for eq in available_equipments:
                # Verificar status novamente para evitar race condition
                if eq.status != 'available':
                    continue
                    
                eq.status = 'reserved'
                
                if event:
                    tour_eq = TourEquipment(
                        tour_id=event.id,
                        equipment_id=eq.id,
                        allocated_at=datetime.utcnow(),
                        current_status='in_company'
                    )
                    db.session.add(tour_eq)
                
                allocated_count += 1
        
        return allocated_count
    
    @staticmethod
    def _allocate_equipment(sep_list, event):
        """Wrapper para compatibilidade"""
        return QuoteAutomation._allocate_equipment_safe(sep_list, event)
    
    @staticmethod
    def _update_lead_to_won(sep_list):
        """Atualiza lead relacionado para 'ganho'"""
        from models.commercial import Lead
        
        try:
            if sep_list.client_email:
                lead = Lead.query.filter_by(
                    company_id=sep_list.company_id,
                    email=sep_list.client_email,
                    status='active'
                ).first()
                
                if lead:
                    lead.stage = 'won'
                    lead.status = 'converted'
                    lead.updated_at = datetime.utcnow()
                    return True
            
            if sep_list.client_name:
                lead = Lead.query.filter_by(
                    company_id=sep_list.company_id,
                    name=sep_list.client_name,
                    status='active'
                ).first()
                
                if lead:
                    lead.stage = 'won'
                    lead.status = 'converted'
                    lead.updated_at = datetime.utcnow()
                    return True
            
            return False
            
        except Exception as e:
            print(f"Erro ao atualizar lead: {e}")
            return False
    
    @staticmethod
    def _generate_pix(invoice, amount):
        """Gera codigo PIX para pagamento"""
        from services.payment_adapter import PaymentAdapter
        
        try:
            result = PaymentAdapter.generate_pix(
                invoice_id=invoice.id,
                amount=float(amount),
                description=f'Pagamento Fatura {invoice.code}'
            )
            return result
            
        except Exception as e:
            print(f"Erro ao gerar PIX: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _notify_team(sep_list, results):
        """Notifica equipe sobre aprovacao do orcamento"""
        from models.financial_expanded import FinancialAlert
        
        try:
            alert = FinancialAlert(
                company_id=sep_list.company_id,
                alert_type='quote_approved',
                severity='low',
                title=f'Orcamento Aprovado: {sep_list.name}',
                message=f'Cliente: {sep_list.client_name}. Invoice criada: {results.get("invoice_code", "N/A")}. Equipamentos alocados: {results.get("equipment_allocated", 0)}.',
                suggested_action='Preparar equipamentos para o evento',
                status='active'
            )
            db.session.add(alert)
            
        except Exception as e:
            print(f"Erro ao notificar: {e}")
    
    @staticmethod
    def _generate_invoice_code(company_id):
        """Gera codigo unico para invoice"""
        from models.financial import Invoice
        
        year = date.today().year
        
        count = Invoice.query.filter(
            Invoice.company_id == company_id,
            Invoice.code.like(f'FAT-{company_id}-{year}-%')
        ).count()
        
        seq = count + 1
        return f'FAT-{company_id}-{year}-{seq:04d}'
    
    @staticmethod
    def on_quote_rejected(separation_list_id, reason=None, user_id=None):
        """
        Executa automacoes quando orcamento e rejeitado
        - Atualiza Lead para perdido
        - Analisa oportunidade de reativacao (IA)
        - Gera estrategias de reconquista
        """
        from models.separation_list import SeparationList
        from models.commercial import Lead, LeadReactivation
        
        results = {
            'success': True,
            'lead_updated': False,
            'reactivation_suggested': False,
            'errors': []
        }
        
        try:
            sep_list = SeparationList.query.get(separation_list_id)
            if not sep_list:
                results['success'] = False
                results['errors'].append('Orcamento nao encontrado')
                return results
            
            lead = None
            if sep_list.client_email:
                lead = Lead.query.filter_by(
                    company_id=sep_list.company_id,
                    email=sep_list.client_email,
                    status='active'
                ).first()
            
            if not lead and sep_list.client_name:
                lead = Lead.query.filter_by(
                    company_id=sep_list.company_id,
                    name=sep_list.client_name,
                    status='active'
                ).first()
            
            if lead:
                lead.stage = 'lost'
                lead.notes = f'{lead.notes or ""}\n[{datetime.now().strftime("%d/%m/%Y")}] Motivo: {reason or "Nao informado"}'
                lead.updated_at = datetime.utcnow()
                results['lead_updated'] = True
                
                if sep_list.event_date and sep_list.event_date > date.today():
                    reactivation = LeadReactivation(
                        lead_id=lead.id,
                        company_id=sep_list.company_id,
                        strategy='discount' if reason and 'preco' in reason.lower() else 'event_reminder',
                        message_suggestion=f'Ainda podemos ajudar com {sep_list.event_name or "seu evento"}?',
                        confidence_score=70,
                        status='pending'
                    )
                    db.session.add(reactivation)
                    results['reactivation_suggested'] = True
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            results['success'] = False
            results['errors'].append(str(e))
            return results
