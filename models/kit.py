from datetime import datetime
from extensions import db

class Kit(db.Model):
    __tablename__ = 'kit'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    creator = db.relationship('User', backref='kits_created')
    requirements = db.relationship('KitRequirement', backref='kit', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Kit {self.name}>'

class KitRequirement(db.Model):
    __tablename__ = 'kit_requirement'

    id = db.Column(db.Integer, primary_key=True)
    kit_id = db.Column(db.Integer, db.ForeignKey('kit.id'), nullable=False)
    equipment_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<KitRequirement {self.quantity}x {self.equipment_name}>'