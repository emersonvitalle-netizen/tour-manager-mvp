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
        console.log('[Wizard] Starting with', this.steps.length, 'steps');
        this.steps.forEach((s, i) => console.log('[Wizard] Step', i, ':', s.title));
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
        }

        const progressTextEl = document.getElementById('wizardProgressText');
        if (progressTextEl) {
            progressTextEl.textContent = `${this.currentStep + 1}/${this.steps.length}`;
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
        <div class="wizard-overlay" id="${this.modalId}">
            <div class="wizard-modal">
                <div class="wizard-header">
                    <div class="wizard-title" id="wizardTitle"></div>
                    <div class="wizard-progress-text" id="wizardProgressText">1/1</div>
                </div>
                <div class="wizard-progress-bar">
                    <div class="wizard-progress-fill" id="wizardProgress"></div>
                </div>
                <div class="wizard-body" id="wizardBody"></div>
                <div class="wizard-buttons">
                    <button type="button" class="wizard-btn wizard-btn-secondary" id="wizardPrev" style="display: none;">Voltar</button>
                    <button type="button" class="wizard-btn wizard-btn-cancel" id="wizardClose">Cancelar</button>
                    <button type="button" class="wizard-btn wizard-btn-primary" id="wizardNext">Próximo</button>
                </div>
            </div>
        </div>
        <style>
            .wizard-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            .wizard-modal {
                background: linear-gradient(180deg, #1e1e1e 0%, #141414 100%);
                border: 2px solid #d4a574;
                border-radius: 16px;
                padding: 24px;
                width: 90%;
                max-width: 420px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
            .wizard-header {
                text-align: center;
                margin-bottom: 16px;
            }
            .wizard-title {
                font-size: 1.3rem;
                font-weight: 600;
                color: #f5f5f5;
                margin-bottom: 4px;
            }
            .wizard-progress-text {
                font-size: 0.85rem;
                color: #888;
            }
            .wizard-progress-bar {
                height: 4px;
                background: #333;
                border-radius: 2px;
                margin-bottom: 20px;
                overflow: hidden;
            }
            .wizard-progress-fill {
                height: 100%;
                background: #d4a574;
                transition: width 0.3s ease;
            }
            .wizard-body {
                color: #fff;
                min-height: 100px;
            }
            .wizard-body .form-label {
                font-size: 0.85rem;
                color: #aaa;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
                display: block;
            }
            .wizard-body .form-control,
            .wizard-body .form-select {
                background: #0a0a0a;
                border: 1px solid #333;
                border-radius: 8px;
                color: #fff;
                padding: 12px 16px;
                font-size: 1rem;
                width: 100%;
            }
            .wizard-body .form-control:focus,
            .wizard-body .form-select:focus {
                border-color: #d4a574;
                box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.2);
                outline: none;
            }
            .wizard-body .mb-3 {
                margin-bottom: 16px;
            }
            .wizard-buttons {
                display: flex;
                gap: 12px;
                margin-top: 24px;
            }
            .wizard-btn {
                flex: 1;
                padding: 14px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                border: none;
                transition: all 0.2s ease;
            }
            .wizard-btn-primary {
                background: #d4a574;
                color: #000;
            }
            .wizard-btn-primary:hover {
                background: #c49464;
            }
            .wizard-btn-secondary {
                background: #333;
                color: #fff;
            }
            .wizard-btn-secondary:hover {
                background: #444;
            }
            .wizard-btn-cancel {
                background: transparent;
                border: 1px solid #444;
                color: #888;
            }
            .wizard-btn-cancel:hover {
                background: #222;
                color: #fff;
            }
        </style>`;
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
        console.log('[Wizard] _next called, currentStep:', this.currentStep, 'totalSteps:', this.steps.length);

        this._collectFormData();
        console.log('[Wizard] Form data collected:', this.data);

        if (!step.validate(this.data)) {
            console.log('[Wizard] Validation failed');
            return;
        }

        const leaveResult = await step.onLeave(this.data);
        console.log('[Wizard] onLeave result:', leaveResult);
        if (leaveResult === false) {
            console.log('[Wizard] onLeave returned false, stopping');
            return;
        }

        if (step.endpoint) {
            console.log('[Wizard] Calling endpoint:', step.endpoint);
            try {
                const response = await this._callEndpoint(step.endpoint);
                console.log('[Wizard] Endpoint response:', response);
                if (response.success) {
                    this.data = { ...this.data, ...response.data };
                } else {
                    this._showError(response.message || 'Erro ao processar');
                    return;
                }
            } catch (error) {
                console.error('[Wizard] Endpoint error:', error);
                this._showError('Erro de conexão');
                return;
            }
        }

        this.currentStep++;
        console.log('[Wizard] Advanced to step:', this.currentStep, 'of', this.steps.length);
        this._findNextValidStep();
        console.log('[Wizard] After findNextValidStep:', this.currentStep, 'of', this.steps.length);
        console.log('[Wizard] Condition check:', this.currentStep, '>=', this.steps.length, '=', this.currentStep >= this.steps.length);

        if (this.currentStep >= this.steps.length) {
            console.log('[Wizard] Completing wizard - currentStep >= steps.length');
            this._complete();
        } else {
            console.log('[Wizard] Rendering step', this.currentStep, ':', this.steps[this.currentStep]?.title);
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
        const overlay = document.getElementById(this.modalId);
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    _hideModal() {
        const overlay = document.getElementById(this.modalId);
        if (overlay) {
            overlay.remove();
        }
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

// ============================================
// WIZARD: APROVAÇÃO DE ORÇAMENTO (SeparationList)
// ============================================
function startQuoteApprovalWizard(quoteId, quoteName, quoteTotal) {
    const wizard = new WizardController({
        onComplete: (data) => {
            showToast('Fluxo concluído com sucesso!', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    });

    // Step 1: Confirmar aprovação
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

    // Step 2: Gerar Contrato?
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
        onLeave: async (data) => {
            if (data.generate_contract === 'yes') {
                try {
                    const response = await fetch(`/api/automation/quote/${quoteId}/contract`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await response.json();
                    if (result.success && result.data && result.data.contract_id) {
                        sessionStorage.setItem('wizardState', JSON.stringify({
                            quoteId: quoteId,
                            quoteName: quoteName,
                            quoteTotal: quoteTotal,
                            currentStep: 'contas_receber',
                            contractId: result.data.contract_id
                        }));
                        const overlay = document.getElementById('wizardModal');
                        if (overlay) overlay.remove();
                        window.location.href = `/financial/contracts/${result.data.contract_id}?continue_wizard=1`;
                        return false;
                    } else {
                        console.error('Contrato criado mas sem ID:', result);
                    }
                } catch (e) {
                    console.error('Erro ao criar contrato:', e);
                }
            }
            return true;
        }
    });

    // Step 3: Gerar Contas a Receber? (CORRIGIDO)
    console.log('[Debug] Before step 3, steps:', wizard.steps.length);
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
        endpoint: `/api/automation/quote/${quoteId}/receivables`
    });

    // Step 4: Criar Evento Automaticamente
    console.log('[Debug] Before step 4, steps:', wizard.steps.length);
    wizard.addStep({
        title: 'Criar Evento',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-calendar-plus" style="font-size: 3rem; color: #17a2b8;"></i>
            </div>
            <p class="text-center mb-3">Criar evento a partir do orçamento:</p>
            <div class="mb-3">
                <label class="form-label">Nome do Evento</label>
                <input type="text" name="event_name" class="form-control bg-dark text-white border-secondary" 
                       value="${quoteName}" readonly style="background: #1a1a1a;">
            </div>
            <div class="mb-3">
                <label class="form-label">Data do Evento</label>
                <input type="date" name="event_date" class="form-control bg-dark text-white border-secondary"
                       value="${quoteDate || new Date().toISOString().split('T')[0]}">
            </div>
            <div class="text-center mt-4">
                <small class="text-muted">O evento será criado com os equipamentos do orçamento</small>
            </div>`,
        onLeave: async (data) => {
            try {
                const response = await fetch('/api/automation/quote/' + quoteId + '/create-event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: data.event_name || quoteName,
                        start_date: data.event_date
                    })
                });
                const result = await response.json();
                console.log('[Wizard] Create event result:', result);
                if (result.success && result.data && result.data.tour_id) {
                    showToast('Evento criado com sucesso!', 'success');
                    setTimeout(() => {
                        window.location.href = '/tour/' + result.data.tour_id;
                    }, 1000);
                    return false;
                } else {
                    showToast(result.message || 'Erro ao criar evento', 'error');
                }
            } catch (e) {
                console.error('Erro ao criar evento:', e);
                showToast('Erro ao criar evento', 'error');
            }
            return true;
        }
    });
    console.log('[Debug] After step 4, steps:', wizard.steps.length);
    if (wizard.steps.length !== 4) {
        alert('[ERRO] Wizard deveria ter 4 steps, mas tem ' + wizard.steps.length);
    }

    wizard.start({
        quoteId: quoteId,
        quoteName: quoteName
    });
}

// ============================================
// WIZARD: FUNCIONÁRIO CLT - DESPESAS AUTOMÁTICAS (CORRIGIDO)
// ============================================
function startEmployeeWizard(employeeId, employeeName, salary) {
    const salaryNum = parseFloat(salary) || 0;
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
            <p class="text-center text-muted mb-4">Salário: R$ ${formatCurrency(salaryNum)}</p>
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
        endpoint: `/api/automation/employee/${employeeId}/auto-expenses`
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

// ============================================
// WIZARD: FREELANCER - REGISTRAR PAGAMENTO (CORRIGIDO)
// ============================================
function startFreelancerPaymentWizard(freelancerId, freelancerName, eventName, dailyRate) {
    const dailyRateNum = parseFloat(dailyRate) || 0;
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
                <label class="form-label">Valor da Diária</label>
                <input type="number" name="daily_rate" id="dailyRateInput" class="form-control bg-dark text-white border-secondary" 
                       value="${dailyRateNum}" step="0.01" onchange="calculateFreelancerTotal()">
            </div>
            <div class="mb-3">
                <label class="form-label">Quantidade de Diárias</label>
                <input type="number" name="days" id="daysInput" class="form-control bg-dark text-white border-secondary" 
                       value="1" min="1" onchange="calculateFreelancerTotal()">
            </div>
            <div class="mb-3">
                <label class="form-label">Valor Total</label>
                <input type="number" name="value" id="totalValueInput" class="form-control bg-dark text-white border-secondary" 
                       value="${dailyRateNum}" step="0.01" readonly style="background: #2a2a2a !important;">
            </div>
            <div class="mb-3">
                <label class="form-label">Data de Pagamento</label>
                <input type="date" name="payment_date" class="form-control bg-dark text-white border-secondary" 
                       value="${new Date().toISOString().split('T')[0]}">
            </div>`,
        endpoint: `/api/automation/freelancer/${freelancerId}/payable`
    });

    // Step 2: Criar Conta a Pagar? (CORRIGIDO - usa mesmo endpoint)
    wizard.addStep({
        title: 'Criar Conta a Pagar?',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-credit-card" style="font-size: 3rem; color: #ffc107;"></i>
            </div>
            <p class="text-center mb-4">Conta a pagar já foi registrada!</p>
            <div class="alert alert-success text-center">
                <i class="bi bi-check-circle"></i> Pagamento do freelancer criado com sucesso
            </div>`
    });

    wizard.setData('freelancer_id', freelancerId);
    wizard.setData('event_name', eventName);
    wizard.start();
}

// ============================================
// WIZARD: PÓS-APROVAÇÃO (CORRIGIDO)
// ============================================
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

// ============================================
// WIZARD: CRIAR WORKLIST (CORRIGIDO)
// ============================================
function startWorkListWizard(quoteId, quoteName, clientName) {
    const wizard = new WizardController({
        onComplete: (data) => {
            if (data.share_token) {
                const shareUrl = `${window.location.origin}/work-list/share/${data.share_token}`;
                showToast('Lista de Separação criada!', 'success');
                setTimeout(() => {
                    if (confirm(`Lista criada!\n\nDeseja copiar o link de compartilhamento?\n\n${shareUrl}`)) {
                        navigator.clipboard.writeText(shareUrl);
                        showToast('Link copiado!', 'success');
                    }
                    location.reload();
                }, 500);
            } else {
                showToast('Lista de Separação criada!', 'success');
                setTimeout(() => location.reload(), 1500);
            }
        }
    });

    wizard.addStep({
        title: 'Criar Lista de Separação',
        content: () => `
            <div class="text-center mb-4">
                <i class="bi bi-list-check" style="font-size: 3rem; color: #6f42c1;"></i>
            </div>
            <h5 class="text-center mb-2">${quoteName}</h5>
            <p class="text-center text-muted mb-3">Cliente: ${clientName || 'Não informado'}</p>
            <div class="alert alert-info text-center" style="background: #1e3a5f; border-color: #2d5a87; color: #a8d4f7;">
                <i class="bi bi-info-circle"></i>
                Os dados de <strong>data</strong> e <strong>local</strong> do evento serão obtidos automaticamente do orçamento.
            </div>
            <p class="text-center">
                Será criada uma lista com os itens do orçamento (sem valores) 
                para separação física dos equipamentos.
            </p>`,
        endpoint: `/api/automation/quote/${quoteId}/worklist`
    });

    wizard.setData('quote_id', quoteId);
    wizard.start();
}

// ============================================
// FUNÇÕES AUXILIARES
// ============================================
function formatCurrency(value) {
    return parseFloat(value || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function calculateFreelancerTotal() {
    const dailyRate = parseFloat(document.getElementById('dailyRateInput')?.value || 0);
    const days = parseInt(document.getElementById('daysInput')?.value || 1);
    const totalInput = document.getElementById('totalValueInput');
    if (totalInput) {
        totalInput.value = (dailyRate * days).toFixed(2);
    }
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toast.setAttribute('role', 'alert');
    toast.style.zIndex = '10000';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    document.body.appendChild(toast);

    if (typeof bootstrap !== 'undefined') {
        new bootstrap.Toast(toast).show();
    } else {
        toast.style.display = 'block';
    }

    setTimeout(() => toast.remove(), 3000);
}