from datetime import datetime
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """Usuário do sistema com 3 níveis de acesso"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    photo_url = db.Column(db.String(500))
    
    # ROLES: admin, tech_responsible, tech_tour
    role = db.Column(db.String(20), default='tech_responsible')
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

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


class TourAccess(db.Model):
    """Acesso temporário para técnico de tour via QR Code"""
    __tablename__ = 'tour_access'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Usuário técnico tour
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Tour específica
    tour_id = db.Column(db.Integer, nullable=False)
    tour_name = db.Column(db.String(200), nullable=False)
    
    # QR Code único de acesso
    access_code = db.Column(db.String(64), unique=True, nullable=False)
    qr_code_url = db.Column(db.String(500))
    
    # Período de acesso
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    revoked_at = db.Column(db.DateTime)
    revoked_by = db.Column(db.Integer)
    
    # Auditoria
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, nullable=False)
    
    @property
    def is_expired(self):
        """Verifica se acesso expirou"""
        from datetime import date
        return date.today() > self.end_date
    
    @property
    def is_valid(self):
        """Acesso válido: ativo, não revogado, não expirado"""
        return self.is_active and not self.is_expired
    
    @property
    def status_label(self):
        if not self.is_active:
            return 'Revogado'
        if self.is_expired:
            return 'Expirado'
        return 'Ativo'
    
    @property
    def status_badge(self):
        if not self.is_active:
            return 'badge-danger'
        if self.is_expired:
            return 'badge-secondary'
        return 'badge-success'
