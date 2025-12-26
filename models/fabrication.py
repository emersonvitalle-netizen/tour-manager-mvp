from datetime import datetime
from extensions import db

class FabricationTemplate(db.Model):
    """Templates de fabricacao (tipos de cabos/reguas que podem ser fabricados)"""
    __tablename__ = 'fabrication_template'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Tipo de item
    item_type = db.Column(db.String(50), nullable=False)  # cable, power_strip, custom
    name = db.Column(db.String(200), nullable=False)
    
    # Descricao
    description = db.Column(db.Text)
    
    # Materiais necessarios (JSON)
    # Exemplo: {"XLR_male": 1, "XLR_female": 1, "cable_xlr": 10}
    materials_recipe = db.Column(db.Text, nullable=False)
    
    # Categoria de equipamento resultante
    equipment_category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    equipment_type_id = db.Column(db.Integer, db.ForeignKey('equipment_type.id'))
    
    # Prefixo para codigo
    code_prefix = db.Column(db.String(20))
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    category = db.relationship('Category')
    equipment_type = db.relationship('EquipmentType')
    fabrications = db.relationship('FabricationRecord', backref='template', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FabricationTemplate {self.name}>'


class FabricationRecord(db.Model):
    """Registro de fabricacao (quando algo foi fabricado)"""
    __tablename__ = 'fabrication_record'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('fabrication_template.id'), nullable=False)
    
    # Quantidade fabricada
    quantity = db.Column(db.Integer, nullable=False)
    
    # Parametros especificos
    # Exemplo: comprimento do cabo, numero de tomadas na regua
    parameters = db.Column(db.Text)  # JSON
    
    # Materiais consumidos (registro real do que foi usado)
    materials_used = db.Column(db.Text)  # JSON com material_stock_id e quantidade
    
    # Equipamentos criados
    equipment_codes = db.Column(db.Text)  # JSON com lista de codigos gerados
    
    # Observacoes
    notes = db.Column(db.Text)
    
    # Metadata
    fabricated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    fabricated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    fabricator = db.relationship('User')
    
    def __repr__(self):
        return f'<FabricationRecord {self.template.name} x{self.quantity}>'


# Extensao do Equipment para rastrear origem
# Adicionar ao Equipment:
# fabrication_record_id = db.Column(db.Integer, db.ForeignKey('fabrication_record.id'))
# fabrication = db.relationship('FabricationRecord')
