from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.separation_list import SeparationList, SeparationListItem
from models.work_list import WorkList, WorkListItem
from models.tour import Tour, TourEquipment
from models.equipment import Equipment
from models.category import Category
from datetime import datetime

orcamento_bp = Blueprint('orcamento', __name__, url_prefix='/orcamento')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@orcamento_bp.route('/')
@login_required
@admin_required
def index():
    status_filter = request.args.get('status', 'pending')

    lists = SeparationList.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status=status_filter
    ).order_by(SeparationList.created_at.desc()).all()

    pending_count = SeparationList.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='pending'
    ).count()

    approved_count = SeparationList.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='approved'
    ).count()

    rejected_count = SeparationList.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='rejected'
    ).count()

    return render_template('orcamento/index.html',
                          lists=lists,
                          status_filter=status_filter,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count)

@orcamento_bp.route('/new')
@login_required
@admin_required
def new():
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()

    return render_template('orcamento/choose_type.html', tours=tours)

@orcamento_bp.route('/new/complete', methods=['GET', 'POST'])
@login_required
@admin_required
def new_complete():
    if request.method == 'POST':
        return create_list_complete()

    from models.equipment_type import EquipmentType

    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()

    categories = Category.query.filter_by(
        company_id=current_user.company_id
    ).all()

    types_by_category = {}
    for cat in categories:
        types = EquipmentType.query.filter_by(
            category_id=cat.id,
            company_id=current_user.company_id
        ).order_by(EquipmentType.name).all()

        if types:
            types_with_equipment = []
            for t in types:
                all_equipments = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    is_active=True
                ).all()

                if all_equipments:
                    for eq in all_equipments:
                        types_with_equipment.append({
                            'id': eq.id,
                            'name': eq.name,
                            'code': eq.code,
                            'brand': eq.brand if eq.brand else 'Sem marca',
                            'model': eq.model if eq.model else 'Sem modelo',
                            'value': float(eq.value) if eq.value else 0.0,
                            'available': 1 if eq.status == 'available' else 0,
                            'total': 1,
                            'type_name': t.name
                        })

            if types_with_equipment:
                types_by_category[cat.name] = {
                    'icon': get_category_icon(cat.name),
                    'types': types_with_equipment
                }

    return render_template('orcamento/new_complete.html',
                         tours=tours,
                         types_by_category=types_by_category)

@orcamento_bp.route('/new/simple', methods=['GET', 'POST'])
@login_required
@admin_required
def new_simple():
    if request.method == 'POST':
        return create_list_simple()

    from models.equipment_type import EquipmentType

    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()

    categories = Category.query.filter_by(
        company_id=current_user.company_id
    ).all()

    types_by_category = {}
    for cat in categories:
        types = EquipmentType.query.filter_by(
            category_id=cat.id,
            company_id=current_user.company_id
        ).order_by(EquipmentType.name).all()

        if types:
            types_with_equipment = []
            for t in types:
                all_equipments = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    is_active=True
                ).all()

                if all_equipments:
                    for eq in all_equipments:
                        types_with_equipment.append({
                            'id': eq.id,
                            'name': eq.name,
                            'code': eq.code,
                            'brand': eq.brand if eq.brand else 'Sem marca',
                            'model': eq.model if eq.model else 'Sem modelo',
                            'available': 1 if eq.status == 'available' else 0,
                            'total': 1,
                            'type_name': t.name
                        })

            if types_with_equipment:
                types_by_category[cat.name] = {
                    'icon': get_category_icon(cat.name),
                    'types': types_with_equipment
                }

    return render_template('orcamento/new_simple.html',
                         tours=tours,
                         types_by_category=types_by_category)

@orcamento_bp.route('/<int:id>')
@login_required
@admin_required
def detail(id):
    sep_list_orm = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('orcamento/detail.html', sep_list=sep_list_orm)

@orcamento_bp.route('/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve(id):
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if sep_list.status != 'pending':
        flash('Este orcamento ja foi processado.', 'warning')
        return redirect(url_for('orcamento.detail', id=id))

    try:
        sep_list.status = 'approved'
        sep_list.approved_by = current_user.id
        sep_list.approved_at = datetime.utcnow()
        sep_list.approval_notes = request.form.get('notes', '')

        work_list = WorkList(
            separation_list_id=sep_list.id,
            tour_id=sep_list.tour_id,
            name=f"{sep_list.name} - Lista de Trabalho",
            description=sep_list.description,
            status='pending',
            company_id=current_user.company_id,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        db.session.add(work_list)
        db.session.flush()

        for item in sep_list.items:
            work_item = WorkListItem(
                work_list_id=work_list.id,
                item_name=item.item_name,
                quantity=item.quantity,
                separated=False
            )
            db.session.add(work_item)

        db.session.commit()
        
        from services.quote_automation import QuoteAutomation
        signal_amount = request.form.get('signal_amount', type=float)
        automation_result = QuoteAutomation.on_quote_approved(
            separation_list_id=id,
            signal_amount=signal_amount,
            user_id=current_user.id
        )
        
        msg = f'Orcamento aprovado! Lista de trabalho #{work_list.id} criada.'
        if automation_result.get('invoice_created'):
            msg += f' Fatura {automation_result.get("invoice_code", "")} gerada.'
        if automation_result.get('event_created'):
            msg += f' Evento criado.'
        if automation_result.get('equipment_allocated', 0) > 0:
            msg += f' {automation_result["equipment_allocated"]} equipamentos alocados.'
        
        flash(msg, 'success')
        return redirect(url_for('orcamento.detail', id=id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar orcamento: {str(e)}', 'danger')
        return redirect(url_for('orcamento.detail', id=id))

@orcamento_bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject(id):
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if sep_list.status != 'pending':
        flash('Este orcamento ja foi processado.', 'warning')
        return redirect(url_for('orcamento.detail', id=id))

    reason = request.form.get('reason', '')
    if not reason:
        flash('Informe o motivo da rejeicao.', 'danger')
        return redirect(url_for('orcamento.detail', id=id))

    try:
        sep_list.status = 'rejected'
        sep_list.approved_by = current_user.id
        sep_list.approved_at = datetime.utcnow()
        sep_list.rejection_reason = reason

        db.session.commit()
        
        from services.quote_automation import QuoteAutomation
        QuoteAutomation.on_quote_rejected(
            separation_list_id=id,
            reason=reason,
            user_id=current_user.id
        )
        
        flash('Orcamento rejeitado.', 'warning')
        return redirect(url_for('orcamento.detail', id=id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar orcamento: {str(e)}', 'danger')
        return redirect(url_for('orcamento.detail', id=id))

@orcamento_bp.route('/<int:id>/toggle-item/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def toggle_item(id, item_id):
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    item = SeparationListItem.query.filter_by(
        id=item_id,
        separation_list_id=id
    ).first_or_404()

    item.is_checked = not item.is_checked
    db.session.commit()

    return jsonify({'success': True, 'is_checked': item.is_checked})


def create_list_complete():
    from models.equipment_type import EquipmentType

    tour_id = request.form.get('tour_id')
    name = request.form.get('name', '').strip()
    observations = request.form.get('observations', '').strip()
    
    # Dados do cliente
    client_name = request.form.get('client_name', '').strip()
    client_phone = request.form.get('client_phone', '').strip()
    client_email = request.form.get('client_email', '').strip()
    client_address = request.form.get('client_address', '').strip()
    
    # Dados do evento
    event_name = request.form.get('event_name', '').strip()
    event_date_str = request.form.get('event_date', '')
    event_time = request.form.get('event_time', '').strip()
    event_location = request.form.get('event_location', '').strip()

    if not name or len(name) < 3:
        flash('Nome do orçamento deve ter pelo menos 3 caracteres.', 'danger')
        return redirect(url_for('orcamento.new_complete'))
    
    if not client_name:
        flash('Nome do cliente é obrigatório.', 'danger')
        return redirect(url_for('orcamento.new_complete'))
    
    if not event_name:
        flash('Nome do evento é obrigatório.', 'danger')
        return redirect(url_for('orcamento.new_complete'))
    
    if not event_date_str:
        flash('Data do evento é obrigatória.', 'danger')
        return redirect(url_for('orcamento.new_complete'))

    # Converter data
    try:
        from datetime import datetime as dt
        event_date = dt.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Data do evento inválida.', 'danger')
        return redirect(url_for('orcamento.new_complete'))

    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            eq_id = key.replace('quantity-', '')
            try:
                quantity = int(request.form.get(f'quantity-{eq_id}', 0))
                unit_price = float(request.form.get(f'unit_price-{eq_id}', 0))
            except (ValueError, TypeError):
                continue

            if quantity < 0 or unit_price < 0:
                flash('Valores negativos não são permitidos.', 'danger')
                return redirect(url_for('orcamento.new_complete'))

            if quantity > 0:
                equipment = Equipment.query.get(int(eq_id))
                if equipment:
                    items_data.append({
                        'type_id': equipment.type_id,
                        'name': equipment.name,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': quantity * unit_price
                    })

    if not name or not items_data:
        flash('Preencha todos os campos obrigatorios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('orcamento.new_complete'))

    try:
        sep_list = SeparationList(
            tour_id=int(tour_id) if tour_id and tour_id.strip() else None,
            name=name,
            observations=observations,
            list_type='complete',
            status='pending',
            created_by=current_user.id,
            company_id=current_user.company_id,
            # Dados do cliente
            client_name=client_name,
            client_phone=client_phone or None,
            client_email=client_email or None,
            client_address=client_address or None,
            # Dados do evento
            event_name=event_name,
            event_date=event_date,
            event_time=event_time or None,
            event_location=event_location or None
        )
        db.session.add(sep_list)
        db.session.flush()

        for item_data in items_data:
            item = SeparationListItem(
                separation_list_id=sep_list.id,
                equipment_type_id=item_data['type_id'],
                item_name=item_data['name'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Orcamento "{name}" criado com sucesso! Aguardando aprovacao.', 'success')
        return redirect(url_for('orcamento.detail', id=sep_list.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar orcamento: {str(e)}', 'danger')
        return redirect(url_for('orcamento.new_complete'))


def create_list_simple():
    from models.equipment_type import EquipmentType

    tour_id = request.form.get('tour_id')
    name = request.form.get('name', '').strip()
    observations = request.form.get('observations', '').strip()
    
    # Dados do cliente
    client_name = request.form.get('client_name', '').strip()
    client_phone = request.form.get('client_phone', '').strip()
    client_email = request.form.get('client_email', '').strip()
    client_address = request.form.get('client_address', '').strip()
    
    # Dados do evento
    event_name = request.form.get('event_name', '').strip()
    event_date_str = request.form.get('event_date', '')
    event_time = request.form.get('event_time', '').strip()
    event_location = request.form.get('event_location', '').strip()

    if not name or len(name) < 3:
        flash('Nome do orçamento deve ter pelo menos 3 caracteres.', 'danger')
        return redirect(url_for('orcamento.new_simple'))
    
    if not client_name:
        flash('Nome do cliente é obrigatório.', 'danger')
        return redirect(url_for('orcamento.new_simple'))
    
    if not event_name:
        flash('Nome do evento é obrigatório.', 'danger')
        return redirect(url_for('orcamento.new_simple'))
    
    if not event_date_str:
        flash('Data do evento é obrigatória.', 'danger')
        return redirect(url_for('orcamento.new_simple'))

    # Converter data
    try:
        from datetime import datetime as dt
        event_date = dt.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Data do evento inválida.', 'danger')
        return redirect(url_for('orcamento.new_simple'))

    try:
        total_value = float(request.form.get('total_value', 0))
        if total_value < 0:
            flash('Valor total não pode ser negativo.', 'danger')
            return redirect(url_for('orcamento.new_simple'))
    except (ValueError, TypeError):
        flash('Valor total inválido.', 'danger')
        return redirect(url_for('orcamento.new_simple'))

    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            eq_id = key.replace('quantity-', '')
            try:
                quantity = int(request.form.get(f'quantity-{eq_id}', 0))
            except (ValueError, TypeError):
                continue

            if quantity < 0:
                flash('Quantidade não pode ser negativa.', 'danger')
                return redirect(url_for('orcamento.new_simple'))

            if quantity > 0:
                equipment = Equipment.query.get(int(eq_id))
                if equipment:
                    items_data.append({
                        'type_id': equipment.type_id,
                        'name': equipment.name,
                        'quantity': quantity
                    })

    if not items_data or total_value <= 0:
        flash('Preencha todos os campos obrigatorios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('orcamento.new_simple'))

    try:
        sep_list = SeparationList(
            tour_id=int(tour_id) if tour_id and tour_id.strip() else None,
            name=name,
            observations=observations,
            list_type='simple',
            total_value=float(total_value),
            status='pending',
            created_by=current_user.id,
            company_id=current_user.company_id,
            # Dados do cliente
            client_name=client_name,
            client_phone=client_phone or None,
            client_email=client_email or None,
            client_address=client_address or None,
            # Dados do evento
            event_name=event_name,
            event_date=event_date,
            event_time=event_time or None,
            event_location=event_location or None
        )
        db.session.add(sep_list)
        db.session.flush()

        for item_data in items_data:
            item = SeparationListItem(
                separation_list_id=sep_list.id,
                equipment_type_id=item_data['type_id'],
                item_name=item_data['name'],
                quantity=item_data['quantity']
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Orcamento "{name}" criado com sucesso! Aguardando aprovacao.', 'success')
        return redirect(url_for('orcamento.detail', id=sep_list.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar orcamento: {str(e)}', 'danger')
        return redirect(url_for('orcamento.new_simple'))


def get_category_icon(category_name):
    icons = {
        'Som': '🎤',
        'Luz': '💡',
        'Materiais': '🔧',
        'Instrumentos': '🎸'
    }
    return icons.get(category_name, '📦')


@orcamento_bp.route('/<int:id>/pdf')
@login_required
@admin_required
def generate_pdf(id):
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    total_units = sum(item.quantity for item in sep_list.items)
    subtotal = sum(item.total_price or 0 for item in sep_list.items)

    return render_template(
        'pdf/orcamento_view.html',
        lista=sep_list,
        company=current_user.company,
        total_units=total_units,
        subtotal=subtotal,
        now=datetime.utcnow()
    )
