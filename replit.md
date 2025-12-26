# TOUR Manager - Sistema de Gestão de Equipamentos e Logística

## 📋 VISÃO GERAL

Sistema MVP para empresas de áudio/eventos gerenciarem equipamentos, tours e manutenção. Multi-tenant com autenticação, QR codes e planejamento futuro para RFID/NFC.

**Nome do App:** TOUR  
**Idioma:** Português (BR)  
**Stack:** Flask (Python) + SQLAlchemy + Jinja2 + Bootstrap

---

## 🎨 DIREÇÃO VISUAL (APROVADA)

### Estilo: Dark Cinematográfico Profissional

**Características:**
- 🎬 Fundo preto/dark (#0a0a0a, #1a1a1a)
- ✨ Fotos dramáticas com iluminação dourada/âmbar
- 🎭 Visual premium tipo Netflix/Apple
- 🎪 Atmosfera de shows e eventos profissionais
- 🔤 Tipografia elegante: Serif para títulos, Sans-serif fina para corpo

**Cores:**
- Background: `#0a0a0a` (preto profundo)
- Cards: `#1a1a1a` (dark charcoal)
- Accent: `#d4a574` (dourado quente)
- Text: `#ffffff` (branco)
- Text Secondary: `#a0a0a0` (cinza claro)

**Imagens de Referência:**
- Card HARDCASE: Hardcase aberto com iluminação dourada dramática
- Card TOUR: Palco de show com bateria e luzes quentes

**Fontes:**
- Títulos: Playfair Display (serif elegante)
- Corpo: Inter / Work Sans (sans-serif fina)
- Peso: 300-400 (thin/light)

---

## 🏗️ ARQUITETURA TÉCNICA

### Backend: Flask + SQLAlchemy

**Estrutura de Pastas:**
```
/
├── models/              # Modelos do banco de dados
│   ├── company.py
│   ├── user.py
│   ├── category.py
│   ├── equipment_type.py
│   ├── equipment.py
│   ├── maintenance.py
│   ├── kit.py
│   └── tour.py
├── routes/              # Blueprints (endpoints)
│   ├── auth.py
│   ├── equipment.py
│   ├── company.py
│   ├── kit.py
│   ├── tour.py
│   ├── orcamento.py     # Orçamentos (propostas comerciais)
│   ├── separation.py    # Redirects legados → orcamento
│   ├── work_list.py
│   ├── users.py
│   └── financial.py
├── services/            # Lógica de negócio
│   ├── qr_service.py
│   ├── payment_adapter.py   # Adaptadores PIX/Boleto (Asaas, Manual)
│   └── nfse_adapter.py      # Adaptadores NFSe (Focus NFe, Manual)
├── utils/
│   └── permissions.py       # Decoradores de permissão
├── templates/           # Jinja2 templates
│   ├── auth/
│   ├── equipment/
│   ├── company/
│   ├── kit/
│   ├── tour/
│   ├── orcamento/       # Templates de orçamento (dark theme)
│   ├── users/
│   ├── financial/
│   ├── base.html
│   └── dashboard.html
├── static/              # Assets estáticos
│   ├── css/
│   ├── js/
│   ├── images/
│   ├── qr/             # QR codes gerados
│   └── uploads/        # Fotos de equipamentos
└── main.py              # Entry point
```

---

## 🗄️ BANCO DE DADOS

### Multi-Tenant Architecture

Todas as tabelas possuem `company_id` (Foreign Key) para isolamento de dados.

### Models Implementados:

#### 1. **Company** (Empresas)
```python
- id (PK)
- name
- cnpj
- logo_url
- email, phone, address
- is_active
```

#### 2. **User** (Usuários)
```python
- id (PK)
- email (unique)
- password_hash
- name, phone, photo_url
- role (admin/user)
- company_id (FK)
- is_active
```

#### 3. **Category** (Categorias de Equipamentos)
```python
- id (PK)
- name (Som, Luz, Materiais, Instrumentos)
- company_id (FK)
- is_system (bool - categorias padrão)
```

#### 4. **EquipmentType** (Tipos de Equipamento)
```python
- id (PK)
- name (Mesa de Som, Microfone, etc)
- category_id (FK)
- company_id (FK)
- is_system
```

#### 5. **Equipment** (Equipamentos Individuais)
```python
- id (PK)
- code (unique - ex: MSX32-001)
- name, brand, model, serial_number
- prefix
- category_id, type_id (FK)
- status (available, maintenance, in_repair, in_tour)
- value, purchase_date
- qr_code_url, primary_photo_url
- company_id (FK)
- created_by (FK user)
```

**Campos FUTUROS (RFID/NFC):**
```python
- nfc_tag_id       # UID da tag NFC (14 chars hex)
- rfid_uhf_tag     # EPC da tag RFID UHF (GS1 format)
```

#### 6. **Maintenance** (Manutenção)
```python
- id (PK)
- equipment_id (FK)
- problem_description, solution_description
- status (pending, in_progress, completed)
- cost
- external_company, external_contact
- started_at, completed_at
- started_by, completed_by (FK user)
- company_id (FK)
```

#### 7. **Kit** (Conjuntos Pré-definidos)
```python
- id (PK)
- name, description
- company_id (FK)
- created_by (FK user)
```

**KitRequirement:**
```python
- kit_id (FK)
- equipment_name
- quantity
```

#### 8. **Tour** (Tours/Shows)
```python
- id (PK)
- name, artist, description
- start_date, end_date
- status (planned, active, completed)
- company_id (FK)
- created_by (FK user)
```

**Show:**
```python
- id (PK)
- tour_id (FK)
- date, time, venue, city
- status (scheduled, in_progress, completed)
- responsible_user_id (FK)
```

**TourRequirement:**
```python
- tour_id (FK)
- equipment_name, brand, model
- quantity
- category_id (FK)
```

**TourEquipment:**
```python
- tour_id, equipment_id (FK)
- allocated_at, returned_at
- current_status (in_company, loading_truck, in_transit, etc)
```

**EquipmentCheckpoint:**
```python
- tour_id, equipment_id, show_id (FK)
- checkpoint_type (saida_empresa, chegada_show, etc)
- timestamp, location, condition
- scanned_by (FK user)
```

---

## 🔐 AUTENTICAÇÃO

**Sistema:** Flask-Login + Flask-Bcrypt

**Roles:**
- `admin` - Pode criar/editar equipamentos, tours, kits
- `user` - Pode visualizar e escanear equipamentos

**Fluxo de Registro:**
1. Usuário cria conta
2. Sistema cria nova Company automaticamente
3. Usuário vira `admin` da empresa
4. Categorias e tipos padrão são criados

**Categorias Padrão:**
- 🎤 Som: Mesa de Som, Microfone, Caixa Ativa, Processador
- 💡 Luz: PAR LED, Moving Head, Projetor, Mesa de Luz
- 🔧 Materiais: Cabo XLR, Cabo P10, Case, Estante
- 🎸 Instrumentos: Guitarra, Baixo, Teclado, Bateria

---

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### Gestão de Equipamentos (HARDCASE)
- ✅ CRUD completo de equipamentos
- ✅ Geração automática de códigos (Prefixo + Contador)
- ✅ Upload de fotos
- ✅ Geração de QR Codes (biblioteca `qrcode`)
- ✅ Impressão em lote de QR Codes
- ✅ Scanner de QR Code (via câmera)
- ✅ Categorização hierárquica (Categoria → Tipo → Equipamento)
- ✅ Contador (Total/Disponível) - exclui status: maintenance, in_repair, in_tour

### Manutenção
- ✅ Enviar para manutenção (status: `maintenance`)
- ✅ Encaminhar para externa (status: `in_repair`)
- ✅ Registrar problema, solução, custo
- ✅ Histórico de manutenções

### Kits (Conjuntos Pré-definidos)
- ✅ Criar kits com requisitos
- ✅ Listar e visualizar kits
- ✅ Deletar (soft delete)

### Tours e Shows
- ✅ Criar tours com artista, datas
- ✅ Adicionar shows à tour
- ✅ Definir requisitos de equipamento
- ✅ Scanear e alocar equipamentos
- ✅ Sistema de checkpoints (saída empresa, chegada show, etc)
- ✅ Finalizar tour (libera equipamentos)

### Configurações
- ✅ Editar dados da empresa
- ✅ Upload de logo da empresa

---

## 🚧 FUNCIONALIDADES PLANEJADAS (NÃO IMPLEMENTADAS)

### RFID/NFC (Especificação Completa)

**Tecnologias:**
1. **QR Code** - Visual, impressão (R$ 0,05/etiqueta) ✅ IMPLEMENTADO
2. **NFC** - Celular Android/iOS (R$ 1-3/tag) ❌ PENDENTE
3. **RFID UHF** - Leitura em massa (R$ 2-5/tag + leitor R$ 1.500-15.000) ❌ PENDENTE

**Endpoints a Implementar:**
```
POST /api/rfid/scan              # Leitura RFID industrial (portal/pistola)
POST /api/rfid/nfc-scan          # Leitura NFC via celular
GET  /api/rfid/reader-status     # Status dos leitores RFID
```

**Templates a Criar:**
- `templates/equipment/scanner_nfc.html`
- `templates/equipment/scanner_rfid.html`

**Services a Criar:**
- `services/rfid_service.py` (geração de EPC codes)
- `services/nfc_service.py`

---

## 📱 DESIGN MOBILE-FIRST

### Estrutura de Navegação

**Dashboard → Cards:**
1. **HARDCASE** (Gestão de Equipamentos)
   - Categorias (grid 2x2)
   - Lista de equipamentos
   - Detalhes + QR Code

2. **TOUR** (Logística e Shows)
   - Kits
   - Tours Ativas
   - Agenda
   - Checkpoints
   - Logística

**Bottom Navigation:**
- 🏠 Início
- 🔔 Alertas
- 📊 Relatórios
- ⚙️ Config

**FAB (Floating Action Button):**
- 📷 Scanner (QR/NFC/RFID)

### Breakpoints Responsivos
```css
Mobile:  max-width: 480px
Tablet:  min-width: 768px
Desktop: min-width: 1024px
```

---

## 🎯 PROGRESSO ATUAL (Dezembro 2025)

### Concluído ✅
- [x] Estrutura backend Flask completa
- [x] 14+ models implementados
- [x] Sistema multi-tenant funcionando
- [x] Autenticação + roles
- [x] CRUD de equipamentos
- [x] QR Code geração e scanner
- [x] Sistema de Tours e Checkpoints
- [x] Upload de fotos
- [x] **Redesign Dark Cinematográfico**
  - [x] CSS dark theme completo
  - [x] Dashboard com cards fotográficos
  - [x] Bottom navigation mobile
  - [x] Templates mobile-first
  - [x] Login redesenhado
  - [x] Paleta de cores dark premium
  - [x] Tipografia elegante (Playfair Display + Inter)
- [x] **Sistema de Controle de Acesso (3 níveis)**
  - [x] Admin: acesso total + financeiro + preços
  - [x] Técnico Responsável: equipamentos + separação + manutenção (sem preços)
  - [x] Técnico Tour: acesso temporário via QR Code com expiração
  - [x] Model TourAccess para QR temporário
  - [x] Rotas /users/ para gestão (admin only)
  - [x] Preços ocultos de não-admins nos templates
- [x] **Módulo Financeiro Brasileiro**
  - [x] Models: Quote, QuoteItem, Contract, Invoice, Payment
  - [x] Adaptador de pagamento multi-provedor (Asaas, Manual)
  - [x] Adaptador de NFSe multi-provedor (Focus NFe, Manual)
  - [x] Dashboard financeiro
  - [x] CRUD de Orçamentos com itens e descontos
  - [x] CRUD de Faturas com registro de pagamentos
  - [x] Códigos únicos por empresa (ORC-{company}-{ano}-{seq})
  - [x] **Contas a Pagar expandido:**
    - [x] Suporte a categoria "Outros" customizada
    - [x] Forma de pagamento (PIX, Boleto, Transferencia, etc)
    - [x] Parcelamento automático (cria N parcelas)
    - [x] Badges visuais de parcelas (ex: 2/6)
  - [x] **Contas a Receber (NOVO):**
    - [x] CRUD completo com filtros por status
    - [x] Suporte a parcelamento automático
    - [x] Integração com cadastro de clientes
    - [x] KPIs: Vencidas, Próx. 7 dias, Este mês
  - [x] **Cadastro de Clientes (NOVO):**
    - [x] CRUD completo
    - [x] Busca por nome no frontend
    - [x] CPF/CNPJ, contato, endereço
  - [x] **DRE com dados reais:**
    - [x] Receitas recebidas e pendentes do mês
    - [x] Despesas: Folha, Contas, Freelancers
    - [x] Cálculo automático de lucro

### Próximas Etapas 📋
1. Implementar contratos (templates e rotas)
2. Integrar provedores de pagamento (Asaas, PagSeguro)
3. Integrar provedores de NFSe (Focus NFe, Enotas)
4. Adicionar campos NFC/RFID ao banco
5. Criar API endpoints RFID/NFC
6. Implementar scanners NFC/RFID
7. Dashboard de relatórios financeiros

---

## 🔧 SETUP E EXECUÇÃO

### Dependências (requirements.txt)
```
Flask
Flask-Bcrypt
Flask-Login
Flask-SQLAlchemy
Flask-Migrate
Pillow
python-dotenv
qrcode
sqlalchemy
```

### Executar Projeto
```bash
python main.py
```

### Porta
```
http://0.0.0.0:5000
```

### Banco de Dados
SQLite: `instance/tour_manager.db`

---

## 📝 NOTAS IMPORTANTES

### Convenções de Código
- **Formato de contador:** `(Total/Disponível)`
- **Status excluídos do contador "Disponível":** `maintenance`, `in_repair`, `in_tour`
- **Códigos de equipamento:** `PREFIXO-NNN` (ex: MSX32-001, CAI-015)
- **Emojis:** Apenas em badges de status e categorias, **não** em nomes de equipamentos
- **Idioma:** Português em toda a UI

### Preferências do Usuário
- Visual dark premium (tipo Netflix/shows)
- Mobile-first approach
- Fotos dramáticas com iluminação dourada
- Tipografia elegante (serif + sans fina)
- Sem infantilização do design
- Profissional e sério

### Tecnologias Futuras
- App mobile nativo (React Native / Flutter)
- Web NFC API (Chrome Android)
- Integração com leitores RFID industriais (Zebra, Impinj)
- Dashboard de monitoramento em tempo real
- Relatórios de eficiência de leitura

---

## 🎬 REFERÊNCIAS VISUAIS

**Cards do Dashboard:**
- HARDCASE: Hardcase profissional aberto, iluminação dourada lateral, fundo preto
- TOUR: Palco de show com bateria, luzes quentes, atmosfera de concert hall

**Paleta de Cores:**
```
#0a0a0a - Background principal
#1a1a1a - Cards e containers
#d4a574 - Accent dourado
#ffffff - Texto principal
#a0a0a0 - Texto secundário
#2a2a2a - Bordas sutis
```

---

**Última Atualização:** Janeiro 2025  
**Status:** MVP em produção, redesign visual em andamento
