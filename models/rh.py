from datetime import datetime
from extensions import db

class Employee(db.Model):
    """Funcionarios CLT"""
    __tablename__ = 'employee'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Se tem acesso ao sistema

    # Dados pessoais
    name = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14), unique=True)
    rg = db.Column(db.String(20))
    birth_date = db.Column(db.Date)

    # Contato
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)

    # Dados trabalhistas
    position = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    admission_date = db.Column(db.Date, nullable=False)
    dismissal_date = db.Column(db.Date)

    # Remuneracao
    salary = db.Column(db.Numeric(10, 2), nullable=False)
    salary_type = db.Column(db.String(20), default='monthly')  # monthly, hourly

    # Status
    status = db.Column(db.String(20), default='active')  # active, on_leave, dismissed

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    company = db.relationship('Company')
    user = db.relationship('User')
    payroll_entries = db.relationship('PayrollEntry', backref='employee', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Employee {self.name}>'


class Freelancer(db.Model):
    """Freelancers / Prestadores de servico"""
    __tablename__ = 'freelancer'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Identificacao
    name = db.Column(db.String(200), nullable=False)
    cpf_cnpj = db.Column(db.String(18))

    # Contato
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))

    # Especialidades
    role = db.Column(db.String(100))  # tecnico_audio, tecnico_luz, roadie, motorista
    skills = db.Column(db.Text)  # JSON com habilidades

    # Valores
    hourly_rate = db.Column(db.Numeric(10, 2))
    daily_rate = db.Column(db.Numeric(10, 2))

    # Ranking (0-100)
    performance_score = db.Column(db.Integer, default=50)
    reliability_score = db.Column(db.Integer, default=50)
    technical_score = db.Column(db.Integer, default=50)
    overall_score = db.Column(db.Integer, default=50)

    # Disponibilidade
    is_available = db.Column(db.Boolean, default=True)
    availability_notes = db.Column(db.Text)

    # Status
    status = db.Column(db.String(20), default='active')  # active, inactive, blacklisted

    # Observacoes
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    company = db.relationship('Company')
    assignments = db.relationship('FreelancerAssignment', backref='freelancer', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('FreelancerReview', backref='freelancer', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_jobs(self):
        """Total de trabalhos realizados"""
        return self.assignments.filter_by(status='completed').count()

    def __repr__(self):
        return f'<Freelancer {self.name}>'


class FreelancerAssignment(db.Model):
    """Alocacao de freelancer em evento"""
    __tablename__ = 'freelancer_assignment'

    id = db.Column(db.Integer, primary_key=True)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'))

    # Funcao neste job
    role = db.Column(db.String(100), nullable=False)

    # Datas
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)

    # Valores
    agreed_rate = db.Column(db.Numeric(10, 2), nullable=False)
    rate_type = db.Column(db.String(20))  # hourly, daily, fixed
    total_amount = db.Column(db.Numeric(10, 2))

    # Status
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_progress, completed, cancelled

    # Pagamento
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid
    paid_at = db.Column(db.DateTime)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    tour = db.relationship('Tour')
    show = db.relationship('Show')

    def __repr__(self):
        return f'<FreelancerAssignment ID:{self.id} - {self.role}>'


class FreelancerReview(db.Model):
    """Avaliacao de freelancer apos evento"""
    __tablename__ = 'freelancer_review'

    id = db.Column(db.Integer, primary_key=True)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('freelancer_assignment.id'))

    # Notas (1-5)
    performance_rating = db.Column(db.Integer)  # Desempenho tecnico
    reliability_rating = db.Column(db.Integer)  # Pontualidade, comprometimento
    communication_rating = db.Column(db.Integer)  # Comunicacao
    teamwork_rating = db.Column(db.Integer)  # Trabalho em equipe

    # Comentarios
    comments = db.Column(db.Text)

    # Recomendaria?
    would_hire_again = db.Column(db.Boolean)

    # Metadata
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    assignment = db.relationship('FreelancerAssignment')
    reviewer = db.relationship('User')

    def __repr__(self):
        return f'<FreelancerReview ID:{self.id} Freelancer:{self.freelancer_id}>'


class PayrollEntry(db.Model):
    """Lancamentos de folha de pagamento"""
    __tablename__ = 'payroll_entry'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Periodo
    reference_month = db.Column(db.Integer, nullable=False)  # 1-12
    reference_year = db.Column(db.Integer, nullable=False)

    # Valores
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)
    overtime_hours = db.Column(db.Numeric(5, 2), default=0)
    overtime_amount = db.Column(db.Numeric(10, 2), default=0)
    bonuses = db.Column(db.Numeric(10, 2), default=0)
    deductions = db.Column(db.Numeric(10, 2), default=0)
    net_salary = db.Column(db.Numeric(10, 2), nullable=False)

    # Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, paid

    # Pagamento
    payment_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))

    # Observacoes
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relacionamentos (employee ja definido via backref em Employee.payroll_entries)
    company = db.relationship('Company')
    approver = db.relationship('User')

    def __repr__(self):
        return f'<PayrollEntry {self.reference_month}/{self.reference_year}>'


class AccountPayable(db.Model):
    """Contas a pagar - despesas fixas e variaveis"""
    __tablename__ = 'account_payable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # aluguel, energia, agua, telefone, internet, outros
    supplier = db.Column(db.String(200))
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(20))  # monthly, weekly, yearly
    
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    paid_at = db.Column(db.DateTime)
    paid_amount = db.Column(db.Numeric(10, 2))
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    company = db.relationship('Company')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<AccountPayable {self.description}>'


class FreelancerPayment(db.Model):
    """Pagamentos para freelancers"""
    __tablename__ = 'freelancer_payment'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('freelancer_assignment.id'))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))  # pix, transferencia, dinheiro
    
    reference = db.Column(db.String(100))  # Referencia do evento/trabalho
    
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    paid_at = db.Column(db.DateTime)
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    company = db.relationship('Company')
    freelancer = db.relationship('Freelancer')
    assignment = db.relationship('FreelancerAssignment')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<FreelancerPayment {self.freelancer_id} - R${self.amount}>'