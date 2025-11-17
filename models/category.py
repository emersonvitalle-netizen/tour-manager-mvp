from datetime import datetime
from extensions import db

class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relacionamento correto
    equipments = db.relationship('Equipment', 
                                backref='equipment_category',
                                lazy=True,
                                foreign_keys='Equipment.category_id',
                                overlaps="category")

    __table_args__ = (
        db.UniqueConstraint('name', 'company_id', name='uix_category_company'),
    )

    def __repr__(self):
        return f'<Category {self.name}>'