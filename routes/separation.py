from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.separation_list import SeparationList, SeparationListItem
from models.tour import Tour, TourEquipment
from models.equipment import Equipment
from models.category import Category
from datetime import datetime

separation_bp = Blueprint('separation', __name__, url_prefix='/separation')

@separation_bp.route('/')
@login_required
def index():
    """Lista todas as listas de separação (tabs: pendentes, aprovadas, rejeitadas)"""
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

@separation_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Criar nova lista de separação"""
    if request.method == 'GET':
        # Buscar tours ativas
        tours = Tour.query.filter_by(
            company_id=current_user.company_id,
            is_active=True,
            status='active'
        ).order_by(Tour.start_date.desc()).all()
        
        # Buscar equipamentos disponíveis por categoria
        categories = Category.query.filter_by(
            company_id=current_user.company_id
        ).all()
        
        equipment_by_category = {}
        for cat in categories:
            items = Equipment.query.filter_by(
                category_id=cat.id,
                company_id=current_user.company_id,
                is_active=True,
                status='available'
            ).order_by(Equipment.code).all()
            
            if items:
                equipment_by_category[cat.name] = {
                    'icon': get_category_icon(cat.name),
                    'items': items,
                    'count': len(items)
                }
        
        return render_template('separation/new.html',
                             tours=tours,
                             equipment_by_category=equipment_by_category)
    
    # POST: Criar lista
    tour_id = request.form.get('tour_id')
    name = request.form.get('name')
    description = request.form.get('description', '')
    equipment_ids = request.form.getlist('equipment_ids')
    
    if not tour_id or not name or not equipment_ids:
        flash('Preencha todos os campos obrigatórios.', 'danger')
        return redirect(url_for('separation.new'))
    
    # Criar lista
    sep_list = SeparationList(
        tour_id=tour_id,
        name=name,
        description=description,
        status='pending',
        created_by=current_user.id,
        company_id=current_user.company_id
    )
    db.session.add(sep_list)
    db.session.flush()
    
    # Adicionar itens
    for eq_id in equipment_ids:
        item = SeparationListItem(
            separation_list_id=sep_list.id,
            equipment_id=int(eq_id)
        )
        db.session.add(item)
    
    db.session.commit()
    flash(f'Lista "{name}" criada com sucesso! Aguardando aprovação.', 'success')
    return redirect(url_for('separation.detail', id=sep_list.id))

@separation_bp.route('/<int:id>')
@login_required
def detail(id):
    """Visualizar detalhes da lista de separação"""
    sep_list = SeparationList.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    # Agrupar itens por categoria
    items = sep_list.items.all()
    equipment_by_category = {}
    
    for item in items:
        eq = item.equipment
        if eq and eq.category:
            cat_name = eq.category.name
            if cat_name not in equipment_by_category:
                equipment_by_category[cat_name] = {
                    'icon': get_category_icon(cat_name),
                    'items': []
                }
            equipment_by_category[cat_name]['items'].append(item)
    
    return render_template('separation/detail.html',
                          sep_list=sep_list,
                          equipment_by_category=equipment_by_category)

@separation_bp.route('/<int:id>/approve', methods=['POST'])
@login_required
def approve(id):
    """Aprovar lista de separação e alocar equipamentos automaticamente"""
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
        # Aprovar lista
        sep_list.status = 'approved'
        sep_list.approved_by = current_user.id
        sep_list.approved_at = datetime.utcnow()
        sep_list.approval_notes = request.form.get('notes', '')
        
        # Alocar equipamentos automaticamente
        items = sep_list.items.all()
        allocated_count = 0
        unavailable_items = []
        
        for item in items:
            eq = item.equipment
            if not eq:
                continue
            
            # Verificar se já está alocado em QUALQUER tour
            existing = TourEquipment.query.filter_by(
                equipment_id=eq.id,
                returned_at=None
            ).first()
            
            if existing:
                unavailable_items.append(f"{eq.code} (já em tour)")
                continue
            
            # Verificar se está disponível
            if eq.status != 'available':
                unavailable_items.append(f"{eq.code} ({eq.status})")
                continue
            
            # Criar TourEquipment (ALOCAÇÃO)
            tour_eq = TourEquipment(
                tour_id=sep_list.tour_id,
                equipment_id=eq.id,
                allocated_at=datetime.utcnow(),
                allocated_by=current_user.id,
                current_status='in_company'
            )
            db.session.add(tour_eq)
            
            # Atualizar status do equipamento
            eq.status = 'in_tour'
            allocated_count += 1
        
        # Commit transacional
        db.session.commit()
        
        # Mensagens
        if allocated_count > 0:
            flash(f'Lista aprovada! {allocated_count} equipamentos alocados automaticamente.', 'success')
        
        if unavailable_items:
            flash(f'Atenção: {len(unavailable_items)} itens não puderam ser alocados: {", ".join(unavailable_items[:3])}', 'warning')
        
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


def get_category_icon(category_name):
    """Retorna emoji do ícone da categoria"""
    icons = {
        'Som': '🎤',
        'Luz': '💡',
        'Materiais': '🔧',
        'Instrumentos': '🎸'
    }
    return icons.get(category_name, '📦')
