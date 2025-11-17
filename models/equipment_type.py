from main import db
from datetime import datetime

class EquipmentType(db.Model):
    __tablename__ = 'equipment_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    category = db.relationship('Category', backref='equipment_types')
    company = db.relationship('Company')

    __table_args__ = (
        db.UniqueConstraint('name', 'category_id', 'company_id', name='unique_type_per_category'),
    )

    def __repr__(self):
        return f'<EquipmentType {self.name}>'