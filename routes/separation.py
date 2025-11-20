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
    """Lista todas as listas de separação (tabs: pendentes, aprovadas, rejeitadas)
    
    SEGURANÇA: Apenas admins podem acessar listas de separação.
    """
    # Bloqueio para técnicos
    if current_user.role != 'admin':
        flash('Acesso negado. Use a lista de trabalho.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    status_filter = request.args.get('status', 'pending')
    
    lists = SeparationList.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status=status_filter
    ).order_by(SeparationList.created_at.desc()).all()
    
    # Contadores para tabs
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
    """Escolher tipo de lista a criar
    
    SEGURANÇA: Apenas admins podem criar listas de separação.
    """
    if current_user.role != 'admin':
        flash('Apenas administradores podem criar listas de separação.', 'danger')
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
    """Criar lista COMPLETA (com preços detalhados)
    
    SEGURANÇA: Apenas admins.
    """
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    if request.method == 'POST':
        return create_list_complete()
    
    # GET: Mostrar formulário
    from models.equipment_type import EquipmentType
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()
    
    # Buscar tipos de equipamento por categoria
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
            # Contar disponíveis de cada tipo
            types_with_count = []
            for t in types:
                available_count = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    status='available',
                    is_active=True
                ).count()
                
                total_count = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    is_active=True
                ).count()
                
                types_with_count.append({
                    'id': t.id,
                    'name': t.name,
                    'available': available_count,
                    'total': total_count
                })
            
            if types_with_count:
                types_by_category[cat.name] = {
                    'icon': get_category_icon(cat.name),
                    'types': types_with_count
                }
    
    return render_template('separation/new_complete.html',
                         tours=tours,
                         types_by_category=types_by_category)

@separation_bp.route('/new/simple', methods=['GET', 'POST'])
@login_required
def new_simple():
    """Criar lista SIMPLES (só valor total)
    
    SEGURANÇA: Apenas admins.
    """
    if current_user.role != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    if request.method == 'POST':
        return create_list_simple()
    
    # GET: Mostrar formulário
    from models.equipment_type import EquipmentType
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.start_date.desc()).all()
    
    # Buscar tipos de equipamento por categoria
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
            # Contar disponíveis de cada tipo
            types_with_count = []
            for t in types:
                available_count = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    status='available',
                    is_active=True
                ).count()
                
                total_count = Equipment.query.filter_by(
                    type_id=t.id,
                    company_id=current_user.company_id,
                    is_active=True
                ).count()
                
                types_with_count.append({
                    'id': t.id,
                    'name': t.name,
                    'available': available_count,
                    'total': total_count
                })
            
            if types_with_count:
                types_by_category[cat.name] = {
                    'icon': get_category_icon(cat.name),
                    'types': types_with_count
                }
    
    return render_template('separation/new_simple.html',
                         tours=tours,
                         types_by_category=types_by_category)

@separation_bp.route('/<int:id>')
@login_required
def detail(id):
    """Visualizar detalhes da lista de separação
    
    SEGURANÇA CRÍTICA: Apenas admins podem acessar SeparationList.
    Técnicos usam WorkList (sem preços) em /work-list/
    """
    # BLOQUEIO TOTAL: Apenas admins acessam listas de separação
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
    """Aprovar lista e criar WorkList para técnicos"""
    # Validar permissão de admin
    if current_user.role != 'admin':
        flash('Apenas administradores podem aprovar listas.', 'danger')
        return redirect(url_for('separation.detail', id=id))
    
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if sep_list.status != 'pending':
        flash('Esta lista já foi processada.', 'warning')
        return redirect(url_for('separation.detail', id=id))
    
    try:
        # 1. Aprovar SeparationList
        sep_list.status = 'approved'
        sep_list.approved_by = current_user.id
        sep_list.approved_at = datetime.utcnow()
        sep_list.approval_notes = request.form.get('notes', '')
        
        # 2. Criar WorkList (SEM preços) para técnicos
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
        db.session.flush()  # Gerar ID
        
        # 3. Copiar itens (SEM preços)
        for item in sep_list.items:
            work_item = WorkListItem(
                work_list_id=work_list.id,
                item_name=item.item_name,
                quantity=item.quantity,
                separated=False
            )
            db.session.add(work_item)
        
        db.session.commit()
        flash(f'Lista aprovada! Lista de trabalho #{work_list.id} criada para técnicos.', 'success')
        return redirect(url_for('separation.detail', id=id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.detail', id=id))

@separation_bp.route('/<int:id>/reject', methods=['POST'])
@login_required
def reject(id):
    """Rejeitar lista de separação"""
    # Validar permissão de admin
    if current_user.role != 'admin':
        flash('Apenas administradores podem rejeitar listas.', 'danger')
        return redirect(url_for('separation.detail', id=id))
    
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if sep_list.status != 'pending':
        flash('Esta lista já foi processada.', 'warning')
        return redirect(url_for('separation.detail', id=id))
    
    reason = request.form.get('reason', '')
    if not reason:
        flash('Informe o motivo da rejeição.', 'danger')
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
    """Toggle checkbox de item (para conferência visual)"""
    item = SeparationListItem.query.filter_by(
        id=item_id,
        separation_list_id=id
    ).first_or_404()
    
    item.is_checked = not item.is_checked
    db.session.commit()
    
    return jsonify({'success': True, 'is_checked': item.is_checked})


def create_list_complete():
    """Processa criação de lista COMPLETA (com preços detalhados)"""
    from models.equipment_type import EquipmentType
    
    tour_id = request.form.get('tour_id')
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    # Itens: format item-{type_id} => quantity, unit_price
    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            type_id = key.replace('quantity-', '')
            quantity = request.form.get(f'quantity-{type_id}')
            unit_price = request.form.get(f'unit_price-{type_id}')
            
            if quantity and int(quantity) > 0:
                eq_type = EquipmentType.query.get(int(type_id))
                if eq_type:
                    items_data.append({
                        'type_id': int(type_id),
                        'name': eq_type.name,
                        'quantity': int(quantity),
                        'unit_price': float(unit_price) if unit_price else 0,
                        'total_price': int(quantity) * (float(unit_price) if unit_price else 0)
                    })
    
    if not tour_id or not name or not items_data:
        flash('Preencha todos os campos obrigatórios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('separation.new_complete'))
    
    try:
        # Criar lista
        sep_list = SeparationList(
            tour_id=tour_id,
            name=name,
            description=description,
            list_type='complete',
            status='pending',
            created_by=current_user.id,
            company_id=current_user.company_id
        )
        db.session.add(sep_list)
        db.session.flush()
        
        # Adicionar itens
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
        flash(f'Lista completa "{name}" criada com sucesso! Aguardando aprovação.', 'success')
        return redirect(url_for('separation.detail', id=sep_list.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.new_complete'))


def create_list_simple():
    """Processa criação de lista SIMPLES (só valor total)"""
    from models.equipment_type import EquipmentType
    
    tour_id = request.form.get('tour_id')
    name = request.form.get('name')
    description = request.form.get('description', '')
    total_value = request.form.get('total_value')
    
    # Itens: format item-{type_id} => quantity
    items_data = []
    for key in request.form.keys():
        if key.startswith('quantity-'):
            type_id = key.replace('quantity-', '')
            quantity = request.form.get(f'quantity-{type_id}')
            
            if quantity and int(quantity) > 0:
                eq_type = EquipmentType.query.get(int(type_id))
                if eq_type:
                    items_data.append({
                        'type_id': int(type_id),
                        'name': eq_type.name,
                        'quantity': int(quantity)
                    })
    
    if not tour_id or not name or not items_data or not total_value:
        flash('Preencha todos os campos obrigatórios e adicione pelo menos um item.', 'danger')
        return redirect(url_for('separation.new_simple'))
    
    try:
        # Criar lista
        sep_list = SeparationList(
            tour_id=tour_id,
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
        
        # Adicionar itens (sem preços)
        for item_data in items_data:
            item = SeparationListItem(
                separation_list_id=sep_list.id,
                equipment_type_id=item_data['type_id'],
                item_name=item_data['name'],
                quantity=item_data['quantity']
            )
            db.session.add(item)
        
        db.session.commit()
        flash(f'Lista simples "{name}" criada com sucesso! Aguardando aprovação.', 'success')
        return redirect(url_for('separation.detail', id=sep_list.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar lista: {str(e)}', 'danger')
        return redirect(url_for('separation.new_simple'))


def get_category_icon(category_name):
    """Retorna emoji do ícone da categoria"""
    icons = {
        'Som': '🎤',
        'Luz': '💡',
        'Materiais': '🔧',
        'Instrumentos': '🎸'
    }
    return icons.get(category_name, '📦')
