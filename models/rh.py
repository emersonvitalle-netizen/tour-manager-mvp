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
    category = db.Column(db.String(50))  # aluguel, energia, agua, telefone, internet, folha, freelancer, veiculo, equipamento, outros
    custom_category = db.Column(db.String(100))  # Quando categoria = outros
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    supplier = db.Column(db.String(200))  # Legacy field
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    
    # Recorrencia
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(20))  # monthly, weekly, yearly
    
    # Parcelas
    installment_number = db.Column(db.Integer)  # 1, 2, 3...
    total_installments = db.Column(db.Integer)  # Total de parcelas
    parent_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))  # Parcela mãe
    
    # Pagamento
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    paid_at = db.Column(db.DateTime)
    paid_amount = db.Column(db.Numeric(10, 2))
    payment_method = db.Column(db.String(30))  # pix, boleto, cartao, dinheiro, transferencia, cheque
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'))
    
    # Comprovante
    receipt_url = db.Column(db.String(500))
    receipt_filename = db.Column(db.String(200))
    
    # Origem (automacao)
    origin_type = db.Column(db.String(30))  # manual, payroll, freelancer, vehicle, equipment
    origin_id = db.Column(db.Integer)  # ID do registro de origem
    
    # Centro de custo
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'))
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')
    creator = db.relationship('User', foreign_keys=[created_by])
    bank_account = db.relationship('BankAccount', foreign_keys=[bank_account_id])
    cost_center = db.relationship('CostCenter', foreign_keys=[cost_center_id])
    supplier_rel = db.relationship('Supplier', foreign_keys=[supplier_id])
    children = db.relationship('AccountPayable', backref=db.backref('parent', remote_side='AccountPayable.id'), foreign_keys='AccountPayable.parent_id')

    @property
    def days_until_due(self):
        """Dias ate o vencimento (negativo se vencida)"""
        from datetime import date
        if self.due_date:
            return (self.due_date - date.today()).days
        return 0

    @property
    def is_overdue(self):
        """Verifica se esta vencida"""
        return self.days_until_due < 0 and self.status == 'pending'

    @property
    def formatted_amount(self):
        """Valor formatado em reais"""
        return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

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


class BankAccount(db.Model):
    """Contas bancarias da empresa"""
    __tablename__ = 'bank_account'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(100))
    bank_code = db.Column(db.String(10))
    agency = db.Column(db.String(20))
    account_number = db.Column(db.String(30))
    account_type = db.Column(db.String(20))  # corrente, poupanca, pagamento

    initial_balance = db.Column(db.Numeric(12, 2), default=0)
    current_balance = db.Column(db.Numeric(12, 2), default=0)

    pix_key = db.Column(db.String(100))
    pix_key_type = db.Column(db.String(20))  # cpf, cnpj, email, telefone, aleatoria

    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<BankAccount {self.name}>'


class CostCenter(db.Model):
    """Centros de custo para alocacao de despesas/receitas"""
    __tablename__ = 'cost_center'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    description = db.Column(db.Text)

    parent_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'))
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')
    children = db.relationship('CostCenter', backref=db.backref('parent', remote_side='CostCenter.id'))

    def __repr__(self):
        return f'<CostCenter {self.name}>'


class AccountReceivable(db.Model):
    """Contas a receber - receitas previstas"""
    __tablename__ = 'account_receivable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # locacao, servico, venda, outros
    custom_category = db.Column(db.String(100))
    
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    client_name = db.Column(db.String(200))

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)

    # Parcelas
    installment_number = db.Column(db.Integer)
    total_installments = db.Column(db.Integer)
    parent_id = db.Column(db.Integer, db.ForeignKey('account_receivable.id'))

    # Recebimento
    status = db.Column(db.String(20), default='pending')  # pending, received, overdue, cancelled
    received_at = db.Column(db.DateTime)
    received_amount = db.Column(db.Numeric(12, 2))
    payment_method = db.Column(db.String(30))
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'))

    # Origem
    origin_type = db.Column(db.String(30))  # manual, quote, contract
    origin_id = db.Column(db.Integer)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'))
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'))

    # Centro de custo
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'))

    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')
    creator = db.relationship('User')
    bank_account = db.relationship('BankAccount')
    cost_center = db.relationship('CostCenter')
    children = db.relationship('AccountReceivable', backref=db.backref('parent', remote_side='AccountReceivable.id'))

    @property
    def days_until_due(self):
        from datetime import date
        if self.due_date:
            return (self.due_date - date.today()).days
        return 0

    @property
    def is_overdue(self):
        return self.days_until_due < 0 and self.status == 'pending'

    @property
    def formatted_amount(self):
        return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def __repr__(self):
        return f'<AccountReceivable {self.description}>'


class Supplier(db.Model):
    """Fornecedores"""
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    trading_name = db.Column(db.String(200))
    cpf_cnpj = db.Column(db.String(18))
    
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(10))

    category = db.Column(db.String(50))  # equipamentos, servicos, manutencao, transporte, outros
    
    # Dados bancarios para pagamento
    bank_name = db.Column(db.String(100))
    bank_agency = db.Column(db.String(20))
    bank_account = db.Column(db.String(30))
    pix_key = db.Column(db.String(100))

    # Desconto por antecipacao
    early_payment_discount = db.Column(db.Numeric(5, 2))  # % desconto
    early_payment_days = db.Column(db.Integer)  # dias de antecedencia

    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<Supplier {self.name}>'


class Client(db.Model):
    """Clientes"""
    __tablename__ = 'client'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Dados basicos
    name = db.Column(db.String(200), nullable=False)
    trading_name = db.Column(db.String(200))
    person_type = db.Column(db.String(10))  # pf, pj
    cpf_cnpj = db.Column(db.String(18))
    rg_ie = db.Column(db.String(20))

    # Contato
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    contact_name = db.Column(db.String(100))

    # Endereco
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(10))

    # Comercial
    source = db.Column(db.String(50))  # indicacao, google, instagram, facebook, site, outro
    segment = db.Column(db.String(100))  # produtora, banda, igreja, empresa, particular

    # Financeiro
    credit_limit = db.Column(db.Numeric(12, 2))
    payment_terms = db.Column(db.Integer, default=0)  # dias para pagamento

    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')
    quotes = db.relationship('Quote', backref='client', lazy='dynamic', foreign_keys='Quote.client_id')

    @property
    def total_quotes(self):
        return self.quotes.count() if self.quotes else 0

    def __repr__(self):
        return f'<Client {self.name}>'


class Vehicle(db.Model):
    """Veiculos da frota"""
    __tablename__ = 'vehicle'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Identificacao
    name = db.Column(db.String(100), nullable=False)
    plate = db.Column(db.String(10))
    renavam = db.Column(db.String(20))

    # Detalhes
    brand = db.Column(db.String(50))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    color = db.Column(db.String(30))
    vehicle_type = db.Column(db.String(30))  # carro, van, caminhao, moto

    # Financeiro
    purchase_date = db.Column(db.Date)
    purchase_value = db.Column(db.Numeric(12, 2))
    current_value = db.Column(db.Numeric(12, 2))

    # Financiamento
    is_financed = db.Column(db.Boolean, default=False)
    financing_bank = db.Column(db.String(100))
    financing_total = db.Column(db.Numeric(12, 2))
    financing_installments = db.Column(db.Integer)
    financing_installment_value = db.Column(db.Numeric(10, 2))
    financing_due_day = db.Column(db.Integer)  # Dia do vencimento

    # Controle
    odometer = db.Column(db.Integer)
    fuel_type = db.Column(db.String(20))  # gasolina, etanol, diesel, flex, eletrico

    # Documentos
    ipva_due_date = db.Column(db.Date)
    insurance_due_date = db.Column(db.Date)
    last_maintenance_date = db.Column(db.Date)
    next_maintenance_km = db.Column(db.Integer)

    status = db.Column(db.String(20), default='active')  # active, maintenance, inactive
    is_active = db.Column(db.Boolean, default=True)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<Vehicle {self.name} - {self.plate}>'


class Consumable(db.Model):
    """Estoque de consumiveis"""
    __tablename__ = 'consumable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(30))
    category = db.Column(db.String(50))  # fitas, pilhas, cabos, conectores, outros
    
    unit = db.Column(db.String(20))  # un, m, kg, rolo
    quantity = db.Column(db.Numeric(10, 2), default=0)
    min_quantity = db.Column(db.Numeric(10, 2), default=0)  # Estoque minimo

    unit_cost = db.Column(db.Numeric(10, 2))
    total_value = db.Column(db.Numeric(12, 2))

    location = db.Column(db.String(100))  # Onde esta armazenado

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')

    @property
    def is_low_stock(self):
        return float(self.quantity or 0) <= float(self.min_quantity or 0)

    def __repr__(self):
        return f'<Consumable {self.name}>'


class ContractTemplate(db.Model):
    """Templates de contrato"""
    __tablename__ = 'contract_template'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    content = db.Column(db.Text)  # HTML/Markdown com variaveis {{cliente}}, {{valor}}, etc
    
    # Upload de arquivo
    file_url = db.Column(db.String(500))
    file_name = db.Column(db.String(200))
    file_type = db.Column(db.String(20))  # pdf, doc, docx

    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<ContractTemplate {self.name}>'


class CashRegister(db.Model):
    """Caixa diario - controle de dinheiro fisico"""
    __tablename__ = 'cash_register'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    
    opening_balance = db.Column(db.Numeric(12, 2), default=0)
    closing_balance = db.Column(db.Numeric(12, 2))
    
    total_in = db.Column(db.Numeric(12, 2), default=0)
    total_out = db.Column(db.Numeric(12, 2), default=0)
    
    status = db.Column(db.String(20), default='open')  # open, closed
    
    opened_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    opened_at = db.Column(db.DateTime)
    closed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    closed_at = db.Column(db.DateTime)
    
    notes = db.Column(db.Text)

    company = db.relationship('Company')
    opener = db.relationship('User', foreign_keys=[opened_by])
    closer = db.relationship('User', foreign_keys=[closed_by])
    entries = db.relationship('CashEntry', backref='register', lazy='dynamic')

    def __repr__(self):
        return f'<CashRegister {self.date}>'


class CashEntry(db.Model):
    """Lancamentos do caixa diario"""
    __tablename__ = 'cash_entry'

    id = db.Column(db.Integer, primary_key=True)
    register_id = db.Column(db.Integer, db.ForeignKey('cash_register.id'), nullable=False)

    entry_type = db.Column(db.String(10), nullable=False)  # in, out
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))

    # Origem
    origin_type = db.Column(db.String(30))  # receivable, payable, manual
    origin_id = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    creator = db.relationship('User')

    def __repr__(self):
        return f'<CashEntry {self.entry_type} R${self.amount}>'