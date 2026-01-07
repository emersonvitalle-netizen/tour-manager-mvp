# TOUR Manager - Sistema de Gestão de Equipamentos e Logística

## Overview

TOUR Manager is an MVP system designed for audio and event companies to manage equipment, tours, and maintenance. It supports multi-tenancy with authentication, QR codes, and has future plans for RFID/NFC integration. The project aims to provide a professional, dark cinematic user experience, akin to Netflix or Apple, emphasizing premium visuals and efficient logistics management for professional events.

## User Preferences

- Visual dark premium (type Netflix/shows)
- Mobile-first approach
- Dramatic photos with golden lighting
- Elegant typography (serif + fine sans)
- No infantilization of design
- Professional and serious
- I prefer the AI to maintain the project's established design aesthetic and communication style.
- The AI should prioritize implementing planned features before suggesting new ones.
- I want iterative development with clear explanations for each step.
- Ask before making major architectural changes.

## System Architecture

The system is built using a Flask (Python) backend with SQLAlchemy for ORM and Jinja2 for templating, styled with Bootstrap. It follows a multi-tenant architecture where all database tables include a `company_id` for data isolation.

### Visual Design

-   **Style:** Dark Cinematic Professional
    -   **Background:** `#0a0a0a` (deep black)
    -   **Cards:** `#1a1a1a` (dark charcoal)
    -   **Accent:** `#d4a574` (warm golden)
    -   **Text:** `#ffffff` (white), `#a0a0a0` (light gray for secondary)
-   **Typography:** Playfair Display (serif for titles), Inter / Work Sans (thin sans-serif for body)
-   **Imagery:** Dramatic photos with golden/amber lighting, premium aesthetic.
-   **Mobile-First:** Responsive design with specific breakpoints for mobile, tablet, and desktop, featuring a dashboard with photographic cards, bottom navigation, and a Floating Action Button (FAB) for scanning.

### Technical Implementation

-   **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-Bcrypt.
-   **Database:** SQLite for development (`instance/tour_manager.db`), with a multi-tenant design using `company_id`.
-   **Core Modules:**
    -   **Equipment Management (HARDCASE):** CRUD, automatic code generation, photo uploads, QR code generation and batch printing, QR code scanner, hierarchical categorization (Category → Type → Equipment), and availability tracking.
    -   **Maintenance:** Workflow for sending equipment for maintenance/repair, tracking problems, solutions, costs, and history.
    -   **Kits:** Creation and management of pre-defined equipment kits.
    -   **Tours & Shows:** Creation of tours with associated shows, equipment requirements, allocation, and checkpoint system for tracking equipment movement.
    -   **Financial Module:** Comprehensive financial management including Quotes, Contracts, Invoices, Payments, Accounts Payable/Receivable, Client management, and a DRE (Income Statement).
    -   **User Management:** Role-based access control (`admin`, `user`, `technical responsible`, `tour technical`).
-   **Functionalities:**
    -   Multi-tenant system with automatic company and user registration.
    -   Authentication with roles.
    -   Complete equipment lifecycle management.
    -   QR Code generation and scanning.
    -   Tour and checkpoint system.
    -   Comprehensive financial features with multi-provider payment and NFSe adapters.
    -   Access control with varying permission levels, including temporary access for tour technicians.

## External Dependencies

-   **Python Libraries:**
    -   Flask
    -   Flask-Bcrypt
    -   Flask-Login
    -   Flask-SQLAlchemy
    -   Flask-Migrate
    -   Pillow (for image processing)
    -   python-dotenv
    -   qrcode (for QR code generation)
    -   sqlalchemy
-   **Frontend Libraries:**
    -   Bootstrap (for styling)
    -   Chart.js (for visual reports)
-   **Payment Gateways (Planned Integration):**
    -   Asaas
    -   PagSeguro
-   **NFSe Providers (Planned Integration):**
    -   Focus NFe
    -   Enotas
-   **Future Hardware Integrations:**
    -   NFC (mobile devices)
    -   RFID UHF (industrial readers like Zebra, Impinj)

## File Structure (Updated Dec/2025)

### Models (18 files)
- `__int__.py`, `category.py`, `commercial.py`, `company.py`
- `equipment.py`, `equipment_model.py` (shared photos by brand/model)
- `equipment_type.py`, `fabrication.py`, `financial.py`
- `financial_expanded.py` (ContaPagar, ContaReceber, Cliente)
- `kit.py`, `maintenance.py`, `material_stock.py`
- `rh.py` (Employee, Freelancer, Payroll)
- `separation_list.py`, `tour.py`, `user.py`, `work_list.py`

### Routes (18 blueprints)
- `auth.py`, `equipment.py`, `company.py`, `kit.py`, `tour.py`
- `financial.py` (complete financial module)
- `rh.py` (HR management)
- `maintenance.py` (+ fabrication + stock)
- `orcamento.py`, `separation.py`, `work_list.py`, `users.py`
- `leads.py` (commercial pipeline)
- `relatorios.py` (Chart.js reports)
- `scanner.py` (QR/NFC/RFID)
- `api_rfid.py`, `automation_api.py`

### Templates (90+ files)
- `auth/` - login, register, invite_*
- `equipment/` - CRUD, scan, print_qr, models
- `financial/` - 20+ templates (DRE, accounts, clients, etc)
- `maintenance/` - index, fabrication, stock, reports
- `rh/` - employees, freelancers, payroll
- `tour/` - 12 templates (checklist, checkpoint, etc)
- `scanner/` - qr, nfc, rfid, rfid_batch_associate
- `orcamento/`, `leads/`, `users/`, `kit/`, `work_list/`

## Recent Changes (Jan/2026)

- **Contas a Pagar - Pastas Mensais Dinâmicas:**
  - Pastas colapsáveis por mês usando padrão HARDCASE (toggleFolder)
  - Meses vencidos aparecem com efeito "breathing" vermelho (animação sutil)
  - Badge "Vencida" em pastas com contas atrasadas
  - Suporte a múltiplos meses vencidos simultâneos (Jan, Fev, Mar...)
  - Transição automática para Repositório quando mês é 100% pago
  - KPIs sincronizados com dados visíveis (derivados do mesmo dataset)
  - Helper classify_folder_state() para estados: on_track, overdue, archivable
- Centro de Custos ativado em Contas a Pagar (CostCenter model + select dropdown)
- Novo relatório de Custo Total por Funcionário (/rh/relatorio/custo-funcionario) com:
  - Salário base, INSS patronal (20%), FGTS (8%)
  - Provisões mensais de férias e 13º
  - Benefícios (VT, VA, VR, plano saúde)
  - Custo total mensal e anual por funcionário
- Cálculo de rescisão completo com multa FGTS 40% (sem justa causa) e 20% (acordo mútuo)

## Recent Changes (Dec/2025)

- Equipment photos shared automatically by brand+model (EquipmentModel)
- Maintenance costs integrated with DRE using Decimal precision
- Equipment history showing last 30 uses via TourEquipment + Show + Tour
- Batch registration generates sequential codes (CAI-001, CAI-002...)
- Wizard popups for maintenance workflows