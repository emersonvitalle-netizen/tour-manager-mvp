from datetime import datetime
from extensions import db

class EquipmentModel(db.Model):
    """Modelo generico de equipamento - foto compartilhada entre unidades identicas"""
    __tablename__ = 'equipment_model'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Identificacao do modelo
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('equipment_type.id'))
    
    # Foto compartilhada (UNICA para todos equipamentos deste modelo)
    photo_url = db.Column(db.String(500))
    
    # Especificacoes genericas
    specs = db.Column(db.Text)  # JSON com especificacoes tecnicas
    reference_value = db.Column(db.Numeric(10, 2))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    company = db.relationship('Company')
    equipment_type = db.relationship('EquipmentType')
    equipments = db.relationship('Equipment', backref='equipment_model', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'brand', 'model', name='unique_model_per_company'),
    )
    
    def __repr__(self):
        return f'<EquipmentModel {self.brand} {self.model}>'
