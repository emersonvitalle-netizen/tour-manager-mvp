from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.separation_list import SeparationList, SeparationListItem
from models.work_list import WorkList, WorkListItem
from models.tour import Tour, TourEquipment
from models.equipment import Equipment
from models.category import Category
from datetime import datetime

separation_bp = Blueprint('separation', __name__, url_prefix='/separation')

@separation_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('Acesso negado. Use a lista de trabalho.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))

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

    return render_template('separation/index.html',
                          lists=lists,
                          status_filter=status_filter,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count)

@separation_bp.route('/new')
@login_required
def new():
    if current_user.role != 'admin':
        flash('Apenas administradores podem criar listas de separacao.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))

    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()

    return render_template('separation/choose_type.html', tours=tours)

@separation_bp.route('/new/complete', methods=['GET', 'POST'])
@login_required
def new_complete():
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))

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

    return render_template('separation/new_complete.html',
                         tours=tours,
                         types_by_category=types_by_category)

@separation_bp.route('/new/simple', methods=['GET', 'POST'])
@login_required
def new_simple():
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))

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

    return render_template('separation/new_simple.html',
                         tours=tours,
                         types_by_category=types_by_category)

@separation_bp.route('/<int:id>')
@login_required
def detail(id):
    if current_user.role != 'admin':
        flash('Acesso negado. Use a lista de trabalho para separar equipamentos.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))

    sep_list_orm = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('separation/detail.html', sep_list=sep_list_orm)

@separation_bp.route('/<int:id>/approve', methods=['POST'])
@login_required
def approve(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem aprovar listas.', 'danger')
        return redirect(url_for('separation.detail', id=id))

    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if sep_list.status != 'pending':
        flash('Esta lista ja foi processada.', 'warning')
        return redirect(url_for('separation.detail', id=id))

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
        flash(f'Lista aprovada! Lista de trabalho #{work_list.id} criada para tecnicos.', 'success')
        return redirect(url_for('separation.detail', id=id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.detail', id=id))

@separation_bp.route('/<int:id>/reject', methods=['POST'])
@login_required
def reject(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem rejeitar listas.', 'danger')
        return redirect(url_for('separation.detail', id=id))

    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if sep_list.status != 'pending':
        flash('Esta lista ja foi processada.', 'warning')
        return redirect(url_for('separation.detail', id=id))

    reason = request.form.get('reason', '')
    if not reason:
        flash('Informe o motivo da rejeicao.', 'danger')
        return redirect(url_for('separation.detail', id=id))

    try:
        sep_list.status = 'rejected'
        sep_list.approved_by = current_user.id
        sep_list.approved_at = datetime.utcnow()
        sep_list.rejection_reason = reason

        db.session.commit()
        flash('Lista rejeitada.', 'warning')
        return redirect(url_for('separation.detail', id=id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.detail', id=id))

@separation_bp.route('/<int:id>/toggle-item/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(id, item_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403

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
    name = request.form.get('name')
    description = request.form.get('description', '')

    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            eq_id = key.replace('quantity-', '')
            quantity = request.form.get(f'quantity-{eq_id}')
            unit_price = request.form.get(f'unit_price-{eq_id}')

            if quantity and int(quantity) > 0:
                equipment = Equipment.query.get(int(eq_id))
                if equipment:
                    items_data.append({
                        'type_id': equipment.type_id,
                        'name': equipment.name,
                        'quantity': int(quantity),
                        'unit_price': float(unit_price) if unit_price else 0,
                        'total_price': int(quantity) * (float(unit_price) if unit_price else 0)
                    })

    if not name or not items_data:
        flash('Preencha todos os campos obrigatorios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('separation.new_complete'))

    try:
        sep_list = SeparationList(
            tour_id=int(tour_id) if tour_id and tour_id.strip() else None,
            name=name,
            description=description,
            list_type='complete',
            status='pending',
            created_by=current_user.id,
            company_id=current_user.company_id
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
        flash(f'Lista completa "{name}" criada com sucesso! Aguardando aprovacao.', 'success')
        return redirect(url_for('separation.detail', id=sep_list.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.new_complete'))


def create_list_simple():
    from models.equipment_type import EquipmentType

    tour_id = request.form.get('tour_id')
    name = request.form.get('name')
    description = request.form.get('description', '')
    total_value = request.form.get('total_value')

    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            eq_id = key.replace('quantity-', '')
            quantity = request.form.get(f'quantity-{eq_id}')

            if quantity and int(quantity) > 0:
                equipment = Equipment.query.get(int(eq_id))
                if equipment:
                    items_data.append({
                        'type_id': equipment.type_id,
                        'name': equipment.name,
                        'quantity': int(quantity)
                    })

    if not name or not items_data or not total_value:
        flash('Preencha todos os campos obrigatorios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('separation.new_simple'))

    try:
        sep_list = SeparationList(
            tour_id=int(tour_id) if tour_id and tour_id.strip() else None,
            name=name,
            description=description,
            list_type='simple',
            total_value=float(total_value),
            status='pending',
            created_by=current_user.id,
            company_id=current_user.company_id
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
        flash(f'Lista simples "{name}" criada com sucesso! Aguardando aprovacao.', 'success')
        return redirect(url_for('separation.detail', id=sep_list.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.new_simple'))


def get_category_icon(category_name):
    icons = {
        'Som': '🎤',
        'Luz': '💡',
        'Materiais': '🔧',
        'Instrumentos': '🎸'
    }
    return icons.get(category_name, '📦')


@separation_bp.route('/<int:id>/pdf')
@login_required
def generate_pdf(id):
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('separation.index'))

    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    try:
        from weasyprint import HTML
        import io

        total_units = sum(item.quantity for item in sep_list.items)
        subtotal = sum(item.total_price or 0 for item in sep_list.items)

        template_name = 'pdf/lista_completa.html' if sep_list.list_type == 'complete' else 'pdf/lista_simples.html'

        html_content = render_template(
            template_name,
            lista=sep_list,
            company_name=current_user.company.name if hasattr(current_user, 'company') else 'HARDCASE',
            total_units=total_units,
            subtotal=subtotal,
            now=datetime.utcnow()
        )

        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        from flask import send_file
        filename = f"lista_{sep_list.id}_{sep_list.name.replace(' ', '_')}.pdf"

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except ImportError:
        flash('Biblioteca WeasyPrint nao instalada. Use: pip install weasyprint', 'danger')
        return redirect(url_for('separation.detail', id=id))
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('separation.detail', id=id))