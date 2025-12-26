from datetime import datetime
from extensions import db

class MaterialStock(db.Model):
    """Estoque de materiais para fabricacao (conectores, cabos, pecas)"""
    __tablename__ = 'material_stock'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Identificacao do material
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # connector, cable, component, consumable
    sub_category = db.Column(db.String(100))  # XLR_male, XLR_female, P10, Powercon, etc
    
    # Quantidade e unidade
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False)  # unit, meter, kg, etc
    
    # Limites de estoque
    minimum_quantity = db.Column(db.Numeric(10, 2), default=0)
    maximum_quantity = db.Column(db.Numeric(10, 2))
    
    # Informacoes adicionais
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    reference_value = db.Column(db.Numeric(10, 2))
    supplier = db.Column(db.String(200))
    notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    company = db.relationship('Company')
    movements = db.relationship('MaterialMovement', backref='material', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def is_low_stock(self):
        """Verifica se esta abaixo do minimo"""
        return self.quantity < self.minimum_quantity
    
    def __repr__(self):
        return f'<MaterialStock {self.name} ({self.quantity}{self.unit})>'


class MaterialMovement(db.Model):
    """Movimentacao de materiais (entrada/saida)"""
    __tablename__ = 'material_movement'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material_stock.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Tipo de movimentacao
    movement_type = db.Column(db.String(20), nullable=False)  # in, out
    
    # Quantidade
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_before = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_after = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Motivo
    reason = db.Column(db.String(50), nullable=False)  # purchase, fabrication, adjustment, loss
    reference_type = db.Column(db.String(50))  # equipment, fabrication, etc
    reference_id = db.Column(db.Integer)  # ID do equipamento fabricado, etc
    
    # Observacoes
    notes = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<MaterialMovement {self.movement_type} {self.quantity}>'
