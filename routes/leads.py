"""
Routes para modulo Comercial (Leads/CRM)
- Kanban visual com drag-drop
- Score de intencao (0-100)
- Temperatura (frio/morno/quente)
- Estrategias de fechamento (IA)
- Reativacao de leads perdidos
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.commercial import Lead, LeadInteraction, LeadReactivation
from datetime import datetime, date, timedelta

leads_bp = Blueprint('leads', __name__, url_prefix='/leads')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@leads_bp.route('/')
@login_required
@admin_required
def index():
    """Dashboard comercial com funil kanban"""
    stages = {
        'new': {'name': 'Novo', 'leads': []},
        'contacted': {'name': 'Contato', 'leads': []},
        'qualified': {'name': 'Qualificado', 'leads': []},
        'proposal': {'name': 'Orcamento', 'leads': []},
        'negotiation': {'name': 'Negociacao', 'leads': []},
    }
    
    leads = Lead.query.filter_by(
        company_id=current_user.company_id,
        status='active'
    ).order_by(Lead.ai_score.desc()).all()
    
    for lead in leads:
        stage_key = lead.stage if lead.stage in stages else 'new'
        stages[stage_key]['leads'].append(lead)
    
    won_count = Lead.query.filter_by(
        company_id=current_user.company_id,
        stage='won'
    ).count()
    
    lost_count = Lead.query.filter_by(
        company_id=current_user.company_id,
        stage='lost'
    ).count()
    
    total_value = db.session.query(db.func.sum(Lead.estimated_value)).filter(
        Lead.company_id == current_user.company_id,
        Lead.status == 'active'
    ).scalar() or 0
    
    return render_template('leads/index.html',
                          stages=stages,
                          won_count=won_count,
                          lost_count=lost_count,
                          total_value=total_value)


@leads_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Criar novo lead"""
    if request.method == 'POST':
        try:
            lead = Lead(
                company_id=current_user.company_id,
                name=request.form.get('name', '').strip(),
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                company_name=request.form.get('company_name', '').strip() or None,
                source=request.form.get('source', 'other'),
                event_type=request.form.get('event_type', '').strip() or None,
                event_location=request.form.get('event_location', '').strip() or None,
                estimated_value=float(request.form.get('estimated_value', 0)) if request.form.get('estimated_value') else None,
                notes=request.form.get('notes', '').strip() or None,
                stage='new',
                status='active',
                ai_score=50,
                assigned_to=current_user.id
            )
            
            event_date_str = request.form.get('event_date', '')
            if event_date_str:
                lead.event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            
            db.session.add(lead)
            db.session.commit()
            
            flash(f'Lead "{lead.name}" criado com sucesso!', 'success')
            return redirect(url_for('leads.view', id=lead.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar lead: {str(e)}', 'danger')
    
    return render_template('leads/form.html', lead=None)


@leads_bp.route('/<int:id>')
@login_required
@admin_required
def view(id):
    """Detalhes do lead"""
    lead = Lead.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    interactions = LeadInteraction.query.filter_by(
        lead_id=id
    ).order_by(LeadInteraction.performed_at.desc()).limit(10).all()
    
    reactivations = LeadReactivation.query.filter_by(
        lead_id=id
    ).order_by(LeadReactivation.created_at.desc()).limit(5).all()
    
    strategies = _generate_closing_strategies(lead)
    
    return render_template('leads/view.html',
                          lead=lead,
                          interactions=interactions,
                          reactivations=reactivations,
                          strategies=strategies)


@leads_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Editar lead"""
    lead = Lead.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            lead.name = request.form.get('name', '').strip()
            lead.email = request.form.get('email', '').strip() or None
            lead.phone = request.form.get('phone', '').strip() or None
            lead.company_name = request.form.get('company_name', '').strip() or None
            lead.source = request.form.get('source', 'other')
            lead.event_type = request.form.get('event_type', '').strip() or None
            lead.event_location = request.form.get('event_location', '').strip() or None
            lead.notes = request.form.get('notes', '').strip() or None
            
            if request.form.get('estimated_value'):
                lead.estimated_value = float(request.form.get('estimated_value'))
            
            event_date_str = request.form.get('event_date', '')
            if event_date_str:
                lead.event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            
            lead.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Lead atualizado com sucesso!', 'success')
            return redirect(url_for('leads.view', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar lead: {str(e)}', 'danger')
    
    return render_template('leads/form.html', lead=lead)


@leads_bp.route('/<int:id>/stage', methods=['POST'])
@login_required
@admin_required
def update_stage(id):
    """Atualizar estagio do lead (via drag-drop)"""
    lead = Lead.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    new_stage = request.json.get('stage')
    valid_stages = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
    
    if new_stage not in valid_stages:
        return jsonify({'success': False, 'error': 'Estagio invalido'}), 400
    
    lead.stage = new_stage
    lead.updated_at = datetime.utcnow()
    
    if new_stage == 'won':
        lead.status = 'converted'
    elif new_stage == 'lost':
        lead.status = 'inactive'
    
    db.session.commit()
    
    _recalculate_score(lead)
    
    return jsonify({
        'success': True,
        'lead_id': lead.id,
        'new_stage': new_stage,
        'score': lead.ai_score
    })


@leads_bp.route('/<int:id>/interaction', methods=['POST'])
@login_required
@admin_required
def add_interaction(id):
    """Adicionar interacao com lead"""
    lead = Lead.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    try:
        interaction = LeadInteraction(
            lead_id=id,
            interaction_type=request.form.get('type', 'call'),
            direction=request.form.get('direction', 'outbound'),
            subject=request.form.get('subject', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None,
            outcome=request.form.get('outcome', 'successful'),
            next_action=request.form.get('next_action', '').strip() or None,
            performed_by=current_user.id,
            performed_at=datetime.utcnow()
        )
        
        next_date_str = request.form.get('next_action_date', '')
        if next_date_str:
            interaction.next_action_date = datetime.strptime(next_date_str, '%Y-%m-%d').date()
        
        db.session.add(interaction)
        
        lead.last_contact_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        _recalculate_score(lead)
        
        db.session.commit()
        
        flash('Interacao registrada com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar interacao: {str(e)}', 'danger')
    
    return redirect(url_for('leads.view', id=id))


@leads_bp.route('/<int:id>/reactivate', methods=['POST'])
@login_required
@admin_required
def reactivate(id):
    """Reativar lead perdido"""
    lead = Lead.query.filter_by(
        id=id,
        company_id=current_user.company_id
    ).first_or_404()
    
    if lead.stage != 'lost':
        flash('Apenas leads perdidos podem ser reativados.', 'warning')
        return redirect(url_for('leads.view', id=id))
    
    try:
        lead.stage = 'contacted'
        lead.status = 'active'
        lead.last_contact_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        interaction = LeadInteraction(
            lead_id=id,
            interaction_type='reactivation',
            direction='outbound',
            subject='Reativacao de lead',
            notes=request.form.get('notes', 'Lead reativado'),
            outcome='successful',
            performed_by=current_user.id,
            performed_at=datetime.utcnow()
        )
        db.session.add(interaction)
        
        db.session.commit()
        
        flash('Lead reativado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao reativar lead: {str(e)}', 'danger')
    
    return redirect(url_for('leads.view', id=id))


def _recalculate_score(lead):
    """Recalcula score de intencao do lead"""
    score = 50
    
    if lead.last_contact_at:
        days_since = (datetime.utcnow() - lead.last_contact_at).days
        if days_since <= 3:
            score += 20
        elif days_since <= 7:
            score += 10
        elif days_since > 14:
            score -= 15
    
    if lead.event_date:
        days_until = (lead.event_date - date.today()).days
        if 15 <= days_until <= 45:
            score += 20
        elif days_until < 15:
            score += 10
        elif days_until > 90:
            score -= 5
    
    if lead.estimated_value:
        if lead.estimated_value >= 20000:
            score += 15
        elif lead.estimated_value >= 10000:
            score += 10
        elif lead.estimated_value >= 5000:
            score += 5
    
    stage_scores = {
        'new': 0,
        'contacted': 10,
        'qualified': 20,
        'proposal': 30,
        'negotiation': 40
    }
    score += stage_scores.get(lead.stage, 0)
    
    lead.ai_score = max(0, min(100, score))
    
    if lead.ai_score >= 75:
        lead.probability = 80
    elif lead.ai_score >= 50:
        lead.probability = 50
    else:
        lead.probability = 20


def _generate_closing_strategies(lead):
    """Gera estrategias de fechamento baseadas no lead"""
    strategies = []
    
    if lead.estimated_value and lead.estimated_value >= 10000:
        strategies.append({
            'tipo': 'desconto_progressivo',
            'titulo': 'Desconto 5-10%',
            'descricao': f'Oferecer desconto progressivo de 5-10% para fechamento rapido',
            'pitch': f'Revisamos os custos e conseguimos oferecer um desconto especial se fecharmos esta semana.',
            'prioridade': 'alta'
        })
    
    if lead.event_date:
        days_until = (lead.event_date - date.today()).days
        if days_until <= 45:
            strategies.append({
                'tipo': 'urgencia_temporal',
                'titulo': 'Urgencia do Prazo',
                'descricao': f'Evento em {days_until} dias - urgencia no fechamento',
                'pitch': f'O evento esta em {days_until} dias e nossa agenda esta se fechando. Precisamos confirmar para garantir os equipamentos.',
                'prioridade': 'alta'
            })
    
    strategies.append({
        'tipo': 'valor_agregado',
        'titulo': 'Servicos Inclusos',
        'descricao': 'Incluir tecnico, seguro ou transporte sem custo adicional',
        'pitch': 'Incluimos tecnico durante o evento, seguro e transporte sem custo adicional.',
        'prioridade': 'media'
    })
    
    return strategies
