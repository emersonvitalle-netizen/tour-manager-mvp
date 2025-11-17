from datetime import datetime
from main import db

class Company(db.Model):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    logo_url = db.Column(db.String(500))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    users = db.relationship('User', backref='company', lazy=True)
    equipments = db.relationship('Equipment', backref='company', lazy=True)
    categories = db.relationship('Category', backref='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.name}>'
