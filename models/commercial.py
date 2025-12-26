from datetime import datetime
from extensions import db

class Lead(db.Model):
    """Leads comerciais - funil de vendas"""
    __tablename__ = 'lead'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Identificacao do lead
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(200))
    
    # Estagio no funil
    stage = db.Column(db.String(50), default='new')  # new, contacted, qualified, proposal, negotiation, won, lost
    status = db.Column(db.String(20), default='active')  # active, inactive, converted
    
    # Score IA (0-100)
    ai_score = db.Column(db.Integer, default=0)
    score_factors = db.Column(db.Text)  # JSON com fatores do score
    
    # Origem
    source = db.Column(db.String(50))  # website, referral, event, social, cold_call
    campaign = db.Column(db.String(100))
    
    # Dados do negocio
    estimated_value = db.Column(db.Numeric(10, 2))
    probability = db.Column(db.Integer, default=0)  # 0-100%
    expected_close_date = db.Column(db.Date)
    
    # Evento relacionado
    event_type = db.Column(db.String(100))  # show, festival, corporate, wedding
    event_date = db.Column(db.Date)
    event_location = db.Column(db.String(200))
    
    # Responsavel
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Observacoes
    notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contact_at = db.Column(db.DateTime)
    
    # Relacionamentos
    company = db.relationship('Company')
    assignee = db.relationship('User')
    interactions = db.relationship('LeadInteraction', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def days_since_contact(self):
        """Dias desde ultimo contato"""
        if self.last_contact_at:
            return (datetime.utcnow() - self.last_contact_at).days
        return (datetime.utcnow() - self.created_at).days
    
    @property
    def needs_followup(self):
        """Precisa de followup? (>7 dias sem contato)"""
        return self.days_since_contact > 7 and self.status == 'active'
    
    def __repr__(self):
        return f'<Lead {self.name}>'


class LeadInteraction(db.Model):
    """Interacoes com leads (historico de contatos)"""
    __tablename__ = 'lead_interaction'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    
    # Tipo de interacao
    interaction_type = db.Column(db.String(50), nullable=False)  # call, email, meeting, whatsapp, proposal
    direction = db.Column(db.String(20))  # inbound, outbound
    
    # Conteudo
    subject = db.Column(db.String(200))
    notes = db.Column(db.Text)
    outcome = db.Column(db.String(50))  # successful, no_answer, scheduled, rejected
    
    # Proximos passos
    next_action = db.Column(db.String(200))
    next_action_date = db.Column(db.Date)
    
    # Metadata
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<LeadInteraction {self.interaction_type}>'


class LeadReactivation(db.Model):
    """Sugestoes de reativacao de leads inativos (IA)"""
    __tablename__ = 'lead_reactivation'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Estrategia de reativacao (gerada por IA)
    strategy = db.Column(db.String(50), nullable=False)  # discount, new_service, event_reminder
    message_suggestion = db.Column(db.Text)  # Mensagem sugerida
    confidence_score = db.Column(db.Integer)  # 0-100
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, executed, successful, failed
    
    # Resultado
    executed_at = db.Column(db.DateTime)
    executed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    result_notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    lead = db.relationship('Lead')
    company = db.relationship('Company')
    executor = db.relationship('User')
    
    def __repr__(self):
        return f'<LeadReactivation {self.strategy}>'
