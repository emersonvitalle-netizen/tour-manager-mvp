from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.tour import Tour, Show, TourRequirement, TourEquipment, EquipmentCheckpoint
from models.equipment import Equipment
from models.kit import Kit, KitRequirement
from datetime import datetime

tour_bp = Blueprint('tour', __name__, url_prefix='/tour')


# ============================================
# API: Lista de Tours em JSON (para wizard)
# ============================================
@tour_bp.route('/api/list')
@login_required
def api_list_tours():
    """API: Retorna lista de tours em JSON para wizard"""
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.created_at.desc()).all()

    return jsonify([{
        'id': t.id,
        'name': t.name,
        'artist': t.artist or '',
        'status': t.status,
        'start_date': t.start_date.isoformat() if t.start_date else None
    } for t in tours])


@tour_bp.route('/')
@login_required
def tour_menu():
    from datetime import date

    all_tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.start_date.asc()).all()

    today = date.today()

    proximos = [t for t in all_tours if t.status == 'planned' or (t.start_date and t.start_date > today)]
    em_andamento = [t for t in all_tours if t.status == 'active']
    concluidos = [t for t in all_tours if t.status == 'completed']

    return render_template('tour/menu.html',
                          proximos=proximos,
                          em_andamento=em_andamento,
                          concluidos=concluidos)


@tour_bp.route('/checklist-selection')
@login_required
def checklist_selection():
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True,
        status='active'
    ).order_by(Tour.created_at.desc()).all()

    return render_template('tour/checklist_selection.html', tours=tours)


@tour_bp.route('/<int:tour_id>/checklist')
@login_required
def checklist(tour_id):
    from models.category import Category

    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()

    allocated = TourEquipment.query.filter_by(
        tour_id=tour_id,
        returned_at=None
    ).all()

    equipment_by_category = {}
    total_count = len(allocated)
    checked_count = sum(1 for e in allocated if e.current_status == 'checked')

    for te in allocated:
        if te.equipment and te.equipment.category:
            cat_name = te.equipment.category.name
            if cat_name not in equipment_by_category:
                equipment_by_category[cat_name] = {
                    'icon': '🎤' if cat_name == 'Som' else '💡' if cat_name == 'Luz' else '🔧' if cat_name == 'Materiais' else '🎸',
                    'items': []
                }
            equipment_by_category[cat_name]['items'].append(te)

    return render_template('tour/checklist.html',
                          tour=tour,
                          equipment_by_category=equipment_by_category,
                          total_count=total_count,
                          checked_count=checked_count,
                          pending_count=total_count - checked_count)


@tour_bp.route('/list')
@login_required
def list_tours():
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.created_at.desc()).all()
    return render_template('tour/list.html', tours=tours)


@tour_bp.route('/<int:id>')
@login_required
def detail_tour(id):
    tour = Tour.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    shows = Show.query.filter_by(tour_id=id).order_by(Show.date).all()
    requirements = TourRequirement.query.filter_by(tour_id=id).all()
    allocated_equipment = TourEquipment.query.filter_by(
        tour_id=id, 
        returned_at=None
    ).all()
    return render_template('tour/detail.html', 
                         tour=tour, 
                         shows=shows,
                         requirements=requirements,
                         allocated_equipment=allocated_equipment)


@tour_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_tour():
    if current_user.role != 'admin':
        flash('Apenas administradores podem criar tours.', 'danger')
        return redirect(url_for('tour.list_tours'))
    if request.method == 'POST':
        name = request.form.get('name')
        artist = request.form.get('artist', '').strip()
        description = request.form.get('description', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        tour = Tour(
            name=name,
            artist=artist if artist else None,
            description=description if description else None,
            start_date=datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None,
            end_date=datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None,
            status='planned',
            company_id=current_user.company_id,
            created_by=current_user.id
        )
        db.session.add(tour)
        db.session.commit()
        flash(f'Tour "{name}" criada com sucesso!', 'success')
        return redirect(url_for('tour.detail_tour', id=tour.id))
    return render_template('tour/new.html')


@tour_bp.route('/<int:tour_id>/add-show', methods=['POST'])
@login_required
def add_show(tour_id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem adicionar shows.', 'danger')
        return redirect(url_for('tour.detail_tour', id=tour_id))
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    date_str = request.form.get('date')
    time_str = request.form.get('time', '').strip()
    venue = request.form.get('venue')
    city = request.form.get('city', '').strip()
    show = Show(
        tour_id=tour_id,
        date=datetime.strptime(date_str, '%Y-%m-%d').date(),
        time=datetime.strptime(time_str, '%H:%M').time() if time_str else None,
        venue=venue,
        city=city if city else None,
        status='scheduled'
    )
    db.session.add(show)
    db.session.commit()
    flash(f'Show adicionado com sucesso!', 'success')
    return redirect(url_for('tour.detail_tour', id=tour_id))


@tour_bp.route('/<int:tour_id>/add-requirement', methods=['GET', 'POST'])
@login_required
def add_requirement(tour_id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem adicionar requisições.', 'danger')
        return redirect(url_for('tour.detail_tour', id=tour_id))
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    if request.method == 'POST':
        data = request.json
        requirements = data.get('requirements', [])
        for req in requirements:
            requirement = TourRequirement(
                tour_id=tour_id,
                equipment_name=req['name'],
                brand=req.get('brand'),
                model=req.get('model'),
                quantity=req['quantity']
            )
            db.session.add(requirement)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Requisições adicionadas!'})
    equipment_list = Equipment.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Equipment.name).all()

    kits = Kit.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Kit.name).all()

    return render_template('tour/add_requirement.html', 
                         tour=tour,
                         equipment_list=equipment_list,
                         kits=kits)


@tour_bp.route('/<int:tour_id>/scan-equipment')
@login_required
def scan_equipment(tour_id):
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    return render_template('tour/scan_equipment.html', tour=tour)


@tour_bp.route('/<int:id>/allocate-scanned', methods=['POST'])
@login_required
def allocate_scanned(id):
    tour = Tour.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    data = request.json
    code = data.get('code')
    equipment = Equipment.query.filter_by(
        code=code,
        company_id=current_user.company_id
    ).first()
    if not equipment:
        return jsonify({
            'success': False,
            'message': 'Equipamento não encontrado'
        }), 404
    if equipment.status != 'available':
        return jsonify({
            'success': False,
            'message': f'{equipment.code} não está disponível (status: {equipment.status})'
        }), 400
    existing = TourEquipment.query.filter_by(
        tour_id=id,
        equipment_id=equipment.id,
        returned_at=None
    ).first()
    if existing:
        return jsonify({
            'success': False,
            'message': f'{equipment.code} já está alocado nesta tour'
        }), 400
    allocation = TourEquipment(
        tour_id=id,
        equipment_id=equipment.id,
        allocated_by=current_user.id,
        current_status='in_company'
    )
    equipment.status = 'in_tour'
    db.session.add(allocation)
    db.session.commit()
    return jsonify({
        'success': True,
        'equipment': {
            'id': equipment.id,
            'code': equipment.code,
            'name': equipment.name
        }
    })


@tour_bp.route('/<int:tour_id>/checkpoint/<checkpoint_type>')
@login_required
def checkpoint_scanner(tour_id, checkpoint_type):
    valid_types = ['load_truck', 'unload_show', 'load_truck_return', 'unload_company']
    if checkpoint_type not in valid_types:
        flash('Tipo de checkpoint inválido', 'danger')
        return redirect(url_for('tour.detail_tour', id=tour_id))
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    checkpoint_labels = {
        'load_truck': '🚛 Carregar Caminhão',
        'unload_show': '📦 Descarregar Show',
        'load_truck_return': '🚛 Carregar Retorno',
        'unload_company': '🏢 Descarregar Empresa'
    }
    show = None
    return render_template('tour/checkpoint_scanner.html', 
                         tour=tour,
                         checkpoint_type=checkpoint_type,
                         checkpoint_label=checkpoint_labels[checkpoint_type],
                         show=show)


@tour_bp.route('/<int:tour_id>/register-checkpoint', methods=['POST'])
@login_required
def register_checkpoint(tour_id):
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    data = request.json
    code = data.get('code')
    checkpoint_type = data.get('checkpoint_type')
    show_id = data.get('show_id')
    equipment = Equipment.query.filter_by(
        code=code,
        company_id=current_user.company_id
    ).first()
    if not equipment:
        return jsonify({
            'success': False,
            'message': 'Equipamento não encontrado'
        }), 404
    allocation = TourEquipment.query.filter_by(
        tour_id=tour_id,
        equipment_id=equipment.id,
        returned_at=None
    ).first()
    if not allocation:
        return jsonify({
            'success': False,
            'message': f'{equipment.code} não está alocado nesta tour'
        }), 400
    checkpoint = EquipmentCheckpoint(
        tour_equipment_id=allocation.id,
        checkpoint_type=checkpoint_type,
        show_id=show_id if show_id else None,
        scanned_by=current_user.id,
        timestamp=datetime.utcnow()
    )
    status_map = {
        'load_truck': 'in_truck',
        'unload_show': 'at_show',
        'load_truck_return': 'returning',
        'unload_company': 'in_company'
    }
    allocation.current_status = status_map.get(checkpoint_type, allocation.current_status)
    if checkpoint_type == 'unload_company':
        allocation.returned_at = datetime.utcnow()
        allocation.returned_by = current_user.id
        equipment.status = 'available'
    db.session.add(checkpoint)
    db.session.commit()
    return jsonify({
        'success': True,
        'equipment': {
            'code': equipment.code,
            'name': equipment.name,
            'status': allocation.current_status
        }
    })


@tour_bp.route('/<int:tour_id>/complete', methods=['POST'])
@login_required
def complete_tour(tour_id):
    if current_user.role != 'admin':
        flash('Apenas administradores podem concluir tours.', 'danger')
        return redirect(url_for('tour.detail_tour', id=tour_id))
    tour = Tour.query.filter_by(
        id=tour_id,
        company_id=current_user.company_id
    ).first_or_404()
    allocations = TourEquipment.query.filter_by(
        tour_id=tour_id,
        returned_at=None
    ).all()
    for allocation in allocations:
        allocation.returned_at = datetime.utcnow()
        allocation.returned_by = current_user.id
        allocation.current_status = 'in_company'
        allocation.equipment.status = 'available'
    tour.status = 'completed'
    db.session.commit()
    flash(f'Tour "{tour.name}" concluída! Todos os equipamentos foram liberados.', 'success')
    return redirect(url_for('tour.detail_tour', id=tour_id))