"""Rotas do módulo financeiro - apenas admin"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func
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


# ============================================
# CONTRATOS
# ============================================

@financial_bp.route('/contracts')
@login_required
@admin_required
def contracts():
    """Lista de contratos"""
    status = request.args.get('status')
    
    query = Contract.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    )
    
    if status:
        query = query.filter_by(status=status)
    
    contracts = query.order_by(Contract.created_at.desc()).all()
    return render_template('financial/contracts.html', contracts=contracts)


@financial_bp.route('/contracts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def contract_new():
    """Criar novo contrato"""
    if request.method == 'POST':
        contract = Contract(
            code=generate_code('CTR'),
            client_name=request.form.get('client_name', '').strip(),
            client_document=request.form.get('client_document', '').strip(),
            client_email=request.form.get('client_email', '').strip(),
            client_phone=request.form.get('client_phone', '').strip(),
            client_address=request.form.get('client_address', '').strip(),
            title=request.form.get('title', '').strip(),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
            total_value=Decimal(request.form.get('total_value', '0')),
            deposit_value=Decimal(request.form.get('deposit_value', '0') or '0'),
            status=request.form.get('status', 'draft'),
            service_description=request.form.get('service_description', ''),
            payment_terms=request.form.get('payment_terms', ''),
            additional_terms=request.form.get('additional_terms', ''),
            created_by=current_user.id,
            company_id=current_user.company_id
        )
        db.session.add(contract)
        db.session.commit()
        
        flash('Contrato criado com sucesso!', 'success')
        return redirect(url_for('financial.contract_edit', contract_id=contract.id))
    
    return render_template('financial/contract_form.html', contract=None)


@financial_bp.route('/contracts/<int:contract_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contract_edit(contract_id):
    """Editar contrato"""
    contract = Contract.query.filter_by(
        id=contract_id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        contract.client_name = request.form.get('client_name', '').strip()
        contract.client_document = request.form.get('client_document', '').strip()
        contract.client_email = request.form.get('client_email', '').strip()
        contract.client_phone = request.form.get('client_phone', '').strip()
        contract.client_address = request.form.get('client_address', '').strip()
        contract.title = request.form.get('title', '').strip()
        contract.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        contract.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        contract.total_value = Decimal(request.form.get('total_value', '0'))
        contract.deposit_value = Decimal(request.form.get('deposit_value', '0') or '0')
        contract.status = request.form.get('status', 'draft')
        contract.service_description = request.form.get('service_description', '')
        contract.payment_terms = request.form.get('payment_terms', '')
        contract.additional_terms = request.form.get('additional_terms', '')
        
        db.session.commit()
        flash('Contrato atualizado!', 'success')
        return redirect(url_for('financial.contract_edit', contract_id=contract.id))
    
    return render_template('financial/contract_form.html', contract=contract)


@financial_bp.route('/contracts/<int:contract_id>/delete', methods=['POST'])
@login_required
@admin_required
def contract_delete(contract_id):
    """Excluir contrato (soft delete)"""
    contract = Contract.query.filter_by(
        id=contract_id,
        company_id=current_user.company_id
    ).first_or_404()
    
    contract.is_active = False
    db.session.commit()
    
    flash('Contrato excluído.', 'warning')
    return redirect(url_for('financial.contracts'))


@financial_bp.route('/api/contracts/<int:contract_id>')
@login_required
@admin_required
def api_contract_get(contract_id):
    """API: Obter dados do contrato para wizard"""
    contract = Contract.query.filter_by(
        id=contract_id,
        company_id=current_user.company_id
    ).first_or_404()
    
    return jsonify({
        'success': True,
        'contract': {
            'id': contract.id,
            'code': contract.code,
            'client_name': contract.client_name,
            'client_email': contract.client_email,
            'title': contract.title,
            'total_value': float(contract.total_value or 0),
            'start_date': contract.start_date.isoformat() if contract.start_date else None,
            'end_date': contract.end_date.isoformat() if contract.end_date else None,
            'status': contract.status,
            'edit_url': url_for('financial.contract_edit', contract_id=contract.id)
        }
    })


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
    """Folha de pagamento CLT - visualizacao (dados do RH)"""
    from models.rh import Employee, PayrollEntry
    from dateutil.relativedelta import relativedelta
    
    funcionarios = Employee.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Employee.name).all()
    
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    total_salarios = sum(float(f.salary or 0) for f in funcionarios)
    encargos_estimados = total_salarios * 0.68
    custo_total = total_salarios + encargos_estimados
    
    funcionarios_data = []
    for func in funcionarios:
        prox_ferias = None
        if func.admission_date:
            anos_trabalhados = (date.today() - func.admission_date).days // 365
            prox_aquisitivo = func.admission_date + relativedelta(years=anos_trabalhados + 1)
            prox_ferias = prox_aquisitivo + relativedelta(months=11)
        
        custo_func = float(func.salary or 0) * 1.68
        
        funcionarios_data.append({
            'id': func.id,
            'name': func.name,
            'position': func.position,
            'salary': float(func.salary or 0),
            'custo_total': custo_func,
            'admission_date': func.admission_date,
            'prox_ferias': prox_ferias
        })
    
    return render_template('financial/folha_clt.html', 
                          funcionarios=funcionarios_data,
                          total_salarios=total_salarios,
                          encargos_estimados=encargos_estimados,
                          custo_total=custo_total,
                          mes=mes_atual,
                          ano=ano_atual)


@financial_bp.route('/freelancers')
@login_required
@admin_required
def freelancers():
    """Pagamentos a freelancers - visualizacao (dados do RH)"""
    from models.rh import Freelancer, FreelancerAssignment
    
    freelancers_list = Freelancer.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Freelancer.overall_score.desc()).all()
    
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    freelancers_data = []
    total_mes = 0
    
    for fl in freelancers_list:
        eventos_mes = FreelancerAssignment.query.filter(
            FreelancerAssignment.freelancer_id == fl.id,
            func.strftime('%Y-%m', FreelancerAssignment.start_date) == f'{ano_atual}-{mes_atual:02d}'
        ).count()
        
        valor_mes = db.session.query(func.sum(FreelancerAssignment.total_amount)).filter(
            FreelancerAssignment.freelancer_id == fl.id,
            func.strftime('%Y-%m', FreelancerAssignment.start_date) == f'{ano_atual}-{mes_atual:02d}'
        ).scalar() or 0
        
        total_mes += float(valor_mes)
        
        freelancers_data.append({
            'id': fl.id,
            'name': fl.name,
            'role': fl.role,
            'daily_rate': float(fl.daily_rate or 0),
            'hourly_rate': float(fl.hourly_rate or 0),
            'eventos_mes': eventos_mes,
            'valor_mes': float(valor_mes),
            'score': fl.overall_score
        })
    
    return render_template('financial/freelancers.html',
                          freelancers=freelancers_data,
                          total_mes=total_mes,
                          mes=mes_atual,
                          ano=ano_atual)


@financial_bp.route('/contas-pagar')
@login_required
@admin_required
def contas_pagar():
    """Contas a pagar - lista com filtros"""
    from models.rh import AccountPayable
    from sqlalchemy import func
    
    status_filter = request.args.get('status', 'pending')
    categoria_filter = request.args.get('categoria', '')
    
    query = AccountPayable.query.filter_by(company_id=current_user.company_id)
    
    if status_filter == 'pending':
        query = query.filter_by(status='pending')
    elif status_filter == 'paid':
        query = query.filter_by(status='paid')
    elif status_filter == 'overdue':
        query = query.filter(
            AccountPayable.status == 'pending',
            AccountPayable.due_date < date.today()
        )
    
    if categoria_filter:
        query = query.filter_by(category=categoria_filter)
    
    contas = query.order_by(AccountPayable.due_date).all()
    
    total_vencidas = db.session.query(func.sum(AccountPayable.amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date < date.today()
    ).scalar() or 0
    
    total_7_dias = db.session.query(func.sum(AccountPayable.amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date >= date.today(),
        AccountPayable.due_date <= date.today() + timedelta(days=7)
    ).scalar() or 0
    
    current_month = date.today().strftime('%Y-%m')
    total_mes = db.session.query(func.sum(AccountPayable.amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        func.strftime('%Y-%m', AccountPayable.due_date) == current_month
    ).scalar() or 0
    
    categorias = ['aluguel', 'energia', 'agua', 'telefone', 'internet', 'combustivel', 'manutencao', 'outros']
    
    return render_template('financial/contas_pagar.html',
                          contas=contas,
                          total_vencidas=total_vencidas,
                          total_7_dias=total_7_dias,
                          total_mes=total_mes,
                          categorias=categorias,
                          status_filter=status_filter,
                          categoria_filter=categoria_filter)


@financial_bp.route('/contas-pagar/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def nova_conta_pagar():
    """Criar nova conta a pagar"""
    from models.rh import AccountPayable
    
    if request.method == 'POST':
        try:
            total_installments = int(request.form.get('total_installments', '1') or '1')
            valor_total = Decimal(request.form.get('amount', '0').replace(',', '.'))
            valor_parcela = valor_total / total_installments if total_installments > 1 else valor_total
            due_date_base = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
            
            from dateutil.relativedelta import relativedelta
            
            for i in range(total_installments):
                due_date = due_date_base + relativedelta(months=i) if total_installments > 1 else due_date_base
                
                conta = AccountPayable(
                    company_id=current_user.company_id,
                    description=request.form.get('description', '').strip(),
                    category=request.form.get('category', 'outros'),
                    custom_category=request.form.get('custom_category', '').strip() if request.form.get('category') == 'outros' else None,
                    supplier=request.form.get('supplier', '').strip(),
                    amount=valor_parcela,
                    due_date=due_date,
                    is_recurring=request.form.get('is_recurring') == 'on' if total_installments == 1 else False,
                    recurrence_type=request.form.get('recurrence_type') if request.form.get('is_recurring') == 'on' and total_installments == 1 else None,
                    payment_method=request.form.get('payment_method', '').strip() or None,
                    installment_number=i + 1 if total_installments > 1 else None,
                    total_installments=total_installments if total_installments > 1 else None,
                    notes=request.form.get('notes', '').strip(),
                    status='pending',
                    created_by=current_user.id
                )
                
                db.session.add(conta)
            
            db.session.commit()
            
            if total_installments > 1:
                flash(f'{total_installments} parcelas cadastradas com sucesso!', 'success')
            else:
                flash('Conta cadastrada com sucesso!', 'success')
            return redirect(url_for('financial.contas_pagar'))
            
        except ValueError as e:
            flash(f'Erro nos dados: verifique valor e data.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    categorias = ['aluguel', 'energia', 'agua', 'telefone', 'internet', 'combustivel', 'manutencao', 'outros']
    return render_template('financial/conta_pagar_form.html', conta=None, categorias=categorias)


@financial_bp.route('/contas-pagar/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_conta_pagar(id):
    """Editar conta a pagar"""
    from models.rh import AccountPayable
    
    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            conta.description = request.form.get('description', conta.description).strip()
            conta.category = request.form.get('category', conta.category)
            conta.custom_category = request.form.get('custom_category', '').strip() if conta.category == 'outros' else None
            conta.supplier = request.form.get('supplier', '').strip()
            conta.amount = Decimal(request.form.get('amount', '0').replace(',', '.'))
            conta.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
            conta.is_recurring = request.form.get('is_recurring') == 'on'
            conta.recurrence_type = request.form.get('recurrence_type') if conta.is_recurring else None
            conta.payment_method = request.form.get('payment_method', '').strip() or None
            conta.notes = request.form.get('notes', '').strip()
            
            db.session.commit()
            
            flash('Conta atualizada!', 'success')
            return redirect(url_for('financial.contas_pagar'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    categorias = ['aluguel', 'energia', 'agua', 'telefone', 'internet', 'combustivel', 'manutencao', 'outros']
    return render_template('financial/conta_pagar_form.html', conta=conta, categorias=categorias)


@financial_bp.route('/contas-pagar/<int:id>/pagar', methods=['POST'])
@login_required
@admin_required
def pagar_conta(id):
    """Marcar conta como paga"""
    from models.rh import AccountPayable
    
    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    valor_pago = request.form.get('paid_amount', '')
    if valor_pago:
        conta.paid_amount = Decimal(valor_pago.replace(',', '.'))
    else:
        conta.paid_amount = conta.amount
    
    conta.status = 'paid'
    conta.paid_at = datetime.utcnow()
    
    db.session.commit()
    
    if conta.is_recurring:
        from dateutil.relativedelta import relativedelta
        
        proxima = AccountPayable(
            company_id=conta.company_id,
            description=conta.description,
            category=conta.category,
            supplier=conta.supplier,
            amount=conta.amount,
            is_recurring=True,
            recurrence_type=conta.recurrence_type,
            notes=conta.notes,
            status='pending',
            created_by=current_user.id
        )
        
        if conta.recurrence_type == 'monthly':
            proxima.due_date = conta.due_date + relativedelta(months=1)
        elif conta.recurrence_type == 'weekly':
            proxima.due_date = conta.due_date + timedelta(days=7)
        elif conta.recurrence_type == 'yearly':
            proxima.due_date = conta.due_date + relativedelta(years=1)
        else:
            proxima.due_date = conta.due_date + relativedelta(months=1)
        
        db.session.add(proxima)
        db.session.commit()
        flash(f'Conta paga! Proxima parcela criada para {proxima.due_date.strftime("%d/%m/%Y")}.', 'success')
    else:
        flash('Conta marcada como paga!', 'success')
    
    return redirect(url_for('financial.contas_pagar'))


@financial_bp.route('/contas-pagar/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_conta_pagar(id):
    """Excluir conta a pagar"""
    from models.rh import AccountPayable
    
    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    conta.status = 'cancelled'
    db.session.commit()
    
    flash('Conta cancelada.', 'warning')
    return redirect(url_for('financial.contas_pagar'))


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
    """Demonstrativo de Resultado do Exercicio com dados reais"""
    from models.rh import AccountPayable, AccountReceivable, FreelancerPayment, PayrollEntry
    
    current_month = date.today().month
    current_year = date.today().year
    current_month_str = date.today().strftime('%Y-%m')
    
    receitas_locacao = db.session.query(func.sum(AccountReceivable.received_amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'received',
        func.strftime('%Y-%m', AccountReceivable.received_at) == current_month_str
    ).scalar() or 0
    
    receitas_pendentes = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'pending',
        func.strftime('%Y-%m', AccountReceivable.due_date) == current_month_str
    ).scalar() or 0
    
    despesas_folha = db.session.query(func.sum(PayrollEntry.net_salary)).filter(
        PayrollEntry.company_id == current_user.company_id,
        PayrollEntry.reference_month == current_month,
        PayrollEntry.reference_year == current_year
    ).scalar() or 0
    
    despesas_contas = db.session.query(func.sum(AccountPayable.paid_amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'paid',
        func.strftime('%Y-%m', AccountPayable.paid_at) == current_month_str
    ).scalar() or 0
    
    despesas_pendentes = db.session.query(func.sum(AccountPayable.amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'pending',
        func.strftime('%Y-%m', AccountPayable.due_date) == current_month_str
    ).scalar() or 0
    
    despesas_freelancers = db.session.query(func.sum(FreelancerPayment.amount)).filter(
        FreelancerPayment.company_id == current_user.company_id,
        FreelancerPayment.status == 'paid',
        func.strftime('%Y-%m', FreelancerPayment.paid_at) == current_month_str
    ).scalar() or 0
    
    total_receitas = float(receitas_locacao)
    total_despesas = float(despesas_folha) + float(despesas_contas) + float(despesas_freelancers)
    lucro = total_receitas - total_despesas
    
    return render_template('financial/dre.html',
                          receitas_locacao=receitas_locacao,
                          receitas_pendentes=receitas_pendentes,
                          despesas_folha=despesas_folha,
                          despesas_contas=despesas_contas,
                          despesas_pendentes=despesas_pendentes,
                          despesas_freelancers=despesas_freelancers,
                          total_receitas=total_receitas,
                          total_despesas=total_despesas,
                          lucro=lucro,
                          mes_atual=date.today().strftime('%B/%Y'))


@financial_bp.route('/contas-receber')
@login_required
@admin_required
def contas_receber():
    """Lista de contas a receber"""
    from models.rh import AccountReceivable, Client
    
    status_filter = request.args.get('status', 'pending')
    
    query = AccountReceivable.query.filter_by(company_id=current_user.company_id)
    
    if status_filter == 'pending':
        query = query.filter(AccountReceivable.status == 'pending')
    elif status_filter == 'overdue':
        query = query.filter(
            AccountReceivable.status == 'pending',
            AccountReceivable.due_date < date.today()
        )
    elif status_filter == 'received':
        query = query.filter(AccountReceivable.status == 'received')
    
    contas = query.order_by(AccountReceivable.due_date.asc()).all()
    
    total_vencidas = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'pending',
        AccountReceivable.due_date < date.today()
    ).scalar() or 0
    
    total_7_dias = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'pending',
        AccountReceivable.due_date >= date.today(),
        AccountReceivable.due_date <= date.today() + timedelta(days=7)
    ).scalar() or 0
    
    current_month = date.today().strftime('%Y-%m')
    total_mes = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'pending',
        func.strftime('%Y-%m', AccountReceivable.due_date) == current_month
    ).scalar() or 0
    
    clientes = Client.query.filter_by(company_id=current_user.company_id, is_active=True).all()
    
    return render_template('financial/contas_receber.html',
                          contas=contas,
                          total_vencidas=total_vencidas,
                          total_7_dias=total_7_dias,
                          total_mes=total_mes,
                          clientes=clientes,
                          status_filter=status_filter)


@financial_bp.route('/contas-receber/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def nova_conta_receber():
    """Criar nova conta a receber"""
    from models.rh import AccountReceivable, Client
    
    if request.method == 'POST':
        try:
            total_installments = int(request.form.get('total_installments', '1') or '1')
            valor_total = Decimal(request.form.get('amount', '0').replace(',', '.'))
            valor_parcela = valor_total / total_installments if total_installments > 1 else valor_total
            due_date_base = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
            
            from dateutil.relativedelta import relativedelta
            
            for i in range(total_installments):
                due_date = due_date_base + relativedelta(months=i) if total_installments > 1 else due_date_base
                
                conta = AccountReceivable(
                    company_id=current_user.company_id,
                    description=request.form.get('description', '').strip(),
                    category=request.form.get('category', 'servico'),
                    client_id=int(request.form.get('client_id')) if request.form.get('client_id') else None,
                    client_name=request.form.get('client_name', '').strip(),
                    amount=valor_parcela,
                    due_date=due_date,
                    payment_method=request.form.get('payment_method', '').strip() or None,
                    installment_number=i + 1 if total_installments > 1 else None,
                    total_installments=total_installments if total_installments > 1 else None,
                    notes=request.form.get('notes', '').strip(),
                    status='pending',
                    created_by=current_user.id
                )
                
                db.session.add(conta)
            
            db.session.commit()
            
            if total_installments > 1:
                flash(f'{total_installments} parcelas cadastradas com sucesso!', 'success')
            else:
                flash('Conta a receber cadastrada!', 'success')
            return redirect(url_for('financial.contas_receber'))
            
        except ValueError as e:
            flash(f'Erro nos dados: verifique valor e data.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    clientes = Client.query.filter_by(company_id=current_user.company_id, is_active=True).all()
    categorias = ['servico', 'venda', 'locacao', 'projeto', 'outros']
    return render_template('financial/conta_receber_form.html', conta=None, categorias=categorias, clientes=clientes)


@financial_bp.route('/contas-receber/<int:id>/receber', methods=['POST'])
@login_required
@admin_required
def receber_conta(id):
    """Marcar conta como recebida"""
    from models.rh import AccountReceivable
    
    conta = AccountReceivable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    valor_recebido = request.form.get('received_amount', '')
    if valor_recebido:
        conta.received_amount = Decimal(valor_recebido.replace(',', '.'))
    else:
        conta.received_amount = conta.amount
    
    conta.status = 'received'
    conta.received_at = datetime.utcnow()
    
    db.session.commit()
    flash('Recebimento confirmado!', 'success')
    
    return redirect(url_for('financial.contas_receber'))


@financial_bp.route('/contas-receber/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_conta_receber(id):
    """Excluir conta a receber"""
    from models.rh import AccountReceivable
    
    conta = AccountReceivable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    conta.status = 'cancelled'
    db.session.commit()
    
    flash('Conta cancelada.', 'warning')
    return redirect(url_for('financial.contas_receber'))


@financial_bp.route('/clientes')
@login_required
@admin_required
def clientes():
    """Lista de clientes"""
    from models.rh import Client
    
    clientes = Client.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).order_by(Client.name).all()
    
    return render_template('financial/clientes.html', clientes=clientes)


@financial_bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_cliente():
    """Criar novo cliente"""
    from models.rh import Client
    
    if request.method == 'POST':
        try:
            cliente = Client(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                document=request.form.get('document', '').strip(),
                document_type=request.form.get('document_type', 'cpf'),
                email=request.form.get('email', '').strip(),
                phone=request.form.get('phone', '').strip(),
                address=request.form.get('address', '').strip(),
                city=request.form.get('city', '').strip(),
                state=request.form.get('state', '').strip(),
                notes=request.form.get('notes', '').strip(),
                is_active=True
            )
            
            db.session.add(cliente)
            db.session.commit()
            
            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('financial.clientes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    return render_template('financial/cliente_form.html', cliente=None)


@financial_bp.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_cliente(id):
    """Editar cliente"""
    from models.rh import Client
    
    cliente = Client.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            cliente.name = request.form.get('name', cliente.name).strip()
            cliente.document = request.form.get('document', '').strip()
            cliente.document_type = request.form.get('document_type', 'cpf')
            cliente.email = request.form.get('email', '').strip()
            cliente.phone = request.form.get('phone', '').strip()
            cliente.address = request.form.get('address', '').strip()
            cliente.city = request.form.get('city', '').strip()
            cliente.state = request.form.get('state', '').strip()
            cliente.notes = request.form.get('notes', '').strip()
            
            db.session.commit()
            
            flash('Cliente atualizado!', 'success')
            return redirect(url_for('financial.clientes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')
    
    return render_template('financial/cliente_form.html', cliente=cliente)


@financial_bp.route('/clientes/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_cliente(id):
    """Desativar cliente"""
    from models.rh import Client
    
    cliente = Client.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    cliente.is_active = False
    db.session.commit()
    
    flash('Cliente removido.', 'warning')
    return redirect(url_for('financial.clientes'))
