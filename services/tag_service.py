import re
from datetime import datetime
from extensions import db
from models.equipment import Equipment

def normalize_nfc_tag(tag_id: str) -> str:
    """Normaliza UID de tag NFC para formato hex uppercase sem espaços"""
    if not tag_id:
        return None
    cleaned = re.sub(r'[^a-fA-F0-9]', '', tag_id)
    return cleaned.upper() if cleaned else None

def normalize_rfid_tag(epc: str) -> str:
    """Normaliza EPC de tag RFID UHF para formato uppercase"""
    if not epc:
        return None
    cleaned = re.sub(r'[^a-fA-F0-9]', '', epc)
    return cleaned.upper() if cleaned else None

def find_equipment_by_nfc(tag_id: str, company_id: int):
    """Busca equipamento por tag NFC dentro da empresa"""
    normalized = normalize_nfc_tag(tag_id)
    if not normalized:
        return None
    return Equipment.query.filter_by(
        nfc_tag_id=normalized,
        company_id=company_id,
        is_active=True
    ).first()

def find_equipment_by_rfid(epc: str, company_id: int):
    """Busca equipamento por tag RFID dentro da empresa"""
    normalized = normalize_rfid_tag(epc)
    if not normalized:
        return None
    return Equipment.query.filter_by(
        rfid_uhf_tag=normalized,
        company_id=company_id,
        is_active=True
    ).first()

def check_tag_exists(tag_type: str, tag_value: str, company_id: int, exclude_equipment_id: int = None):
    """Verifica se tag já está associada a outro equipamento"""
    if tag_type == 'nfc':
        normalized = normalize_nfc_tag(tag_value)
        field = 'nfc_tag_id'
    else:
        normalized = normalize_rfid_tag(tag_value)
        field = 'rfid_uhf_tag'
    
    if not normalized:
        return None
    
    query = Equipment.query.filter_by(
        company_id=company_id,
        is_active=True,
        **{field: normalized}
    )
    
    if exclude_equipment_id:
        query = query.filter(Equipment.id != exclude_equipment_id)
    
    return query.first()

def associate_nfc_tag(equipment_id: int, tag_id: str, user_id: int, company_id: int):
    """Associa tag NFC a um equipamento"""
    normalized = normalize_nfc_tag(tag_id)
    if not normalized:
        return {'success': False, 'error': 'Tag inválida'}
    
    existing = check_tag_exists('nfc', normalized, company_id, equipment_id)
    if existing:
        return {
            'success': False, 
            'error': f'Tag já associada ao equipamento {existing.code}',
            'existing_equipment': existing
        }
    
    equipment = Equipment.query.filter_by(
        id=equipment_id,
        company_id=company_id,
        is_active=True
    ).first()
    
    if not equipment:
        return {'success': False, 'error': 'Equipamento não encontrado'}
    
    equipment.nfc_tag_id = normalized
    equipment.tag_associated_at = datetime.now()
    equipment.tag_associated_by = user_id
    db.session.commit()
    
    return {'success': True, 'equipment': equipment}

def associate_rfid_tag(equipment_id: int, epc: str, user_id: int, company_id: int):
    """Associa tag RFID UHF a um equipamento"""
    normalized = normalize_rfid_tag(epc)
    if not normalized:
        return {'success': False, 'error': 'Tag inválida'}
    
    existing = check_tag_exists('rfid', normalized, company_id, equipment_id)
    if existing:
        return {
            'success': False, 
            'error': f'Tag já associada ao equipamento {existing.code}',
            'existing_equipment': existing
        }
    
    equipment = Equipment.query.filter_by(
        id=equipment_id,
        company_id=company_id,
        is_active=True
    ).first()
    
    if not equipment:
        return {'success': False, 'error': 'Equipamento não encontrado'}
    
    equipment.rfid_uhf_tag = normalized
    equipment.tag_associated_at = datetime.now()
    equipment.tag_associated_by = user_id
    db.session.commit()
    
    return {'success': True, 'equipment': equipment}

def remove_tag(equipment_id: int, tag_type: str, company_id: int):
    """Remove tag de um equipamento"""
    equipment = Equipment.query.filter_by(
        id=equipment_id,
        company_id=company_id,
        is_active=True
    ).first()
    
    if not equipment:
        return {'success': False, 'error': 'Equipamento não encontrado ou acesso negado'}
    
    if tag_type == 'nfc':
        equipment.nfc_tag_id = None
    elif tag_type == 'rfid':
        equipment.rfid_uhf_tag = None
    else:
        return {'success': False, 'error': 'Tipo de tag inválido'}
    
    equipment.tag_associated_at = None
    equipment.tag_associated_by = None
    
    db.session.commit()
    return {'success': True, 'equipment': equipment}

def batch_lookup_rfid(epc_list: list, company_id: int):
    """Busca múltiplos equipamentos por lista de EPCs (leitura em lote)"""
    results = []
    for epc in epc_list:
        equipment = find_equipment_by_rfid(epc, company_id)
        results.append({
            'epc': epc,
            'found': equipment is not None,
            'equipment': {
                'id': equipment.id,
                'code': equipment.code,
                'name': equipment.name,
                'status': equipment.status
            } if equipment else None
        })
    return results
