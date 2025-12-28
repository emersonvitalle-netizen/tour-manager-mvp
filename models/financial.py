"""Models financeiros para gestão de propostas, contratos, faturas e pagamentos"""
from datetime import datetime, date
from extensions import db
import uuid


class Quote(db.Model):
    """Proposta/Orçamento para cliente"""
    __tablename__ = 'quote'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(120))
    client_phone = db.Column(db.String(20))
    client_document = db.Column(db.String(20))
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    discount_value = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    
    valid_until = db.Column(db.Date)
    status = db.Column(db.String(20), default='draft')
    
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    items = db.relationship('QuoteItem', backref='quote', lazy=True, cascade='all, delete-orphan')
    
    @property
    def status_label(self):
        labels = {
            'draft': 'Rascunho',
            'sent': 'Enviada',
            'approved': 'Aprovada',
            'rejected': 'Rejeitada',
            'expired': 'Expirada'
        }
        return labels.get(self.status, self.status)
    
    @property
    def status_badge(self):
        badges = {
            'draft': 'badge-secondary',
            'sent': 'badge-info',
            'approved': 'badge-success',
            'rejected': 'badge-danger',
            'expired': 'badge-warning'
        }
        return badges.get(self.status, 'badge-secondary')
    
    @property
    def is_expired(self):
        if self.valid_until:
            return date.today() > self.valid_until
        return False


class QuoteItem(db.Model):
    """Item de proposta"""
    __tablename__ = 'quote_item'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=False)
    
    description = db.Column(db.String(300), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    
    equipment_type_id = db.Column(db.Integer)
    category_id = db.Column(db.Integer)


class Contract(db.Model):
    """Contrato de locação"""
    __tablename__ = 'contract'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'))
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    
    client_name = db.Column(db.String(200), nullable=False)
    client_document = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    client_phone = db.Column(db.String(20))
    client_address = db.Column(db.Text)
    
    title = db.Column(db.String(200), nullable=False)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    total_value = db.Column(db.Numeric(12, 2), default=0)
    deposit_value = db.Column(db.Numeric(12, 2), default=0)
    
    status = db.Column(db.String(20), default='draft')
    
    terms = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    service_description = db.Column(db.Text)
    payment_terms = db.Column(db.Text)
    additional_terms = db.Column(db.Text)
    
    signed_at = db.Column(db.DateTime)
    signed_by_client = db.Column(db.String(200))
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    @property
    def status_label(self):
        labels = {
            'draft': 'Rascunho',
            'pending_signature': 'Aguardando Assinatura',
            'active': 'Ativo',
            'completed': 'Concluído',
            'cancelled': 'Cancelado'
        }
        return labels.get(self.status, self.status)
    
    @property
    def status_badge(self):
        badges = {
            'draft': 'badge-secondary',
            'pending_signature': 'badge-warning',
            'active': 'badge-success',
            'completed': 'badge-info',
            'cancelled': 'badge-danger'
        }
        return badges.get(self.status, 'badge-secondary')


class Invoice(db.Model):
    """Fatura / Nota Fiscal de Serviço"""
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    
    client_name = db.Column(db.String(200), nullable=False)
    client_document = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    
    description = db.Column(db.Text)
    
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_percent = db.Column(db.Numeric(5, 2), default=0)
    tax_value = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    
    due_date = db.Column(db.Date, nullable=False)
    paid_at = db.Column(db.DateTime)
    
    status = db.Column(db.String(20), default='pending')
    
    nfse_number = db.Column(db.String(50))
    nfse_code = db.Column(db.String(100))
    nfse_url = db.Column(db.String(500))
    nfse_issued_at = db.Column(db.DateTime)
    nfse_provider = db.Column(db.String(50))
    
    pix_code = db.Column(db.Text)
    pix_qr_url = db.Column(db.String(500))
    boleto_code = db.Column(db.String(100))
    boleto_url = db.Column(db.String(500))
    
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    payments = db.relationship('Payment', backref='invoice', lazy=True)
    
    @property
    def status_label(self):
        labels = {
            'pending': 'Pendente',
            'paid': 'Pago',
            'partial': 'Parcial',
            'overdue': 'Vencida',
            'cancelled': 'Cancelada'
        }
        return labels.get(self.status, self.status)
    
    @property
    def status_badge(self):
        badges = {
            'pending': 'badge-warning',
            'paid': 'badge-success',
            'partial': 'badge-info',
            'overdue': 'badge-danger',
            'cancelled': 'badge-secondary'
        }
        return badges.get(self.status, 'badge-secondary')
    
    @property
    def is_overdue(self):
        if self.status == 'pending' and self.due_date:
            return date.today() > self.due_date
        return False
    
    @property
    def amount_paid(self):
        return sum(p.amount for p in self.payments if p.status == 'confirmed')
    
    @property
    def amount_pending(self):
        return float(self.total or 0) - float(self.amount_paid or 0)


class Payment(db.Model):
    """Pagamento recebido"""
    __tablename__ = 'payment'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4())[:8].upper())
    
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    method = db.Column(db.String(20), nullable=False)
    
    status = db.Column(db.String(20), default='pending')
    
    transaction_id = db.Column(db.String(100))
    provider = db.Column(db.String(50))
    provider_data = db.Column(db.Text)
    
    paid_at = db.Column(db.DateTime)
    confirmed_by = db.Column(db.Integer)
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    @property
    def method_label(self):
        labels = {
            'pix': 'PIX',
            'boleto': 'Boleto',
            'credit_card': 'Cartão de Crédito',
            'debit_card': 'Cartão de Débito',
            'transfer': 'Transferência',
            'cash': 'Dinheiro',
            'check': 'Cheque'
        }
        return labels.get(self.method, self.method)
    
    @property
    def status_label(self):
        labels = {
            'pending': 'Pendente',
            'confirmed': 'Confirmado',
            'failed': 'Falhou',
            'refunded': 'Estornado'
        }
        return labels.get(self.status, self.status)
    
    @property
    def status_badge(self):
        badges = {
            'pending': 'badge-warning',
            'confirmed': 'badge-success',
            'failed': 'badge-danger',
            'refunded': 'badge-secondary'
        }
        return badges.get(self.status, 'badge-secondary')
