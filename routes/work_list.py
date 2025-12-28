from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.work_list import WorkList, WorkListItem
from datetime import datetime

work_list_bp = Blueprint('work_list', __name__, url_prefix='/work-list')


@work_list_bp.route('/share/<token>')
def public_view(token):
    """Visualização pública da WorkList (sem login, sem preços)"""
    work_list = WorkList.query.filter_by(share_token=token).first_or_404()
    
    items = work_list.items.all()
    
    return render_template('work_list/public.html', 
                          work_list=work_list, 
                          items=items)

@work_list_bp.route('/')
@login_required
def list_work_lists():
    """Lista todas as work lists da empresa do usuário"""
    work_lists = WorkList.query.filter_by(
        company_id=current_user.company_id
    ).order_by(WorkList.created_at.desc()).all()
    
    return render_template('work_list/list.html', work_lists=work_lists)


@work_list_bp.route('/<int:id>')
@login_required
def detail(id):
    """Detalhes de uma work list"""
    work_list = WorkList.query.get_or_404(id)
    
    # Verificar permissão
    if work_list.company_id != current_user.company_id:
        flash('Acesso negado', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    return render_template('work_list/detail.html', work_list=work_list)


@work_list_bp.route('/<int:id>/mark-separated/<int:item_id>', methods=['POST'])
@login_required
def mark_separated(id, item_id):
    """Marca um item como separado"""
    work_list = WorkList.query.get_or_404(id)
    
    # Verificar permissão
    if work_list.company_id != current_user.company_id:
        flash('Acesso negado', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    item = WorkListItem.query.get_or_404(item_id)
    
    if item.work_list_id != work_list.id:
        flash('Item não pertence a esta lista', 'danger')
        return redirect(url_for('work_list.detail', id=id))
    
    # Alternar status
    item.separated = not item.separated
    if item.separated:
        item.separated_at = datetime.utcnow()
        item.separated_by = current_user.id
    else:
        item.separated_at = None
        item.separated_by = None
    
    db.session.commit()
    
    status = 'separado' if item.separated else 'não separado'
    flash(f'Item marcado como {status}', 'success')
    
    return redirect(url_for('work_list.detail', id=id))


@work_list_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
def complete(id):
    """Marca work list como completa"""
    work_list = WorkList.query.get_or_404(id)
    
    # Verificar permissão
    if work_list.company_id != current_user.company_id:
        flash('Acesso negado', 'danger')
        return redirect(url_for('work_list.list_work_lists'))
    
    # Verificar se todos os itens foram separados
    total = work_list.items.count()
    separated = work_list.items.filter_by(separated=True).count()
    
    if separated < total:
        flash(f'Complete todos os itens antes de finalizar ({separated}/{total} separados)', 'warning')
        return redirect(url_for('work_list.detail', id=id))
    
    work_list.status = 'completed'
    work_list.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Lista de trabalho finalizada!', 'success')
    return redirect(url_for('work_list.list_work_lists'))
