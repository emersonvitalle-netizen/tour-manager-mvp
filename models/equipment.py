from datetime import datetime
from extensions import db

class Equipment(db.Model):
    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    prefix = db.Column(db.String(20))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    type_id = db.Column(db.Integer, db.ForeignKey('equipment_type.id'))
    status = db.Column(db.String(50), default='available')
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    value = db.Column(db.Float)
    purchase_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    qr_code_url = db.Column(db.String(500))
    primary_photo_url = db.Column(db.String(500))
    
    # ========== RFID/NFC Tags ==========
    nfc_tag_id = db.Column(db.String(64))  # UID da tag NFC (hex string)
    rfid_uhf_tag = db.Column(db.String(128))  # EPC da tag RFID UHF
    tag_associated_at = db.Column(db.DateTime)  # Data de associação da tag
    tag_associated_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Quem associou
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    category = db.relationship('Category', 
                              foreign_keys=[category_id],
                              overlaps="equipment_category,equipments")

    equipment_type = db.relationship('EquipmentType', 
                                    foreign_keys=[type_id],
                                    backref='equipments')

    def generate_qr_code(self):
        from services.qr_service import generate_qr_code
        self.qr_code_url = generate_qr_code(self)
        return self.qr_code_url

    def __repr__(self):
        return f'<Equipment {self.code}>'