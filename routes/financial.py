"""Rotas do modulo financeiro - apenas admin"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func
from models.financial import Quote, QuoteItem, Contract, Invoice, Payment
from models.company import Company
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
    """Gera cÃƒÂ³digo sequencial para documentos (inclui company_id para unicidade global)"""
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
    """Dashboard financeiro com dados REAIS"""
    from models.rh import AccountReceivable, AccountPayable, PayrollEntry, FreelancerPayment

    company_id = current_user.company_id
    hoje = date.today()
    mes_atual = hoje.replace(day=1)
    mes_fim = (mes_atual + timedelta(days=32)).replace(day=1)

    # ========== FATURAMENTO MÃƒÅ S ==========
    faturamento_mes = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'received',
        func.date(AccountReceivable.received_at) >= mes_atual,
        func.date(AccountReceivable.received_at) < mes_fim
    ).scalar() or 0)

    # ========== DESPESAS MÃƒÅ S ==========
    despesas_folha = float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
        PayrollEntry.company_id == company_id,
        PayrollEntry.reference_month == hoje.month,
        PayrollEntry.reference_year == hoje.year
    ).scalar() or 0)

    despesas_contas = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'paid',
        func.date(AccountPayable.paid_at) >= mes_atual,
        func.date(AccountPayable.paid_at) < mes_fim
    ).scalar() or 0)

    despesas_freelancers = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
        FreelancerPayment.company_id == company_id,
        FreelancerPayment.status == 'paid',
        func.date(FreelancerPayment.paid_at) >= mes_atual,
        func.date(FreelancerPayment.paid_at) < mes_fim
    ).scalar() or 0)

    despesas_mes = despesas_folha + despesas_contas + despesas_freelancers

    # ========== LUCRO E MARGEM ==========
    lucro_mes = faturamento_mes - despesas_mes
    margem = round((lucro_mes / faturamento_mes * 100), 1) if faturamento_mes > 0 else 0

    # ========== CONTAS A VENCER (7 DIAS) ==========
    sete_dias = hoje + timedelta(days=7)

    contas_vencer = AccountPayable.query.filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'pending',
        AccountPayable.due_date >= hoje,
        AccountPayable.due_date <= sete_dias
    ).order_by(AccountPayable.due_date).all()

    pending_accounts = []
    for conta in contas_vencer:
        dias_restantes = (conta.due_date - hoje).days

        if dias_restantes <= 2:
            badge = 'URGENTE'
            badge_class = 'urgent'
        elif dias_restantes <= 5:
            badge = 'ATENCAO'
            badge_class = 'warning'
        else:
            badge = 'OK'
            badge_class = 'ok'

        pending_accounts.append({
            'description': conta.description,
            'amount': float(conta.amount),
            'due_date': conta.due_date,
            'days_left': dias_restantes,
            'badge': badge,
            'badge_class': badge_class
        })

    # ========== FLUXO DE CAIXA (6 MESES) ==========
    fluxo_labels = []
    fluxo_receitas = []
    fluxo_despesas = []

    for i in range(5, -1, -1):
        mes = (mes_atual - timedelta(days=30*i)).replace(day=1)
        mes_prox = (mes + timedelta(days=32)).replace(day=1)
        fluxo_labels.append(mes.strftime('%b/%y'))

        rec = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
            AccountReceivable.company_id == company_id,
            AccountReceivable.status == 'received',
            func.date(AccountReceivable.received_at) >= mes,
            func.date(AccountReceivable.received_at) < mes_prox
        ).scalar() or 0)
        fluxo_receitas.append(rec)

        desp_f = float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
            PayrollEntry.company_id == company_id,
            PayrollEntry.reference_month == mes.month,
            PayrollEntry.reference_year == mes.year
        ).scalar() or 0)

        desp_c = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            func.date(AccountPayable.paid_at) >= mes,
            func.date(AccountPayable.paid_at) < mes_prox
        ).scalar() or 0)

        desp_fl = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
            FreelancerPayment.company_id == company_id,
            FreelancerPayment.status == 'paid',
            func.date(FreelancerPayment.paid_at) >= mes,
            func.date(FreelancerPayment.paid_at) < mes_prox
        ).scalar() or 0)

        fluxo_despesas.append(desp_f + desp_c + desp_fl)

    # ========== MÃƒâ€°TRICAS AUXILIARES ==========
    quotes_pending = Quote.query.filter_by(
        company_id=company_id,
        status='sent',
        is_active=True
    ).count()

    invoices_pending = Invoice.query.filter_by(
        company_id=company_id,
        status='pending',
        is_active=True
    ).count()

    invoices_overdue = Invoice.query.filter(
        Invoice.company_id == company_id,
        Invoice.status == 'pending',
        Invoice.due_date < hoje,
        Invoice.is_active == True
    ).count()

    contracts_active = Contract.query.filter_by(
        company_id=company_id,
        status='active',
        is_active=True
    ).count()

    recent_quotes = Quote.query.filter_by(
        company_id=company_id,
        is_active=True
    ).order_by(Quote.created_at.desc()).limit(5).all()

    recent_invoices = Invoice.query.filter_by(
        company_id=company_id,
        is_active=True
    ).order_by(Invoice.created_at.desc()).limit(5).all()

    # Cobrancas Asaas pendentes (PIX/Boleto)
    cobrancas_pendentes = Payment.query.join(Invoice).filter(
        Invoice.company_id == company_id,
        Payment.status == 'pending',
        Payment.provider == 'asaas'
    ).all()

    cobrancas_qtd = len(cobrancas_pendentes)
    cobrancas_total = sum(float(p.amount) for p in cobrancas_pendentes)

    return render_template('financial/index.html',
                          # KPIs principais
                          faturamento_mes=faturamento_mes,
                          despesas_mes=despesas_mes,
                          lucro_mes=lucro_mes,
                          margem=margem,
                          # Contas a vencer
                          pending_accounts=pending_accounts,
                          # Fluxo de caixa
                          fluxo_labels=fluxo_labels,
                          fluxo_receitas=fluxo_receitas,
                          fluxo_despesas=fluxo_despesas,
                          # Metricas auxiliares
                          quotes_pending=quotes_pending,
                          invoices_pending=invoices_pending,
                          invoices_overdue=invoices_overdue,
                          contracts_active=contracts_active,
                          recent_quotes=recent_quotes,
                          recent_invoices=recent_invoices,
                          # Cobrancas Asaas
                          cobrancas_qtd=cobrancas_qtd,
                          cobrancas_total=cobrancas_total,
                          # Helper para template
                          date=date)


@financial_bp.route('/quotes')
@login_required
@admin_required
def quotes():
    """Lista de orÃƒÂ§amentos"""
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
    """Criar novo orÃƒÂ§amento"""
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

        flash('OrÃƒÂ§amento criado! Adicione os itens.', 'success')
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
    """Visualizar orÃƒÂ§amento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    return render_template('financial/quote_view.html', quote=quote)


@financial_bp.route('/quotes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_quote(id):
    """Editar orÃƒÂ§amento"""
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
        flash('OrÃƒÂ§amento atualizado!', 'success')
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
    """Adicionar item ao orÃƒÂ§amento"""
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
    """Remover item do orÃƒÂ§amento"""
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
    """Marcar orÃƒÂ§amento como enviado"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    quote.status = 'sent'
    db.session.commit()

    flash('OrÃƒÂ§amento marcado como enviado!', 'success')
    return redirect(url_for('financial.view_quote', id=quote.id))


@financial_bp.route('/quotes/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_quote(id):
    """Aprovar orÃƒÂ§amento"""
    quote = Quote.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    quote.status = 'approved'
    quote.approved_at = datetime.utcnow()
    quote.approved_by = current_user.id
    db.session.commit()

    # === EVENTBUS: QUOTE_APPROVED ===
    try:
        from services.event_bus import EventBus, Events
        EventBus.emit(Events.QUOTE_APPROVED, {
            'quote_id': quote.id,
            'client_id': quote.client_id,
            'total_value': float(quote.total or 0),
            'company_id': current_user.company_id,
            'approved_by': current_user.id
        })
    except ImportError:
        pass

    flash('OrÃƒÂ§amento aprovado!', 'success')
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

    flash('Contrato excluido.', 'warning')
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
    """Recalcula totais do orÃƒÂ§amento"""
    subtotal = sum(item.total for item in quote.items)
    quote.subtotal = subtotal
    quote.discount_value = subtotal * (quote.discount_percent or 0) / 100
    quote.total = subtotal - quote.discount_value


@financial_bp.route('/invoices/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_invoice(id):
    """Editar fatura"""
    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if request.method == 'POST':
        invoice.client_name = request.form.get('client_name')
        invoice.client_document = request.form.get('client_document')
        invoice.client_email = request.form.get('client_email')
        invoice.description = request.form.get('description')
        invoice.subtotal = Decimal(request.form.get('subtotal', '0'))
        invoice.total = Decimal(request.form.get('total', '0'))

        due_date_str = request.form.get('due_date')
        if due_date_str:
            invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Fatura atualizada!', 'success')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    return render_template('financial/invoice_form.html', invoice=invoice, edit=True)


@financial_bp.route('/invoices/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_invoice(id):
    """Excluir fatura"""
    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if invoice.status == 'paid':
        flash('Nao e possivel excluir fatura paga.', 'danger')
        return redirect(url_for('financial.receitas'))

    # Soft delete
    invoice.is_active = False
    db.session.commit()

    flash(f'Fatura {invoice.code} excluida.', 'success')
    return redirect(url_for('financial.receitas'))


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

    return render_template('financial/receitas.html', faturas=faturas, status=status, today=date.today())


# ============================================
# DESPESAS - CORRIGIDO COM DADOS REAIS
# ============================================

@financial_bp.route('/despesas')
@login_required
@admin_required
def despesas():
    """Visao geral de despesas - DADOS REAIS"""
    from models.rh import AccountPayable, PayrollEntry, FreelancerPayment
    from models.maintenance import Maintenance

    company_id = current_user.company_id
    hoje = date.today()
    mes_atual = hoje.replace(day=1)
    mes_fim = (mes_atual + timedelta(days=32)).replace(day=1)

    # ========== FOLHA CLT (mÃƒÂªs atual) ==========
    folha_clt = float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
        PayrollEntry.company_id == company_id,
        PayrollEntry.reference_month == hoje.month,
        PayrollEntry.reference_year == hoje.year
    ).scalar() or 0)

    # ========== CONTAS PAGAS (mÃƒÂªs atual) ==========
    contas_fixas = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'paid',
        func.date(AccountPayable.paid_at) >= mes_atual,
        func.date(AccountPayable.paid_at) < mes_fim
    ).scalar() or 0)

    # ========== FREELANCERS (mÃƒÂªs atual) ==========
    freelancers_total = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
        FreelancerPayment.company_id == company_id,
        FreelancerPayment.status == 'paid',
        func.date(FreelancerPayment.paid_at) >= mes_atual,
        func.date(FreelancerPayment.paid_at) < mes_fim
    ).scalar() or 0)

    # ========== MANUTENÃƒâ€¡ÃƒÆ’O (mÃƒÂªs atual) ==========
    manutencao = float(db.session.query(func.sum(Maintenance.total_cost)).filter(
        Maintenance.company_id == company_id,
        Maintenance.status == 'completed',
        func.date(Maintenance.completed_at) >= mes_atual,
        func.date(Maintenance.completed_at) < mes_fim
    ).scalar() or 0)

    # ========== TOTAL MÃƒÅ S ==========
    total_mes = folha_clt + contas_fixas + freelancers_total + manutencao

    # ========== ÃƒÅ¡LTIMAS DESPESAS (10 mais recentes) ==========
    ultimas_despesas = []

    # Contas pagas recentes
    contas_recentes = AccountPayable.query.filter(
        AccountPayable.company_id == company_id,
        AccountPayable.status == 'paid'
    ).order_by(AccountPayable.paid_at.desc()).limit(5).all()

    for conta in contas_recentes:
        if conta.paid_at:
            ultimas_despesas.append({
                'tipo': 'conta',
                'categoria': conta.category or 'Conta',
                'descricao': conta.description or 'Pagamento',
                'valor': float(conta.paid_amount or conta.amount or 0),
                'data': conta.paid_at
            })

    # Freelancers pagos recentes
    freelancers_recentes = FreelancerPayment.query.filter(
        FreelancerPayment.company_id == company_id,
        FreelancerPayment.status == 'paid'
    ).order_by(FreelancerPayment.paid_at.desc()).limit(3).all()

    for fp in freelancers_recentes:
        if fp.paid_at:
            freelancer_name = fp.freelancer.name if fp.freelancer else 'Freelancer'
            ultimas_despesas.append({
                'tipo': 'freelancer',
                'categoria': 'Freelancer',
                'descricao': f'{freelancer_name} - {fp.description or "Pagamento"}',
                'valor': float(fp.amount or 0),
                'data': fp.paid_at
            })

    # ManutenÃƒÂ§ÃƒÂµes concluÃƒÂ­das recentes
    manutencoes_recentes = Maintenance.query.filter(
        Maintenance.company_id == company_id,
        Maintenance.status == 'completed',
        Maintenance.total_cost > 0
    ).order_by(Maintenance.completed_at.desc()).limit(3).all()

    for m in manutencoes_recentes:
        if m.completed_at:
            equip_name = m.equipment.name if m.equipment else 'Equipamento'
            ultimas_despesas.append({
                'tipo': 'manutencao',
                'categoria': 'Manutencao',
                'descricao': f'{m.maintenance_type or "Reparo"} - {equip_name}',
                'valor': float(m.total_cost or 0),
                'data': m.completed_at
            })

    # Ordenar por data (mais recente primeiro) e limitar a 10
    ultimas_despesas.sort(key=lambda x: x['data'], reverse=True)
    ultimas_despesas = ultimas_despesas[:10]

    return render_template('financial/despesas.html',
                          total_mes=total_mes,
                          folha_clt=folha_clt,
                          contas_fixas=contas_fixas,
                          freelancers_total=freelancers_total,
                          manutencao=manutencao,
                          ultimas_despesas=ultimas_despesas)


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
    """Contas a pagar - pastas mensais colapsaveis com meses vencidos dinamicos"""
    from models.rh import AccountPayable
    from sqlalchemy import func
    from dateutil.relativedelta import relativedelta
    from collections import OrderedDict

    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)

    # Filtros
    status_filter = request.args.get('status', 'pending')
    categoria_filter = request.args.get('categoria', '')

    # LISTA EXPANDIDA DE CATEGORIAS (24 categorias)
    categorias = [
        'folha_clt', 'freelancers', 'manutencao',
        'aluguel', 'energia', 'agua', 'telefone', 'internet',
        'contabilidade', 'juridico', 'softwares',
        'transporte', 'combustivel', 'pedagios', 'manutencao_veiculos',
        'impostos', 'seguros',
        'equipamentos', 'veiculos',
        'marketing',
        'materiais_consumo', 'ferramentas',
        'parcelamentos', 'outros'
    ]

    # Helper para classificar estado da pasta
    def classify_folder_state(folder_date, has_pending):
        """Retorna: 'overdue', 'on_track', ou 'archivable'"""
        if folder_date < mes_atual:
            return 'overdue' if has_pending else 'archivable'
        return 'on_track'

    # Base query com filtros
    query = AccountPayable.query.filter(AccountPayable.company_id == current_user.company_id)

    if status_filter == 'pending':
        query = query.filter(AccountPayable.status.in_(['pending', 'partial']))
    elif status_filter == 'paid':
        query = query.filter(AccountPayable.status == 'paid')
    elif status_filter == 'overdue':
        query = query.filter(
            AccountPayable.status.in_(['pending', 'partial']),
            AccountPayable.due_date < hoje
        )
    elif status_filter == 'all':
        pass  # sem filtro de status

    if categoria_filter:
        query = query.filter(AccountPayable.category == categoria_filter)

    contas_todas = query.order_by(AccountPayable.due_date).all()

    # Primeiro passo: identificar TODOS os meses presentes no dataset filtrado
    meses_no_dataset = set()
    for conta in contas_todas:
        if conta.due_date:
            meses_no_dataset.add(conta.due_date.strftime('%Y-%m'))

    # Gerar pastas: todos os meses no dataset + 12 meses rolling
    pastas = OrderedDict()

    # Adicionar meses do dataset que sao anteriores ao mes atual (ordenados)
    meses_passados = sorted([m for m in meses_no_dataset if m < mes_atual.strftime('%Y-%m')])
    for mes_key in meses_passados:
        ano, mes_num = int(mes_key[:4]), int(mes_key[5:7])
        mes_inicio = date(ano, mes_num, 1)
        pastas[mes_key] = {
            'label': mes_inicio.strftime('%b/%Y').capitalize(),
            'inicio': mes_inicio,
            'fim': mes_inicio + relativedelta(months=1, days=-1),
            'contas': [],
            'total': Decimal('0'),
            'qtd': 0,
            'state': 'on_track'  # sera recalculado depois
        }

    # Adicionar 12 meses rolling (atual + 11 futuros)
    for i in range(12):
        mes = mes_atual + relativedelta(months=i)
        mes_key = mes.strftime('%Y-%m')
        if mes_key not in pastas:
            pastas[mes_key] = {
                'label': mes.strftime('%b/%Y').capitalize(),
                'inicio': mes,
                'fim': mes + relativedelta(months=1, days=-1),
                'contas': [],
                'total': Decimal('0'),
                'qtd': 0,
                'state': 'on_track'
            }

    # Agrupar contas nas pastas
    for conta in contas_todas:
        if conta.due_date:
            mes_key = conta.due_date.strftime('%Y-%m')
            if mes_key in pastas:
                pastas[mes_key]['contas'].append(conta)
                pastas[mes_key]['total'] += conta.amount or Decimal('0')
                pastas[mes_key]['qtd'] += 1

    # Atualizar estado das pastas (verificar se tem pendencias vencidas)
    for mes_key, pasta in pastas.items():
        has_pending = any(c.status in ['pending', 'partial'] for c in pasta['contas'])
        pasta['state'] = classify_folder_state(pasta['inicio'], has_pending)

    # KPIs derivados do mesmo dataset filtrado
    # Total vencidas = soma de TODAS as contas vencidas (due_date < hoje E status pendente)
    total_vencidas = sum(
        float(c.amount or 0) 
        for c in contas_todas
        if c.due_date and c.due_date < hoje and c.status in ['pending', 'partial']
    )
    qtd_vencidas = sum(
        1 for c in contas_todas
        if c.due_date and c.due_date < hoje and c.status in ['pending', 'partial']
    )

    # KPI de 7 dias - calculado a partir do dataset ja filtrado
    total_7_dias = sum(
        float(c.amount or 0) for c in contas_todas 
        if c.due_date and hoje <= c.due_date <= hoje + timedelta(days=7)
    )

    # KPI mes atual - ja calculado nas pastas
    total_mes_atual = float(pastas[mes_atual.strftime('%Y-%m')]['total']) if mes_atual.strftime('%Y-%m') in pastas else 0

    # Contar repositorios (anos com contas pagas)
    anos_repositorio = db.session.query(
        func.strftime('%Y', AccountPayable.due_date)
    ).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'paid'
    ).distinct().all()
    anos_repositorio = [a[0] for a in anos_repositorio if a[0]]

    return render_template('financial/contas_pagar.html',
                          pastas=pastas,
                          total_vencidas=total_vencidas,
                          qtd_vencidas=qtd_vencidas,
                          total_7_dias=total_7_dias,
                          total_mes=total_mes_atual,
                          anos_repositorio=anos_repositorio,
                          mes_atual_key=mes_atual.strftime('%Y-%m'),
                          today=hoje,
                          categorias=categorias,
                          status_filter=status_filter,
                          categoria_filter=categoria_filter)


@financial_bp.route('/contas-pagar/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def nova_conta_pagar():
    """Criar nova conta a pagar"""
    from models.rh import AccountPayable, CostCenter

    if request.method == 'POST':
        try:
            total_installments = int(request.form.get('total_installments', '1') or '1')
            valor_total = Decimal(request.form.get('amount', '0').replace(',', '.'))
            valor_parcela = valor_total / total_installments if total_installments > 1 else valor_total
            due_date_base = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
            cost_center_id = request.form.get('cost_center_id') or None
            if cost_center_id:
                cost_center_id = int(cost_center_id)

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
                    cost_center_id=cost_center_id,
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

    cost_centers = CostCenter.query.filter_by(company_id=current_user.company_id, is_active=True).order_by(CostCenter.name).all()
    return render_template('financial/conta_pagar_form.html', conta=None, cost_centers=cost_centers)


@financial_bp.route('/contas-pagar/repositorio')
@login_required
@admin_required
def repositorio_contas():
    """Repositorio de contas pagas por exercicio (ano)"""
    from models.rh import AccountPayable
    from sqlalchemy import func
    from collections import OrderedDict

    ano_filtro = request.args.get('ano', str(date.today().year))

    # Buscar contas pagas do ano
    contas_pagas = AccountPayable.query.filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'paid',
        func.strftime('%Y', AccountPayable.due_date) == ano_filtro
    ).order_by(AccountPayable.due_date).all()

    # Agrupar por mes
    meses_nomes = {
        '01': 'Janeiro', '02': 'Fevereiro', '03': 'Marco', '04': 'Abril',
        '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
        '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
    }

    pastas = OrderedDict()
    for m in range(1, 13):
        mes_key = f"{m:02d}"
        pastas[mes_key] = {
            'label': f"{meses_nomes[mes_key]}/{ano_filtro}",
            'contas': [],
            'total': Decimal('0'),
            'qtd': 0
        }

    for conta in contas_pagas:
        if conta.due_date:
            mes_key = conta.due_date.strftime('%m')
            if mes_key in pastas:
                pastas[mes_key]['contas'].append(conta)
                pastas[mes_key]['total'] += conta.amount or Decimal('0')
                pastas[mes_key]['qtd'] += 1

    # Total geral do ano
    total_ano = sum(float(p['total']) for p in pastas.values())
    qtd_total = sum(p['qtd'] for p in pastas.values())

    # Anos disponiveis
    anos_disponiveis = db.session.query(
        func.strftime('%Y', AccountPayable.due_date)
    ).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'paid'
    ).distinct().order_by(func.strftime('%Y', AccountPayable.due_date).desc()).all()
    anos_disponiveis = [a[0] for a in anos_disponiveis if a[0]]

    return render_template('financial/repositorio_contas.html',
                          pastas=pastas,
                          ano_filtro=ano_filtro,
                          anos_disponiveis=anos_disponiveis,
                          total_ano=total_ano,
                          qtd_total=qtd_total)


@financial_bp.route('/contas-pagar/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_conta_pagar(id):
    """Editar conta a pagar"""
    from models.rh import AccountPayable, CostCenter

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
            cost_center_id = request.form.get('cost_center_id') or None
            conta.cost_center_id = int(cost_center_id) if cost_center_id else None
            conta.notes = request.form.get('notes', '').strip()

            db.session.commit()

            flash('Conta atualizada!', 'success')
            return redirect(url_for('financial.contas_pagar'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar: {str(e)}', 'danger')

    cost_centers = CostCenter.query.filter_by(company_id=current_user.company_id, is_active=True).order_by(CostCenter.name).all()
    return render_template('financial/conta_pagar_form.html', conta=conta, cost_centers=cost_centers)


@financial_bp.route('/contas-pagar/<int:id>/pagar', methods=['POST'])
@login_required
@admin_required
def pagar_conta(id):
    """Marcar conta como paga e sincronizar com RH se necessÃ¡rio"""
    from models.rh import AccountPayable, PayrollEntry

    conta = AccountPayable.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    # Verificar se jÃ¡ estÃ¡ paga
    if conta.status == 'paid':
        flash('Esta conta jÃ¡ foi paga!', 'warning')
        return redirect(url_for('financial.contas_pagar'))

    valor_pago = request.form.get('paid_amount', '')
    if valor_pago:
        conta.paid_amount = Decimal(valor_pago.replace(',', '.'))
    else:
        conta.paid_amount = conta.amount

    conta.status = 'paid'
    conta.paid_at = datetime.utcnow()

    # ========== SINCRONIZAÃ‡ÃƒO COM RH ==========
    # Se for folha_pagamento, atualizar PayrollEntry
    if conta.payroll_entry_id and conta.category == 'folha_pagamento':
        entry = PayrollEntry.query.get(conta.payroll_entry_id)
        if entry and entry.status != 'paid':
            entry.status = 'paid'
            entry.payment_date = date.today()
            entry.financial_integrated = True

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


@financial_bp.route('/emitir-nfse')
@login_required
@admin_required
def emitir_nfse():
    """Redireciona para receitas - NFSe agora e emitida pela fatura"""
    flash('Para emitir NFSe, acesse uma fatura PAGA e clique em "Emitir NFSe"', 'info')
    return redirect(url_for('financial.receitas', status='paid'))


# ============================================
# DRE - CORRIGIDO COM MANUTENCAO
# ============================================

@financial_bp.route('/dre')
@login_required
@admin_required
def dre():
    """Demonstrativo de Resultado do Exercicio com dados reais"""
    from models.rh import AccountPayable, AccountReceivable, FreelancerPayment, PayrollEntry
    from models.maintenance import Maintenance

    current_month = date.today().month
    current_year = date.today().year
    current_month_str = date.today().strftime('%Y-%m')
    mes_atual_inicio = date.today().replace(day=1)
    mes_atual_fim = (mes_atual_inicio + timedelta(days=32)).replace(day=1)

    # ========== RECEITAS ==========
    # Contas a Receber (modelo antigo)
    receitas_contas = db.session.query(func.sum(AccountReceivable.received_amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'received',
        func.strftime('%Y-%m', AccountReceivable.received_at) == current_month_str
    ).scalar() or 0

    # Faturas pagas (Invoice) - NOVO
    receitas_faturas = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.status == 'paid',
        Invoice.is_active == True,
        func.date(Invoice.paid_at) >= mes_atual_inicio,
        func.date(Invoice.paid_at) < mes_atual_fim
    ).scalar() or 0

    # Total receitas = contas recebidas + faturas pagas
    receitas_locacao = float(receitas_contas) + float(receitas_faturas)

    # Pendentes (contas + faturas)
    receitas_pendentes_contas = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == current_user.company_id,
        AccountReceivable.status == 'pending',
        func.strftime('%Y-%m', AccountReceivable.due_date) == current_month_str
    ).scalar() or 0

    receitas_pendentes_faturas = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.status == 'pending',
        Invoice.is_active == True,
        func.date(Invoice.due_date) >= mes_atual_inicio,
        func.date(Invoice.due_date) < mes_atual_fim
    ).scalar() or 0

    receitas_pendentes = float(receitas_pendentes_contas) + float(receitas_pendentes_faturas)

    # ========== DESPESAS ==========
    despesas_folha = db.session.query(func.sum(PayrollEntry.net_salary)).filter(
        PayrollEntry.company_id == current_user.company_id,
        PayrollEntry.reference_month == current_month,
        PayrollEntry.reference_year == current_year
    ).scalar() or 0

    # ========== DESPESAS POR CATEGORIA (AccountPayable) ==========
    # Funcao auxiliar para somar por categoria
    def soma_categoria(categoria):
        return db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == current_user.company_id,
            AccountPayable.status == 'paid',
            AccountPayable.category == categoria,
            func.strftime('%Y-%m', AccountPayable.paid_at) == current_month_str
        ).scalar() or 0

    # Categorias RH separadas
    despesas_adiantamento = float(soma_categoria('adiantamento'))
    despesas_13 = float(soma_categoria('13o_salario'))
    despesas_ferias = float(soma_categoria('ferias'))
    despesas_inss = float(soma_categoria('inss'))
    despesas_fgts = float(soma_categoria('fgts'))
    despesas_irrf = float(soma_categoria('irrf'))

    # Contas pagas (excluindo categorias RH especificas para nao duplicar)
    categorias_rh = ['adiantamento', '13o_salario', 'ferias', 'inss', 'fgts', 'irrf', 'folha_pagamento']
    despesas_contas = db.session.query(func.sum(AccountPayable.paid_amount)).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status == 'paid',
        ~AccountPayable.category.in_(categorias_rh),
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

    # ========== MANUTENCAO ==========
    despesas_manutencao = db.session.query(func.sum(Maintenance.total_cost)).filter(
        Maintenance.company_id == current_user.company_id,
        Maintenance.status == 'completed',
        func.date(Maintenance.completed_at) >= mes_atual_inicio,
        func.date(Maintenance.completed_at) < mes_atual_fim
    ).scalar() or 0

    # ========== TOTAIS ==========
    total_receitas = float(receitas_locacao)
    total_despesas = (
        float(despesas_folha) + 
        float(despesas_contas) + 
        float(despesas_freelancers) + 
        float(despesas_manutencao) +
        despesas_adiantamento +
        despesas_13 +
        despesas_ferias +
        despesas_inss +
        despesas_fgts +
        despesas_irrf
    )
    lucro = total_receitas - total_despesas

    return render_template('financial/dre.html',
                          receitas_locacao=receitas_locacao,
                          receitas_pendentes=receitas_pendentes,
                          despesas_folha=despesas_folha,
                          despesas_contas=despesas_contas,
                          despesas_pendentes=despesas_pendentes,
                          despesas_freelancers=despesas_freelancers,
                          despesas_manutencao=despesas_manutencao,
                          # Novas categorias RH
                          despesas_adiantamento=despesas_adiantamento,
                          despesas_13=despesas_13,
                          despesas_ferias=despesas_ferias,
                          despesas_inss=despesas_inss,
                          despesas_fgts=despesas_fgts,
                          despesas_irrf=despesas_irrf,
                          # Totais
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


@financial_bp.route('/contas-receber/from-quote/<int:quote_id>', methods=['POST'])
@login_required
@admin_required
def contas_receber_from_quote(quote_id):
    """Gera contas a receber a partir de um orÃƒÂ§amento aprovado (wizard automation)"""
    from models.rh import AccountReceivable
    from models.separation_list import SeparationList
    from dateutil.relativedelta import relativedelta

    # Try SeparationList first (main quote system), fallback to Quote
    quote = SeparationList.query.filter_by(
        id=quote_id,
        company_id=current_user.company_id
    ).first()

    if not quote:
        quote = Quote.query.filter_by(
            id=quote_id,
            company_id=current_user.company_id
        ).first_or_404()

    data = request.get_json() or {}
    num_parcelas = int(data.get('installments', 1))
    primeiro_vencimento_str = data.get('first_due_date', '')

    if primeiro_vencimento_str:
        primeiro_vencimento = datetime.strptime(primeiro_vencimento_str, '%Y-%m-%d').date()
    else:
        primeiro_vencimento = date.today() + timedelta(days=30)

    # SeparationList uses calculated_total or total_value; Quote uses total_value
    valor_total = Decimal('0')
    if hasattr(quote, 'calculated_total') and quote.calculated_total:
        valor_total = Decimal(str(quote.calculated_total))
    elif quote.total_value:
        valor_total = Decimal(str(quote.total_value))

    valor_parcela = valor_total / num_parcelas if num_parcelas > 0 else valor_total

    # SeparationList uses 'name', Quote uses 'code'
    quote_identifier = getattr(quote, 'code', None) or getattr(quote, 'name', f'#{quote.id}')

    contas_criadas = []
    for i in range(num_parcelas):
        due_date = primeiro_vencimento + relativedelta(months=i)

        conta = AccountReceivable(
            company_id=current_user.company_id,
            description=f"OrÃƒÂ§amento {quote_identifier} - Parcela {i+1}/{num_parcelas}" if num_parcelas > 1 else f"OrÃƒÂ§amento {quote_identifier}",
            category='locacao',
            client_name=quote.client_name or '',
            amount=valor_parcela,
            due_date=due_date,
            installment_number=i + 1 if num_parcelas > 1 else None,
            total_installments=num_parcelas if num_parcelas > 1 else None,
            notes=f"Gerado automaticamente do orÃƒÂ§amento {quote_identifier}",
            status='pending',
            created_by=current_user.id
        )
        db.session.add(conta)
        contas_criadas.append(conta)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{num_parcelas} conta(s) a receber gerada(s)!',
        'count': len(contas_criadas)
    })


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


@financial_bp.route('/api/fluxo-caixa')
@login_required
@admin_required
def api_fluxo_caixa():
    """API para fluxo de caixa com periodo customizado"""
    from models.rh import AccountReceivable, AccountPayable, PayrollEntry, FreelancerPayment

    company_id = current_user.company_id
    periodo = request.args.get('periodo', 'mensal')

    labels = []
    receitas = []
    despesas = []
    hoje = date.today()

    if periodo == 'diario':
        # Ultimos 30 dias
        for i in range(29, -1, -1):
            dia = hoje - timedelta(days=i)
            dia_prox = dia + timedelta(days=1)
            labels.append(dia.strftime('%d/%m'))

            rec = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'received',
                func.date(AccountReceivable.received_at) >= dia,
                func.date(AccountReceivable.received_at) < dia_prox
            ).scalar() or 0)
            receitas.append(rec)

            desp_c = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status == 'paid',
                func.date(AccountPayable.paid_at) >= dia,
                func.date(AccountPayable.paid_at) < dia_prox
            ).scalar() or 0)

            desp_fl = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
                FreelancerPayment.company_id == company_id,
                FreelancerPayment.status == 'paid',
                func.date(FreelancerPayment.paid_at) >= dia,
                func.date(FreelancerPayment.paid_at) < dia_prox
            ).scalar() or 0)

            despesas.append(desp_c + desp_fl)

    elif periodo == 'semanal':
        # Ultimas 12 semanas
        for i in range(11, -1, -1):
            semana_inicio = hoje - timedelta(days=hoje.weekday()) - timedelta(weeks=i)
            semana_fim = semana_inicio + timedelta(days=7)
            labels.append(f"{semana_inicio.strftime('%d/%m')} - {semana_fim.strftime('%d/%m')}")

            rec = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'received',
                func.date(AccountReceivable.received_at) >= semana_inicio,
                func.date(AccountReceivable.received_at) < semana_fim
            ).scalar() or 0)
            receitas.append(rec)

            desp_c = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status == 'paid',
                func.date(AccountPayable.paid_at) >= semana_inicio,
                func.date(AccountPayable.paid_at) < semana_fim
            ).scalar() or 0)

            desp_fl = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
                FreelancerPayment.company_id == company_id,
                FreelancerPayment.status == 'paid',
                func.date(FreelancerPayment.paid_at) >= semana_inicio,
                func.date(FreelancerPayment.paid_at) < semana_fim
            ).scalar() or 0)

            despesas.append(desp_c + desp_fl)

    elif periodo == 'mensal':
        # Ultimos 12 meses
        mes_atual = hoje.replace(day=1)
        for i in range(11, -1, -1):
            mes = (mes_atual - timedelta(days=30*i)).replace(day=1)
            mes_prox = (mes + timedelta(days=32)).replace(day=1)
            labels.append(mes.strftime('%b/%y'))

            rec = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'received',
                func.date(AccountReceivable.received_at) >= mes,
                func.date(AccountReceivable.received_at) < mes_prox
            ).scalar() or 0)
            receitas.append(rec)

            desp_f = float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
                PayrollEntry.company_id == company_id,
                PayrollEntry.reference_month == mes.month,
                PayrollEntry.reference_year == mes.year
            ).scalar() or 0)

            desp_c = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status == 'paid',
                func.date(AccountPayable.paid_at) >= mes,
                func.date(AccountPayable.paid_at) < mes_prox
            ).scalar() or 0)

            desp_fl = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
                FreelancerPayment.company_id == company_id,
                FreelancerPayment.status == 'paid',
                func.date(FreelancerPayment.paid_at) >= mes,
                func.date(FreelancerPayment.paid_at) < mes_prox
            ).scalar() or 0)

            despesas.append(desp_f + desp_c + desp_fl)

    elif periodo == 'anual':
        # Ultimos 5 anos
        ano_atual = hoje.year
        for i in range(4, -1, -1):
            ano = ano_atual - i
            ano_inicio = date(ano, 1, 1)
            ano_fim = date(ano + 1, 1, 1)
            labels.append(str(ano))

            rec = float(db.session.query(func.sum(AccountReceivable.received_amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'received',
                func.date(AccountReceivable.received_at) >= ano_inicio,
                func.date(AccountReceivable.received_at) < ano_fim
            ).scalar() or 0)
            receitas.append(rec)

            desp_f = 0
            for mes_num in range(1, 13):
                desp_f += float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
                    PayrollEntry.company_id == company_id,
                    PayrollEntry.reference_month == mes_num,
                    PayrollEntry.reference_year == ano
                ).scalar() or 0)

            desp_c = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status == 'paid',
                func.date(AccountPayable.paid_at) >= ano_inicio,
                func.date(AccountPayable.paid_at) < ano_fim
            ).scalar() or 0)

            desp_fl = float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
                FreelancerPayment.company_id == company_id,
                FreelancerPayment.status == 'paid',
                func.date(FreelancerPayment.paid_at) >= ano_inicio,
                func.date(FreelancerPayment.paid_at) < ano_fim
            ).scalar() or 0)

            despesas.append(desp_f + desp_c + desp_fl)

    return jsonify({
        'periodo': periodo,
        'labels': labels,
        'receitas': receitas,
        'despesas': despesas
    })

# ============================================
# INTEGRACAO ASAAS - COBRANCAS PIX E BOLETO
# ============================================

@financial_bp.route('/invoices/<int:id>/gerar-pix', methods=['POST'])
@login_required
@admin_required
def gerar_pix_asaas(id):
    """Gera cobranca PIX via Asaas para uma fatura"""
    from models.company import Company
    from services.payment_adapter import get_payment_provider

    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if invoice.status == 'paid':
        flash('Esta fatura ja esta paga.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    company = Company.query.get(current_user.company_id)

    if not company.asaas_api_key:
        flash('Configure a integracao Asaas nas configuracoes da empresa.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    valor = float(invoice.amount_pending or invoice.total)

    result = provider.create_pix(
        invoice_id=str(invoice.id),
        amount=valor,
        description=f"Fatura {invoice.code} - {invoice.description or 'Servicos'}",
        customer_name=invoice.client_name,
        customer_document=invoice.client_document,
        customer_email=invoice.client_email
    )

    if not result.get('success'):
        flash(f"Erro ao gerar PIX: {result.get('error', 'Erro desconhecido')}", 'danger')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    payment = Payment(
        invoice_id=invoice.id,
        amount=Decimal(str(valor)),
        method='pix',
        status='pending',
        transaction_id=result.get('transaction_id') or result.get('asaas_id'),
        provider=result.get('provider', 'asaas'),
        provider_data=result.get('raw_response'),
        notes=f"PIX gerado via {result.get('provider', 'asaas')}",
        company_id=current_user.company_id
    )
    db.session.add(payment)
    db.session.commit()

    return render_template('financial/cobranca_gerada.html',
        invoice=invoice,
        payment=payment,
        tipo='pix',
        pix_code=result.get('pix_code'),
        pix_qr_base64=result.get('pix_qr_url'),
        invoice_url=result.get('invoice_url'),
        valor=valor
    )


@financial_bp.route('/invoices/<int:id>/gerar-boleto', methods=['POST'])
@login_required
@admin_required
def gerar_boleto(id):
    """Gera boleto via Asaas para uma fatura"""
    from models.company import Company
    from services.payment_adapter import get_payment_provider

    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if invoice.status == 'paid':
        flash('Esta fatura ja esta paga.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    company = Company.query.get(current_user.company_id)

    if not company.asaas_api_key:
        flash('Configure a integracao Asaas nas configuracoes da empresa.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    valor = float(invoice.amount_pending or invoice.total)

    result = provider.create_boleto(
        invoice_id=str(invoice.id),
        amount=valor,
        due_date=invoice.due_date or date.today(),
        description=f"Fatura {invoice.code} - {invoice.description or 'Servicos'}",
        customer_name=invoice.client_name,
        customer_document=invoice.client_document,
        customer_email=invoice.client_email
    )

    if not result.get('success'):
        flash(f"Erro ao gerar boleto: {result.get('error', 'Erro desconhecido')}", 'danger')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    payment = Payment(
        invoice_id=invoice.id,
        amount=Decimal(str(valor)),
        method='boleto',
        status='pending',
        transaction_id=result.get('transaction_id') or result.get('asaas_id'),
        provider=result.get('provider', 'asaas'),
        provider_data=result.get('raw_response'),
        notes=f"Boleto gerado via {result.get('provider', 'asaas')}",
        company_id=current_user.company_id
    )
    db.session.add(payment)
    db.session.commit()

    return render_template('financial/cobranca_gerada.html',
        invoice=invoice,
        payment=payment,
        tipo='boleto',
        boleto_url=result.get('boleto_url'),
        boleto_line=result.get('boleto_line'),
        invoice_url=result.get('invoice_url'),
        valor=valor,
        vencimento=result.get('due_date') or invoice.due_date
    )


@financial_bp.route('/invoices/<int:id>/verificar-pagamento/<int:payment_id>')
@login_required
@admin_required
def verificar_pagamento(id, payment_id):
    """Verifica status de pagamento no Asaas"""
    from models.company import Company
    from services.payment_adapter import get_payment_provider

    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    payment = Payment.query.filter_by(
        id=payment_id,
        invoice_id=invoice.id
    ).first_or_404()

    if not payment.transaction_id:
        flash('Pagamento sem ID de transacao.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    company = Company.query.get(current_user.company_id)

    if not company.asaas_api_key:
        flash('Configure a integracao Asaas nas configuracoes da empresa.', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    result = provider.check_payment_status(payment.transaction_id)

    if result.get('success') and result.get('status') == 'confirmed':
        payment.status = 'confirmed'
        payment.paid_at = datetime.utcnow()
        payment.confirmed_by = current_user.id

        total_pago = sum(p.amount for p in invoice.payments if p.status == 'confirmed')
        total_pago += payment.amount

        if total_pago >= invoice.total:
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
        else:
            invoice.status = 'partial'

        db.session.commit()
        flash('Pagamento confirmado!', 'success')
    else:
        flash(f"Status: {result.get('asaas_status', result.get('status', 'pendente'))}", 'info')

    return redirect(url_for('financial.view_invoice', id=invoice.id))


@financial_bp.route('/webhook/asaas', methods=['POST'])
def webhook_asaas():
    """Webhook para receber notificacoes do Asaas (Pagamentos e NFSe)"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data'}), 400

        event = data.get('event')

        # ============================================
        # EVENTOS DE NFSE
        # ============================================
        if event and event.startswith('INVOICE_'):
            invoice_data = data.get('invoice', {})
            nfse_id = invoice_data.get('id')

            if not nfse_id:
                return jsonify({'error': 'No invoice id'}), 400

            # Busca fatura pelo nfse_id
            invoice = Invoice.query.filter_by(nfse_id=nfse_id).first()

            if not invoice:
                # Tenta buscar pelo payment vinculado
                payment_id = invoice_data.get('payment')
                if payment_id:
                    payment = Payment.query.filter_by(external_id=payment_id).first()
                    if payment:
                        invoice = Invoice.query.get(payment.invoice_id)

            if not invoice:
                return jsonify({'error': 'Invoice not found for NFSe'}), 404

            if event == 'INVOICE_AUTHORIZED':
                # NFSe emitida com sucesso
                invoice.nfse_status = 'AUTHORIZED'
                invoice.nfse_number = invoice_data.get('number') or invoice.nfse_number
                invoice.nfse_url = invoice_data.get('pdfUrl') or invoice.nfse_url
                invoice.nfse_xml_url = invoice_data.get('xmlUrl')
                db.session.commit()
                return jsonify({'success': True, 'event': event, 'status': 'authorized'}), 200

            elif event == 'INVOICE_ERROR':
                # Erro na emissao
                invoice.nfse_status = 'ERROR'
                error_msg = invoice_data.get('errorMessage', 'Erro desconhecido')
                # Salva erro nas observacoes ou campo especifico
                db.session.commit()
                return jsonify({'success': True, 'event': event, 'error': error_msg}), 200

            elif event == 'INVOICE_CANCELED':
                # NFSe cancelada
                invoice.nfse_status = 'CANCELED'
                db.session.commit()
                return jsonify({'success': True, 'event': event, 'status': 'canceled'}), 200

            elif event == 'INVOICE_CREATED':
                # NFSe agendada/criada
                invoice.nfse_status = 'SCHEDULED'
                invoice.nfse_id = nfse_id
                db.session.commit()
                return jsonify({'success': True, 'event': event, 'status': 'scheduled'}), 200

            elif event == 'INVOICE_SYNCHRONIZED':
                # NFSe enviada para prefeitura
                invoice.nfse_status = 'PROCESSING'
                db.session.commit()
                return jsonify({'success': True, 'event': event, 'status': 'processing'}), 200

            elif event == 'INVOICE_UPDATED':
                # Atualizacao na NFSe
                invoice.nfse_number = invoice_data.get('number') or invoice.nfse_number
                invoice.nfse_url = invoice_data.get('pdfUrl') or invoice.nfse_url
                invoice.nfse_status = invoice_data.get('status') or invoice.nfse_status
                db.session.commit()
                return jsonify({'success': True, 'event': event}), 200

            elif event in ['INVOICE_CANCELLATION_DENIED', 'INVOICE_PROCESSING_CANCELLATION']:
                # Eventos de cancelamento
                invoice.nfse_status = invoice_data.get('status', invoice.nfse_status)
                db.session.commit()
                return jsonify({'success': True, 'event': event}), 200

            return jsonify({'success': True, 'event': event, 'message': 'Event processed'}), 200

        # ============================================
        # EVENTOS DE PAGAMENTO (codigo existente)
        # ============================================
        payment_data = data.get('payment', {})

        external_ref = payment_data.get('externalReference')
        if not external_ref:
            return jsonify({'error': 'No external reference'}), 400

        try:
            invoice_id = int(external_ref)
        except:
            return jsonify({'error': 'Invalid reference'}), 400

        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        asaas_id = payment_data.get('id')

        payment = Payment.query.filter_by(
            invoice_id=invoice.id,
            transaction_id=asaas_id
        ).first()

        if event in ['PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED']:
            if payment:
                payment.status = 'confirmed'
                payment.paid_at = datetime.utcnow()
            else:
                payment = Payment(
                    invoice_id=invoice.id,
                    amount=Decimal(str(payment_data.get('value', 0))),
                    method=payment_data.get('billingType', 'pix').lower(),
                    status='confirmed',
                    transaction_id=asaas_id,
                    provider='asaas',
                    paid_at=datetime.utcnow(),
                    notes=f"Confirmado via webhook - {event}",
                    company_id=invoice.company_id
                )
                db.session.add(payment)

            db.session.flush()
            total_pago = sum(p.amount for p in invoice.payments if p.status == 'confirmed')

            if total_pago >= invoice.total:
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
            else:
                invoice.status = 'partial'

        elif event == 'PAYMENT_REFUNDED':
            if payment:
                payment.status = 'refunded'

        db.session.commit()

        # === EVENTBUS: PAYMENT_RECEIVED (webhook) ===
        if event in ['PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED']:
            try:
                from services.event_bus import EventBus, Events
                EventBus.emit(Events.PAYMENT_RECEIVED, {
                    'payment_id': payment.id if payment else None,
                    'invoice_id': invoice.id,
                    'invoice_code': invoice.code,
                    'amount': float(payment_data.get('value', 0)),
                    'method': payment_data.get('billingType', 'pix').lower(),
                    'asaas_id': asaas_id,
                    'event': event,
                    'company_id': invoice.company_id
                })
            except ImportError:
                pass
        return jsonify({'success': True, 'event': event}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@financial_bp.route('/cobrancas-pendentes')
@login_required
@admin_required
def cobrancas_pendentes():
    """Lista cobrancas PIX/Boleto pendentes"""
    payments = Payment.query.join(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Payment.status == 'pending',
        Payment.provider != 'manual'
    ).order_by(Payment.created_at.desc()).all()

    return render_template('financial/cobrancas_pendentes.html', payments=payments)


# ============================================
# NFSe - NOTA FISCAL DE SERVICO ELETRONICA
# ============================================

@financial_bp.route('/invoices/<int:id>/emitir-nfse', methods=['GET', 'POST'])
@login_required
@admin_required
def emitir_nfse_fatura(id):
    """Emitir NFSe para uma fatura paga"""
    from services.payment_adapter import get_payment_provider

    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    company = Company.query.get(current_user.company_id)

    # Verifica se Asaas esta configurado
    if not company.asaas_api_key:
        flash('Configure a integracao Asaas primeiro', 'warning')
        return redirect(url_for('company.settings'))

    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    if request.method == 'POST':
        # Busca o payment_id do Asaas (se existir)
        payment = Payment.query.filter_by(
            invoice_id=invoice.id,
            provider='asaas',
            status='confirmed'
        ).first()

        service_description = request.form.get('service_description', f'Servicos conforme fatura {invoice.code}')
        service_code = request.form.get('service_code', '')
        service_id = request.form.get('service_id', '')
        service_name = request.form.get('service_name', '')
        observations = request.form.get('observations', '')

        # Impostos
        taxes = {
            'iss': float(request.form.get('iss', 0) or 0),
            'cofins': float(request.form.get('cofins', 0) or 0),
            'csll': float(request.form.get('csll', 0) or 0),
            'inss': float(request.form.get('inss', 0) or 0),
            'ir': float(request.form.get('ir', 0) or 0),
            'pis': float(request.form.get('pis', 0) or 0),
            'retain_iss': request.form.get('retain_iss') == 'on'
        }

        # Emite NFSe
        result = provider.emit_nfse(
            payment_id=payment.external_id if payment else None,
            service_description=service_description,
            service_code=service_code or None,
            service_id=service_id or None,
            service_name=service_name or None,
            value=float(invoice.total),
            effective_date=date.today().isoformat(),
            taxes=taxes,
            observations=observations
        )

        if result.get('success'):
            # Salva dados da NFSe na fatura
            invoice.nfse_id = result.get('nfse_id')
            invoice.nfse_number = result.get('nfse_number')
            invoice.nfse_status = result.get('nfse_status', 'SCHEDULED')
            invoice.nfse_url = result.get('nfse_url')
            db.session.commit()

            flash('NFSe agendada com sucesso! Aguarde a emissao.', 'success')
            return redirect(url_for('financial.view_invoice', id=invoice.id))
        else:
            flash(f'Erro ao emitir NFSe: {result.get("error")}', 'danger')

    # GET - Busca servicos municipais
    services_result = provider.get_municipal_services()
    services = services_result.get('services', [])

    return render_template('financial/emitir_nfse.html', 
                          invoice=invoice, 
                          services=services)


@financial_bp.route('/invoices/<int:id>/nfse-status')
@login_required
@admin_required
def verificar_nfse(id):
    """Verifica status da NFSe"""
    from services.payment_adapter import get_payment_provider

    invoice = Invoice.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()

    if not invoice.nfse_id:
        flash('Esta fatura nao possui NFSe', 'warning')
        return redirect(url_for('financial.view_invoice', id=invoice.id))

    company = Company.query.get(current_user.company_id)
    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    result = provider.get_nfse_status(invoice.nfse_id)

    if result.get('success'):
        invoice.nfse_status = result.get('status_raw', invoice.nfse_status)
        invoice.nfse_number = result.get('nfse_number') or invoice.nfse_number
        invoice.nfse_url = result.get('nfse_url') or invoice.nfse_url
        db.session.commit()

        status_msg = result.get('status', 'desconhecido')
        if result.get('error_message'):
            flash(f'Status NFSe: {status_msg} - {result.get("error_message")}', 'warning')
        else:
            flash(f'Status NFSe: {status_msg}', 'info')
    else:
        flash(f'Erro ao verificar NFSe: {result.get("error")}', 'danger')

    return redirect(url_for('financial.view_invoice', id=invoice.id))


@financial_bp.route('/nfse/servicos-municipais')
@login_required
@admin_required
def listar_servicos_municipais():
    """Lista servicos municipais disponiveis (AJAX)"""
    from services.payment_adapter import get_payment_provider

    company = Company.query.get(current_user.company_id)

    if not company.asaas_api_key:
        return jsonify({'success': False, 'error': 'Asaas nao configurado'})

    provider = get_payment_provider(
        "asaas",
        api_key=company.asaas_api_key,
        sandbox=company.asaas_sandbox
    )

    description = request.args.get('description', '')
    result = provider.get_municipal_services(description)

    return jsonify(result)


# ============================================
# CENTRO DE CUSTOS
# ============================================

@financial_bp.route('/centros-custo')
@login_required
@admin_required
def centros_custo():
    """Lista de centros de custo com analise de gastos"""
    from models.rh import CostCenter, AccountPayable
    from sqlalchemy import func, case
    from decimal import Decimal

    centros = CostCenter.query.filter_by(
        company_id=current_user.company_id
    ).order_by(CostCenter.code).all()

    # Calcular totais por centro de custo usando status correto
    # Inclui pagamentos parciais corretamente
    gastos_por_centro = db.session.query(
        AccountPayable.cost_center_id,
        func.sum(case(
            (AccountPayable.status.in_(['paid', 'partial']), func.coalesce(AccountPayable.paid_amount, 0)),
            else_=0
        )).label('total_pago'),
        func.sum(case(
            (AccountPayable.status == 'paid', 0),
            (AccountPayable.status == 'partial', func.coalesce(AccountPayable.amount, 0) - func.coalesce(AccountPayable.paid_amount, 0)),
            else_=func.coalesce(AccountPayable.amount, 0)
        )).label('total_pendente'),
        func.count(AccountPayable.id).label('qtd_contas')
    ).filter(
        AccountPayable.company_id == current_user.company_id,
        AccountPayable.status != 'cancelled'
    ).group_by(AccountPayable.cost_center_id).all()

    # Mapear para dict
    gastos_map = {}
    total_geral_pago = Decimal('0')
    total_geral_pendente = Decimal('0')
    sem_centro_pago = Decimal('0')
    sem_centro_pendente = Decimal('0')

    for g in gastos_por_centro:
        pago = Decimal(str(g.total_pago or 0))
        pendente = Decimal(str(g.total_pendente or 0))

        if g.cost_center_id:
            gastos_map[g.cost_center_id] = {
                'pago': pago,
                'pendente': pendente,
                'qtd': g.qtd_contas
            }
            total_geral_pago += pago
            total_geral_pendente += pendente
        else:
            sem_centro_pago = pago
            sem_centro_pendente = pendente

    total_geral_pago += sem_centro_pago
    total_geral_pendente += sem_centro_pendente
    total_geral = total_geral_pago + total_geral_pendente

    # Enriquecer centros com dados de gastos
    centros_data = []
    maior_centro = None
    maior_valor = Decimal('0')

    for c in centros:
        dados = gastos_map.get(c.id, {'pago': Decimal('0'), 'pendente': Decimal('0'), 'qtd': 0})
        total_centro = dados['pago'] + dados['pendente']
        percent = (total_centro / total_geral * 100) if total_geral > 0 else 0

        centro_info = {
            'obj': c,
            'pago': float(dados['pago']),
            'pendente': float(dados['pendente']),
            'total': float(total_centro),
            'percent': float(percent),
            'qtd': dados['qtd']
        }
        centros_data.append(centro_info)

        if total_centro > maior_valor:
            maior_valor = total_centro
            maior_centro = c.name

    # Pendentes mes a mes (proximos 6 meses)
    from datetime import date
    from dateutil.relativedelta import relativedelta

    hoje = date.today()
    pendentes_mes = []
    labels_mes = []

    for i in range(6):
        mes_inicio = date(hoje.year, hoje.month, 1) + relativedelta(months=i)
        mes_fim = mes_inicio + relativedelta(months=1, days=-1)

        total_mes = db.session.query(
            func.sum(case(
                (AccountPayable.status == 'paid', 0),
                (AccountPayable.status == 'partial', func.coalesce(AccountPayable.amount, 0) - func.coalesce(AccountPayable.paid_amount, 0)),
                else_=func.coalesce(AccountPayable.amount, 0)
            ))
        ).filter(
            AccountPayable.company_id == current_user.company_id,
            AccountPayable.status.notin_(['paid', 'cancelled']),
            AccountPayable.due_date >= mes_inicio,
            AccountPayable.due_date <= mes_fim
        ).scalar() or 0

        pendentes_mes.append(float(total_mes))
        labels_mes.append(mes_inicio.strftime('%b/%y'))

    return render_template('financial/centros_custo.html', 
        centros=centros_data,
        total_pago=float(total_geral_pago),
        total_pendente=float(total_geral_pendente),
        total_geral=float(total_geral),
        sem_centro_pago=float(sem_centro_pago),
        sem_centro_pendente=float(sem_centro_pendente),
        maior_centro=maior_centro,
        pendentes_mes=pendentes_mes,
        labels_mes=labels_mes
    )


@financial_bp.route('/centros-custo/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_centro_custo():
    """Criar novo centro de custo"""
    from models.rh import CostCenter

    if request.method == 'POST':
        try:
            centro = CostCenter(
                company_id=current_user.company_id,
                code=request.form.get('code', '').strip().upper(),
                name=request.form.get('name', '').strip(),
                description=request.form.get('description', '').strip() or None,
                is_active=request.form.get('is_active') == 'on'
            )
            db.session.add(centro)
            db.session.commit()
            flash('Centro de custo criado!', 'success')
            return redirect(url_for('financial.centros_custo'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('financial/centro_custo_form.html', centro=None)


@financial_bp.route('/centros-custo/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_centro_custo(id):
    """Editar centro de custo"""
    from models.rh import CostCenter

    centro = CostCenter.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    if request.method == 'POST':
        try:
            centro.code = request.form.get('code', '').strip().upper()
            centro.name = request.form.get('name', '').strip()
            centro.description = request.form.get('description', '').strip() or None
            centro.is_active = request.form.get('is_active') == 'on'
            db.session.commit()
            flash('Centro de custo atualizado!', 'success')
            return redirect(url_for('financial.centros_custo'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'danger')

    return render_template('financial/centro_custo_form.html', centro=centro)


@financial_bp.route('/centros-custo/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_centro_custo(id):
    """Excluir centro de custo"""
    from models.rh import CostCenter

    centro = CostCenter.query.filter_by(
        id=id, company_id=current_user.company_id
    ).first_or_404()

    try:
        db.session.delete(centro)
        db.session.commit()
        flash('Centro de custo excluido!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {str(e)}', 'danger')

    return redirect(url_for('financial.centros_custo'))


@financial_bp.route('/api/centro-custo', methods=['POST'])
@login_required
def api_criar_centro_custo():
    """API para criar centro de custo inline"""
    from models.rh import CostCenter

    data = request.get_json()
    code = data.get('code', '').strip().upper()
    name = data.get('name', '').strip()

    if not code or not name:
        return jsonify({'success': False, 'error': 'Codigo e nome obrigatorios'})

    try:
        centro = CostCenter(
            company_id=current_user.company_id,
            code=code,
            name=name,
            is_active=True
        )
        db.session.add(centro)
        db.session.commit()
        return jsonify({'success': True, 'id': centro.id, 'code': centro.code, 'name': centro.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})