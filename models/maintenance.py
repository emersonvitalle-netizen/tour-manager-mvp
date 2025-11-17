from datetime import datetime
from main import db

class Maintenance(db.Model):
    __tablename__ = 'maintenance'

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    problem_description = db.Column(db.Text, nullable=False)
    solution_description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    cost = db.Column(db.Float, default=0.0)
    external_company = db.Column(db.String(200))
    external_contact = db.Column(db.String(100))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    started_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    equipment = db.relationship('Equipment', backref='maintenance_records', foreign_keys=[equipment_id])
    starter = db.relationship('User', foreign_keys=[started_by])
    completer = db.relationship('User', foreign_keys=[completed_by])

    def __repr__(self):
        return f'<Maintenance {self.id} - {self.status}>'