from datetime import datetime
from extensions import db

class Maintenance(db.Model):
    """Manutencao de equipamentos - EXPANDIDO"""
    __tablename__ = 'maintenance'

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Tipo e status
    maintenance_type = db.Column(db.String(50), nullable=False)  # preventive, corrective, calibration
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled

    # Problema e solucao
    problem_description = db.Column(db.Text, nullable=False)
    problem_type = db.Column(db.String(50))  # electrical, mechanical, wear, other
    solution_description = db.Column(db.Text)

    # Localizacao da falha (para relatorios)
    failure_location = db.Column(db.String(200))  # Onde ocorreu: show, ensaio, transporte, deposito
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))  # Se ocorreu em um tour

    # Custos
    parts_cost = db.Column(db.Numeric(10, 2), default=0)
    labor_cost = db.Column(db.Numeric(10, 2), default=0)
    total_cost = db.Column(db.Numeric(10, 2), default=0)

    # Datas
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Tempo estimado vs real
    estimated_hours = db.Column(db.Numeric(5, 2))
    actual_hours = db.Column(db.Numeric(5, 2))

    # Responsaveis
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Observacoes
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Notas privadas do tecnico

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    equipment = db.relationship('Equipment', backref='maintenances')
    company = db.relationship('Company')
    reporter = db.relationship('User', foreign_keys=[reported_by])
    assignee = db.relationship('User', foreign_keys=[assigned_to])
    completer = db.relationship('User', foreign_keys=[completed_by])
    tour = db.relationship('Tour', foreign_keys=[tour_id])
    parts_used = db.relationship('MaintenancePart', backref='maintenance', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        """Verifica se esta atrasada (pendente por mais de 7 dias)"""
        if self.status == 'pending' and self.reported_at:
            days_pending = (datetime.utcnow() - self.reported_at).days
            return days_pending > 7
        return False

    @property
    def downtime_days(self):
        """Calcula dias parado"""
        if self.completed_at:
            return (self.completed_at - self.reported_at).days
        return (datetime.utcnow() - self.reported_at).days

    def __repr__(self):
        return f'<Maintenance {self.id} - {self.equipment.code}>'


class MaintenancePart(db.Model):
    """Pecas usadas em manutencao"""
    __tablename__ = 'maintenance_part'

    id = db.Column(db.Integer, primary_key=True)
    maintenance_id = db.Column(db.Integer, db.ForeignKey('maintenance.id'), nullable=False)

    # Peca
    part_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2))
    total_cost = db.Column(db.Numeric(10, 2))

    # Origem
    material_stock_id = db.Column(db.Integer, db.ForeignKey('material_stock.id'))  # Se veio do estoque
    supplier = db.Column(db.String(200))  # Se foi comprado

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos (comentado - MaterialStock carrega depois)
    # stock_item = db.relationship('MaterialStock')

    def __repr__(self):
        return f'<MaintenancePart {self.part_name}>'


class MaintenanceSchedule(db.Model):
    """Agendamento de manutencoes preventivas"""
    __tablename__ = 'maintenance_schedule'

    id = db.Column(db.Integer, primary_key=True)
    equipment_model_id = db.Column(db.Integer, db.ForeignKey('equipment_model.id'))  # Modelo ou...
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))  # ...equipamento especifico
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Tipo de manutencao preventiva
    maintenance_type = db.Column(db.String(100), nullable=False)  # Ex: "Calibracao anual", "Limpeza trimestral"
    description = db.Column(db.Text)

    # Frequencia
    frequency = db.Column(db.String(20), nullable=False)  # monthly, quarterly, biannual, annual
    interval_days = db.Column(db.Integer)  # Ou dias especificos

    # Proxima manutencao
    next_maintenance_date = db.Column(db.Date, nullable=False)
    last_maintenance_date = db.Column(db.Date)

    # Status
    is_active = db.Column(db.Boolean, default=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    equipment_model = db.relationship('EquipmentModel')
    equipment = db.relationship('Equipment')
    company = db.relationship('Company')

    def __repr__(self):
        return f'<MaintenanceSchedule {self.maintenance_type}>'