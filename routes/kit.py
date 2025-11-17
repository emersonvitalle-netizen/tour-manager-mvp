from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from main import db
from models.kit import Kit, KitRequirement
from models.equipment import Equipment

kit_bp = Blueprint('kit', __name__, url_prefix='/kit')

@kit_bp.route('/')
@login_required
def list_kits():
    kits = Kit.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Kit.name).all()

    return render_template('kit/list.html', kits=kits)

@kit_bp.route('/<int:id>')
@login_required
def detail_kit(id):
    kit = Kit.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('kit/detail.html', kit=kit)

@kit_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_kit():
    if current_user.role != 'admin':
        flash('Apenas administradores podem criar kits.', 'danger')
        return redirect(url_for('kit.list_kits'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '').strip()

        kit = Kit(
            name=name,
            description=description if description else None,
            company_id=current_user.company_id,
            created_by=current_user.id
        )
        db.session.add(kit)
        db.session.flush()

        equipment_names = request.form.getlist('equipment_name[]')
        quantities = request.form.getlist('quantity[]')

        for eq_name, qty in zip(equipment_names, quantities):
            if eq_name.strip():
                req = KitRequirement(
                    kit_id=kit.id,
                    equipment_name=eq_name.strip(),
                    quantity=int(qty) if qty else 1
                )
                db.session.add(req)

        db.session.commit()
        flash(f'Kit "{name}" criado com sucesso!', 'success')
        return redirect(url_for('kit.detail_kit', id=kit.id))

    equipment_list = Equipment.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Equipment.name).all()

    return render_template('kit/new.html', equipment_list=equipment_list)

@kit_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_kit(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem deletar kits.', 'danger')
        return redirect(url_for('kit.list_kits'))

    kit = Kit.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    kit_name = kit.name
    kit.is_active = False

    db.session.commit()

    flash(f'Kit "{kit_name}" removido com sucesso.', 'success')
    return redirect(url_for('kit.list_kits'))