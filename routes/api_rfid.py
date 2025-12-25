from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models.equipment import Equipment
from models.tour import TourEquipment, EquipmentCheckpoint
from services import tag_service
from extensions import db
from datetime import datetime

api_rfid_bp = Blueprint('api_rfid', __name__, url_prefix='/api/v1/rfid')

def api_key_or_login_required(f):
    """Permite autenticação via API key ou sessão Flask-Login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key:
            from models.company import Company
            company = Company.query.filter_by(api_key=api_key, is_active=True).first()
            if not company:
                return jsonify({'error': 'API key inválida'}), 401
            kwargs['company_id'] = company.id
            kwargs['user_id'] = None
        elif current_user.is_authenticated:
            kwargs['company_id'] = current_user.company_id
            kwargs['user_id'] = current_user.id
        else:
            return jsonify({'error': 'Autenticação necessária'}), 401
        return f(*args, **kwargs)
    return decorated

@api_rfid_bp.route('/scan', methods=['POST'])
@api_key_or_login_required
def scan_single(company_id, user_id):
    """
    Processa leitura de uma única tag RFID
    
    Request:
    {
        "epc": "300833B2DDD9014000000001"
    }
    
    Response:
    {
        "success": true,
        "found": true,
        "equipment": { ... }
    }
    """
    data = request.get_json()
    epc = data.get('epc')
    
    if not epc:
        return jsonify({'success': False, 'error': 'EPC não informado'}), 400
    
    equipment = tag_service.find_equipment_by_rfid(epc, company_id)
    
    if equipment:
        return jsonify({
            'success': True,
            'found': True,
            'equipment': {
                'id': equipment.id,
                'code': equipment.code,
                'name': equipment.name,
                'brand': equipment.brand,
                'model': equipment.model,
                'status': equipment.status,
                'category': equipment.category.name if equipment.category else None
            }
        })
    else:
        return jsonify({
            'success': True,
            'found': False,
            'epc': epc,
            'message': 'Tag não associada'
        })

@api_rfid_bp.route('/batch', methods=['POST'])
@api_key_or_login_required
def scan_batch(company_id, user_id):
    """
    Processa leitura em lote de múltiplas tags (portal/antena)
    
    Request:
    {
        "epc_list": ["EPC1", "EPC2", "EPC3", ...],
        "reader_id": "PORTAL-01",
        "location": "Entrada Galpão"
    }
    
    Response:
    {
        "success": true,
        "total": 50,
        "found": 45,
        "not_found": 5,
        "results": [ ... ]
    }
    """
    data = request.get_json()
    epc_list = data.get('epc_list', [])
    reader_id = data.get('reader_id', 'unknown')
    location = data.get('location', '')
    
    if not epc_list:
        return jsonify({'success': False, 'error': 'Lista de EPCs vazia'}), 400
    
    if len(epc_list) > 1000:
        return jsonify({'success': False, 'error': 'Máximo 1000 tags por requisição'}), 400
    
    results = tag_service.batch_lookup_rfid(epc_list, company_id)
    
    found_count = sum(1 for r in results if r['found'])
    
    return jsonify({
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'reader_id': reader_id,
        'location': location,
        'total': len(results),
        'found': found_count,
        'not_found': len(results) - found_count,
        'results': results
    })

@api_rfid_bp.route('/inventory', methods=['POST'])
@api_key_or_login_required
def inventory_check(company_id, user_id):
    """
    Verificação de inventário - compara tags lidas com esperado
    
    Request:
    {
        "epc_list": ["EPC1", "EPC2", ...],
        "expected_codes": ["MSX32-001", "CAI-015", ...],  // opcional
        "location": "Caminhão 01"
    }
    
    Response:
    {
        "success": true,
        "summary": {
            "total_read": 50,
            "identified": 45,
            "unknown_tags": 5,
            "missing": 3  // se expected_codes fornecido
        },
        "identified": [ ... ],
        "unknown_tags": ["EPC-X", "EPC-Y"],
        "missing": ["MSX32-001", ...]  // se expected_codes fornecido
    }
    """
    data = request.get_json()
    epc_list = data.get('epc_list', [])
    expected_codes = data.get('expected_codes', [])
    location = data.get('location', '')
    
    if not epc_list:
        return jsonify({'success': False, 'error': 'Lista de EPCs vazia'}), 400
    
    results = tag_service.batch_lookup_rfid(epc_list, company_id)
    
    identified = []
    unknown_tags = []
    found_codes = set()
    
    for result in results:
        if result['found']:
            identified.append(result['equipment'])
            found_codes.add(result['equipment']['code'])
        else:
            unknown_tags.append(result['epc'])
    
    response = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'location': location,
        'summary': {
            'total_read': len(epc_list),
            'identified': len(identified),
            'unknown_tags': len(unknown_tags)
        },
        'identified': identified,
        'unknown_tags': unknown_tags
    }
    
    if expected_codes:
        expected_set = set(expected_codes)
        missing = list(expected_set - found_codes)
        extra = list(found_codes - expected_set)
        response['summary']['expected'] = len(expected_codes)
        response['summary']['missing'] = len(missing)
        response['summary']['extra'] = len(extra)
        response['missing'] = missing
        response['extra'] = extra
    
    return response

@api_rfid_bp.route('/checkpoint', methods=['POST'])
@api_key_or_login_required
def register_checkpoint(company_id, user_id):
    """
    Registra checkpoint de passagem (portal de entrada/saída)
    
    Request:
    {
        "epc_list": ["EPC1", "EPC2", ...],
        "checkpoint_type": "saida_empresa",  // saida_empresa, chegada_show, etc
        "tour_id": 5,  // opcional
        "location": "Portão Principal",
        "reader_id": "PORTAL-01"
    }
    
    Response:
    {
        "success": true,
        "checkpoints_created": 45,
        "details": [ ... ]
    }
    """
    data = request.get_json()
    epc_list = data.get('epc_list', [])
    checkpoint_type = data.get('checkpoint_type', 'passagem')
    tour_id = data.get('tour_id')
    location = data.get('location', '')
    reader_id = data.get('reader_id', 'unknown')
    
    if not epc_list:
        return jsonify({'success': False, 'error': 'Lista de EPCs vazia'}), 400
    
    results = tag_service.batch_lookup_rfid(epc_list, company_id)
    
    checkpoints_created = 0
    details = []
    
    for result in results:
        if result['found']:
            equipment_id = result['equipment']['id']
            
            checkpoint = EquipmentCheckpoint(
                tour_id=tour_id,
                equipment_id=equipment_id,
                checkpoint_type=checkpoint_type,
                location=location,
                timestamp=datetime.utcnow(),
                scanned_by=user_id,
                condition='ok',
                notes=f'Leitor: {reader_id}'
            )
            db.session.add(checkpoint)
            checkpoints_created += 1
            
            details.append({
                'equipment_code': result['equipment']['code'],
                'equipment_name': result['equipment']['name'],
                'checkpoint_type': checkpoint_type,
                'status': 'registered'
            })
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'checkpoint_type': checkpoint_type,
        'location': location,
        'reader_id': reader_id,
        'checkpoints_created': checkpoints_created,
        'total_tags': len(epc_list),
        'details': details
    })

@api_rfid_bp.route('/associate', methods=['POST'])
@api_key_or_login_required
def associate_tag(company_id, user_id):
    """
    Associa tag RFID a equipamento
    
    Request:
    {
        "epc": "300833B2DDD9014000000001",
        "equipment_code": "MSX32-001"
    }
    """
    data = request.get_json()
    epc = data.get('epc')
    equipment_code = data.get('equipment_code')
    
    if not epc or not equipment_code:
        return jsonify({'success': False, 'error': 'EPC e código do equipamento são obrigatórios'}), 400
    
    equipment = Equipment.query.filter_by(
        code=equipment_code,
        company_id=company_id,
        is_active=True
    ).first()
    
    if not equipment:
        return jsonify({'success': False, 'error': 'Equipamento não encontrado'}), 404
    
    result = tag_service.associate_rfid_tag(
        equipment_id=equipment.id,
        epc=epc,
        user_id=user_id,
        company_id=company_id
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Tag associada com sucesso',
            'equipment': {
                'id': equipment.id,
                'code': equipment.code,
                'name': equipment.name
            }
        })
    else:
        return jsonify(result), 400

@api_rfid_bp.route('/status', methods=['GET'])
@api_key_or_login_required
def api_status(company_id, user_id):
    """
    Retorna status da API e estatísticas
    """
    total_equipment = Equipment.query.filter_by(
        company_id=company_id,
        is_active=True
    ).count()
    
    with_rfid = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.is_active == True,
        Equipment.rfid_uhf_tag.isnot(None)
    ).count()
    
    return jsonify({
        'success': True,
        'api_version': '1.0',
        'timestamp': datetime.utcnow().isoformat(),
        'stats': {
            'total_equipment': total_equipment,
            'with_rfid_tag': with_rfid,
            'without_rfid_tag': total_equipment - with_rfid
        }
    })
