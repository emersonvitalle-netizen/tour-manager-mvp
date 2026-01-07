"""
Models para modulo RH e Financeiro
- Employee (CLT) - EXPANDIDO com adicionais e controle de ferias
- Freelancer, FreelancerAssignment, FreelancerReview
- PayrollEntry (Holerite completo)
- VacationPeriod (Ferias) - NOVO
- ThirteenthSalary (13o Salario) - NOVO
- Termination (Rescisao) - NOVO
- AccountPayable, AccountReceivable
- BankAccount, CostCenter, Supplier, Client
- FreelancerPayment, Vehicle, Consumable
- ContractTemplate, CashRegister, CashEntry
"""

from datetime import datetime
from extensions import db


class Employee(db.Model):
    """Funcionarios CLT - EXPANDIDO"""
    __tablename__ = 'employee'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

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

    # Documentos trabalhistas
    pis_pasep = db.Column(db.String(20))
    ctps_numero = db.Column(db.String(20))
    ctps_serie = db.Column(db.String(10))
    ctps_uf = db.Column(db.String(2))

    # Remuneracao base
    salary = db.Column(db.Numeric(10, 2), nullable=False)
    salary_type = db.Column(db.String(20), default='monthly')

    # ========== ADICIONAIS (% sobre salario base) ==========
    adicional_noturno_percent = db.Column(db.Numeric(5, 2), default=0)  # 20% padrao
    adicional_periculosidade = db.Column(db.Numeric(5, 2), default=0)   # 30% fixo por lei
    adicional_insalubridade_grau = db.Column(db.String(10))             # minimo/medio/maximo
    adicional_insalubridade_percent = db.Column(db.Numeric(5, 2), default=0)  # 10/20/40%
    adicional_funcao = db.Column(db.Numeric(10, 2), default=0)          # Gratificacao de funcao
    comissao_percent = db.Column(db.Numeric(5, 2), default=0)           # % sobre vendas

    # ========== DESCONTOS FIXOS ==========
    pensao_alimenticia_percent = db.Column(db.Numeric(5, 2), default=0)  # % sobre liquido
    pensao_alimenticia_valor = db.Column(db.Numeric(10, 2), default=0)   # Valor fixo
    emprestimo_consignado = db.Column(db.Numeric(10, 2), default=0)      # Desconto mensal
    outros_descontos_fixos = db.Column(db.Numeric(10, 2), default=0)
    descricao_outros_descontos = db.Column(db.String(200))

    # ========== BENEFICIOS ==========
    vt_value = db.Column(db.Numeric(10, 2), default=0)
    vr_value = db.Column(db.Numeric(10, 2), default=0)
    va_value = db.Column(db.Numeric(10, 2), default=0)
    health_insurance = db.Column(db.Numeric(10, 2), default=0)
    health_insurance_discount = db.Column(db.Numeric(10, 2), default=0)  # Parte funcionario
    other_benefits = db.Column(db.Numeric(10, 2), default=0)

    # Dependentes (para IRRF)
    dependents_count = db.Column(db.Integer, default=0)

    # ========== CONTROLE DE FERIAS ==========
    ultima_ferias_inicio = db.Column(db.Date)
    ultima_ferias_fim = db.Column(db.Date)
    dias_ferias_disponiveis = db.Column(db.Integer, default=0)
    ferias_vencidas = db.Column(db.Boolean, default=False)

    # ========== DADOS BANCARIOS ==========
    banco_nome = db.Column(db.String(100))
    banco_agencia = db.Column(db.String(20))
    banco_conta = db.Column(db.String(30))
    banco_tipo_conta = db.Column(db.String(20))  # corrente/poupanca
    pix_chave = db.Column(db.String(200))
    pix_tipo = db.Column(db.String(20))  # cpf/email/telefone/aleatoria

    # Status
    status = db.Column(db.String(20), default='active')

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    company = db.relationship('Company')
    user = db.relationship('User')
    payroll_entries = db.relationship('PayrollEntry', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    vacation_periods = db.relationship('VacationPeriod', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    thirteenth_salaries = db.relationship('ThirteenthSalary', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    terminations = db.relationship('Termination', backref='employee', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Employee {self.name}>'

    @property
    def salario_com_adicionais(self):
        """Retorna salario base + adicionais fixos"""
        base = float(self.salary or 0)
        periculosidade = base * float(self.adicional_periculosidade or 0) / 100
        insalubridade = base * float(self.adicional_insalubridade_percent or 0) / 100
        funcao = float(self.adicional_funcao or 0)
        return base + periculosidade + insalubridade + funcao


class Freelancer(db.Model):
    """Freelancers / Prestadores de servico"""
    __tablename__ = 'freelancer'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    cpf_cnpj = db.Column(db.String(18))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(100))
    hourly_rate = db.Column(db.Numeric(10, 2))
    daily_rate = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')

    performance_score = db.Column(db.Integer, default=50)
    reliability_score = db.Column(db.Integer, default=50)
    technical_score = db.Column(db.Integer, default=50)
    overall_score = db.Column(db.Integer, default=50)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = db.relationship('Company')
    assignments = db.relationship('FreelancerAssignment', backref='freelancer', lazy='dynamic')
    payments = db.relationship('FreelancerPayment', backref='freelancer_ref', lazy='dynamic')

    def __repr__(self):
        return f'<Freelancer {self.name}>'


class FreelancerAssignment(db.Model):
    """Alocacao de freelancer em evento"""
    __tablename__ = 'freelancer_assignment'

    id = db.Column(db.Integer, primary_key=True)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    show_id = db.Column(db.Integer, db.ForeignKey('show.id'))

    role = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    daily_rate = db.Column(db.Numeric(10, 2))
    total_days = db.Column(db.Integer)
    total_amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FreelancerAssignment {self.freelancer_id}>'


class FreelancerReview(db.Model):
    """Avaliacao de freelancer apos evento"""
    __tablename__ = 'freelancer_review'

    id = db.Column(db.Integer, primary_key=True)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('freelancer_assignment.id'))

    performance_score = db.Column(db.Integer)
    reliability_score = db.Column(db.Integer)
    technical_score = db.Column(db.Integer)
    comments = db.Column(db.Text)
    would_hire_again = db.Column(db.Boolean)

    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignment = db.relationship('FreelancerAssignment')
    reviewer = db.relationship('User')

    def __repr__(self):
        return f'<FreelancerReview ID:{self.id} Freelancer:{self.freelancer_id}>'


class PayrollEntry(db.Model):
    """Holerite completo CLT com todos os encargos - Tabelas 2025"""
    __tablename__ = 'payroll_entry'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Periodo
    reference_month = db.Column(db.Integer, nullable=False)
    reference_year = db.Column(db.Integer, nullable=False)

    # ========== PROVENTOS ==========
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)
    overtime_hours = db.Column(db.Numeric(5, 2), default=0)
    overtime_amount = db.Column(db.Numeric(10, 2), default=0)
    night_shift_hours = db.Column(db.Numeric(5, 2), default=0)
    night_shift_amount = db.Column(db.Numeric(10, 2), default=0)

    # Adicionais
    adicional_periculosidade = db.Column(db.Numeric(10, 2), default=0)
    adicional_insalubridade = db.Column(db.Numeric(10, 2), default=0)
    adicional_funcao = db.Column(db.Numeric(10, 2), default=0)
    comissoes = db.Column(db.Numeric(10, 2), default=0)

    bonuses = db.Column(db.Numeric(10, 2), default=0)
    commissions = db.Column(db.Numeric(10, 2), default=0)
    other_earnings = db.Column(db.Numeric(10, 2), default=0)

    # Total bruto
    gross_salary = db.Column(db.Numeric(10, 2), default=0)

    # ========== DESCONTOS FUNCIONARIO ==========
    inss_employee = db.Column(db.Numeric(10, 2), default=0)
    irrf = db.Column(db.Numeric(10, 2), default=0)
    vt_discount = db.Column(db.Numeric(10, 2), default=0)
    vr_discount = db.Column(db.Numeric(10, 2), default=0)
    health_discount = db.Column(db.Numeric(10, 2), default=0)
    union_fee = db.Column(db.Numeric(10, 2), default=0)
    advances = db.Column(db.Numeric(10, 2), default=0)

    # Descontos extras
    pensao_alimenticia = db.Column(db.Numeric(10, 2), default=0)
    emprestimo_consignado = db.Column(db.Numeric(10, 2), default=0)
    other_deductions = db.Column(db.Numeric(10, 2), default=0)
    deductions = db.Column(db.Numeric(10, 2), default=0)

    # ========== ENCARGOS EMPRESA ==========
    inss_employer = db.Column(db.Numeric(10, 2), default=0)
    inss_rat = db.Column(db.Numeric(10, 2), default=0)
    inss_terceiros = db.Column(db.Numeric(10, 2), default=0)
    fgts = db.Column(db.Numeric(10, 2), default=0)

    # ========== PROVISOES MENSAIS ==========
    provision_13th = db.Column(db.Numeric(10, 2), default=0)
    provision_vacation = db.Column(db.Numeric(10, 2), default=0)
    provision_vacation_bonus = db.Column(db.Numeric(10, 2), default=0)
    provision_fgts_13th = db.Column(db.Numeric(10, 2), default=0)
    provision_fgts_vacation = db.Column(db.Numeric(10, 2), default=0)

    # ========== TOTAIS ==========
    net_salary = db.Column(db.Numeric(10, 2), nullable=False)
    total_employer_cost = db.Column(db.Numeric(10, 2), default=0)
    total_provisions = db.Column(db.Numeric(10, 2), default=0)

    # ========== BENEFICIOS PAGOS ==========
    vt_paid = db.Column(db.Numeric(10, 2), default=0)
    vr_paid = db.Column(db.Numeric(10, 2), default=0)
    va_paid = db.Column(db.Numeric(10, 2), default=0)
    health_paid = db.Column(db.Numeric(10, 2), default=0)

    # Status
    status = db.Column(db.String(20), default='pending')

    # Pagamento
    payment_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))

    # Integracao financeira
    account_payable_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))
    financial_integrated = db.Column(db.Boolean, default=False)

    # Observacoes
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relacionamentos
    company = db.relationship('Company')
    approver = db.relationship('User')

    def __repr__(self):
        return f'<PayrollEntry {self.reference_month}/{self.reference_year}>'


class VacationPeriod(db.Model):
    """Controle de Ferias CLT"""
    __tablename__ = 'vacation_period'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # ========== PERIODO AQUISITIVO (12 meses trabalhados) ==========
    acquisition_start = db.Column(db.Date, nullable=False)  # Inicio periodo aquisitivo
    acquisition_end = db.Column(db.Date, nullable=False)    # Fim periodo aquisitivo

    # ========== PERIODO CONCESSIVO (12 meses para gozar) ==========
    concession_start = db.Column(db.Date)  # Inicio periodo concessivo
    concession_end = db.Column(db.Date)    # Fim periodo concessivo (apos = vencidas)

    # ========== GOZO DAS FERIAS ==========
    vacation_start = db.Column(db.Date)     # Inicio ferias
    vacation_end = db.Column(db.Date)       # Fim ferias
    days_taken = db.Column(db.Integer, default=30)  # Dias gozados (max 30)
    days_sold = db.Column(db.Integer, default=0)    # Dias vendidos - abono (max 10)

    # Fracionamento (reforma trabalhista)
    is_split = db.Column(db.Boolean, default=False)  # Ferias fracionadas?
    split_number = db.Column(db.Integer, default=1)  # Qual fracao (1, 2 ou 3)
    split_total = db.Column(db.Integer, default=1)   # Total de fracoes

    # ========== VALORES ==========
    base_salary = db.Column(db.Numeric(10, 2))
    vacation_value = db.Column(db.Numeric(10, 2), default=0)       # Valor ferias
    bonus_value = db.Column(db.Numeric(10, 2), default=0)          # 1/3 constitucional
    sold_value = db.Column(db.Numeric(10, 2), default=0)           # Abono pecuniario
    sold_bonus = db.Column(db.Numeric(10, 2), default=0)           # 1/3 sobre abono
    gross_value = db.Column(db.Numeric(10, 2), default=0)          # Total bruto

    # Descontos
    inss_discount = db.Column(db.Numeric(10, 2), default=0)
    irrf_discount = db.Column(db.Numeric(10, 2), default=0)
    other_discounts = db.Column(db.Numeric(10, 2), default=0)

    # Liquido
    net_value = db.Column(db.Numeric(10, 2), default=0)

    # ========== STATUS ==========
    status = db.Column(db.String(20), default='pending')
    # pending = aguardando agendamento
    # scheduled = agendada
    # enjoying = em gozo
    # completed = concluida
    # paid = paga
    # cancelled = cancelada

    # ========== PAGAMENTO ==========
    payment_date = db.Column(db.Date)       # Data pagamento (2 dias antes inicio)
    payment_method = db.Column(db.String(50))
    paid_at = db.Column(db.DateTime)

    # ========== INTEGRACAO FINANCEIRA ==========
    account_payable_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))
    financial_integrated = db.Column(db.Boolean, default=False)

    # Observacoes
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)

    # Relacionamentos
    company = db.relationship('Company')
    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<VacationPeriod Employee:{self.employee_id} {self.acquisition_start}-{self.acquisition_end}>'

    @property
    def is_overdue(self):
        """Verifica se ferias estao vencidas"""
        from datetime import date
        if self.concession_end and self.status == 'pending':
            return date.today() > self.concession_end
        return False


class ThirteenthSalary(db.Model):
    """13o Salario - Primeira e Segunda Parcela"""
    __tablename__ = 'thirteenth_salary'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # Ano referencia
    reference_year = db.Column(db.Integer, nullable=False)

    # Meses trabalhados no ano (para proporcional)
    months_worked = db.Column(db.Integer, default=12)

    # Salario base para calculo
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)

    # ========== PRIMEIRA PARCELA (ate 30/nov - 50% sem descontos) ==========
    first_installment_value = db.Column(db.Numeric(10, 2), default=0)
    first_installment_date = db.Column(db.Date)        # Data pagamento
    first_installment_paid = db.Column(db.Boolean, default=False)
    first_installment_paid_at = db.Column(db.DateTime)
    first_installment_method = db.Column(db.String(50))

    # ========== SEGUNDA PARCELA (ate 20/dez - 50% com descontos) ==========
    second_installment_gross = db.Column(db.Numeric(10, 2), default=0)
    second_installment_inss = db.Column(db.Numeric(10, 2), default=0)   # INSS sobre TOTAL
    second_installment_irrf = db.Column(db.Numeric(10, 2), default=0)   # IRRF sobre TOTAL
    second_installment_net = db.Column(db.Numeric(10, 2), default=0)    # Liquido 2a parcela
    second_installment_date = db.Column(db.Date)
    second_installment_paid = db.Column(db.Boolean, default=False)
    second_installment_paid_at = db.Column(db.DateTime)
    second_installment_method = db.Column(db.String(50))

    # ========== TOTAIS ==========
    total_gross = db.Column(db.Numeric(10, 2), default=0)    # Total bruto (1a + 2a)
    total_inss = db.Column(db.Numeric(10, 2), default=0)     # Total INSS
    total_irrf = db.Column(db.Numeric(10, 2), default=0)     # Total IRRF
    total_net = db.Column(db.Numeric(10, 2), default=0)      # Total liquido

    # ========== STATUS ==========
    status = db.Column(db.String(20), default='pending')
    # pending = aguardando geracao
    # first_paid = 1a parcela paga
    # completed = ambas pagas
    # cancelled = cancelado

    # ========== INTEGRACAO FINANCEIRA ==========
    first_account_payable_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))
    second_account_payable_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))
    financial_integrated = db.Column(db.Boolean, default=False)

    # Observacoes
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relacionamentos
    company = db.relationship('Company')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<ThirteenthSalary Employee:{self.employee_id} Year:{self.reference_year}>'


class Termination(db.Model):
    """Rescisao Trabalhista CLT"""
    __tablename__ = 'termination'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    # ========== DATAS ==========
    termination_date = db.Column(db.Date, nullable=False)   # Data desligamento
    notice_start = db.Column(db.Date)                        # Inicio aviso previo
    last_day_worked = db.Column(db.Date)                     # Ultimo dia trabalhado
    payment_deadline = db.Column(db.Date)                    # Prazo pagamento (10 dias)

    # ========== TIPO RESCISAO ==========
    termination_type = db.Column(db.String(30), nullable=False)
    # sem_justa_causa = Demissao sem justa causa
    # justa_causa = Demissao por justa causa
    # pedido_demissao = Pedido de demissao
    # acordo_mutuo = Acordo mutuo (reforma trabalhista)
    # culpa_reciproca = Culpa reciproca
    # falecimento = Falecimento do empregado

    # ========== AVISO PREVIO ==========
    notice_type = db.Column(db.String(20))
    # trabalhado = Aviso trabalhado
    # indenizado = Aviso indenizado (pago)
    # dispensado = Aviso dispensado
    # cumprido_parcial = Cumprido parcialmente

    notice_days = db.Column(db.Integer, default=30)  # 30 + 3/ano (max 90)
    notice_days_worked = db.Column(db.Integer, default=0)
    notice_days_indemnified = db.Column(db.Integer, default=0)

    # ========== SALARIO E TEMPO ==========
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)
    admission_date = db.Column(db.Date, nullable=False)
    years_worked = db.Column(db.Integer, default=0)
    months_worked_year = db.Column(db.Integer, default=0)  # Meses no ano corrente
    days_worked_month = db.Column(db.Integer, default=0)   # Dias no mes

    # ========== VERBAS RESCISORIAS ==========
    # Proventos
    salary_balance = db.Column(db.Numeric(10, 2), default=0)       # Saldo de salario
    notice_value = db.Column(db.Numeric(10, 2), default=0)         # Aviso previo indenizado
    thirteenth_prop = db.Column(db.Numeric(10, 2), default=0)      # 13o proporcional
    vacation_overdue = db.Column(db.Numeric(10, 2), default=0)     # Ferias vencidas
    vacation_overdue_bonus = db.Column(db.Numeric(10, 2), default=0)  # 1/3 ferias vencidas
    vacation_prop = db.Column(db.Numeric(10, 2), default=0)        # Ferias proporcionais
    vacation_prop_bonus = db.Column(db.Numeric(10, 2), default=0)  # 1/3 ferias proporcionais
    other_credits = db.Column(db.Numeric(10, 2), default=0)        # Outros creditos

    # Total proventos
    gross_total = db.Column(db.Numeric(10, 2), default=0)

    # ========== DESCONTOS ==========
    inss_discount = db.Column(db.Numeric(10, 2), default=0)
    irrf_discount = db.Column(db.Numeric(10, 2), default=0)
    notice_discount = db.Column(db.Numeric(10, 2), default=0)      # Se nao cumpriu aviso
    advances_discount = db.Column(db.Numeric(10, 2), default=0)    # Adiantamentos pendentes
    other_discounts = db.Column(db.Numeric(10, 2), default=0)

    # Total descontos
    total_discounts = db.Column(db.Numeric(10, 2), default=0)

    # ========== FGTS ==========
    fgts_balance = db.Column(db.Numeric(10, 2), default=0)         # Saldo FGTS depositado
    fgts_month = db.Column(db.Numeric(10, 2), default=0)           # FGTS mes rescisao
    fgts_13th = db.Column(db.Numeric(10, 2), default=0)            # FGTS sobre 13o
    fgts_notice = db.Column(db.Numeric(10, 2), default=0)          # FGTS sobre aviso
    fgts_fine = db.Column(db.Numeric(10, 2), default=0)            # Multa FGTS (40% ou 20%)
    fgts_fine_percent = db.Column(db.Integer, default=0)           # 40 ou 20
    fgts_total_deposit = db.Column(db.Numeric(10, 2), default=0)   # Total a depositar
    fgts_total_withdraw = db.Column(db.Numeric(10, 2), default=0)  # Total a sacar

    # ========== TOTAIS ==========
    net_total = db.Column(db.Numeric(10, 2), default=0)            # Liquido rescisao
    employer_cost = db.Column(db.Numeric(10, 2), default=0)        # Custo total empresa

    # ========== STATUS ==========
    status = db.Column(db.String(20), default='draft')
    # draft = Rascunho
    # calculated = Calculado
    # approved = Aprovado
    # paid = Pago
    # cancelled = Cancelado

    # ========== DOCUMENTOS ==========
    trct_generated = db.Column(db.Boolean, default=False)   # TRCT gerado
    grrf_generated = db.Column(db.Boolean, default=False)   # GRRF gerado
    seguro_desemprego = db.Column(db.Boolean, default=False)  # Tem direito?
    guias_generated = db.Column(db.Boolean, default=False)  # Guias geradas

    # ========== PAGAMENTO ==========
    payment_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))
    paid_at = db.Column(db.DateTime)

    # ========== INTEGRACAO FINANCEIRA ==========
    account_payable_id = db.Column(db.Integer, db.ForeignKey('account_payable.id'))
    financial_integrated = db.Column(db.Boolean, default=False)

    # Homologacao
    homologation_date = db.Column(db.Date)
    homologation_local = db.Column(db.String(200))

    # Observacoes
    notes = db.Column(db.Text)
    reason = db.Column(db.Text)  # Motivo da rescisao

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)

    # Relacionamentos
    company = db.relationship('Company')
    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<Termination Employee:{self.employee_id} Type:{self.termination_type}>'

    @property
    def has_fgts_fine(self):
        """Verifica se tem direito a multa FGTS"""
        return self.termination_type in ['sem_justa_causa', 'acordo_mutuo', 'culpa_reciproca']

    @property
    def has_seguro_desemprego(self):
        """Verifica se tem direito a seguro desemprego"""
        return self.termination_type == 'sem_justa_causa'


# ============================================
# MODELS FINANCEIROS (mantidos iguais)
# ============================================

class AccountPayable(db.Model):
    """Contas a pagar"""
    __tablename__ = 'account_payable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)

    # Recorrencia
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_type = db.Column(db.String(20))
    recurrence_day = db.Column(db.Integer)

    # Pagamento
    status = db.Column(db.String(20), default='pending')
    paid_amount = db.Column(db.Numeric(10, 2))
    paid_at = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'))

    # Origem (qual modulo gerou)
    origin_type = db.Column(db.String(50))  # payroll, vacation, thirteenth, termination, maintenance, etc
    origin_id = db.Column(db.Integer)

    # Centro de Custo
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'))

    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    company = db.relationship('Company')
    supplier = db.relationship('Supplier')
    bank_account = db.relationship('BankAccount')
    creator = db.relationship('User')
    cost_center = db.relationship('CostCenter')

    def __repr__(self):
        return f'<AccountPayable {self.description}>'

    @property
    def days_until_due(self):
        if self.due_date:
            from datetime import date
            return (self.due_date - date.today()).days
        return 0

    @property
    def formatted_amount(self):
        if self.amount:
            return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return "R$ 0,00"


class AccountReceivable(db.Model):
    """Contas a receber"""
    __tablename__ = 'account_receivable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)

    # Recebimento
    status = db.Column(db.String(20), default='pending')
    received_amount = db.Column(db.Numeric(10, 2))
    received_at = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'))

    # Origem
    origin_type = db.Column(db.String(50))
    origin_id = db.Column(db.Integer)

    # Integracao Asaas
    asaas_payment_id = db.Column(db.String(100))
    asaas_invoice_url = db.Column(db.String(500))
    asaas_pix_qrcode = db.Column(db.Text)
    asaas_pix_payload = db.Column(db.Text)
    asaas_boleto_url = db.Column(db.String(500))

    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    company = db.relationship('Company')
    client = db.relationship('Client')
    bank_account = db.relationship('BankAccount')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<AccountReceivable {self.description}>'

    @property
    def formatted_amount(self):
        if self.amount:
            return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return "R$ 0,00"


class FreelancerPayment(db.Model):
    """Pagamentos para freelancers"""
    __tablename__ = 'freelancer_payment'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('freelancer.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('freelancer_assignment.id'))

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))

    reference = db.Column(db.String(100))
    description = db.Column(db.String(200))

    status = db.Column(db.String(20), default='pending')
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
    account_type = db.Column(db.String(20))

    initial_balance = db.Column(db.Numeric(10, 2), default=0)
    current_balance = db.Column(db.Numeric(10, 2), default=0)

    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<BankAccount {self.name}>'


class CostCenter(db.Model):
    """Centros de custo"""
    __tablename__ = 'cost_center'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    description = db.Column(db.Text)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<CostCenter {self.name}>'


class Supplier(db.Model):
    """Fornecedores"""
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    cnpj_cpf = db.Column(db.String(18))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    category = db.Column(db.String(50))

    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))

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

    name = db.Column(db.String(200), nullable=False)
    cnpj_cpf = db.Column(db.String(18))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)

    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))

    # Integracao Asaas
    asaas_customer_id = db.Column(db.String(100))

    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<Client {self.name}>'


class Vehicle(db.Model):
    """Veiculos da frota"""
    __tablename__ = 'vehicle'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    plate = db.Column(db.String(10))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    color = db.Column(db.String(30))

    vehicle_type = db.Column(db.String(30))
    fuel_type = db.Column(db.String(20))
    capacity = db.Column(db.String(50))

    status = db.Column(db.String(20), default='available')
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<Vehicle {self.plate}>'


class Consumable(db.Model):
    """Consumiveis/Materiais"""
    __tablename__ = 'consumable'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20))

    quantity = db.Column(db.Numeric(10, 2), default=0)
    min_quantity = db.Column(db.Numeric(10, 2), default=0)
    unit_cost = db.Column(db.Numeric(10, 2), default=0)

    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))

    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')
    supplier = db.relationship('Supplier')

    def __repr__(self):
        return f'<Consumable {self.name}>'


class ContractTemplate(db.Model):
    """Templates de contrato"""
    __tablename__ = 'contract_template'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    contract_type = db.Column(db.String(50))
    content = db.Column(db.Text)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')

    def __repr__(self):
        return f'<ContractTemplate {self.name}>'


class CashRegister(db.Model):
    """Caixa da empresa"""
    __tablename__ = 'cash_register'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    current_balance = db.Column(db.Numeric(10, 2), default=0)

    is_open = db.Column(db.Boolean, default=False)
    opened_at = db.Column(db.DateTime)
    opened_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    opening_balance = db.Column(db.Numeric(10, 2), default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company')
    opener = db.relationship('User')

    def __repr__(self):
        return f'<CashRegister {self.name}>'


class CashEntry(db.Model):
    """Lancamentos do caixa"""
    __tablename__ = 'cash_entry'

    id = db.Column(db.Integer, primary_key=True)
    cash_register_id = db.Column(db.Integer, db.ForeignKey('cash_register.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    entry_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(200))
    category = db.Column(db.String(50))

    reference_type = db.Column(db.String(50))
    reference_id = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    cash_register = db.relationship('CashRegister')
    company = db.relationship('Company')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<CashEntry {self.entry_type} R${self.amount}>'