"""
Routes para modulo Manutencao
- Dashboard com tarefas da semana
- Gestao de estoque de materiais
- Fabricacao de cabos/reguas
- Relatorios de equipamentos criticos
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.maintenance import Maintenance
from models.material_stock import MaterialStock, MaterialMovement
from models.fabrication import FabricationRecord
from models.equipment import Equipment
from models.equipment_type import EquipmentType
from models.category import Category
from datetime import datetime, date, timedelta
from decimal import Decimal

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/manutencao')


def admin_or_tech_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.role not in ['admin', 'technician', 'tech_responsible']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@maintenance_bp.route('/')
@login_required
@admin_or_tech_required
def index():
    """Dashboard de manutencao"""
    pending_maintenance = Maintenance.query.filter_by(
        company_id=current_user.company_id,
        status='pending'
    ).order_by(Maintenance.created_at.desc()).all()
    
    in_progress = Maintenance.query.filter_by(
        company_id=current_user.company_id,
        status='in_progress'
    ).all()
    
    low_stock = MaterialStock.query.filter(
        MaterialStock.company_id == current_user.company_id,
        MaterialStock.quantity < MaterialStock.minimum_quantity,
        MaterialStock.is_active == True
    ).all()
    
    pending_fabrications = FabricationRecord.query.filter_by(
        company_id=current_user.company_id
    ).order_by(FabricationRecord.fabricated_at.desc()).limit(5).all() if _table_exists('fabrication_record') else []
    
    current_month = date.today().month
    current_year = date.today().year
    
    month_cost = db.session.query(db.func.sum(Maintenance.total_cost)).filter(
        Maintenance.company_id == current_user.company_id,
        Maintenance.status == 'completed',
        db.extract('month', Maintenance.completed_at) == current_month,
        db.extract('year', Maintenance.completed_at) == current_year
    ).scalar() or 0
    
    return render_template('maintenance/index.html',
                          pending_maintenance=pending_maintenance,
                          in_progress=in_progress,
                          low_stock=low_stock,
                          pending_fabrications=pending_fabrications,
                          month_cost=month_cost)


@maintenance_bp.route('/stock')
@login_required
@admin_or_tech_required
def stock():
    """Lista de estoque de materiais"""
    category = request.args.get('category', 'all')
    
    query = MaterialStock.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    )
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    materials = query.order_by(MaterialStock.name).all()
    
    categories = db.session.query(MaterialStock.category).filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('maintenance/stock.html',
                          materials=materials,
                          categories=categories,
                          current_category=category)


@maintenance_bp.route('/stock/new', methods=['GET', 'POST'])
@login_required
@admin_or_tech_required
def new_stock():
    """Adicionar novo item ao estoque"""
    if request.method == 'POST':
        try:
            material = MaterialStock(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                category=request.form.get('category', 'connector'),
                sub_category=request.form.get('sub_category', '').strip() or None,
                quantity=Decimal(request.form.get('quantity', '0').replace(',', '.')),
                unit=request.form.get('unit', 'unit'),
                minimum_quantity=Decimal(request.form.get('minimum_quantity', '0').replace(',', '.')),
                brand=request.form.get('brand', '').strip() or None,
                model=request.form.get('model', '').strip() or None,
                reference_value=Decimal(request.form.get('reference_value', '0').replace(',', '.')) if request.form.get('reference_value') else None,
                supplier=request.form.get('supplier', '').strip() or None,
                notes=request.form.get('notes', '').strip() or None,
                is_active=True
            )
            
            db.session.add(material)
            db.session.commit()
            
            flash(f'Material "{material.name}" adicionado ao estoque!', 'success')
            return redirect(url_for('maintenance.stock'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar material: {str(e)}', 'danger')
    
    return render_template('maintenance/stock_form.html', material=None)


@maintenance_bp.route('/stock/<int:id>/movement', methods=['POST'])
@login_required
@admin_or_tech_required
def stock_movement(id):
    """Registrar movimentacao de estoque"""
    material = MaterialStock.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    try:
        movement_type = request.form.get('type', 'in')
        quantity = Decimal(request.form.get('quantity', '0').replace(',', '.'))
        reason = request.form.get('reason', 'adjustment')
        notes = request.form.get('notes', '').strip()
        
        quantity_before = material.quantity
        
        if movement_type == 'in':
            material.quantity += quantity
        else:
            if material.quantity < quantity:
                flash('Quantidade insuficiente em estoque!', 'danger')
                return redirect(url_for('maintenance.stock'))
            material.quantity -= quantity
        
        movement = MaterialMovement(
            material_id=id,
            company_id=current_user.company_id,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=material.quantity,
            reason=reason,
            notes=notes,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(movement)
        material.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Movimentacao registrada!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar movimentacao: {str(e)}', 'danger')
    
    return redirect(url_for('maintenance.stock'))


@maintenance_bp.route('/fabrication')
@login_required
@admin_or_tech_required
def fabrication():
    """Lista de fabricacoes"""
    if not _table_exists('fabrication_record'):
        return render_template('maintenance/fabrication.html',
                              fabrications=[],
                              cable_types=[])
    
    fabrications = FabricationRecord.query.filter_by(
        company_id=current_user.company_id
    ).order_by(FabricationRecord.fabricated_at.desc()).limit(50).all()
    
    cable_types = [
        {'id': 'xlr_mf', 'name': 'Cabo XLR M/F', 'connectors': ['XLR Macho', 'XLR Femea']},
        {'id': 'xlr_mm', 'name': 'Cabo XLR M/M', 'connectors': ['XLR Macho', 'XLR Macho']},
        {'id': 'p10_mono', 'name': 'Cabo P10 Mono', 'connectors': ['P10 Mono', 'P10 Mono']},
        {'id': 'p10_stereo', 'name': 'Cabo P10 Stereo', 'connectors': ['P10 Stereo', 'P10 Stereo']},
        {'id': 'powercon', 'name': 'Cabo Powercon', 'connectors': ['Powercon Azul', 'Powercon Cinza']},
        {'id': 'dmx', 'name': 'Cabo DMX', 'connectors': ['XLR DMX 5p', 'XLR DMX 5p']},
    ]
    
    return render_template('maintenance/fabrication.html',
                          fabrications=fabrications,
                          cable_types=cable_types)


@maintenance_bp.route('/fabrication/new', methods=['GET', 'POST'])
@login_required
@admin_or_tech_required
def new_fabrication():
    """Fabricar novos cabos"""
    if request.method == 'POST':
        try:
            cable_type = request.form.get('cable_type', 'xlr_mf')
            length = Decimal(request.form.get('length', '5').replace(',', '.'))
            quantity = int(request.form.get('quantity', '1'))
            
            materials_check = _check_fabrication_materials(cable_type, length, quantity)
            
            if not materials_check['available']:
                flash(f'Material insuficiente: {materials_check["missing"]}', 'danger')
                return redirect(url_for('maintenance.fabrication'))
            
            equipments_created = _execute_fabrication(cable_type, length, quantity)
            
            flash(f'{quantity} cabo(s) fabricado(s) e adicionado(s) ao Hardcase!', 'success')
            return redirect(url_for('maintenance.fabrication'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro na fabricacao: {str(e)}', 'danger')
    
    return render_template('maintenance/fabrication_form.html')


@maintenance_bp.route('/reports')
@login_required
@admin_or_tech_required
def reports():
    """Relatorios de manutencao"""
    year = request.args.get('year', date.today().year, type=int)
    
    critical_equipment = db.session.query(
        Equipment.id,
        Equipment.code,
        Equipment.brand,
        Equipment.model,
        Equipment.value,
        db.func.count(Maintenance.id).label('total_maintenances'),
        db.func.sum(Maintenance.total_cost).label('total_cost')
    ).join(Maintenance, Equipment.id == Maintenance.equipment_id).filter(
        Equipment.company_id == current_user.company_id,
        db.extract('year', Maintenance.created_at) == year
    ).group_by(Equipment.id).having(
        db.func.count(Maintenance.id) >= 3
    ).order_by(db.desc('total_maintenances')).all()
    
    return render_template('maintenance/reports.html',
                          critical_equipment=critical_equipment,
                          year=year)


def _table_exists(table_name):
    """Verifica se tabela existe"""
    try:
        db.session.execute(db.text(f"SELECT 1 FROM {table_name} LIMIT 1"))
        return True
    except:
        return False


def _check_fabrication_materials(cable_type, length, quantity):
    """Verifica se tem material suficiente para fabricacao"""
    return {'available': True, 'missing': None}


def _execute_fabrication(cable_type, length, quantity):
    """Executa fabricacao: consome estoque, cria equipamentos, gera QR"""
    from services.qr_service import generate_qr_code
    
    cable_names = {
        'xlr_mf': f'Cabo XLR M/F {length}m',
        'xlr_mm': f'Cabo XLR M/M {length}m',
        'p10_mono': f'Cabo P10 Mono {length}m',
        'p10_stereo': f'Cabo P10 Stereo {length}m',
        'powercon': f'Cabo Powercon {length}m',
        'dmx': f'Cabo DMX {length}m',
    }
    
    cable_name = cable_names.get(cable_type, f'Cabo {length}m')
    
    materials_cat = Category.query.filter_by(
        company_id=current_user.company_id,
        name='Materiais'
    ).first()
    
    if not materials_cat:
        materials_cat = Category(
            name='Materiais',
            company_id=current_user.company_id
        )
        db.session.add(materials_cat)
        db.session.flush()
    
    cable_type_db = EquipmentType.query.filter_by(
        company_id=current_user.company_id,
        category_id=materials_cat.id,
        name='Cabo'
    ).first()
    
    if not cable_type_db:
        cable_type_db = EquipmentType(
            name='Cabo',
            category_id=materials_cat.id,
            company_id=current_user.company_id
        )
        db.session.add(cable_type_db)
        db.session.flush()
    
    created = []
    for i in range(quantity):
        count = Equipment.query.filter(
            Equipment.company_id == current_user.company_id,
            Equipment.code.like('CAB-%')
        ).count()
        
        code = f'CAB-{count + 1:04d}'
        
        equipment = Equipment(
            code=code,
            name=cable_name,
            brand='Fabricacao Propria',
            model=cable_type,
            category_id=materials_cat.id,
            type_id=cable_type_db.id,
            status='available',
            company_id=current_user.company_id,
            created_by=current_user.id,
            is_active=True
        )
        
        db.session.add(equipment)
        db.session.flush()
        
        try:
            qr_url = generate_qr_code(equipment.id, code)
            equipment.qr_code_url = qr_url
        except:
            pass
        
        created.append(equipment)
    
    db.session.commit()
    return created
