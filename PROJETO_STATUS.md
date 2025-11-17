Vou criar o documento completo de estado do projeto agora.

-----

## CRIAR ARQUIVO: `PROJETO_STATUS.md`

Na raiz do projeto (mesma pasta do main.py) → **“New file”** → nome: `PROJETO_STATUS.md`

Cole este conteúdo **COMPLETO**:

```markdown
# TOUR MANAGER MVP - STATUS DO PROJETO
**Última atualização:** 02/10/2025  
**Versão:** 0.1.0 - Hardcase MVP 95% completo

---

## VISÃO GERAL DO SISTEMA

O Tour Manager é um sistema completo para gestão de equipamentos, turnês e manutenção de empresas de áudio/eventos.

### Módulos Planejados (4 no total):
1. **HARDCASE** - Gestão de patrimônio/inventário (95% completo)
2. **TOUR** - Gestão de turnês e shows (0% - não iniciado)
3. **MANUTENÇÃO** - Ordens de serviço (0% - não iniciado)
4. **RELATÓRIOS** - Analytics e custos (0% - não iniciado)

---

## MÓDULO HARDCASE - STATUS ATUAL

### Funcionalidades Implementadas ✅

#### Autenticação
- [x] Registro de usuário com criação automática de empresa
- [x] Login/Logout com sessão persistente (Flask-Login)
- [x] Hash de senhas com BCrypt
- [x] User loader configurado
- [x] Proteção de rotas com @login_required
- [x] Controle de permissões (role: admin/user)

#### Gestão de Equipamentos
- [x] Cadastro individual de equipamento
- [x] Cadastro em lote (múltiplos equipamentos de uma vez)
- [x] Geração automática de códigos sequenciais (ex: EV-001, EV-002)
- [x] Geração automática de prefixos a partir do nome
- [x] Prefixos customizados opcionais
- [x] Campos completos: nome, marca, modelo, número de série, observações
- [x] Upload de foto principal do equipamento
- [x] Geração de QR Code único por equipamento (formato JSON)
- [x] Listagem de equipamentos com filtros por empresa
- [x] Página de detalhes completa de cada equipamento
- [x] Status visual: Disponível / Manutenção / Em Tour
- [x] Separação multi-tenant (por empresa)

#### Categorias
- [x] 9 categorias padrão criadas automaticamente no registro
- [x] Criação de categorias customizadas via formulário
- [x] Campo "Outros" que abre input para nova categoria
- [x] Categorias vinculadas por empresa

#### Interface
- [x] Templates HTML responsivos
- [x] Design limpo e funcional
- [x] Alertas de sucesso/erro (Flash messages)
- [x] Branding "Hardcase" com emoji 🧳
- [x] Dashboard com cards de acesso rápido

### Funcionalidades Pendentes ⏳

- [ ] Editar equipamento (formulário de edição)
- [ ] Botão "Enviar para Manutenção" funcional (mudar status)
- [ ] Histórico de movimentações do equipamento
- [ ] Deletar equipamento (soft delete)
- [ ] Filtros avançados na listagem
- [ ] Busca por código/nome
- [ ] Exportar relatório PDF/Excel
- [ ] Upload de múltiplas fotos (galeria)

---

## ESTRUTURA DO BANCO DE DADOS

### Tabelas Implementadas

#### `company`
```python
- id (PK)
- name
- cnpj
- logo_url
- created_at
- is_active
```

#### `user`

```python
- id (PK)
- email (unique)
- password_hash
- name
- phone
- photo_url
- role (admin/user)
- company_id (FK)
- created_at
- last_login
- is_active
```

#### `category`

```python
- id (PK)
- name
- company_id (FK)
- is_system (bool - se é categoria padrão)
- created_at
- is_active
- CONSTRAINT: unique(name, company_id)
```

#### `equipment`

```python
- id (PK)
- name
- code (unique)
- prefix
- category_id (FK)
- status (available/maintenance/in_tour)
- brand
- model
- serial_number
- value
- purchase_date
- notes
- qr_code_url
- primary_photo_url
- company_id (FK)
- created_by (FK user)
- created_at
- updated_at
- is_active
```

### Relacionamentos

- Company → Users (1:N)
- Company → Categories (1:N)
- Company → Equipment (1:N)
- Category → Equipment (1:N)
- User → Equipment (1:N) [created_by]

-----

## ESTRUTURA DE ARQUIVOS

```
tour-manager-mvp/
├── main.py                 # App Flask principal
├── config.py               # Configurações (DB, Secret Key)
├── requirements.txt        # Dependências pip
├── pyproject.toml         # Dependências Poetry (Replit)
├── instance/
│   └── tour_manager.db    # Banco SQLite
├── static/
│   ├── uploads/           # Fotos dos equipamentos
│   └── qr/                # QR Codes gerados
├── templates/
│   ├── base.html          # Template base
│   ├── dashboard.html     # Dashboard principal
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   └── equipment/
│       ├── list.html      # Lista de equipamentos
│       ├── new.html       # Formulário de cadastro
│       └── detail.html    # Detalhes do equipamento
├── models/
│   ├── __init__.py
│   ├── company.py
│   ├── user.py
│   ├── category.py
│   └── equipment.py
├── routes/
│   ├── __init__.py
│   ├── auth.py            # Rotas de autenticação
│   └── equipment.py       # Rotas de equipamentos
├── services/
│   ├── __init__.py
│   └── qr_service.py      # Geração de QR Code
└── utils/
    ├── __init__.py
    └── auth_helpers.py    # Decorators de auth
```

-----

## ROTAS IMPLEMENTADAS

### Autenticação (`/auth`)

- `GET/POST /auth/register` - Registro de novo usuário
- `GET/POST /auth/login` - Login
- `GET /auth/logout` - Logout

### Equipamentos (`/equipment`)

- `GET /equipment/` - Listagem de equipamentos
- `GET /equipment/<id>` - Detalhes do equipamento
- `GET/POST /equipment/new` - Cadastro novo equipamento
- `POST /equipment/<id>/upload-photo` - Upload de foto
- `POST /equipment/<id>/generate-qr` - Gerar QR Code

### Outras

- `GET /` - Redireciona para login ou dashboard
- `GET /dashboard` - Dashboard principal

-----

## DEPENDÊNCIAS (requirements.txt)

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Bcrypt==1.0.1
python-dotenv==1.0.0
qrcode==7.4.2
Pillow==10.1.0
```

-----

## CATEGORIAS PADRÃO

Criadas automaticamente no primeiro registro:

1. PA System
1. FOH
1. Monitor
1. Microfones
1. Cabos
1. Estrutura
1. Iluminação
1. Instrumentos
1. Outros

-----

## FORMATO DO QR CODE

Cada equipamento tem um QR Code único em JSON:

```json
{
  "v": "1.0",
  "t": "equipment",
  "i": 123,
  "c": "EV-001",
  "co": 1
}
```

- `v`: versão do formato
- `t`: tipo (equipment)
- `i`: ID do equipamento
- `c`: código do equipamento
- `co`: ID da empresa

-----

## DECISÕES DE DESIGN IMPORTANTES

### Multi-tenant

- Cada empresa tem dados isolados
- Filtros por `company_id` em todas as queries
- Usuário só vê dados da própria empresa

### Códigos de Equipamento

- Formato: `PREFIXO-NNN` (ex: EV-001)
- Prefixo gerado automaticamente das iniciais do nome
- Sequencial por prefixo
- Único por empresa

### Permissões

- **Admin**: pode criar, editar, deletar, gerar QR, upload foto
- **User**: apenas visualizar (futuro: adicionar permissões granulares)

### Uploads

- Fotos: `/static/uploads/`
- QR Codes: `/static/qr/`
- Nome do arquivo: `{codigo}_{nome_original}`

-----

## PRÓXIMOS PASSOS PRIORIZADOS

### Curto Prazo (Completar Hardcase)

1. Implementar edição de equipamento
1. Funcionalidade “Enviar para Manutenção”
1. Sistema de histórico básico

### Médio Prazo (Módulo Tour)

1. Model de Tour (turnê)
1. Model de Show (paradas da turnê)
1. Relacionamento Tour ↔ Equipment
1. Checklists progressivos
1. Stage plot básico

### Longo Prazo

1. Módulo de Manutenção
1. Módulo de Relatórios
1. Dashboard com métricas
1. Exportação de dados

-----

## COMANDOS ÚTEIS

### Rodar o projeto

```bash
python main.py
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Criar backup do banco

```bash
cp instance/tour_manager.db instance/backup_$(date +%Y%m%d).db
```

-----

## NOTAS TÉCNICAS

- SQLite usado para MVP (migrar para PostgreSQL em produção)
- Flask debug=True apenas em desenvolvimento
- Secret key deve vir de variável de ambiente em produção
- QR Codes regeneráveis a qualquer momento
- Soft delete implementado (`is_active` flag)

-----

## PARA CONTINUAR EM NOVA CONVERSA

Compartilhe este arquivo com a mensagem:

“Estou desenvolvendo o Tour Manager MVP. Aqui está o arquivo PROJETO_STATUS.md com todo o contexto do projeto. Quero continuar de onde parei.”

E indique o que deseja fazer:

- Completar funcionalidade X
- Iniciar módulo Y
- Corrigir bug Z

```
---

Salve este arquivo e você terá documentação completa para retomar em qualquer momento. Quer fazer mais alguma coisa ou pausamos por aqui?​​​​​​​​​​​​​​​​
```
Abra o arquivo **`PROJETO_STATUS.md`**

Procure a seção que começa com:

```markdown
## MÓDULO KITS - PLANEJADO (NÃO INICIADO)
```

**APAGUE toda essa seção** e **SUBSTITUA** por este conteúdo completo:

```markdown
---

## MÓDULO KITS - PLANEJADO (NÃO INICIADO)

### Conceito
Kits são agrupamentos customizáveis de **tipos/categorias** de equipamentos criados pelo usuário, não de unidades específicas. O kit define requisitos (tipos e quantidades), mas não equipamentos fixos.

**Importante:** Não existem kits pré-configurados. Cada empresa monta seus próprios kits conforme necessidade.

### Diferença Fundamental: Requisitos vs Unidades Específicas

#### Kit define (Requisitos):
- 1x Projetor (qualquer projetor disponível)
- 1x Cabo HDMI 10m (qualquer cabo disponível)
- 2x Caixa Ativa (quaisquer 2 caixas disponíveis)
- 1x Mixer 4 canais (qualquer mixer 4ch disponível)
- 2x Microfone (quaisquer 2 microfones disponíveis)

#### Na expedição/tour, usuário seleciona unidades específicas:
- PROJ-010 (poderia ser PROJ-002 ou outro)
- HDMI-003 (poderia ser HDMI-001 ou outro)
- EV-002 e EV-014 (poderia ser EV-008 e EV-021)
- MIX-003 (poderia ser MIX-001 ou outro)
- MIC-001 e MIC-007 (poderia ser outros 2 microfones)

**Ordem não importa**, apenas que os requisitos sejam atendidos.

### Exemplo Prático
**Kit "Projeção Básica"**
- Requisitos: 1 projetor, 2 caixas, 1 mixer, 2 microfones, 1 cabo HDMI
- Tour 1 levou: PROJ-010, EV-002, EV-014, MIX-003, MIC-001, MIC-007, HDMI-003
- Tour 2 levou: PROJ-002, EV-008, EV-021, MIX-001, MIC-005, MIC-012, HDMI-001

Mesmo kit, equipamentos diferentes.

### Tabelas Necessárias

#### `kit`
```python
- id (PK)
- name
- description
- company_id (FK)
- created_by (FK user)
- created_at
- updated_at
- is_active
```

#### `kit_requirement` (não kit_item)

```python
- id (PK)
- kit_id (FK)
- category_id (FK) # qual tipo de equipamento
- quantity # quantos desse tipo
- specifications (TEXT/JSON opcional) # ex: "4 canais", "10 metros"
- notes (TEXT opcional)
```

### Funcionalidades Planejadas

#### CRUD Básico

- [ ] Criar kit (nome + descrição)
- [ ] Adicionar requisitos ao kit (categoria + quantidade + specs opcionais)
- [ ] Editar requisitos do kit
- [ ] Remover requisitos do kit
- [ ] Listar todos os kits da empresa
- [ ] Ver detalhes do kit (todos os requisitos)
- [ ] Clonar kit existente
- [ ] Deletar kit (soft delete)

#### Validação de Disponibilidade (CRÍTICO)

- [ ] **Validação em tempo real antes de criar/clonar kit:**
  - Calcular quantos equipamentos de cada categoria estão disponíveis
  - Calcular quantos já estão alocados (em tours, outros kits em uso)
  - Calcular quantos estão em manutenção
  - **Bloquear criação** se não houver estoque suficiente
  - Mostrar mensagem detalhada: “Precisa X, disponível Y, faltam Z”
  - Indicar onde estão os equipamentos indisponíveis:
    - “6 em manutenção”
    - “4 em tour”
    - “3 em outros kits ativos”

#### Exemplo de Validação:

```
Cliente tenta criar 5º Kit de Projeção

⚠️ Não é possível montar mais kits deste tipo

Equipamentos insuficientes:
❌ Cabo HDMI 10m: precisa 5, disponível 3 (faltam 2)
   └─ 2 em tour "Festival Rock 2025"

❌ Caixa Ativa: precisa 10, disponível 6 (faltam 4)
   └─ 6 em manutenção
   └─ 4 em tour "Show Acústico"

✅ Projetor: precisa 5, disponível 5 ✓
✅ Mixer 4 canais: precisa 5, disponível 8 ✓
✅ Microfone: precisa 10, disponível 15 ✓
```

#### Integração com Tours/Checklist

- [ ] Selecionar kit na criação de tour/checklist
- [ ] Sistema lista requisitos do kit
- [ ] Sistema sugere equipamentos disponíveis que atendem cada requisito
- [ ] Usuário seleciona manualmente quais unidades específicas levar
- [ ] Sistema valida se as escolhas atendem os requisitos do kit
- [ ] Permitir substituições (ex: trocar EV-002 por EV-008)

### Regras de Negócio

1. Kit define **requisitos** (tipo + quantidade), não unidades específicas
1. Na expedição, usuário escolhe **quais unidades** de cada tipo
1. Ordem dos equipamentos não importa, apenas atender requisitos
1. Um equipamento pode ser usado em múltiplas tours (em momentos diferentes)
1. Sistema calcula disponibilidade em tempo real considerando:

- Equipamentos disponíveis (status = available)
- Equipamentos em tour (status = in_tour)
- Equipamentos em manutenção (status = maintenance)
- Equipamentos já alocados em outros kits ativos

1. **Bloqueia criação de kit** se não houver equipamentos suficientes disponíveis
1. Mostra detalhamento de onde estão os equipamentos indisponíveis
1. Kit não tem QR Code próprio (apenas equipamentos individuais têm)
1. Apenas admins podem criar/editar kits
1. Usuários comuns podem visualizar kits da empresa
1. Sistema pode sugerir equipamentos disponíveis baseado nos requisitos
1. Validação acontece ANTES de criar/clonar kit (não depois)

### Fluxo de Uso: Criação de Kit

1. Admin clica “Criar Kit”
1. Preenche nome e descrição
1. Adiciona requisitos:

- Categoria: Projetor, Quantidade: 1
- Categoria: Caixa Ativa, Quantidade: 2
- Categoria: Mixer, Quantidade: 1, Specs: “4 canais”

1. **Sistema valida disponibilidade em tempo real**
1. Se OK: Kit criado ✓
1. Se faltar equipamento: Mostra erro detalhado e bloqueia

### Fluxo de Uso: Usar Kit em Tour

1. Usuário cria nova tour/checklist
1. Seleciona kit “Projeção Básica”
1. Sistema mostra requisitos:

- 1x Projetor
- 2x Caixa Ativa
- 1x Mixer 4ch

1. Sistema sugere equipamentos disponíveis para cada requisito
1. Usuário seleciona unidades específicas:

- Projetor: PROJ-010
- Caixas: EV-002, EV-014
- Mixer: MIX-003

1. Sistema valida e confirma
1. Status dos equipamentos muda para “in_tour”

### Integração com Outros Módulos

- **Hardcase:**
  - Buscar equipamentos por categoria para sugestões
  - Verificar status e disponibilidade
- **Tour/Checklist:**
  - Selecionar kit → listar requisitos → escolher unidades
  - Marcar equipamentos como “in_tour”
- **Manutenção:**
  - Equipamentos em manutenção não aparecem como disponíveis para kits
- **Relatórios:**
  - Kits mais usados
  - Custo médio por kit
  - Taxa de utilização de kits

### Queries SQL Importantes

```sql
-- Verificar disponibilidade para criar kit
SELECT c.name, 
       COUNT(*) as total,
       SUM(CASE WHEN e.status = 'available' THEN 1 ELSE 0 END) as disponivel,
       SUM(CASE WHEN e.status = 'in_tour' THEN 1 ELSE 0 END) as em_tour,
       SUM(CASE WHEN e.status = 'maintenance' THEN 1 ELSE 0 END) as em_manutencao
FROM equipment e
JOIN category c ON e.category_id = c.id
WHERE e.company_id = ? AND e.is_active = true
GROUP BY c.id, c.name;
```

-----

```
