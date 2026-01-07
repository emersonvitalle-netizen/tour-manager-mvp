from main import app
from models.separation_list import SeparationList
from models.equipment import Equipment

with app.app_context():
    # Verificar equipamentos disponiveis com type_id=1
    equips = Equipment.query.filter_by(type_id=1, status='available', is_active=True).all()
    print(f"Equipamentos disponiveis type_id=1: {len(equips)}")
    for eq in equips:
        print(f"  {eq.id} - {eq.name} - status: {eq.status}")