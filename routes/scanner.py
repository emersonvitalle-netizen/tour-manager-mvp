from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models.equipment import Equipment
from services import tag_service
from extensions import db
from datetime import datetime

scanner_bp = Blueprint('scanner', __name__, url_prefix='/scanner')

@scanner_bp.route('/nfc')
@login_required
def nfc():
    """Página do scanner NFC"""
    equipment_id = request.args.get('equipment_id', type=int)
    mode = request.args.get('mode', 'scan')  # scan, associate
    
    equipment = None
    if equipment_id:
        equipment = Equipment.query.filter_by(
            id=equipment_id,
            company_id=current_user.company_id,
            is_active=True
        ).first()
    
    return render_template('scanner/nfc.html', 
                         equipment=equipment, 
                         mode=mode)

@scanner_bp.route('/rfid')
@login_required
def rfid():
    """Página do scanner RFID"""
    equipment_id = request.args.get('equipment_id', type=int)
    mode = request.args.get('mode', 'scan')
    
    equipment = None
    if equipment_id:
        equipment = Equipment.query.filter_by(
            id=equipment_id,
            company_id=current_user.company_id,
            is_active=True
        ).first()
    
    return render_template('scanner/rfid.html', 
                         equipment=equipment, 
                         mode=mode)

@scanner_bp.route('/nfc/scan', methods=['POST'])
@login_required
def nfc_scan():
    """Processa leitura NFC"""
    data = request.get_json()
    tag_id = data.get('tag_id')
    
    if not tag_id:
        return jsonify({'success': False, 'error': 'Tag não informada'}), 400
    
    equipment = tag_service.find_equipment_by_nfc(tag_id, current_user.company_id)
    
    if equipment:
        return jsonify({
            'success': True,
            'found': True,
            'equipment': {
                'id': equipment.id,
                'code': equipment.code,
                'name': equipment.name,
                'status': equipment.status,
                'brand': equipment.brand,
                'model': equipment.model,
                'url': url_for('equipment.detail', id=equipment.id)
            }
        })
    else:
        return jsonify({
            'success': True,
            'found': False,
            'tag_id': tag_id,
            'message': 'Tag não associada a nenhum equipamento'
        })

@scanner_bp.route('/rfid/scan', methods=['POST'])
@login_required
def rfid_scan():
    """Processa leitura RFID"""
    data = request.get_json()
    epc = data.get('epc')
    
    if not epc:
        return jsonify({'success': False, 'error': 'EPC não informado'}), 400
    
    equipment = tag_service.find_equipment_by_rfid(epc, current_user.company_id)
    
    if equipment:
        return jsonify({
            'success': True,
            'found': True,
            'equipment': {
                'id': equipment.id,
                'code': equipment.code,
                'name': equipment.name,
                'status': equipment.status,
                'brand': equipment.brand,
                'model': equipment.model,
                'url': url_for('equipment.detail', id=equipment.id)
            }
        })
    else:
        return jsonify({
            'success': True,
            'found': False,
            'epc': epc,
            'message': 'Tag não associada a nenhum equipamento'
        })

@scanner_bp.route('/rfid/batch', methods=['POST'])
@login_required
def rfid_batch():
    """Processa leitura RFID em lote (para leitores industriais)"""
    data = request.get_json()
    epc_list = data.get('epc_list', [])
    
    if not epc_list:
        return jsonify({'success': False, 'error': 'Lista de EPCs vazia'}), 400
    
    results = tag_service.batch_lookup_rfid(epc_list, current_user.company_id)
    
    found_count = sum(1 for r in results if r['found'])
    
    return jsonify({
        'success': True,
        'total': len(results),
        'found': found_count,
        'not_found': len(results) - found_count,
        'results': results
    })

@scanner_bp.route('/associate/nfc', methods=['POST'])
@login_required
def associate_nfc():
    """Associa tag NFC a equipamento"""
    data = request.get_json()
    equipment_id = data.get('equipment_id')
    tag_id = data.get('tag_id')
    
    if not equipment_id or not tag_id:
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
    
    result = tag_service.associate_nfc_tag(
        equipment_id=equipment_id,
        tag_id=tag_id,
        user_id=current_user.id,
        company_id=current_user.company_id
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Tag NFC associada com sucesso',
            'equipment': {
                'id': result['equipment'].id,
                'code': result['equipment'].code,
                'name': result['equipment'].name
            }
        })
    else:
        return jsonify(result), 400

@scanner_bp.route('/associate/rfid', methods=['POST'])
@login_required
def associate_rfid():
    """Associa tag RFID a equipamento"""
    data = request.get_json()
    equipment_id = data.get('equipment_id')
    epc = data.get('epc')
    
    if not equipment_id or not epc:
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
    
    result = tag_service.associate_rfid_tag(
        equipment_id=equipment_id,
        epc=epc,
        user_id=current_user.id,
        company_id=current_user.company_id
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Tag RFID associada com sucesso',
            'equipment': {
                'id': result['equipment'].id,
                'code': result['equipment'].code,
                'name': result['equipment'].name
            }
        })
    else:
        return jsonify(result), 400

@scanner_bp.route('/remove/<int:equipment_id>/<tag_type>', methods=['POST'])
@login_required
def remove_tag(equipment_id, tag_type):
    """Remove tag de equipamento"""
    if tag_type not in ['nfc', 'rfid']:
        return jsonify({'success': False, 'error': 'Tipo de tag inválido'}), 400
    
    equipment = Equipment.query.filter_by(
        id=equipment_id,
        company_id=current_user.company_id,
        is_active=True
    ).first()
    
    if not equipment:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    result = tag_service.remove_tag(
        equipment_id=equipment_id,
        tag_type=tag_type,
        company_id=current_user.company_id
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': f'Tag {tag_type.upper()} removida com sucesso'
        })
    else:
        return jsonify(result), 400
