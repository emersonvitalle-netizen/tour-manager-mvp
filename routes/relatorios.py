"""
Blueprint para Relatórios Visuais (Dashboards com Chart.js)
"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func, extract
from datetime import datetime, date, timedelta
from decimal import Decimal

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')


def admin_required(f):
    """Decorator para rotas apenas admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            from flask import flash, redirect, url_for
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@relatorios_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard principal de relatórios visuais"""
    return render_template('relatorios/index.html')


@relatorios_bp.route('/api/dados')
@login_required
@admin_required
def api_dados():
    """
    API JSON que retorna todos os dados para os gráficos
    """
    from models.equipment import Equipment
    from models.category import Category
    from models.maintenance import Maintenance
    from models.rh import AccountReceivable, AccountPayable, PayrollEntry, FreelancerPayment

    company_id = current_user.company_id

    # ========== FINANCEIRO ==========

    # Receitas vs Despesas (12 meses)
    receitas_12m = []
    despesas_12m = []
    meses_labels = []

    for i in range(11, -1, -1):
        mes_ref = date.today().replace(day=1) - timedelta(days=30*i)
        mes_str = mes_ref.strftime('%Y-%m')
        meses_labels.append(mes_ref.strftime('%b/%y'))

        # Receitas do mês
        receita = db.session.query(func.sum(AccountReceivable.amount)).filter(
            AccountReceivable.company_id == company_id,
            AccountReceivable.status == 'received',
            func.strftime('%Y-%m', AccountReceivable.received_at) == mes_str
        ).scalar() or 0
        receitas_12m.append(float(receita))

        # Despesas do mês
        despesa_folha = db.session.query(func.sum(PayrollEntry.net_salary)).filter(
            PayrollEntry.company_id == company_id,
            func.strftime('%Y-%m', PayrollEntry.reference_date) == mes_str
        ).scalar() or 0

        despesa_contas = db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            func.strftime('%Y-%m', AccountPayable.paid_at) == mes_str
        ).scalar() or 0

        despesa_freelancers = db.session.query(func.sum(FreelancerPayment.amount)).filter(
            FreelancerPayment.company_id == company_id,
            FreelancerPayment.status == 'paid',
            func.strftime('%Y-%m', FreelancerPayment.paid_at) == mes_str
        ).scalar() or 0

        total_despesa = float(despesa_folha) + float(despesa_contas) + float(despesa_freelancers)
        despesas_12m.append(total_despesa)

    # Margem de Lucro (6 meses)
    margem_6m = []
    margem_labels = []
    for i in range(5, -1, -1):
        mes_ref = date.today().replace(day=1) - timedelta(days=30*i)
        margem_labels.append(mes_ref.strftime('%b/%y'))

        idx = 11 - i
        if idx < len(receitas_12m):
            rec = receitas_12m[idx]
            desp = despesas_12m[idx]
            margem = ((rec - desp) / rec * 100) if rec > 0 else 0
            margem_6m.append(round(margem, 1))
        else:
            margem_6m.append(0)

    # Despesas por Categoria
    despesas_cat = {
        'Folha': float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
            PayrollEntry.company_id == company_id,
            func.strftime('%Y-%m', PayrollEntry.reference_date) == date.today().strftime('%Y-%m')
        ).scalar() or 0),
        'Freelancers': float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
            FreelancerPayment.company_id == company_id,
            FreelancerPayment.status == 'paid',
            func.strftime('%Y-%m', FreelancerPayment.paid_at) == date.today().strftime('%Y-%m')
        ).scalar() or 0),
        'Contas': float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            func.strftime('%Y-%m', AccountPayable.paid_at) == date.today().strftime('%Y-%m')
        ).scalar() or 0),
        'Manutenção': 0  # TODO: adicionar quando model de manutenção tiver custo
    }

    # ========== EQUIPAMENTOS ==========

    # Total de equipamentos por categoria
    categories = Category.query.filter_by(company_id=company_id).all()
    equip_por_categoria = {}
    equip_icons = {'Som': '🎤', 'Luz': '💡', 'Materiais': '🔧', 'Instrumentos': '🎸'}

    for cat in categories:
        count = Equipment.query.filter_by(
            company_id=company_id,
            category_id=cat.id,
            is_active=True
        ).count()
        equip_por_categoria[cat.name] = {
            'count': count,
            'icon': equip_icons.get(cat.name, '📦')
        }

    total_equipment = Equipment.query.filter_by(
        company_id=company_id,
        is_active=True
    ).count()

    # Crescimento por categoria (12 meses) - SIMULADO
    crescimento_categorias = {}
    for cat_name in equip_por_categoria.keys():
        # Simulando crescimento gradual
        base = equip_por_categoria[cat_name]['count']
        crescimento = []
        for i in range(12):
            valor = int(base * (0.7 + (i * 0.025)))
            crescimento.append(valor)
        crescimento_categorias[cat_name] = crescimento

    # ========== MANUTENÇÃO ==========

    # Gastos com manutenção (12 meses) - SIMULADO
    manutencao_gastos = []
    for i in range(12):
        # Simulando custos variáveis
        custo = 8000 + (i * 500) + ((i % 3) * 2000)
        manutencao_gastos.append(custo)

    # Manutenções por tipo - SIMULADO
    manutencao_tipos = {
        'Preventiva': 42,
        'Corretiva': 35,
        'Preditiva': 15,
        'Emergencial': 8
    }

    # Top 10 equipamentos com mais manutenções - SIMULADO
    top_manutencao = [
        {'nome': 'Moving Head Robe Robin #12', 'count': 7},
        {'nome': 'Amplificador Crown XTi #3', 'count': 6},
        {'nome': 'Console Yamaha CL5 #1', 'count': 5},
        {'nome': 'LED PAR Cameo #22', 'count': 5},
        {'nome': 'Microfone Shure SM58 #45', 'count': 4},
        {'nome': 'Processador DBX #8', 'count': 4},
        {'nome': 'Caixa Line Array #5', 'count': 3},
        {'nome': 'Dimmer Avolites #2', 'count': 3},
        {'nome': 'Cabo XLR 10m #89', 'count': 3},
        {'nome': 'Pedestal Microfone #67', 'count': 2}
    ]

    # ========== AQUISIÇÕES ==========

    aquisicoes_por_cat = {}
    for cat_name in equip_por_categoria.keys():
        # Simulando valores de investimento
        valores = {'Som': 85000, 'Luz': 142000, 'Materiais': 38000, 'Instrumentos': 25000}
        aquisicoes_por_cat[cat_name] = valores.get(cat_name, 50000)

    # ========== MÉTRICAS DO TOPO ==========

    mes_atual = date.today().strftime('%Y-%m')

    receita_mes = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'received',
        func.strftime('%Y-%m', AccountReceivable.received_at) == mes_atual
    ).scalar() or 0

    manutencoes_mes = 28  # SIMULADO
    custo_manutencao_mes = 15400  # SIMULADO
    taxa_utilizacao = 67.8  # SIMULADO
    margem_lucro = margem_6m[-1] if margem_6m else 0

    # ========== ALERTAS ==========

    alertas = [
        {
            'tipo': 'danger',
            'icone': '🚨',
            'titulo': 'Manutenção Atrasada',
            'mensagem': '3 equipamentos com manutenção atrasada há mais de 15 dias'
        },
        {
            'tipo': 'warning',
            'icone': '⚠️',
            'titulo': 'Equipamento Crítico',
            'mensagem': 'Moving Head #12 - 5 manutenções em 3 meses (R$ 3.200)'
        },
        {
            'tipo': 'warning',
            'icone': '⚠️',
            'titulo': 'Gastos Elevados',
            'mensagem': 'Custos de manutenção 23% acima da média trimestral'
        },
        {
            'tipo': 'info',
            'icone': 'ℹ️',
            'titulo': 'Equipamentos Ociosos',
            'mensagem': '18 equipamentos sem uso há mais de 90 dias - considerar realocação'
        },
        {
            'tipo': 'success',
            'icone': '✅',
            'titulo': 'Meta Atingida',
            'mensagem': 'Taxa de utilização aumentou 8,5% - meta trimestral alcançada'
        }
    ]

    # ========== RESPOSTA JSON ==========

    dados = {
        'financeiro': {
            'receitas_12m': receitas_12m,
            'despesas_12m': despesas_12m,
            'meses_labels': meses_labels,
            'margem_6m': margem_6m,
            'margem_labels': margem_labels,
            'despesas_categoria': despesas_cat
        },
        'equipamentos': {
            'total': total_equipment,
            'por_categoria': equip_por_categoria,
            'crescimento': crescimento_categorias
        },
        'manutencao': {
            'gastos_12m': manutencao_gastos,
            'tipos': manutencao_tipos,
            'top_equipamentos': top_manutencao
        },
        'aquisicoes': aquisicoes_por_cat,
        'metricas': {
            'receita_mes': float(receita_mes),
            'total_equipamentos': total_equipment,
            'manutencoes_mes': manutencoes_mes,
            'custo_manutencao_mes': custo_manutencao_mes,
            'taxa_utilizacao': taxa_utilizacao,
            'margem_lucro': margem_lucro
        },
        'alertas': alertas
    }

    return jsonify(dados)