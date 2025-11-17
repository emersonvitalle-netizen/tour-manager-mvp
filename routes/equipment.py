from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models.equipment import Equipment
from models.category import Category
from models.equipment_type import EquipmentType
from models.maintenance import Maintenance
from datetime import datetime
from sqlalchemy import or_
import os

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@equipment_bp.route('/')
@login_required
def list_equipment():
    equipments = Equipment.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Equipment.code).all()

    return render_template('equipment/list.html', equipments=equipments)

@equipment_bp.route('/<int:id>')
@login_required
def detail_equipment(id):
    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    maintenances = Maintenance.query.filter_by(
        equipment_id=id
    ).order_by(Maintenance.created_at.desc()).all()

    return render_template('equipment/detail.html', 
                         equipment=equipment,
                         maintenances=maintenances)

@equipment_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_equipment():
    if current_user.role != 'admin':
        flash('Apenas administradores podem cadastrar equipamentos.', 'danger')
        return redirect(url_for('equipment.list_equipment'))

    if request.method == 'POST':
        name = request.form.get('name')
        quantity = int(request.form.get('quantity', 1))
        custom_prefix = request.form.get('custom_prefix', '').strip().upper()

        category_id = request.form.get('category_id')
        type_id = request.form.get('type_id')
        custom_type_name = request.form.get('custom_type_name', '').strip()

        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        notes = request.form.get('notes', '').strip()

        final_type_id = None

        if custom_type_name and category_id:
            eq_type = EquipmentType.query.filter_by(
                name=custom_type_name,
                category_id=category_id,
                company_id=current_user.company_id
            ).first()

            if not eq_type:
                eq_type = EquipmentType(
                    name=custom_type_name,
                    category_id=category_id,
                    company_id=current_user.company_id,
                    is_system=False
                )
                db.session.add(eq_type)
                db.session.flush()

            final_type_id = eq_type.id
        elif type_id:
            final_type_id = int(type_id)

        if custom_prefix:
            prefix = custom_prefix
        else:
            prefix = ''.join([c for c in name if c.isupper()])[:3]
            if not prefix:
                prefix = name[:3].upper()

        created = []
        for i in range(quantity):
            counter = 1
            while True:
                code = f"{prefix}-{counter:03d}"
                existing = Equipment.query.filter_by(
                    code=code, 
                    company_id=current_user.company_id
                ).first()
                if not existing:
                    break
                counter += 1

            equipment = Equipment(
                name=name,
                code=code,
                prefix=prefix,
                category_id=int(category_id) if category_id else None,
                type_id=final_type_id,
                brand=brand if brand else None,
                model=model if model else None,
                serial_number=serial_number if serial_number else None,
                notes=notes if notes else None,
                status='available',
                company_id=current_user.company_id,
                created_by=current_user.id,
                is_active=True
            )

            db.session.add(equipment)
            db.session.flush()

            equipment.generate_qr_code()

            created.append(code)

        db.session.commit()

        flash(f'{quantity} equipamento(s) cadastrado(s): {", ".join(created)}', 'success')
        return redirect(url_for('equipment.list_equipment'))

    categories = Category.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Category.name).all()

    return render_template('equipment/new.html', categories=categories)

@equipment_bp.route('/get-types/<int:category_id>')
@login_required
def get_types(category_id):
    types = EquipmentType.query.filter_by(
        category_id=category_id,
        company_id=current_user.company_id,
        is_active=True
    ).order_by(EquipmentType.name).all()

    return jsonify([{
        'id': t.id,
        'name': t.name
    } for t in types])

@equipment_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_equipment(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem editar equipamentos.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if request.method == 'POST':
        equipment.name = request.form.get('name')
        equipment.brand = request.form.get('brand', '').strip() or None
        equipment.model = request.form.get('model', '').strip() or None
        equipment.serial_number = request.form.get('serial_number', '').strip() or None
        equipment.notes = request.form.get('notes', '').strip() or None

        value_str = request.form.get('value', '').strip()
        if value_str:
            equipment.value = float(value_str)

        purchase_date_str = request.form.get('purchase_date', '').strip()
        if purchase_date_str:
            equipment.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{equipment.code}_{file.filename}")
                filepath = os.path.join('static', 'uploads', filename)
                os.makedirs('static/uploads', exist_ok=True)
                file.save(filepath)
                equipment.primary_photo_url = f"/static/uploads/{filename}"

        db.session.commit()

        flash('Equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('equipment.detail_equipment', id=equipment.id))

    categories = Category.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Category.name).all()

    return render_template('equipment/edit.html', 
                         equipment=equipment,
                         categories=categories)

@equipment_bp.route('/<int:id>/upload-photo', methods=['POST'])
@login_required
def upload_photo(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem adicionar fotos.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{equipment.code}_{file.filename}")
            filepath = os.path.join('static', 'uploads', filename)
            os.makedirs('static/uploads', exist_ok=True)
            file.save(filepath)
            equipment.primary_photo_url = f"/static/uploads/{filename}"
            db.session.commit()
            flash('Foto adicionada com sucesso!', 'success')

    return redirect(url_for('equipment.detail_equipment', id=id))

@equipment_bp.route('/<int:id>/update-serial', methods=['POST'])
@login_required
def update_serial(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem atualizar o número de série.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    serial = request.form.get('serial_number', '').strip()
    if serial:
        equipment.serial_number = serial
        db.session.commit()
        flash('Número de série atualizado!', 'success')

    return redirect(url_for('equipment.detail_equipment', id=id))

@equipment_bp.route('/<int:id>/send-to-maintenance', methods=['POST'])
@login_required
def send_to_maintenance(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem enviar para manutenção.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    problem = request.form.get('problem_description', '').strip()

    if not problem:
        flash('Descreva o problema!', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    maintenance = Maintenance(
        equipment_id=id,
        problem_description=problem,
        status='in_progress',
        company_id=current_user.company_id,
        started_by=current_user.id
    )

    equipment.status = 'maintenance'

    db.session.add(maintenance)
    db.session.commit()

    flash('Equipamento enviado para manutenção!', 'success')
    return redirect(url_for('equipment.detail_equipment', id=id))

@equipment_bp.route('/<int:id>/forward-to-external', methods=['POST'])
@login_required
def forward_to_external(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem encaminhar para conserto externo.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    external_company = request.form.get('external_company', '').strip()
    external_contact = request.form.get('external_contact', '').strip()

    if not external_company:
        flash('Informe a empresa/técnico!', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    maintenance = Maintenance.query.filter_by(
        equipment_id=id,
        status='in_progress'
    ).order_by(Maintenance.started_at.desc()).first()

    if not maintenance:
        flash('Nenhuma manutenção ativa encontrada!', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    maintenance.external_company = external_company
    maintenance.external_contact = external_contact if external_contact else None
    maintenance.status = 'external_repair'
    equipment.status = 'external_repair'

    db.session.commit()

    flash('Equipamento enviado para conserto externo!', 'success')
    return redirect(url_for('equipment.detail_equipment', id=id))

@equipment_bp.route('/<int:id>/complete-maintenance', methods=['POST'])
@login_required
def complete_maintenance(id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem concluir manutenção.', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    equipment = Equipment.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    solution = request.form.get('solution_description', '').strip()
    cost_str = request.form.get('cost', '0').strip()

    maintenance = Maintenance.query.filter(
        Maintenance.equipment_id == id,
        Maintenance.status.in_(['in_progress', 'external_repair'])
    ).order_by(Maintenance.started_at.desc()).first()

    if not maintenance:
        flash('Nenhuma manutenção ativa encontrada!', 'danger')
        return redirect(url_for('equipment.detail_equipment', id=id))

    maintenance.solution_description = solution if solution else None
    maintenance.status = 'completed'
    maintenance.cost = float(cost_str) if cost_str else 0.0
    maintenance.completed_at = datetime.now()
    maintenance.completed_by = current_user.id

    equipment.status = 'available'

    db.session.commit()

    flash('Manutenção concluída! Equipamento liberado.', 'success')
    return redirect(url_for('equipment.detail_equipment', id=id))

@equipment_bp.route('/print-qr')
@login_required
def print_qr():
    equipment_id = request.args.get('equipment_id')

    if equipment_id:
        equipments = Equipment.query.filter_by(
            id=equipment_id,
            company_id=current_user.company_id,
            is_active=True
        ).all()
    else:
        equipments = Equipment.query.filter_by(
            company_id=current_user.company_id,
            is_active=True
        ).order_by(Equipment.code).all()

    return render_template('equipment/print_qr.html', equipments=equipments)

@equipment_bp.route('/scan')
@login_required
def scan():
    return render_template('equipment/scan.html')

@equipment_bp.route('/scan-status')
@login_required
def scan_status():
    return render_template('equipment/scan_status.html')