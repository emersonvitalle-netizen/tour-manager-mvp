"""
Blueprint para Relatórios Visuais (Dashboards com Chart.js)
VERSÃO FINAL - SEM SIMULAÇÕES - 100% DADOS REAIS
ATUALIZADO: despesas_cat separado por categorias RH (consistente com DRE)
"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func, and_, or_
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
    """API JSON que retorna todos os dados REAIS para os gráficos"""
    from models.equipment import Equipment
    from models.category import Category
    from models.maintenance import Maintenance
    from models.rh import AccountReceivable, AccountPayable, PayrollEntry, FreelancerPayment
    from models.tour import TourEquipment

    company_id = current_user.company_id

    # ========== FINANCEIRO ==========
    receitas_12m = []
    despesas_12m = []
    meses_labels = []

    for i in range(11, -1, -1):
        mes_inicio = (date.today().replace(day=1) - timedelta(days=30*i))
        mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1)
        meses_labels.append(mes_inicio.strftime('%b/%y'))

        receita = db.session.query(func.sum(AccountReceivable.amount)).filter(
            AccountReceivable.company_id == company_id,
            AccountReceivable.status == 'received',
            func.date(AccountReceivable.received_at) >= mes_inicio,
            func.date(AccountReceivable.received_at) < mes_fim
        ).scalar() or 0
        receitas_12m.append(float(receita))

        despesa_folha = db.session.query(func.sum(PayrollEntry.net_salary)).filter(
            PayrollEntry.company_id == company_id,
            PayrollEntry.reference_month == mes_inicio.month,
            PayrollEntry.reference_year == mes_inicio.year
        ).scalar() or 0

        despesa_contas = db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            func.date(AccountPayable.paid_at) >= mes_inicio,
            func.date(AccountPayable.paid_at) < mes_fim
        ).scalar() or 0

        despesa_freelancers = db.session.query(func.sum(FreelancerPayment.amount)).filter(
            FreelancerPayment.company_id == company_id,
            FreelancerPayment.status == 'paid',
            func.date(FreelancerPayment.paid_at) >= mes_inicio,
            func.date(FreelancerPayment.paid_at) < mes_fim
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

    # ========== DESPESAS POR CATEGORIA (mês atual) - SEPARADO POR TIPO ==========
    mes_atual_inicio = date.today().replace(day=1)
    mes_atual_fim = (mes_atual_inicio + timedelta(days=32)).replace(day=1)

    # Custo de manutenção do mês
    custo_manutencao_mes_atual = float(db.session.query(func.sum(Maintenance.total_cost)).filter(
        Maintenance.company_id == company_id,
        Maintenance.status == 'completed',
        func.date(Maintenance.completed_at) >= mes_atual_inicio,
        func.date(Maintenance.completed_at) < mes_atual_fim
    ).scalar() or 0)

    # Função auxiliar para somar AccountPayable por categoria
    def soma_contas_categoria(categoria):
        return float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            AccountPayable.category == categoria,
            func.date(AccountPayable.paid_at) >= mes_atual_inicio,
            func.date(AccountPayable.paid_at) < mes_atual_fim
        ).scalar() or 0)

    # Categorias RH separadas
    categorias_rh = ['adiantamento', 'inss', 'fgts', 'irrf']

    # Outras contas (excluindo categorias RH)
    outras_contas = float(db.session.query(func.sum(AccountPayable.paid_amount)).filter(
            AccountPayable.company_id == company_id,
            AccountPayable.status == 'paid',
            ~AccountPayable.category.in_(categorias_rh),
            func.date(AccountPayable.paid_at) >= mes_atual_inicio,
            func.date(AccountPayable.paid_at) < mes_atual_fim
    ).scalar() or 0)

    # Despesas por categoria - CONSISTENTE COM DRE
    despesas_cat = {
        'Salarios': float(db.session.query(func.sum(PayrollEntry.net_salary)).filter(
            PayrollEntry.company_id == company_id,
            PayrollEntry.reference_month == date.today().month,
            PayrollEntry.reference_year == date.today().year
        ).scalar() or 0),
        'Adiantamentos': soma_contas_categoria('adiantamento'),
        'Encargos': soma_contas_categoria('inss') + soma_contas_categoria('fgts') + soma_contas_categoria('irrf'),
        'Freelancers': float(db.session.query(func.sum(FreelancerPayment.amount)).filter(
            FreelancerPayment.company_id == company_id,
            FreelancerPayment.status == 'paid',
            func.date(FreelancerPayment.paid_at) >= mes_atual_inicio,
            func.date(FreelancerPayment.paid_at) < mes_atual_fim
        ).scalar() or 0),
        'Outras Contas': outras_contas,
        'Manutencao': custo_manutencao_mes_atual
    }

    # Remover categorias com valor zero para não poluir o gráfico
    despesas_cat = {k: v for k, v in despesas_cat.items() if v > 0}

    # ========== EQUIPAMENTOS ==========
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

    # Crescimento por categoria (12 meses)
    crescimento_categorias = {}
    for cat in categories:
        crescimento = []
        for i in range(11, -1, -1):
            mes_ref = date.today().replace(day=1) - timedelta(days=30*i)
            mes_fim = (mes_ref + timedelta(days=32)).replace(day=1)
            count = Equipment.query.filter(
                Equipment.company_id == company_id,
                Equipment.category_id == cat.id,
                Equipment.is_active == True,
                Equipment.created_at < mes_fim
            ).count()
            crescimento.append(count)
        crescimento_categorias[cat.name] = crescimento

    # ========== MANUTENÇÃO ==========
    manutencao_gastos = []
    for i in range(11, -1, -1):
        mes_inicio = date.today().replace(day=1) - timedelta(days=30*i)
        mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1)
        custo = float(db.session.query(func.sum(Maintenance.total_cost)).filter(
            Maintenance.company_id == company_id,
            Maintenance.status == 'completed',
            func.date(Maintenance.completed_at) >= mes_inicio,
            func.date(Maintenance.completed_at) < mes_fim
        ).scalar() or 0)
        manutencao_gastos.append(custo)

    manutencao_tipos = {}
    tipos_query = db.session.query(
        Maintenance.maintenance_type,
        func.count(Maintenance.id)
    ).filter(
        Maintenance.company_id == company_id
    ).group_by(Maintenance.maintenance_type).all()

    for tipo, count in tipos_query:
        tipo_label = {
            'preventive': 'Preventiva',
            'corrective': 'Corretiva',
            'calibration': 'Calibracao',
            'emergency': 'Emergencial'
        }.get(tipo, tipo or 'Outros')
        manutencao_tipos[tipo_label] = count

    top_manutencao_query = db.session.query(
        Equipment.code,
        Equipment.brand,
        Equipment.model,
        func.count(Maintenance.id).label('count')
    ).join(Maintenance, Equipment.id == Maintenance.equipment_id).filter(
        Equipment.company_id == company_id
    ).group_by(Equipment.id).order_by(func.count(Maintenance.id).desc()).limit(10).all()

    top_manutencao = []
    for eq_code, eq_brand, eq_model, count in top_manutencao_query:
        nome = f"{eq_brand or ''} {eq_model or ''} {eq_code}".strip()
        top_manutencao.append({'nome': nome, 'count': count})

    # ========== AQUISIÇÕES - DADOS REAIS ==========
    aquisicoes_por_cat = {}
    ano_atual = date.today().year

    for cat in categories:
        try:
            total = db.session.query(func.sum(Equipment.purchase_price)).filter(
                Equipment.company_id == company_id,
                Equipment.category_id == cat.id,
                func.strftime('%Y', Equipment.purchase_date) == str(ano_atual)
            ).scalar() or 0
        except:
            try:
                total = db.session.query(func.sum(Equipment.value)).filter(
                    Equipment.company_id == company_id,
                    Equipment.category_id == cat.id,
                    func.strftime('%Y', Equipment.purchase_date) == str(ano_atual)
                ).scalar() or 0
            except:
                total = 0
        aquisicoes_por_cat[cat.name] = float(total)

    # ========== MÉTRICAS DO TOPO - SEM SIMULAÇÕES ==========
    receita_mes = db.session.query(func.sum(AccountReceivable.amount)).filter(
        AccountReceivable.company_id == company_id,
        AccountReceivable.status == 'received',
        func.date(AccountReceivable.received_at) >= mes_atual_inicio,
        func.date(AccountReceivable.received_at) < mes_atual_fim
    ).scalar() or 0

    manutencoes_mes = Maintenance.query.filter(
        Maintenance.company_id == company_id,
        func.date(Maintenance.started_at) >= mes_atual_inicio,
        func.date(Maintenance.started_at) < mes_atual_fim
    ).count()

    custo_manutencao_mes = custo_manutencao_mes_atual

    # Taxa de utilização - DADOS REAIS
    total_equip = Equipment.query.filter_by(company_id=company_id, is_active=True).count()
    em_uso = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.is_active == True,
        Equipment.status.in_(['in_tour', 'loading', 'in_transit'])
    ).count()
    taxa_utilizacao = (em_uso / total_equip * 100) if total_equip > 0 else 0

    margem_lucro = margem_6m[-1] if margem_6m else 0

    # ========== ALERTAS - DADOS REAIS ==========
    alertas = []

    manutencoes_atrasadas = Maintenance.query.filter(
        Maintenance.company_id == company_id,
        Maintenance.status == 'pending',
        Maintenance.started_at < datetime.now() - timedelta(days=15)
    ).count()

    if manutencoes_atrasadas > 0:
        alertas.append({
            'tipo': 'danger',
            'icone': '🚨',
            'titulo': 'Manutencao Atrasada',
            'mensagem': f'{manutencoes_atrasadas} equipamento(s) com manutencao atrasada ha mais de 15 dias'
        })

    equipamentos_criticos = db.session.query(
        Equipment.code,
        func.count(Maintenance.id).label('count')
    ).join(Maintenance, Equipment.id == Maintenance.equipment_id).filter(
        Equipment.company_id == company_id,
        func.strftime('%Y', Maintenance.started_at) == str(ano_atual)
    ).group_by(Equipment.id).having(func.count(Maintenance.id) >= 3).all()

    if equipamentos_criticos:
        eq_code, eq_count = equipamentos_criticos[0]
        alertas.append({
            'tipo': 'warning',
            'icone': '⚠️',
            'titulo': 'Equipamento Critico',
            'mensagem': f'{eq_code} - {eq_count} manutencoes este ano'
        })

    # Equipamentos ociosos - CORRIGIDO (verifica manutenção E tours)
    equipamentos_ids_usados = set()

    # IDs de equipamentos em manutenção recente
    manut_ids = db.session.query(Maintenance.equipment_id).filter(
        Maintenance.started_at > datetime.now() - timedelta(days=90)
    ).all()
    equipamentos_ids_usados.update([m[0] for m in manut_ids])

    # IDs de equipamentos em tours recentes
    tour_ids = db.session.query(TourEquipment.equipment_id).filter(
        TourEquipment.allocated_at > datetime.now() - timedelta(days=90)
    ).all()
    equipamentos_ids_usados.update([t[0] for t in tour_ids])

    ociosos = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.status == 'available',
        Equipment.is_active == True,
        ~Equipment.id.in_(equipamentos_ids_usados) if equipamentos_ids_usados else True
    ).count()

    if ociosos > 5:
        alertas.append({
            'tipo': 'info',
            'icone': 'ℹ️',
            'titulo': 'Equipamentos Ociosos',
            'mensagem': f'{ociosos} equipamentos sem uso ha mais de 90 dias - considerar realocacao'
        })

    if margem_lucro > 0:
        alertas.append({
            'tipo': 'success',
            'icone': '✅',
            'titulo': 'Margem Positiva',
            'mensagem': f'Margem de lucro em {margem_lucro:.1f}% - resultado positivo'
        })

    # ========== KPIs REAIS - DISPONÍVEIS E EM TOUR ==========
    equipamentos_disponiveis = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.status == 'available',
        Equipment.is_active == True
    ).count()

    equipamentos_em_tour = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.status.in_(['in_tour', 'loading', 'in_transit']),
        Equipment.is_active == True
    ).count()

    equipamentos_em_manutencao = Equipment.query.filter(
        Equipment.company_id == company_id,
        Equipment.status.in_(['maintenance', 'in_repair', 'external_repair'])
    ).count()

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
            'crescimento': crescimento_categorias,
            'em_manutencao': equipamentos_em_manutencao,
            'disponiveis': equipamentos_disponiveis,
            'em_tour': equipamentos_em_tour
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
            'taxa_utilizacao': round(taxa_utilizacao, 1),
            'margem_lucro': margem_lucro
        },
        'alertas': alertas
    }

    return jsonify(dados)