from datetime import datetime
from extensions import db

class FinancialProvision(db.Model):
    """Provisionamento financeiro automatico"""
    __tablename__ = 'financial_provision'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'))
    
    # Tipo de provisionamento
    provision_type = db.Column(db.String(50), nullable=False)  # revenue, expense, tax
    category = db.Column(db.String(100))
    
    # Valores
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference_month = db.Column(db.Integer, nullable=False)
    reference_year = db.Column(db.Integer, nullable=False)
    
    # Data de competencia vs realizacao
    competence_date = db.Column(db.Date, nullable=False)
    expected_realization_date = db.Column(db.Date)
    actual_realization_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='provisioned')  # provisioned, realized, cancelled
    
    # Vinculacao
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    
    # Observacoes
    notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_system = db.Column(db.Boolean, default=True)  # Criado automaticamente
    
    # Relacionamentos
    company = db.relationship('Company')
    tour = db.relationship('Tour')
    quote = db.relationship('Quote')
    invoice = db.relationship('Invoice')
    
    def __repr__(self):
        return f'<FinancialProvision {self.provision_type} - R$ {self.amount}>'


class PaymentStrategy(db.Model):
    """Estrategias de pagamento sugeridas por IA"""
    __tablename__ = 'payment_strategy'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    
    # Estrategia sugerida
    strategy_type = db.Column(db.String(50), nullable=False)  # early_payment, installment, negotiate_terms
    description = db.Column(db.Text, nullable=False)
    
    # Beneficios esperados
    expected_savings = db.Column(db.Numeric(10, 2))
    expected_cashflow_improvement = db.Column(db.Numeric(10, 2))
    risk_score = db.Column(db.Integer)  # 0-100 (maior = mais arriscado)
    
    # Confianca da IA
    ai_confidence = db.Column(db.Integer)  # 0-100
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, executed
    
    # Resultado
    executed_at = db.Column(db.DateTime)
    actual_savings = db.Column(db.Numeric(10, 2))
    result_notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    invoice = db.relationship('Invoice')
    payment = db.relationship('Payment')
    
    def __repr__(self):
        return f'<PaymentStrategy {self.strategy_type}>'


class CashFlowProjection(db.Model):
    """Projecao de fluxo de caixa"""
    __tablename__ = 'cash_flow_projection'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Periodo
    projection_date = db.Column(db.Date, nullable=False)
    projection_month = db.Column(db.Integer, nullable=False)
    projection_year = db.Column(db.Integer, nullable=False)
    
    # Valores projetados
    projected_revenue = db.Column(db.Numeric(10, 2), default=0)
    projected_expenses = db.Column(db.Numeric(10, 2), default=0)
    projected_balance = db.Column(db.Numeric(10, 2), default=0)
    
    # Valores realizados (para comparacao)
    actual_revenue = db.Column(db.Numeric(10, 2))
    actual_expenses = db.Column(db.Numeric(10, 2))
    actual_balance = db.Column(db.Numeric(10, 2))
    
    # Confianca da projecao
    confidence_level = db.Column(db.Integer)  # 0-100
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    
    @property
    def variance_percentage(self):
        """Variacao percentual entre projetado e realizado"""
        if self.actual_balance and self.projected_balance:
            return ((self.actual_balance - self.projected_balance) / self.projected_balance) * 100
        return None
    
    def __repr__(self):
        return f'<CashFlowProjection {self.projection_month}/{self.projection_year}>'


class TaxCalculation(db.Model):
    """Calculos de impostos (Simples Nacional, MEI, etc)"""
    __tablename__ = 'tax_calculation'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Periodo
    reference_month = db.Column(db.Integer, nullable=False)
    reference_year = db.Column(db.Integer, nullable=False)
    
    # Regime tributario
    tax_regime = db.Column(db.String(50))  # simples_nacional, lucro_presumido, mei
    
    # Valores
    gross_revenue = db.Column(db.Numeric(10, 2), nullable=False)
    tax_base = db.Column(db.Numeric(10, 2))
    tax_rate = db.Column(db.Numeric(5, 2))  # Percentual
    calculated_tax = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Detalhamento
    calculation_details = db.Column(db.Text)  # JSON com detalhes
    
    # Status
    status = db.Column(db.String(20), default='calculated')  # calculated, paid, overdue
    
    # Pagamento
    due_date = db.Column(db.Date)
    payment_date = db.Column(db.Date)
    payment_amount = db.Column(db.Numeric(10, 2))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    company = db.relationship('Company')
    
    def __repr__(self):
        return f'<TaxCalculation {self.reference_month}/{self.reference_year}>'


class FinancialAlert(db.Model):
    """Alertas financeiros automaticos"""
    __tablename__ = 'financial_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Tipo de alerta
    alert_type = db.Column(db.String(50), nullable=False)  # low_cash, overdue_payment, high_expense, revenue_drop
    severity = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    
    # Mensagem
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, acknowledged, resolved
    
    # Vinculacao
    reference_type = db.Column(db.String(50))  # invoice, payment, provision
    reference_id = db.Column(db.Integer)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_at = db.Column(db.DateTime)
    
    # Relacionamentos
    company = db.relationship('Company')
    acknowledger = db.relationship('User')
    
    def __repr__(self):
        return f'<FinancialAlert {self.alert_type}>'
