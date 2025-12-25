from extensions import db
from datetime import datetime

class SeparationList(db.Model):
    """Lista de Separação / Orçamento para aprovação"""
    __tablename__ = 'separation_list'
    
    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Tipo de lista: 'complete' (com preços detalhados) ou 'simple' (só valor total)
    list_type = db.Column(db.String(20), default='complete', nullable=False)
    
    # Valor total (usado em lista 'simple')
    total_value = db.Column(db.Numeric(10, 2))
    
    # Desconto
    discount_percent = db.Column(db.Numeric(5, 2), default=0)  # Desconto em %
    discount_value = db.Column(db.Numeric(10, 2), default=0)  # Desconto em R$
    
    # ========== DADOS DO CLIENTE ==========
    client_name = db.Column(db.String(200))  # Nome do cliente (obrigatório)
    client_phone = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    client_address = db.Column(db.Text)  # Endereço completo do cliente
    
    # ========== INFORMAÇÕES DO EVENTO ==========
    event_name = db.Column(db.String(200))  # Nome do evento (obrigatório)
    event_date = db.Column(db.Date)  # Data do evento (obrigatório)
    event_time = db.Column(db.String(10))  # Horário do evento
    event_location = db.Column(db.Text)  # Local do evento
    
    # ========== VALIDADE E OBSERVAÇÕES ==========
    validity_date = db.Column(db.Date)  # Validade do orçamento
    observations = db.Column(db.Text)  # Observações gerais (condições, inclusões, etc.)
    
    # Status: pending, approved, rejected, in_separation
    status = db.Column(db.String(20), default='pending', nullable=False)
    
    # Usuários
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime)
    
    # Observações de aprovação/rejeição
    rejection_reason = db.Column(db.Text)
    approval_notes = db.Column(db.Text)
    
    # Multi-tenant
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    tour = db.relationship('Tour', backref='separation_lists')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_separation_lists')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_separation_lists')
    company = db.relationship('Company', backref='separation_lists')
    items = db.relationship('SeparationListItem', backref='separation_list', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SeparationList {self.name}>'
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def status_badge_class(self):
        """Retorna classe CSS para badge de status"""
        status_classes = {
            'pending': 'badge-warning',
            'approved': 'badge-success',
            'rejected': 'badge-danger'
        }
        return status_classes.get(self.status, 'badge-secondary')
    
    @property
    def status_label(self):
        """Retorna label em português para status"""
        status_labels = {
            'pending': 'Pendente',
            'approved': 'Aprovada',
            'rejected': 'Rejeitada',
            'in_separation': 'Em Separação'
        }
        return status_labels.get(self.status, self.status)
    
    @property
    def subtotal(self):
        """Calcula subtotal (antes do desconto)"""
        if self.list_type == 'simple':
            return float(self.total_value or 0)
        
        total = 0
        for item in self.items:
            if item.total_price:
                total += float(item.total_price)
        return total
    
    @property
    def discount_amount(self):
        """Calcula valor do desconto"""
        if self.discount_value and float(self.discount_value) > 0:
            return float(self.discount_value)
        if self.discount_percent and float(self.discount_percent) > 0:
            return self.subtotal * (float(self.discount_percent) / 100)
        return 0
    
    @property
    def calculated_total(self):
        """Calcula total final (com desconto)"""
        return self.subtotal - self.discount_amount
    
    @property
    def orcamento_number(self):
        """Gera número do orçamento no formato ORC-YYYY-NNN"""
        year = self.created_at.year if self.created_at else datetime.now().year
        return f"ORC-{year}-{self.id:03d}"


class SeparationListItem(db.Model):
    """Item de uma lista de separação"""
    __tablename__ = 'separation_list_item'
    
    id = db.Column(db.Integer, primary_key=True)
    separation_list_id = db.Column(db.Integer, db.ForeignKey('separation_list.id'), nullable=False)
    
    # Tipo de equipamento (não equipamento específico)
    equipment_type_id = db.Column(db.Integer, db.ForeignKey('equipment_type.id'))
    item_name = db.Column(db.String(200), nullable=False)  # Nome do item
    item_description = db.Column(db.String(500))  # Descrição adicional (modelo, marca, etc.)
    
    # Quantidade
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # Preços (opcional - apenas para listas 'complete')
    unit_price = db.Column(db.Numeric(10, 2))  # Preço unitário
    total_price = db.Column(db.Numeric(10, 2))  # Preço total (quantidade * unitário)
    
    # Campos opcionais
    notes = db.Column(db.Text)
    
    # Status de conferência (para checklist visual)
    is_checked = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment_type = db.relationship('EquipmentType', backref='separation_list_items')
    
    def __repr__(self):
        return f'<SeparationListItem {self.item_name} x{self.quantity}>'
