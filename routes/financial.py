"""Rotas do módulo financeiro - apenas admin"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.financial import Quote, QuoteItem, Contract, Invoice, Payment
from models.tour import Tour
from datetime import datetime, date, timedelta
from decimal import Decimal

financial_bp = Blueprint('financial', __name__, url_prefix='/financial')


def admin_required(f):
    """Decorator para rotas apenas admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def generate_code(prefix: str) -> str:
    """Gera código sequencial para documentos (inclui company_id para unicidade global)"""
    year = datetime.now().year
    company_id = current_user.company_id
    code_prefix = f'{prefix}-{company_id}-{year}'
    last_doc = None
    
    if prefix == 'ORC':
        last_doc = Quote.query.filter(
            Quote.code.like(f'{code_prefix}-%'),
            Quote.company_id == company_id
        ).order_by(Quote.id.desc()).first()
    elif prefix == 'CTR':
        last_doc = Contract.query.filter(
            Contract.code.like(f'{code_prefix}-%'),
            Contract.company_id == company_id
        ).order_by(Contract.id.desc()).first()
    elif prefix == 'FAT':
        last_doc = Invoice.query.filter(
            Invoice.code.like(f'{code_prefix}-%'),
            Invoice.company_id == company_id
        ).order_by(Invoice.id.desc()).first()
    
    if last_doc:
        try:
            last_num = int(last_doc.code.split('-')[-1])
            return f'{code_prefix}-{str(last_num + 1).zfill(4)}'
        except:
            pass
    
    return f'{code_prefix}-0001'


@financial_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard financeiro"""
    quotes_pending = Quote.query.filter_by(
        company_id=current_user.company_id,
        status='sent',
        is_active=True
    ).count()
    
    invoices_pending = Invoice.query.filter_by(
        company_id=current_user.company_id,
        status='pending',
        is_active=True
    ).count()
    
    invoices_overdue = Invoice.query.filter(
        Invoice.company_id == current_user.company_id,
        Invoice.status == 'pending',
        Invoice.due_date < date.today(),
        Invoice.is_active == True
    ).count()
    
    contracts_active = Contract.query.filter_by(
        company_id=current_user.company_id,
        status='active',
        is_active=True
    ).count()
    
    recent_quotes = Quote.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Quote.created_at.desc()).limit(5).all()
    
    recent_invoices = Invoice.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Invoice.created_at.desc()).limit(5).all()
    
    return render_template('financial/index.html',
                          quotes_pending=quotes_pending,
                          invoices_pending=invoices_pending,
                          invoices_overdue=invoices_overdue,
                          contracts_active=contracts_active,
                          recent_quotes=recent_quotes,
                          recent_invoices=recent_invoices)


@financial_bp.route('/quotes')
@login_required
@admin_required
def quotes():
    """Lista de orçamentos"""
    status = request.args.get('status', 'all')
    
    query = Quote.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    )
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    quotes = query.order_by(Quote.created_at.desc()).all()
    
    return render_template('financial/quotes.html', quotes=quotes, status=status)


@financial_bp.route('/quotes/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_quote():
    """Criar novo orçamento"""
    if request.method == 'POST':
        quote = Quote(
            code=generate_code('ORC'),
            client_name=request.form.get('client_name', '').strip(),
            client_email=request.form.get('client_email', '').strip(),
            client_phone=request.form.get('client_phone', '').strip(),
            client_document=request.form.get('client_document', '').strip(),
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', '').strip(),
            notes=request.form.get('notes', '').strip(),
            created_by=current_user.id,
            company_id=current_user.company_id
        )
        
        valid_until = request.form.get('valid_until')
        if valid_until:
            quote.valid_until = datetime.strptime(valid_until, '%Y-%m-%d').date()
        
        tour_id = request.form.get('tour_id')
        if tour_id:
            quote.tour_id = int(tour_id)
        
        db.session.add(quote)
        db.session.commit()
        
        flash('Orçamento criado! Adicione os itens.', 'success')
        return redirect(url_for('financial.edit_quote', id=quote.id))
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.start_date.desc()).all()
    
    return render_template('financial/quote_form.html', quote=None, tours=tours)


@financial_bp.route('/quotes/<int:id>')
@login_required
@admin_required
def view_quote(id):
    """Visualizar orçamento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    return render_template('financial/quote_view.html', quote=quote)


@financial_bp.route('/quotes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_quote(id):
    """Editar orçamento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        quote.client_name = request.form.get('client_name', quote.client_name).strip()
        quote.client_email = request.form.get('client_email', '').strip()
        quote.client_phone = request.form.get('client_phone', '').strip()
        quote.client_document = request.form.get('client_document', '').strip()
        quote.title = request.form.get('title', quote.title).strip()
        quote.description = request.form.get('description', '').strip()
        quote.notes = request.form.get('notes', '').strip()
        
        valid_until = request.form.get('valid_until')
        if valid_until:
            quote.valid_until = datetime.strptime(valid_until, '%Y-%m-%d').date()
        
        discount_percent = request.form.get('discount_percent', '0')
        quote.discount_percent = Decimal(discount_percent or '0')
        
        recalculate_quote_totals(quote)
        
        db.session.commit()
        flash('Orçamento atualizado!', 'success')
        return redirect(url_for('financial.view_quote', id=quote.id))
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.start_date.desc()).all()
    
    return render_template('financial/quote_form.html', quote=quote, tours=tours)


@financial_bp.route('/quotes/<int:id>/items', methods=['POST'])
@login_required
@admin_required
def add_quote_item(id):
    """Adicionar item ao orçamento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    item = QuoteItem(
        quote_id=quote.id,
        description=request.form.get('description', '').strip(),
        quantity=int(request.form.get('quantity', 1)),
        unit_price=Decimal(request.form.get('unit_price', '0'))
    )
    item.total = item.quantity * item.unit_price
    
    db.session.add(item)
    recalculate_quote_totals(quote)
    db.session.commit()
    
    flash('Item adicionado!', 'success')
    return redirect(url_for('financial.edit_quote', id=quote.id))


@financial_bp.route('/quotes/<int:id>/items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_quote_item(id, item_id):
    """Remover item do orçamento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    item = QuoteItem.query.filter_by(id=item_id, quote_id=quote.id).first_or_404()
    db.session.delete(item)
    recalculate_quote_totals(quote)
    db.session.commit()
    
    flash('Item removido.', 'warning')
    return redirect(url_for('financial.edit_quote', id=quote.id))


@financial_bp.route('/quotes/<int:id>/send', methods=['POST'])
@login_required
@admin_required
def send_quote(id):
    """Marcar orçamento como enviado"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    quote.status = 'sent'
    db.session.commit()
    
    flash('Orçamento marcado como enviado!', 'success')
    return redirect(url_for('financial.view_quote', id=quote.id))


@financial_bp.route('/quotes/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_quote(id):
    """Aprovar orçamento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    quote.status = 'approved'
    quote.approved_at = datetime.utcnow()
    quote.approved_by = current_user.id
    db.session.commit()
    
    flash('Orçamento aprovado!', 'success')
    return redirect(url_for('financial.view_quote', id=quote.id))


@financial_bp.route('/invoices')
@login_required
@admin_required
def invoices():
    """Lista de faturas"""
    status = request.args.get('status', 'all')
    
    query = Invoice.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    )
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    invoices = query.order_by(Invoice.created_at.desc()).all()
    
    return render_template('financial/invoices.html', invoices=invoices, status=status)


@financial_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_invoice():
    """Criar nova fatura"""
    if request.method == 'POST':
        invoice = Invoice(
            code=generate_code('FAT'),
            client_name=request.form.get('client_name', '').strip(),
            client_email=request.form.get('client_email', '').strip(),
            client_document=request.form.get('client_document', '').strip(),
            description=request.form.get('description', '').strip(),
            subtotal=Decimal(request.form.get('subtotal', '0')),
            due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(),
            created_by=current_user.id,
            company_id=current_user.company_id
        )
        
        tax_percent = request.form.get('tax_percent', '0')
        invoice.tax_percent = Decimal(tax_percent or '0')
        invoice.tax_value = invoice.subtotal * invoice.tax_percent / 100
        invoice.total = invoice.subtotal + invoice.tax_value
        
        tour_id = request.form.get('tour_id')
        if tour_id:
            invoice.tour_id = int(tour_id)
        
        contract_id = request.form.get('contract_id')
        if contract_id:
            invoice.contract_id = int(contract_id)
        
        db.session.add(invoice)
        db.session.commit()
        
        flash('Fatura criada!', 'success')
        return redirect(url_for('financial.view_invoice', id=invoice.id))
    
    tours = Tour.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Tour.start_date.desc()).all()
    
    return render_template('financial/invoice_form.html', invoice=None, tours=tours)


@financial_bp.route('/invoices/<int:id>')
@login_required
@admin_required
def view_invoice(id):
    """Visualizar fatura"""
    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    return render_template('financial/invoice_view.html', invoice=invoice)


@financial_bp.route('/invoices/<int:id>/register-payment', methods=['POST'])
@login_required
@admin_required
def register_payment(id):
    """Registrar pagamento manual"""
    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    payment = Payment(
        invoice_id=invoice.id,
        amount=Decimal(request.form.get('amount', '0')),
        method=request.form.get('method', 'pix'),
        status='confirmed',
        paid_at=datetime.utcnow(),
        confirmed_by=current_user.id,
        notes=request.form.get('notes', ''),
        provider='manual',
        company_id=current_user.company_id
    )
    
    db.session.add(payment)
    
    if payment.amount >= invoice.amount_pending:
        invoice.status = 'paid'
        invoice.paid_at = datetime.utcnow()
    else:
        invoice.status = 'partial'
    
    db.session.commit()
    
    flash('Pagamento registrado!', 'success')
    return redirect(url_for('financial.view_invoice', id=invoice.id))


def recalculate_quote_totals(quote):
    """Recalcula totais do orçamento"""
    subtotal = sum(item.total for item in quote.items)
    quote.subtotal = subtotal
    quote.discount_value = subtotal * (quote.discount_percent or 0) / 100
    quote.total = subtotal - quote.discount_value


@financial_bp.route('/receitas')
@login_required
@admin_required
def receitas():
    """Lista de receitas (faturas)"""
    status = request.args.get('status', 'all')
    
    query = Invoice.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    )
    
    if status == 'pago':
        query = query.filter_by(status='paid')
    elif status == 'pendente':
        query = query.filter_by(status='pending')
    elif status == 'atrasado':
        query = query.filter(Invoice.status == 'pending', Invoice.due_date < date.today())
    
    faturas = query.order_by(Invoice.created_at.desc()).all()
    
    return render_template('financial/receitas.html', faturas=faturas, status=status)


@financial_bp.route('/despesas')
@login_required
@admin_required
def despesas():
    """Visao geral de despesas"""
    return render_template('financial/despesas.html')


@financial_bp.route('/folha-clt')
@login_required
@admin_required
def folha_clt():
    """Folha de pagamento CLT"""
    from models.rh import Employee, PayrollEntry
    
    funcionarios = Employee.query.filter_by(
        company_id=current_user.company_id,
        employment_type='clt',
        is_active=True
    ).all()
    
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    return render_template('financial/folha_clt.html', 
                          funcionarios=funcionarios,
                          mes=mes_atual,
                          ano=ano_atual)


@financial_bp.route('/freelancers')
@login_required
@admin_required
def freelancers():
    """Pagamentos a freelancers"""
    from models.rh import Employee, FreelancerPayment
    
    freelancers_list = Employee.query.filter_by(
        company_id=current_user.company_id,
        employment_type='freelancer',
        is_active=True
    ).all()
    
    pagamentos_recentes = FreelancerPayment.query.filter_by(
        company_id=current_user.company_id
    ).order_by(FreelancerPayment.created_at.desc()).limit(10).all()
    
    return render_template('financial/freelancers.html',
                          freelancers=freelancers_list,
                          pagamentos=pagamentos_recentes)


@financial_bp.route('/contas-pagar')
@login_required
@admin_required
def contas_pagar():
    """Contas a pagar"""
    from models.rh import AccountPayable
    
    vencidas = AccountPayable.query.filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date < date.today()
    ).all()
    
    proximos_7_dias = AccountPayable.query.filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date >= date.today(),
        AccountPayable.due_date <= date.today() + timedelta(days=7)
    ).all()
    
    todas = AccountPayable.query.filter_by(
        company_id=current_user.company_id,
        status='pending'
    ).order_by(AccountPayable.due_date).all()
    
    return render_template('financial/contas_pagar.html',
                          vencidas=vencidas,
                          proximos_7_dias=proximos_7_dias,
                          contas=todas)


@financial_bp.route('/emitir-nfse', methods=['GET', 'POST'])
@login_required
@admin_required
def emitir_nfse():
    """Emitir NFSe"""
    if request.method == 'POST':
        flash('NFSe seria emitida aqui (integracao pendente)', 'info')
        return redirect(url_for('financial.emitir_nfse'))
    
    return render_template('financial/emitir_nfse.html')


@financial_bp.route('/gerar-pix', methods=['GET', 'POST'])
@login_required
@admin_required
def gerar_pix():
    """Gerar QR Code PIX"""
    faturas = Invoice.query.filter_by(
        company_id=current_user.company_id,
        status='pending',
        is_active=True
    ).all()
    
    if request.method == 'POST':
        flash('QR Code PIX seria gerado aqui (integracao pendente)', 'info')
        return redirect(url_for('financial.gerar_pix'))
    
    return render_template('financial/gerar_pix.html', faturas=faturas)


@financial_bp.route('/dre')
@login_required
@admin_required
def dre():
    """Demonstrativo de Resultado do Exercicio"""
    return render_template('financial/dre.html')
