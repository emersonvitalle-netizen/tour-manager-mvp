from datetime import datetime
from extensions import db


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

    # Campos de endereco detalhado
    cellphone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    inscricao_estadual = db.Column(db.String(20))
    street = db.Column(db.String(200))
    number = db.Column(db.String(20))
    complement = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zipcode = db.Column(db.String(10))

    # API Key para leitores RFID
    api_key = db.Column(db.String(64))

    # ========== INTEGRACAO ASAAS ==========
    asaas_api_key = db.Column(db.String(200))  # Chave API do Asaas
    asaas_sandbox = db.Column(db.Boolean, default=True)  # True = sandbox, False = producao
    asaas_webhook_token = db.Column(db.String(64))  # Token para validar webhooks
    asaas_enabled = db.Column(db.Boolean, default=False)  # Integracao ativa?

    # Relacionamentos
    users = db.relationship('User', backref='company', lazy=True)
    equipments = db.relationship('Equipment', backref='company', lazy=True)
    categories = db.relationship('Category', backref='company', lazy=True)

    @property
    def asaas_configured(self):
        """Verifica se Asaas esta configurado"""
        return bool(self.asaas_api_key and self.asaas_enabled)

    @property
    def endereco_completo(self):
        """Retorna endereco formatado"""
        partes = []
        if self.street:
            partes.append(self.street)
        if self.number:
            partes.append(self.number)
        if self.complement:
            partes.append(f"({self.complement})")
        if self.neighborhood:
            partes.append(f"- {self.neighborhood}")
        if self.city and self.state:
            partes.append(f"- {self.city}/{self.state}")
        if self.zipcode:
            partes.append(f"CEP {self.zipcode}")
        return ' '.join(partes) if partes else self.address or ''

    def __repr__(self):
        return f'<Company {self.name}>'