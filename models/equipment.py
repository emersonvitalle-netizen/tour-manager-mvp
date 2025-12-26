from datetime import datetime
from extensions import db

class Equipment(db.Model):
    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    prefix = db.Column(db.String(20))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    type_id = db.Column(db.Integer, db.ForeignKey('equipment_type.id'))
    
    # NOVO: Referencia ao modelo (foto compartilhada)
    model_id = db.Column(db.Integer, db.ForeignKey('equipment_model.id'), nullable=True)
    
    # DEPRECATED: Manter temporariamente para migracao
    brand = db.Column(db.String(100))  # Sera removido apos migracao
    model = db.Column(db.String(100))  # Sera removido apos migracao
    primary_photo_url = db.Column(db.String(500))  # Sera removido apos migracao
    
    # Dados individuais
    status = db.Column(db.String(50), default='available')
    serial_number = db.Column(db.String(100))
    value = db.Column(db.Float)
    purchase_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    qr_code_url = db.Column(db.String(500))
    
    # Metadata
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    # Relacionamentos
    category = db.relationship('Category', 
                              foreign_keys=[category_id],
                              overlaps="equipment_category,equipments")

    equipment_type = db.relationship('EquipmentType', 
                                    foreign_keys=[type_id],
                                    backref='equipments')
    
    # NOVO: Acessa foto via modelo
    # equipment.equipment_model.photo_url

    def generate_qr_code(self):
        from services.qr_service import generate_qr_code
        self.qr_code_url = generate_qr_code(self)
        return self.qr_code_url
    
    @property
    def photo(self):
        """Retorna foto do modelo ou foto individual (fallback para migracao)"""
        if self.equipment_model and self.equipment_model.photo_url:
            return self.equipment_model.photo_url
        return self.primary_photo_url
    
    @property
    def brand_name(self):
        """Retorna marca do modelo ou marca individual (fallback)"""
        if self.equipment_model:
            return self.equipment_model.brand
        return self.brand
    
    @property
    def model_name(self):
        """Retorna modelo do modelo ou modelo individual (fallback)"""
        if self.equipment_model:
            return self.equipment_model.model
        return self.model

    def __repr__(self):
        return f'<Equipment {self.code}>'
