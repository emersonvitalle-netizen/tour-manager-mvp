from datetime import datetime
from main import db

class Tour(db.Model):
    __tablename__ = 'tour'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200))
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='planned')  # planned, active, completed
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    creator = db.relationship('User', backref='tours_created')
    shows = db.relationship('Show', backref='tour', lazy=True, cascade='all, delete-orphan')
    requirements = db.relationship('TourRequirement', backref='tour', lazy=True, cascade='all, delete-orphan')
    allocated_equipment = db.relationship('TourEquipment', backref='tour', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tour {self.name}>'

class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time)
    venue = db.Column(db.String(200))
    city = db.Column(db.String(100))
    status = db.Column(db.String(50), default='scheduled')  # scheduled, in_progress, completed
    notes = db.Column(db.Text)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    responsible = db.relationship('User', backref='shows_responsible')
    checkpoints = db.relationship('EquipmentCheckpoint', backref='show', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Show {self.venue} - {self.date}>'

class TourRequirement(db.Model):
    """Requisição de equipamentos por tipo - não vincula códigos específicos"""
    __tablename__ = 'tour_requirement'

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    equipment_name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    notes = db.Column(db.Text)

    category = db.relationship('Category')

    def __repr__(self):
        return f'<TourRequirement {self.quantity}x {self.equipment_name}>'

class TourEquipment(db.Model):
    """Equipamentos REAIS alocados à tour"""
    __tablename__ = 'tour_equipment'

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)
    allocated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    returned_at = db.Column(db.DateTime)
    returned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    current_status = db.Column(db.String(50), default='in_company')  # in_company, in_truck, in_show, in_transit
    notes = db.Column(db.Text)

    equipment = db.relationship('Equipment', backref='tour_allocations')
    allocator = db.relationship('User', foreign_keys=[allocated_by], backref='equipment_allocations')
    returner = db.relationship('User', foreign_keys=[returned_by])
    checkpoints = db.relationship('EquipmentCheckpoint', backref='tour_equipment', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TourEquipment {self.equipment.code} in Tour {self.tour_id}>'

class EquipmentCheckpoint(db.Model):
    """Registro de cada bipe/checkpoint do equipamento"""
    __tablename__ = 'equipment_checkpoint'

    id = db.Column(db.Integer, primary_key=True)
    tour_equipment_id = db.Column(db.Integer, db.ForeignKey('tour_equipment.id'), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'))
    checkpoint_type = db.Column(db.String(50), nullable=False)  # load_truck, unload_show, load_truck_return, unload_company
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    scanned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    location = db.Column(db.String(200))  # Local onde foi feito o checkpoint
    condition = db.Column(db.String(50), default='good')  # good, damaged, broken
    notes = db.Column(db.Text)

    scanner = db.relationship('User', backref='checkpoints_scanned')

    def __repr__(self):
        return f'<Checkpoint {self.checkpoint_type} at {self.timestamp}>'

class EquipmentTransfer(db.Model):
    """Transferências de equipamento entre shows"""
    __tablename__ = 'equipment_transfer'

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    from_show_id = db.Column(db.Integer, db.ForeignKey('show.id'))
    to_show_id = db.Column(db.Integer, db.ForeignKey('show.id'), nullable=False)
    reason = db.Column(db.String(50))  # replacement, borrowed, additional
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)
    transferred_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)

    equipment = db.relationship('Equipment')
    from_show = db.relationship('Show', foreign_keys=[from_show_id])
    to_show = db.relationship('Show', foreign_keys=[to_show_id])
    transferrer = db.relationship('User')

    def __repr__(self):
        return f'<Transfer {self.equipment_id} to Show {self.to_show_id}>'

class EquipmentReplacement(db.Model):
    """Solicitações de reposição de equipamentos"""
    __tablename__ = 'equipment_replacement'

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'))
    original_equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    replacement_equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    fulfilled_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='pending')  # pending, fulfilled, cancelled
    reason = db.Column(db.Text)
    source = db.Column(db.String(50))  # company, external_rental, borrowed
    notes = db.Column(db.Text)

    original_equipment = db.relationship('Equipment', foreign_keys=[original_equipment_id])
    replacement_equipment = db.relationship('Equipment', foreign_keys=[replacement_equipment_id])
    requester = db.relationship('User')

    def __repr__(self):
        return f'<Replacement for Equipment {self.original_equipment_id}>'