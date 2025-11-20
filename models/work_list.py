from extensions import db
from datetime import datetime

class WorkList(db.Model):
    """Lista de trabalho para técnicos (SEM preços)
    
    Criada automaticamente quando admin aprova SeparationList.
    Técnicos usam para separar equipamentos fisicamente.
    """
    __tablename__ = 'work_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    separation_list_id = db.Column(db.Integer, nullable=True)  # Referência simples
    tour_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    
    # Multi-tenant
    company_id = db.Column(db.Integer, nullable=False)
    
    # Auditoria
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_to = db.Column(db.Integer, nullable=True)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('WorkListItem', backref='work_list', lazy='dynamic')
    
    @property
    def total_items(self):
        """Total de itens na lista"""
        return self.items.count()
    
    @property
    def separated_items(self):
        """Itens já separados"""
        return self.items.filter_by(separated=True).count()
    
    @property
    def progress_percentage(self):
        """Percentual de conclusão"""
        if self.total_items == 0:
            return 0
        return int((self.separated_items / self.total_items) * 100)
    
    @property
    def status_label(self):
        """Label traduzida do status"""
        labels = {
            'pending': 'Pendente',
            'in_progress': 'Em Andamento',
            'completed': 'Concluída'
        }
        return labels.get(self.status, self.status)
    
    @property
    def status_badge_class(self):
        """Classe CSS do badge de status"""
        classes = {
            'pending': 'badge-warning',
            'in_progress': 'badge-info',
            'completed': 'badge-success'
        }
        return classes.get(self.status, 'badge-secondary')


class WorkListItem(db.Model):
    """Item da lista de trabalho (SEM preços)"""
    __tablename__ = 'work_list_items'
    
    id = db.Column(db.Integer, primary_key=True)
    work_list_id = db.Column(db.Integer, db.ForeignKey('work_lists.id'), nullable=False)
    
    # Item (tipo de equipamento + quantidade)
    item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    # Status de separação
    separated = db.Column(db.Boolean, default=False)
    separated_at = db.Column(db.DateTime)
    separated_by = db.Column(db.Integer, nullable=True)
