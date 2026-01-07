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

        except Exception as e:
            db.session.rollback()
            results['success'] = False
            results['errors'].append(f'Erro geral: {str(e)}')

        return results

    @staticmethod
    def _create_invoice_safe(sep_list, signal_amount=None, user_id=None):
        """Cria Invoice (Fatura) baseada no orcamento (sem commit)"""
        from models.financial import Invoice

        # Gerar codigo unico
        year = datetime.now().year
        last_invoice = Invoice.query.filter(
            Invoice.company_id == sep_list.company_id,
            Invoice.code.like(f'FAT-{sep_list.company_id}-{year}-%')
        ).order_by(Invoice.id.desc()).first()

        if last_invoice:
            try:
                last_num = int(last_invoice.code.split('-')[-1])
                new_code = f'FAT-{sep_list.company_id}-{year}-{str(last_num + 1).zfill(4)}'
            except:
                new_code = f'FAT-{sep_list.company_id}-{year}-0001'
        else:
            new_code = f'FAT-{sep_list.company_id}-{year}-0001'

        # Calcular total
        total = sep_list.calculated_total if hasattr(sep_list, 'calculated_total') else float(sep_list.total_value or 0)

        invoice = Invoice(
            code=new_code,
            separation_list_id=sep_list.id,
            company_id=sep_list.company_id,
            client_name=getattr(sep_list, 'client_name', None) or 'Cliente',
            client_email=getattr(sep_list, 'client_email', None),
            client_phone=getattr(sep_list, 'client_phone', None),
            total_amount=Decimal(str(total)),
            signal_amount=Decimal(str(signal_amount)) if signal_amount else None,
            status='pending',
            due_date=date.today() + timedelta(days=30),
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
            status='planned',
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
        """
        Aloca equipamentos do orcamento para o evento (sem commit)

        LOGICA MELHORADA:
        1. Se item tem equipment_type_id -> busca por type_id
        2. Se nao tem -> busca por nome do equipamento (fallback)
        3. Aloca equipamentos disponiveis ate atingir quantidade
        """
        from models.equipment import Equipment
        from models.tour import TourEquipment
        from sqlalchemy import or_, func

        allocated_count = 0

        # Converter items para lista se necessario
        items_list = sep_list.items.all() if hasattr(sep_list.items, 'all') else list(sep_list.items)

        for item in items_list:
            quantity_needed = item.quantity or 1
            available_equipments = []

            # ESTRATEGIA 1: Buscar por equipment_type_id (metodo original)
            if hasattr(item, 'equipment_type_id') and item.equipment_type_id:
                available_equipments = Equipment.query.filter_by(
                    type_id=item.equipment_type_id,
                    company_id=sep_list.company_id,
                    status='available',
                    is_active=True
                ).limit(quantity_needed).all()

            # ESTRATEGIA 2: Fallback - buscar por nome do equipamento
            if not available_equipments and item.item_name:
                # Busca exata por nome
                available_equipments = Equipment.query.filter(
                    Equipment.company_id == sep_list.company_id,
                    Equipment.status == 'available',
                    Equipment.is_active == True,
                    Equipment.name == item.item_name
                ).limit(quantity_needed).all()

                # Se nao encontrou exato, busca parcial (LIKE)
                if not available_equipments:
                    search_term = f'%{item.item_name}%'
                    available_equipments = Equipment.query.filter(
                        Equipment.company_id == sep_list.company_id,
                        Equipment.status == 'available',
                        Equipment.is_active == True,
                        Equipment.name.ilike(search_term)
                    ).limit(quantity_needed).all()

            # ESTRATEGIA 3: Buscar por item_description se existir
            if not available_equipments and hasattr(item, 'item_description') and item.item_description:
                search_term = f'%{item.item_description}%'
                available_equipments = Equipment.query.filter(
                    Equipment.company_id == sep_list.company_id,
                    Equipment.status == 'available',
                    Equipment.is_active == True,
                    or_(
                        Equipment.name.ilike(search_term),
                        Equipment.brand.ilike(search_term),
                        Equipment.model.ilike(search_term)
                    )
                ).limit(quantity_needed).all()

            # Alocar equipamentos encontrados
            for eq in available_equipments:
                # Verificar status novamente para evitar race condition
                if eq.status != 'available':
                    continue

                # Marcar como reservado
                eq.status = 'reserved'

                # Vincular ao evento se existir
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
            client_email = getattr(sep_list, 'client_email', None)
            if client_email:
                lead = Lead.query.filter_by(
                    company_id=sep_list.company_id,
                    email=client_email,
                    status='active'
                ).first()

                if lead:
                    lead.stage = 'won'
                    lead.status = 'converted'
                    lead.converted_at = datetime.utcnow()
                    return True
        except Exception:
            pass

        return False

    @staticmethod
    def _generate_pix(invoice, amount):
        """Gera codigo PIX para pagamento"""
        try:
            from services.payment_adapter import PaymentAdapter
            return PaymentAdapter.generate_pix(
                amount=float(amount),
                description=f'Fatura {invoice.code}',
                invoice_id=invoice.id
            )
        except ImportError:
            return {'success': False, 'message': 'PaymentAdapter nao disponivel'}
        except Exception as e:
            return {'success': False, 'message': str(e)}