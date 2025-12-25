from flask import Blueprint, redirect, url_for
from flask_login import login_required

separation_bp = Blueprint('separation', __name__, url_prefix='/separation')

@separation_bp.route('/')
@login_required
def index():
    return redirect(url_for('orcamento.index'))

@separation_bp.route('/new')
@login_required
def new():
    return redirect(url_for('orcamento.new'))

@separation_bp.route('/<int:id>')
@login_required
def detail(id):
    return redirect(url_for('orcamento.detail', id=id))
