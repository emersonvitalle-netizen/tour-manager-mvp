from datetime import datetime
from extensions import db

class Company(db.Model):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    inscricao_estadual = db.Column(db.String(20))
    logo_url = db.Column(db.String(500))
    
    # Contato
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))  # Telefone fixo
    cellphone = db.Column(db.String(20))  # Celular
    website = db.Column(db.String(200))
    
    # Endereço separado
    address = db.Column(db.Text)  # Legado - manter compatibilidade
    street = db.Column(db.String(200))  # Rua/Av/Praça
    number = db.Column(db.String(20))  # Número
    complement = db.Column(db.String(100))  # Complemento
    neighborhood = db.Column(db.String(100))  # Bairro
    city = db.Column(db.String(100))  # Cidade
    state = db.Column(db.String(2))  # Estado (UF)
    zipcode = db.Column(db.String(10))  # CEP
    
    # API para leitores externos
    api_key = db.Column(db.String(64), unique=True)  # Chave API para leitores RFID
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    users = db.relationship('User', backref='company', lazy=True)
    equipments = db.relationship('Equipment', backref='company', lazy=True)
    categories = db.relationship('Category', backref='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.name}>'
    
    @property
    def full_address(self):
        """Retorna endereço completo formatado"""
        parts = []
        if self.street:
            addr = self.street
            if self.number:
                addr += f", {self.number}"
            if self.complement:
                addr += f" - {self.complement}"
            parts.append(addr)
        if self.neighborhood:
            parts.append(self.neighborhood)
        if self.city:
            city_state = self.city
            if self.state:
                city_state += f"/{self.state}"
            parts.append(city_state)
        if self.zipcode:
            parts.append(f"CEP: {self.zipcode}")
        
        if parts:
            return " - ".join(parts)
        return self.address or ""
    
    @property
    def full_phone(self):
        """Retorna telefones formatados"""
        phones = []
        if self.phone:
            phones.append(f"Tel: {self.phone}")
        if self.cellphone:
            phones.append(f"Cel: {self.cellphone}")
        return " | ".join(phones) if phones else ""
