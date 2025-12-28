from datetime import datetime, date
import secrets
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """Usuário do sistema com 3 níveis de acesso"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    photo_url = db.Column(db.String(500))
    
    # ROLES: admin, tech_responsible, tech_tour
    role = db.Column(db.String(20), default='tech_responsible')
    
    # PIN para acesso rápido (técnicos)
    pin_hash = db.Column(db.String(200))
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Flag para usuários criados via convite QR (ainda não completaram cadastro)
    pending_setup = db.Column(db.Boolean, default=False)

    # Propriedades de permissão
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_tech_responsible(self):
        return self.role == 'tech_responsible'
    
    @property
    def is_tech_tour(self):
        return self.role == 'tech_tour'
    
    @property
    def can_view_prices(self):
        """Apenas admin vê preços"""
        return self.role == 'admin'
    
    @property
    def can_manage_equipment(self):
        """Admin e técnico responsável gerenciam equipamentos"""
        return self.role in ['admin', 'tech_responsible']
    
    @property
    def can_manage_maintenance(self):
        """Todos podem marcar manutenção (com restrições)"""
        return True
    
    @property
    def can_approve_lists(self):
        """Apenas admin aprova listas"""
        return self.role == 'admin'
    
    @property
    def role_label(self):
        labels = {
            'admin': 'Administrador',
            'tech_responsible': 'Técnico Responsável',
            'tech_tour': 'Técnico Tour'
        }
        return labels.get(self.role, self.role)
    
    @property
    def role_badge(self):
        badges = {
            'admin': 'badge-danger',
            'tech_responsible': 'badge-primary',
            'tech_tour': 'badge-warning'
        }
        return badges.get(self.role, 'badge-secondary')

    def __repr__(self):
        return f'<User {self.email}>'


class TechnicianAccess(db.Model):
    """Convite/Acesso para técnico responsável via QR Code"""
    __tablename__ = 'technician_access'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Usuário técnico (criado após onboarding)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Token único do convite/acesso
    access_token = db.Column(db.String(64), unique=True, nullable=False)
    qr_code_url = db.Column(db.String(500))
    
    # Status do convite: pending, active, expired, revoked
    status = db.Column(db.String(20), default='pending')
    
    # Dados do convite (preenchidos pelo admin)
    invite_name = db.Column(db.String(100))
    invite_phone = db.Column(db.String(20))
    
    # Permissões granulares
    can_equipment = db.Column(db.Boolean, default=True)
    can_maintenance = db.Column(db.Boolean, default=True)
    can_separation = db.Column(db.Boolean, default=True)
    can_tours = db.Column(db.Boolean, default=True)
    can_scanner = db.Column(db.Boolean, default=True)
    
    # Validade (null = permanente)
    expires_at = db.Column(db.Date, nullable=True)
    
    # Auditoria
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    revoked_by = db.Column(db.Integer)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='technician_access')
    creator = db.relationship('User', foreign_keys=[created_by])
    company = db.relationship('Company')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return date.today() > self.expires_at
    
    @property
    def is_valid(self):
        return self.status == 'active' and not self.is_expired
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def status_label(self):
        labels = {
            'pending': 'Aguardando Cadastro',
            'active': 'Ativo',
            'expired': 'Expirado',
            'revoked': 'Revogado'
        }
        if self.status == 'active' and self.is_expired:
            return 'Expirado'
        return labels.get(self.status, self.status)
    
    @property
    def status_badge(self):
        if self.status == 'pending':
            return 'badge-warning'
        if self.status == 'active' and not self.is_expired:
            return 'badge-success'
        return 'badge-secondary'
    
    def __repr__(self):
        return f'<TechnicianAccess {self.access_token[:8]}...>'


class TourAccess(db.Model):
    """Acesso temporário para técnico de tour via QR Code"""
    __tablename__ = 'tour_access'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Usuário técnico tour (criado após onboarding)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Tour específica
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    
    # Token único do convite/acesso
    access_token = db.Column(db.String(64), unique=True, nullable=False)
    qr_code_url = db.Column(db.String(500))
    
    # Status do convite: pending, active, expired, revoked
    status = db.Column(db.String(20), default='pending')
    
    # Dados do convite (preenchidos pelo admin)
    invite_name = db.Column(db.String(100))
    invite_phone = db.Column(db.String(20))
    
    # Permissões específicas para tour
    can_scanner = db.Column(db.Boolean, default=True)
    can_checkpoints = db.Column(db.Boolean, default=True)
    can_view_list = db.Column(db.Boolean, default=True)
    
    # Período de acesso (automaticamente da tour ou customizado)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Auditoria
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    revoked_by_id = db.Column(db.Integer)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='tour_accesses')
    tour = db.relationship('Tour', backref='access_passes')
    creator = db.relationship('User', foreign_keys=[created_by])
    company = db.relationship('Company')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    @property
    def is_expired(self):
        return date.today() > self.end_date
    
    @property
    def is_valid(self):
        today = date.today()
        return (self.status == 'active' and 
                self.start_date <= today <= self.end_date)
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def status_label(self):
        if self.status == 'revoked':
            return 'Revogado'
        if self.status == 'active' and self.is_expired:
            return 'Expirado'
        if self.status == 'pending':
            return 'Aguardando Cadastro'
        if self.status == 'active':
            return 'Ativo'
        return self.status
    
    @property
    def status_badge(self):
        if self.status == 'pending':
            return 'badge-warning'
        if self.status == 'revoked':
            return 'badge-danger'
        if self.status == 'active' and not self.is_expired:
            return 'badge-success'
        return 'badge-secondary'
    
    def __repr__(self):
        return f'<TourAccess {self.access_token[:8]}... for Tour {self.tour_id}>'
