class WizardController {
    constructor(options = {}) {
        this.steps = [];
        this.currentStep = 0;
        this.data = {};
        this.onComplete = options.onComplete || (() => {});
        this.onCancel = options.onCancel || (() => {});
        this.modalId = options.modalId || 'wizardModal';
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    addStep(step) {
        this.steps.push({
            title: step.title || `Passo ${this.steps.length + 1}`,
            content: step.content || '',
            endpoint: step.endpoint || null,
            validate: step.validate || (() => true),
            onEnter: step.onEnter || (() => {}),
            onLeave: step.onLeave || (() => {}),
            skipIf: step.skipIf || (() => false)
        });
        return this;
    }

    start(initialData = {}) {
        this.data = { ...initialData };
        this.currentStep = 0;
        this._findNextValidStep();
        this._render();
        this._showModal();
    }

    _findNextValidStep() {
        while (this.currentStep < this.steps.length && 
               this.steps[this.currentStep].skipIf(this.data)) {
            this.currentStep++;
        }
    }

    _render() {
        const step = this.steps[this.currentStep];
        if (!step) return;

        const modal = document.getElementById(this.modalId);
        if (!modal) {
            this._createModal();
        }

        const titleEl = document.getElementById('wizardTitle');
        const bodyEl = document.getElementById('wizardBody');
        const progressEl = document.getElementById('wizardProgress');
        const prevBtn = document.getElementById('wizardPrev');
        const nextBtn = document.getElementById('wizardNext');

        if (titleEl) titleEl.textContent = step.title;
        if (bodyEl) bodyEl.innerHTML = typeof step.content === 'function' 
            ? step.content(this.data) 
            : step.content;
        
        if (progressEl) {
            const progress = ((this.currentStep + 1) / this.steps.length) * 100;
            progressEl.style.width = `${progress}%`;
            progressEl.textContent = `${this.currentStep + 1}/${this.steps.length}`;
        }

        if (prevBtn) prevBtn.style.display = this.currentStep > 0 ? 'block' : 'none';
        if (nextBtn) {
            nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Concluir' : 'Próximo';
        }

        step.onEnter(this.data);
        this._bindEvents();
    }

    _createModal() {
        const modalHtml = `
        <div class="modal fade" id="${this.modalId}" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content" style="background: #1a1a1a; border: 1px solid #333;">
                    <div class="modal-header" style="border-bottom: 1px solid #333;">
                        <h5 class="modal-title" id="wizardTitle" style="color: #d4a574;"></h5>
                        <button type="button" class="btn-close btn-close-white" id="wizardClose"></button>
                    </div>
                    <div class="progress" style="height: 4px; background: #333;">
                        <div class="progress-bar" id="wizardProgress" style="background: #d4a574;"></div>
                    </div>
                    <div class="modal-body" id="wizardBody" style="color: #fff; min-height: 150px;">
                    </div>
                    <div class="modal-footer" style="border-top: 1px solid #333;">
                        <button type="button" class="btn btn-outline-secondary" id="wizardPrev" style="display: none;">
                            <i class="bi bi-arrow-left"></i> Voltar
                        </button>
                        <button type="button" class="btn" id="wizardNext" style="background: #d4a574; color: #000;">
                            Próximo <i class="bi bi-arrow-right"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    _bindEvents() {
        const nextBtn = document.getElementById('wizardNext');
        const prevBtn = document.getElementById('wizardPrev');
        const closeBtn = document.getElementById('wizardClose');

        if (nextBtn) {
            nextBtn.onclick = () => this._next();
        }
        if (prevBtn) {
            prevBtn.onclick = () => this._prev();
        }
        if (closeBtn) {
            closeBtn.onclick = () => this._cancel();
        }
    }

    async _next() {
        const step = this.steps[this.currentStep];
        
        this._collectFormData();
        
        if (!step.validate(this.data)) {
            return;
        }

        await step.onLeave(this.data);

        if (step.endpoint) {
            try {
                const response = await this._callEndpoint(step.endpoint);
                if (response.success) {
                    this.data = { ...this.data, ...response.data };
                } else {
                    this._showError(response.message || 'Erro ao processar');
                    return;
                }
            } catch (error) {
                this._showError('Erro de conexão');
                return;
            }
        }

        this.currentStep++;
        this._findNextValidStep();

        if (this.currentStep >= this.steps.length) {
            this._complete();
        } else {
            this._render();
        }
    }

    _prev() {
        if (this.currentStep > 0) {
            this.currentStep--;
            while (this.currentStep > 0 && this.steps[this.currentStep].skipIf(this.data)) {
                this.currentStep--;
            }
            this._render();
        }
    }

    _collectFormData() {
        const form = document.getElementById('wizardBody').querySelector('form');
        if (form) {
            const formData = new FormData(form);
            formData.forEach((value, key) => {
                this.data[key] = value;
            });
        }
        
        document.querySelectorAll('#wizardBody input, #wizardBody select, #wizardBody textarea').forEach(el => {
            if (el.name && !el.closest('form')) {
                if (el.type === 'checkbox') {
                    this.data[el.name] = el.checked;
                } else if (el.type === 'radio') {
                    if (el.checked) this.data[el.name] = el.value;
                } else {
                    this.data[el.name] = el.value;
                }
            }
        });
    }

    async _callEndpoint(endpoint) {
        const url = typeof endpoint === 'function' ? endpoint(this.data) : endpoint;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(this.data)
        });
        return response.json();
    }

    _showError(message) {
        const bodyEl = document.getElementById('wizardBody');
        const existingAlert = bodyEl.querySelector('.alert-danger');
        if (existingAlert) existingAlert.remove();
        
        bodyEl.insertAdjacentHTML('afterbegin', 
            `<div class="alert alert-danger alert-dismissible fade show">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`);
    }

    _showModal() {
        const modal = new bootstrap.Modal(document.getElementById(this.modalId));
        modal.show();
    }

    _hideModal() {
        const modalEl = document.getElementById(this.modalId);
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
    }

    _complete() {
        this._hideModal();
        this.onComplete(this.data);
    }

    _cancel() {
        this._hideModal();
        this.onCancel(this.data);
    }

    setData(key, value) {
        this.data[key] = value;
        return this;
    }

    getData(key) {
        return key ? this.data[key] : this.data;
    }
}

function startQuoteApprovalWizard(quoteId, quoteName, quoteTotal) {
    const wizard = new WizardController({
        onComplete: (data) => {
            showToast('Fluxo concluído com sucesso!', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    });

    wizard.addStep({
        title: 'Aprovar Orçamento',
        content: (data) => `
            <div class="text-center mb-4">
                <i class="bi bi-check-circle" style="font-size: 3rem; color: #28a745;"></i>
            </div>
            <h5 class="text-center mb-3">${quoteName}</h5>
            <p class="text-center text-muted">Valor: R$ ${quoteTotal}</p>
            <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" name="confirm_approve" id="confirmApprove" required>
                <label class="form-check-label" for="confirmApprove">
                    Confirmo a aprovação deste orçamento
                </label>
            </div>`,
        validate: (data) => {
            if (!data.confirm_approve) {
                alert('Confirme a aprovação');
                return false;
            }
            return true;
        },
        endpoint: `/orcamento/${quoteId}/approve`
    });

    wizard.addStep({
        title: 'Gerar Contrato?',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-file-earmark-text" style="font-size: 3rem; color: #d4a574;"></i>
            </div>
            <p class="text-center mb-4">Deseja gerar um contrato a partir deste orçamento?</p>
            <div class="d-flex justify-content-center gap-3">
                <label class="btn btn-outline-light">
                    <input type="radio" name="generate_contract" value="yes" class="d-none" checked> 
                    <i class="bi bi-check-lg"></i> Sim
                </label>
                <label class="btn btn-outline-secondary">
                    <input type="radio" name="generate_contract" value="no" class="d-none"> 
                    <i class="bi bi-x-lg"></i> Não
                </label>
            </div>`,
        endpoint: (data) => data.generate_contract === 'yes' ? `/financial/contracts/from-quote/${quoteId}` : null
    });

    wizard.addStep({
        title: 'Gerar Contas a Receber?',
        content: (data) => `
            <div class="text-center mb-4">
                <i class="bi bi-cash-stack" style="font-size: 3rem; color: #28a745;"></i>
            </div>
            <p class="text-center mb-3">Configurar parcelas do recebimento:</p>
            <div class="mb-3">
                <label class="form-label">Número de Parcelas</label>
                <select name="installments" class="form-select bg-dark text-white border-secondary">
                    <option value="1">À vista</option>
                    <option value="2">2x</option>
                    <option value="3">3x</option>
                    <option value="4">4x</option>
                    <option value="6">6x</option>
                    <option value="12">12x</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Primeiro Vencimento</label>
                <input type="date" name="first_due_date" class="form-control bg-dark text-white border-secondary" 
                       value="${new Date().toISOString().split('T')[0]}">
            </div>`,
        endpoint: `/financial/contas-receber/from-quote/${quoteId}`
    });

    wizard.addStep({
        title: 'Vincular a Evento?',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-calendar-event" style="font-size: 3rem; color: #17a2b8;"></i>
            </div>
            <p class="text-center mb-3">Deseja vincular a um evento/tour existente?</p>
            <div class="mb-3">
                <select name="tour_id" class="form-select bg-dark text-white border-secondary">
                    <option value="">Não vincular</option>
                </select>
            </div>`,
        onEnter: async (data) => {
            try {
                const response = await fetch('/tour/api/list');
                const tours = await response.json();
                const select = document.querySelector('select[name="tour_id"]');
                tours.forEach(tour => {
                    select.insertAdjacentHTML('beforeend', 
                        `<option value="${tour.id}">${tour.name} - ${tour.artist}</option>`);
                });
            } catch (e) {}
        }
    });

    wizard.setData('quote_id', quoteId);
    wizard.start();
}

function startEmployeeWizard(employeeId, employeeName, salary) {
    const wizard = new WizardController({
        onComplete: (data) => {
            showToast('Funcionário configurado com sucesso!', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    });

    wizard.addStep({
        title: 'Despesas Automáticas',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-person-badge" style="font-size: 3rem; color: #d4a574;"></i>
            </div>
            <h5 class="text-center mb-3">${employeeName}</h5>
            <p class="text-center text-muted mb-4">Salário: R$ ${salary}</p>
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" name="auto_salary" id="autoSalary" checked>
                <label class="form-check-label" for="autoSalary">
                    Criar despesa mensal de salário
                </label>
            </div>
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" name="auto_benefits" id="autoBenefits">
                <label class="form-check-label" for="autoBenefits">
                    Criar despesas de benefícios (VT, VR)
                </label>
            </div>`,
        endpoint: `/rh/employees/${employeeId}/auto-expenses`
    });

    wizard.addStep({
        title: 'Configurar Benefícios',
        skipIf: (data) => !data.auto_benefits,
        content: () => `
            <div class="mb-3">
                <label class="form-label">Vale Transporte (mensal)</label>
                <input type="number" name="vt_value" class="form-control bg-dark text-white border-secondary" 
                       placeholder="0.00" step="0.01">
            </div>
            <div class="mb-3">
                <label class="form-label">Vale Refeição (mensal)</label>
                <input type="number" name="vr_value" class="form-control bg-dark text-white border-secondary" 
                       placeholder="0.00" step="0.01">
            </div>`
    });

    wizard.setData('employee_id', employeeId);
    wizard.start();
}

function startFreelancerPaymentWizard(freelancerId, freelancerName, eventName, value) {
    const wizard = new WizardController({
        onComplete: (data) => {
            showToast('Pagamento registrado!', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    });

    wizard.addStep({
        title: 'Registrar Pagamento',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-person-check" style="font-size: 3rem; color: #28a745;"></i>
            </div>
            <h5 class="text-center mb-2">${freelancerName}</h5>
            <p class="text-center text-muted mb-3">${eventName}</p>
            <div class="mb-3">
                <label class="form-label">Valor</label>
                <input type="number" name="value" class="form-control bg-dark text-white border-secondary" 
                       value="${value}" step="0.01">
            </div>
            <div class="mb-3">
                <label class="form-label">Data de Pagamento</label>
                <input type="date" name="payment_date" class="form-control bg-dark text-white border-secondary" 
                       value="${new Date().toISOString().split('T')[0]}">
            </div>`,
        endpoint: `/rh/freelancers/${freelancerId}/register-payment`
    });

    wizard.addStep({
        title: 'Criar Conta a Pagar?',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-credit-card" style="font-size: 3rem; color: #ffc107;"></i>
            </div>
            <p class="text-center mb-4">Registrar na Contas a Pagar?</p>
            <div class="d-flex justify-content-center gap-3">
                <label class="btn btn-outline-success">
                    <input type="radio" name="create_payable" value="yes" class="d-none" checked> 
                    <i class="bi bi-check-lg"></i> Sim
                </label>
                <label class="btn btn-outline-secondary">
                    <input type="radio" name="create_payable" value="no" class="d-none"> 
                    <i class="bi bi-x-lg"></i> Não
                </label>
            </div>`,
        endpoint: (data) => data.create_payable === 'yes' ? `/financial/contas-pagar/from-freelancer` : null
    });

    wizard.setData('freelancer_id', freelancerId);
    wizard.setData('event_name', eventName);
    wizard.start();
}

function startPostApprovalWizard(quoteId, quoteName, quoteTotal) {
    const wizard = new WizardController({
        onComplete: (data) => {
            showToast('Fluxo concluído com sucesso!', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    });

    wizard.addStep({
        title: 'Gerar Contrato?',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-file-earmark-text" style="font-size: 3rem; color: #d4a574;"></i>
            </div>
            <h5 class="text-center mb-3">${quoteName}</h5>
            <p class="text-center text-muted mb-3">Valor: R$ ${quoteTotal}</p>
            <p class="text-center mb-4">Deseja gerar um contrato a partir deste orçamento aprovado?</p>
            <div class="d-flex justify-content-center gap-3">
                <label class="btn btn-outline-light">
                    <input type="radio" name="generate_contract" value="yes" class="d-none" checked> 
                    <i class="bi bi-check-lg"></i> Sim
                </label>
                <label class="btn btn-outline-secondary">
                    <input type="radio" name="generate_contract" value="no" class="d-none"> 
                    <i class="bi bi-x-lg"></i> Não
                </label>
            </div>`,
        endpoint: (data) => data.generate_contract === 'yes' ? `/api/automation/quote/${quoteId}/contract` : null
    });

    wizard.addStep({
        title: 'Gerar Contas a Receber?',
        content: (data) => `
            <div class="text-center mb-4">
                <i class="bi bi-cash-stack" style="font-size: 3rem; color: #28a745;"></i>
            </div>
            <p class="text-center mb-3">Configurar parcelas do recebimento:</p>
            <div class="mb-3">
                <label class="form-label">Número de Parcelas</label>
                <select name="installments" class="form-select bg-dark text-white border-secondary">
                    <option value="1">À vista</option>
                    <option value="2">2x</option>
                    <option value="3">3x</option>
                    <option value="4">4x</option>
                    <option value="6">6x</option>
                    <option value="12">12x</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Primeiro Vencimento</label>
                <input type="date" name="first_due_date" class="form-control bg-dark text-white border-secondary" 
                       value="${new Date(Date.now() + 30*24*60*60*1000).toISOString().split('T')[0]}">
            </div>`,
        endpoint: `/api/automation/quote/${quoteId}/receivables`
    });

    wizard.setData('quote_id', quoteId);
    wizard.start();
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    document.body.appendChild(toast);
    new bootstrap.Toast(toast).show();
    setTimeout(() => toast.remove(), 3000);
}
