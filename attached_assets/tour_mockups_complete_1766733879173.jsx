import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const TourManagerMockups = () => {
  const [currentScreen, setCurrentScreen] = useState('menu');
  const [viewMode, setViewMode] = useState('mobile');

  // Dados para gráficos
  const fluxoCaixaData = [
    { mes: 'Jan', receitas: 45000, despesas: 32000 },
    { mes: 'Fev', receitas: 52000, despesas: 35000 },
    { mes: 'Mar', receitas: 48000, despesas: 33000 },
    { mes: 'Abr', receitas: 61000, despesas: 38000 },
    { mes: 'Mai', receitas: 55000, despesas: 36000 },
    { mes: 'Jun', receitas: 58000, despesas: 37000 },
  ];

  const containerClass = viewMode === 'mobile' 
    ? 'max-w-md mx-auto bg-gray-900 min-h-screen' 
    : 'max-w-7xl mx-auto bg-gray-900 min-h-screen p-6';

  // MENU PRINCIPAL
  const MenuPrincipal = () => (
    <div className={containerClass}>
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">TOUR Manager - Mockups</h1>
          <div className="flex gap-2">
            <button 
              onClick={() => setViewMode('mobile')}
              className={`px-3 py-1 rounded text-xs ${viewMode === 'mobile' ? 'bg-amber-600' : 'bg-gray-700'} text-white`}
            >
              📱 Mobile
            </button>
            <button 
              onClick={() => setViewMode('desktop')}
              className={`px-3 py-1 rounded text-xs ${viewMode === 'desktop' ? 'bg-amber-600' : 'bg-gray-700'} text-white`}
            >
              💻 Desktop
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { id: 'dash-financeiro', icon: '💰', title: 'Dashboard Financeiro', sub: 'KPIs e gráficos' },
            { id: 'receitas', icon: '📊', title: 'Receitas', sub: 'NFSe e faturas' },
            { id: 'despesas', icon: '💸', title: 'Despesas', sub: 'Visão geral' },
            { id: 'folha-clt', icon: '👔', title: 'Folha CLT', sub: 'Funcionários' },
            { id: 'freelancers', icon: '🎯', title: 'Freelancers', sub: 'Pagamentos PJ' },
            { id: 'contas-pagar', icon: '📋', title: 'Contas a Pagar', sub: 'Fixas e variáveis' },
            { id: 'emitir-nfse', icon: '📄', title: 'Emitir NFSe', sub: 'Nota fiscal' },
            { id: 'gerar-pix', icon: '💳', title: 'Gerar PIX', sub: 'QR Code' },
            { id: 'dash-comercial', icon: '🎯', title: 'Dashboard Comercial', sub: 'Funil vendas' },
            { id: 'leads-kanban', icon: '📌', title: 'Leads Kanban', sub: 'Gestão visual' },
            { id: 'lead-form', icon: '📝', title: 'Cadastro Lead', sub: 'Novo cliente' },
            { id: 'dash-rh', icon: '👥', title: 'Dashboard RH', sub: 'Ranking' },
            { id: 'funcionarios', icon: '👔', title: 'Funcionários', sub: 'Lista CLT/PJ' },
            { id: 'cadastro-clt', icon: '➕', title: 'Novo CLT', sub: 'Funcionário' },
            { id: 'cadastro-freelancer', icon: '➕', title: 'Novo Freelancer', sub: 'PJ' },
            { id: 'dash-manutencao', icon: '🔧', title: 'Dashboard Manutenção', sub: 'Equipamentos' },
            { id: 'equipamentos-problema', icon: '⚠️', title: 'Equipamentos Críticos', sub: 'Problemáticos' },
            { id: 'manutencao-preventiva', icon: '📅', title: 'Manutenção Preventiva', sub: 'Agendar' },
            { id: 'dash-operacional', icon: '📦', title: 'Dashboard Operacional', sub: 'Hardcase' },
            { id: 'relatorio-utilizacao', icon: '📊', title: 'Relatório Utilização', sub: 'Taxa ocupação' },
            { id: 'dre', icon: '📄', title: 'DRE', sub: 'Resultado' },
            { id: 'fluxo-caixa', icon: '💰', title: 'Fluxo de Caixa', sub: 'Entradas/saídas' },
          ].map(screen => (
            <button
              key={screen.id}
              onClick={() => setCurrentScreen(screen.id)}
              className="bg-gradient-to-br from-gray-800 to-gray-900 p-4 rounded-lg hover:from-amber-900 hover:to-amber-800 transition-all border border-gray-700 text-left"
            >
              <div className="text-3xl mb-2">{screen.icon}</div>
              <div className="text-white font-bold">{screen.title}</div>
              <div className="text-gray-400 text-xs mt-1">{screen.sub}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  // DASHBOARD FINANCEIRO
  const DashboardFinanceiro = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">💰 Dashboard Financeiro</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gradient-to-br from-green-900 to-green-800 p-4 rounded-lg">
            <div className="text-green-300 text-sm">Faturamento Mês</div>
            <div className="text-white text-2xl font-bold">R$ 58k</div>
            <div className="text-green-400 text-xs">+12%</div>
          </div>
          <div className="bg-gradient-to-br from-red-900 to-red-800 p-4 rounded-lg">
            <div className="text-red-300 text-sm">Despesas Mês</div>
            <div className="text-white text-2xl font-bold">R$ 37k</div>
            <div className="text-red-400 text-xs">+5%</div>
          </div>
          <div className="bg-gradient-to-br from-blue-900 to-blue-800 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">Lucro Líquido</div>
            <div className="text-white text-2xl font-bold">R$ 21k</div>
            <div className="text-blue-400 text-xs">36%</div>
          </div>
          <div className="bg-gradient-to-br from-purple-900 to-purple-800 p-4 rounded-lg">
            <div className="text-purple-300 text-sm">Margem</div>
            <div className="text-white text-2xl font-bold">36%</div>
            <div className="text-purple-400 text-xs">Meta: 35%</div>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg mb-6">
          <h3 className="text-white font-bold mb-4">Fluxo de Caixa (6 meses)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={fluxoCaixaData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" />
              <XAxis dataKey="mes" stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none' }} />
              <Legend />
              <Line type="monotone" dataKey="receitas" stroke="#10b981" strokeWidth={2} name="Receitas" />
              <Line type="monotone" dataKey="despesas" stroke="#ef4444" strokeWidth={2} name="Despesas" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">Contas a Vencer (7 dias)</h3>
          <div className="space-y-3">
            {[
              { conta: 'Energia', valor: 850, dias: 2, status: 'urgente' },
              { conta: 'Internet', valor: 299, dias: 5, status: 'atencao' },
              { conta: 'Aluguel', valor: 3500, dias: 7, status: 'ok' },
            ].map((c, i) => (
              <div key={i} className="flex justify-between items-center bg-gray-700 p-3 rounded">
                <div>
                  <div className="text-white font-medium">{c.conta}</div>
                  <div className="text-gray-400 text-sm">Vence em {c.dias} dias</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {c.valor}</div>
                  <div className={`text-xs ${c.status === 'urgente' ? 'text-red-400' : c.status === 'atencao' ? 'text-yellow-400' : 'text-green-400'}`}>
                    {c.status === 'urgente' ? '🔴' : c.status === 'atencao' ? '🟡' : '🟢'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // RECEITAS
  const Receitas = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">📊 Receitas</h1>
          <button className="bg-green-600 text-white px-4 py-2 rounded-lg font-bold">+ Nova</button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <button className="bg-amber-600 text-white px-4 py-2 rounded">Todas</button>
          <button className="bg-gray-700 text-gray-300 px-4 py-2 rounded">Pagas</button>
          <button className="bg-gray-700 text-gray-300 px-4 py-2 rounded">Pendentes</button>
          <button className="bg-gray-700 text-gray-300 px-4 py-2 rounded">Atrasadas</button>
        </div>

        <div className="space-y-4">
          {[
            { codigo: 'FAT-001-2025-0012', cliente: 'Produtora ABC', valor: 8500, status: 'pago', data: '15/06', nfse: 'Sim' },
            { codigo: 'FAT-001-2025-0011', cliente: 'Eventos XYZ', valor: 12300, status: 'pendente', data: '28/06', nfse: 'Não' },
            { codigo: 'FAT-001-2025-0010', cliente: 'Show Nacional', valor: 25000, status: 'atrasado', data: '20/06', nfse: 'Sim' },
          ].map((fat, i) => (
            <div key={i} className="bg-gray-800 p-4 rounded-lg border-l-4" style={{ borderLeftColor: fat.status === 'pago' ? '#10b981' : fat.status === 'atrasado' ? '#ef4444' : '#fbbf24' }}>
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="text-white font-bold">{fat.codigo}</div>
                  <div className="text-gray-400 text-sm">{fat.cliente}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {fat.valor.toLocaleString()}</div>
                  <div className={`text-xs px-2 py-1 rounded ${fat.status === 'pago' ? 'bg-green-900 text-green-300' : fat.status === 'atrasado' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>
                    {fat.status.toUpperCase()}
                  </div>
                </div>
              </div>
              <div className="flex justify-between text-sm text-gray-400">
                <span>Venc: {fat.data}</span>
                <span>NFSe: {fat.nfse === 'Sim' ? '✅' : '❌'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // DESPESAS
  const Despesas = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">💸 Despesas</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-red-900 p-4 rounded-lg">
            <div className="text-red-300 text-sm">Total Mês</div>
            <div className="text-white text-xl font-bold">R$ 37k</div>
          </div>
          <div className="bg-orange-900 p-4 rounded-lg">
            <div className="text-orange-300 text-sm">Folha CLT</div>
            <div className="text-white text-xl font-bold">R$ 18.5k</div>
          </div>
          <div className="bg-yellow-900 p-4 rounded-lg">
            <div className="text-yellow-300 text-sm">Contas Fixas</div>
            <div className="text-white text-xl font-bold">R$ 9.2k</div>
          </div>
          <div className="bg-purple-900 p-4 rounded-lg">
            <div className="text-purple-300 text-sm">Manutenção</div>
            <div className="text-white text-xl font-bold">R$ 6.8k</div>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <button className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-lg font-bold">👔 Folha</button>
          <button className="bg-gradient-to-r from-green-600 to-green-700 text-white p-4 rounded-lg font-bold">🎯 Freelancers</button>
          <button className="bg-gradient-to-r from-orange-600 to-orange-700 text-white p-4 rounded-lg font-bold">💧 Contas</button>
          <button className="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-4 rounded-lg font-bold">🔧 Manutenção</button>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">Últimas Despesas</h3>
          <div className="space-y-3">
            {[
              { tipo: 'Freelancer', desc: 'João Silva - 3 shows', valor: 1500, data: '20/06', icone: '🎯' },
              { tipo: 'Energia', desc: 'Conta de luz junho', valor: 850, data: '18/06', icone: '💡' },
              { tipo: 'Manutenção', desc: 'Reparo Mesa X32', valor: 620, data: '15/06', icone: '🔧' },
            ].map((d, i) => (
              <div key={i} className="flex justify-between items-center bg-gray-700 p-3 rounded">
                <div className="flex gap-3 items-center">
                  <div className="text-2xl">{d.icone}</div>
                  <div>
                    <div className="text-white font-medium">{d.tipo}</div>
                    <div className="text-gray-400 text-sm">{d.desc}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {d.valor}</div>
                  <div className="text-gray-400 text-xs">{d.data}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // FOLHA CLT
  const FolhaCLT = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">👔 Folha de Pagamento CLT</h1>

        <div className="bg-gradient-to-r from-blue-900 to-purple-900 p-6 rounded-lg mb-6">
          <div className="text-blue-200 text-sm mb-2">Folha de Junho/2025</div>
          <div className="text-white text-3xl font-bold mb-4">R$ 18.500</div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-blue-200 text-xs">INSS</div>
              <div className="text-white font-bold">R$ 1.850</div>
            </div>
            <div>
              <div className="text-blue-200 text-xs">FGTS</div>
              <div className="text-white font-bold">R$ 1.480</div>
            </div>
            <div>
              <div className="text-blue-200 text-xs">IRRF</div>
              <div className="text-white font-bold">R$ 920</div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {[
            { nome: 'João Silva', cargo: 'Técnico Áudio', salario: 4500, liquido: 3825 },
            { nome: 'Maria Santos', cargo: 'Técnica Luz', salario: 4200, liquido: 3590 },
            { nome: 'Pedro Costa', cargo: 'Assistente', salario: 3500, liquido: 3015 },
          ].map((func, i) => (
            <div key={i} className="bg-gray-800 p-4 rounded-lg">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="text-white font-bold">{func.nome}</div>
                  <div className="text-gray-400 text-sm">{func.cargo}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {func.liquido.toLocaleString()}</div>
                  <div className="text-gray-400 text-xs">Líquido</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-gray-700 p-2 rounded text-center">
                  <div className="text-gray-400">Bruto</div>
                  <div className="text-white">{func.salario}</div>
                </div>
                <div className="bg-gray-700 p-2 rounded text-center">
                  <div className="text-gray-400">INSS</div>
                  <div className="text-white">{(func.salario * 0.11).toFixed(0)}</div>
                </div>
                <div className="bg-gray-700 p-2 rounded text-center">
                  <div className="text-gray-400">IRRF</div>
                  <div className="text-white">{(func.salario * 0.075).toFixed(0)}</div>
                </div>
              </div>
              <button className="w-full mt-3 bg-blue-600 text-white py-2 rounded">Ver Holerite</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // FREELANCERS
  const Freelancers = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">🎯 Pagamentos Freelancers</h1>

        <div className="bg-gray-800 p-6 rounded-lg mb-6">
          <h3 className="text-white font-bold mb-4">Pagamento Rápido</h3>
          <div className="space-y-4">
            <select className="w-full bg-gray-700 text-white p-3 rounded">
              <option>Selecione freelancer...</option>
              <option>Carlos Técnico</option>
              <option>Ana Fotógrafa</option>
            </select>
            <input type="text" placeholder="Descrição do serviço" className="w-full bg-gray-700 text-white p-3 rounded" />
            <input type="number" placeholder="R$ 0,00" className="w-full bg-gray-700 text-white p-3 rounded" />
            <button className="w-full bg-green-600 text-white py-3 rounded-lg font-bold">Registrar Pagamento</button>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">Histórico Recente</h3>
          <div className="space-y-3">
            {[
              { nome: 'Carlos Técnico', servico: '3 shows', valor: 1500, status: 'pago' },
              { nome: 'Ana Fotógrafa', servico: 'Cobertura', valor: 800, status: 'pendente' },
            ].map((p, i) => (
              <div key={i} className="flex justify-between bg-gray-700 p-3 rounded">
                <div>
                  <div className="text-white font-medium">{p.nome}</div>
                  <div className="text-gray-400 text-sm">{p.servico}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {p.valor}</div>
                  <div className={`text-xs ${p.status === 'pago' ? 'text-green-400' : 'text-yellow-400'}`}>
                    {p.status === 'pago' ? '✅' : '⏳'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // CONTAS A PAGAR
  const ContasPagar = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📋 Contas a Pagar</h1>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-red-900 p-4 rounded-lg">
            <div className="text-red-300 text-sm">Vencidas</div>
            <div className="text-white text-xl font-bold">R$ 2.4k</div>
          </div>
          <div className="bg-yellow-900 p-4 rounded-lg">
            <div className="text-yellow-300 text-sm">7 dias</div>
            <div className="text-white text-xl font-bold">R$ 4.6k</div>
          </div>
          <div className="bg-blue-900 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">Mês</div>
            <div className="text-white text-xl font-bold">R$ 9.2k</div>
          </div>
        </div>

        <div className="space-y-4">
          {[
            { cat: 'Energia', desc: 'Luz - Junho', valor: 850, venc: '25/06', status: 'urgente', rec: true },
            { cat: 'Internet', desc: 'Fibra 500MB', valor: 299, venc: '28/06', status: 'atencao', rec: true },
            { cat: 'Aluguel', desc: 'Galpão', valor: 3500, venc: '05/07', status: 'ok', rec: true },
          ].map((c, i) => (
            <div key={i} className={`bg-gray-800 p-4 rounded-lg border-l-4 ${c.status === 'urgente' ? 'border-red-500' : c.status === 'atencao' ? 'border-yellow-500' : 'border-green-500'}`}>
              <div className="flex justify-between mb-2">
                <div>
                  <div className="flex gap-2 items-center">
                    <div className="text-white font-bold">{c.cat}</div>
                    {c.rec && <span className="bg-purple-900 text-purple-300 text-xs px-2 py-1 rounded">REC</span>}
                  </div>
                  <div className="text-gray-400 text-sm">{c.desc}</div>
                </div>
                <div className="text-right">
                  <div className="text-white font-bold">R$ {c.valor}</div>
                  <div className="text-gray-400 text-xs">{c.venc}</div>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 bg-green-600 text-white py-2 rounded">Pagar</button>
                <button className="flex-1 bg-gray-700 text-white py-2 rounded">Agendar</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // EMITIR NFSE
  const EmitirNFSe = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📄 Emitir NFSe</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <input type="text" placeholder="Nome/Razão Social" className="w-full bg-gray-700 text-white p-3 rounded" />
            <div className="grid grid-cols-2 gap-4">
              <input type="text" placeholder="CPF/CNPJ" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="text" placeholder="Insc. Municipal" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <textarea placeholder="Descrição do serviço" className="w-full bg-gray-700 text-white p-3 rounded h-24"></textarea>
            <div className="grid grid-cols-2 gap-4">
              <input type="number" placeholder="Valor Total" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="number" placeholder="Alíquota ISS (%)" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <select className="w-full bg-gray-700 text-white p-3 rounded">
              <option>Focus NFe</option>
              <option>Manual</option>
            </select>
            <button className="w-full bg-green-600 text-white py-4 rounded-lg font-bold">Emitir NFSe</button>
          </div>
        </div>
      </div>
    </div>
  );

  // GERAR PIX
  const GerarPIX = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">💳 Gerar PIX</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <input type="text" placeholder="Descrição" className="w-full bg-gray-700 text-white p-3 rounded" />
            <input type="number" placeholder="R$ 0,00" className="w-full bg-gray-700 text-white p-3 rounded text-2xl font-bold" />
            <select className="w-full bg-gray-700 text-white p-3 rounded">
              <option>Vincular a fatura...</option>
              <option>FAT-001-2025-0012</option>
            </select>
            <button className="w-full bg-green-600 text-white py-4 rounded-lg font-bold">Gerar QR Code</button>
          </div>

          <div className="mt-6 bg-white p-8 rounded-lg text-center">
            <div className="bg-gray-200 h-48 w-48 mx-auto rounded-lg flex items-center justify-center">
              <div className="text-gray-500 text-sm">QR Code</div>
            </div>
            <div className="mt-4 text-gray-800 font-mono text-xs bg-gray-100 p-3 rounded">
              00020126360014BR.GOV.BCB.PIX...
            </div>
            <button className="mt-4 bg-blue-600 text-white px-6 py-2 rounded">Copiar Código</button>
          </div>
        </div>
      </div>
    </div>
  );

  // DASHBOARD COMERCIAL
  const DashboardComercial = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">🎯 Dashboard Comercial</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-orange-900 p-4 rounded-lg">
            <div className="text-orange-300 text-sm">Leads Ativos</div>
            <div className="text-white text-2xl font-bold">24</div>
          </div>
          <div className="bg-green-900 p-4 rounded-lg">
            <div className="text-green-300 text-sm">Taxa Conversão</div>
            <div className="text-white text-2xl font-bold">42%</div>
          </div>
          <div className="bg-blue-900 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">Ticket Médio</div>
            <div className="text-white text-2xl font-bold">R$ 8.5k</div>
          </div>
          <div className="bg-purple-900 p-4 rounded-lg">
            <div className="text-purple-300 text-sm">Tempo Médio</div>
            <div className="text-white text-2xl font-bold">5 dias</div>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">Funil de Vendas</h3>
          <div className="space-y-3">
            {[
              { etapa: 'Leads', qtd: 150, perc: 100 },
              { etapa: 'Contato', qtd: 100, perc: 67 },
              { etapa: 'Orçamento', qtd: 80, perc: 53 },
              { etapa: 'Negociação', qtd: 60, perc: 40 },
              { etapa: 'Fechados', qtd: 40, perc: 27 },
            ].map((e, i) => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-300">{e.etapa}</span>
                  <span className="text-white font-bold">{e.qtd} ({e.perc}%)</span>
                </div>
                <div className="bg-gray-700 h-8 rounded-full overflow-hidden">
                  <div className="bg-gradient-to-r from-amber-500 to-orange-500 h-full flex items-center px-3 text-white text-sm font-bold" style={{ width: `${e.perc}%` }}>
                    {e.perc}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // LEADS KANBAN
  const LeadsKanban = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📌 Leads - Kanban</h1>

        <div className={`${viewMode === 'desktop' ? 'grid grid-cols-5 gap-4' : 'space-y-4'}`}>
          {[
            { status: 'Novo', cor: 'bg-gray-700', leads: [{ nome: 'Produtora XYZ', valor: 12000 }] },
            { status: 'Contato', cor: 'bg-blue-700', leads: [{ nome: 'Show Nacional', valor: 25000 }] },
            { status: 'Orçamento', cor: 'bg-yellow-700', leads: [{ nome: 'Festival', valor: 35000 }] },
            { status: 'Negociação', cor: 'bg-orange-700', leads: [{ nome: 'Tour', valor: 18000 }] },
            { status: 'Fechado', cor: 'bg-green-700', leads: [{ nome: 'Show Corp', valor: 9500 }] },
          ].map((col, i) => (
            <div key={i} className={`${col.cor} p-4 rounded-lg`}>
              <div className="text-white font-bold mb-3">{col.status} ({col.leads.length})</div>
              <div className="space-y-2">
                {col.leads.map((l, j) => (
                  <div key={j} className="bg-gray-800 p-3 rounded">
                    <div className="text-white font-medium text-sm">{l.nome}</div>
                    <div className="text-gray-300 text-xs">R$ {l.valor.toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // LEAD FORM
  const LeadForm = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📝 Novo Lead</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <input type="text" placeholder="Nome/Empresa" className="w-full bg-gray-700 text-white p-3 rounded" />
            <div className="grid grid-cols-2 gap-4">
              <input type="tel" placeholder="Telefone" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="email" placeholder="Email" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <select className="w-full bg-gray-700 text-white p-3 rounded">
              <option>Origem...</option>
              <option>Instagram</option>
              <option>Indicação</option>
            </select>
            <input type="number" placeholder="Valor Estimado" className="w-full bg-gray-700 text-white p-3 rounded" />
            <button className="w-full bg-green-600 text-white py-4 rounded-lg font-bold">Criar Lead</button>
          </div>
        </div>
      </div>
    </div>
  );

  // DASHBOARD RH
  const DashboardRH = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">👥 Dashboard RH</h1>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-900 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">CLT</div>
            <div className="text-white text-2xl font-bold">12</div>
          </div>
          <div className="bg-green-900 p-4 rounded-lg">
            <div className="text-green-300 text-sm">Freelancers</div>
            <div className="text-white text-2xl font-bold">8</div>
          </div>
          <div className="bg-purple-900 p-4 rounded-lg">
            <div className="text-purple-300 text-sm">Folha</div>
            <div className="text-white text-2xl font-bold">R$ 45k</div>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">🏆 Ranking Performance</h3>
          <div className="space-y-3">
            {[
              { nome: 'João Silva', tours: 24, perf: 95, pos: 1 },
              { nome: 'Maria Santos', tours: 22, perf: 92, pos: 2 },
              { nome: 'Pedro Costa', tours: 19, perf: 88, pos: 3 },
            ].map((f, i) => (
              <div key={i} className="bg-gray-700 p-4 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${i === 0 ? 'bg-yellow-500 text-yellow-900' : i === 1 ? 'bg-gray-400 text-gray-900' : 'bg-orange-600 text-white'}`}>
                      {f.pos}
                    </div>
                    <div className="text-white font-bold">{f.nome}</div>
                  </div>
                  <div className="text-green-400 font-bold">{f.perf}%</div>
                </div>
                <div className="text-sm text-gray-300">Tours: {f.tours}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // FUNCIONÁRIOS
  const Funcionarios = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">👔 Funcionários</h1>

        <div className="flex gap-2 mb-6">
          <button className="bg-amber-600 text-white px-4 py-2 rounded">Todos (20)</button>
          <button className="bg-gray-700 text-gray-300 px-4 py-2 rounded">CLT (12)</button>
          <button className="bg-gray-700 text-gray-300 px-4 py-2 rounded">PJ (8)</button>
        </div>

        <div className="space-y-4">
          {[
            { nome: 'João Silva', cargo: 'Técnico Áudio', tipo: 'CLT', sal: 4500 },
            { nome: 'Maria Santos', cargo: 'Técnica Luz', tipo: 'CLT', sal: 4200 },
            { nome: 'Carlos Free', cargo: 'Técnico', tipo: 'PJ', sal: null },
          ].map((f, i) => (
            <div key={i} className="bg-gray-800 p-4 rounded-lg">
              <div className="flex justify-between mb-3">
                <div>
                  <div className="flex gap-2 items-center">
                    <div className="text-white font-bold">{f.nome}</div>
                    <span className={`text-xs px-2 py-1 rounded ${f.tipo === 'CLT' ? 'bg-blue-900 text-blue-300' : 'bg-green-900 text-green-300'}`}>{f.tipo}</span>
                  </div>
                  <div className="text-gray-400 text-sm">{f.cargo}</div>
                </div>
                {f.sal && <div className="text-white font-bold">R$ {f.sal}</div>}
              </div>
              <div className="flex gap-2">
                <button className="flex-1 bg-blue-600 text-white py-2 rounded">Detalhes</button>
                <button className="flex-1 bg-gray-700 text-white py-2 rounded">Editar</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // CADASTRO CLT
  const CadastroCLT = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">➕ Novo CLT</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <input type="text" placeholder="Nome Completo" className="w-full bg-gray-700 text-white p-3 rounded" />
            <div className="grid grid-cols-2 gap-4">
              <input type="text" placeholder="CPF" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="text" placeholder="RG" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <input type="text" placeholder="Cargo" className="w-full bg-gray-700 text-white p-3 rounded" />
            <div className="grid grid-cols-2 gap-4">
              <input type="date" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="number" placeholder="Salário" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <button className="w-full bg-green-600 text-white py-4 rounded-lg font-bold">Cadastrar</button>
          </div>
        </div>
      </div>
    </div>
  );

  // CADASTRO FREELANCER
  const CadastroFreelancer = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">➕ Novo Freelancer</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <input type="text" placeholder="Nome/Razão Social" className="w-full bg-gray-700 text-white p-3 rounded" />
            <div className="grid grid-cols-2 gap-4">
              <input type="text" placeholder="CPF/CNPJ" className="w-full bg-gray-700 text-white p-3 rounded" />
              <input type="text" placeholder="Especialidade" className="w-full bg-gray-700 text-white p-3 rounded" />
            </div>
            <input type="tel" placeholder="Telefone" className="w-full bg-gray-700 text-white p-3 rounded" />
            <input type="text" placeholder="Chave PIX" className="w-full bg-gray-700 text-white p-3 rounded" />
            <button className="w-full bg-green-600 text-white py-4 rounded-lg font-bold">Cadastrar</button>
          </div>
        </div>
      </div>
    </div>
  );

  // DASHBOARD MANUTENÇÃO
  const DashboardManutencao = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">🔧 Dashboard Manutenção</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-orange-900 p-4 rounded-lg">
            <div className="text-orange-300 text-sm">Em Manutenção</div>
            <div className="text-white text-2xl font-bold">8</div>
          </div>
          <div className="bg-red-900 p-4 rounded-lg">
            <div className="text-red-300 text-sm">Atrasadas</div>
            <div className="text-white text-2xl font-bold">3</div>
          </div>
          <div className="bg-purple-900 p-4 rounded-lg">
            <div className="text-purple-300 text-sm">Custo Mês</div>
            <div className="text-white text-2xl font-bold">R$ 3.2k</div>
          </div>
          <div className="bg-blue-900 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">Tempo Médio</div>
            <div className="text-white text-2xl font-bold">4 dias</div>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">⚠️ Equipamentos Críticos</h3>
          <div className="space-y-3">
            {[
              { eq: 'Mesa X32', man: 8, custo: 4200 },
              { eq: 'Moving Head', man: 6, custo: 3800 },
            ].map((e, i) => (
              <div key={i} className="bg-gray-700 p-4 rounded-lg">
                <div className="flex justify-between mb-2">
                  <div className="text-white font-bold">{e.eq}</div>
                  <div className="bg-red-900 text-red-300 px-3 py-1 rounded text-sm">{e.man}x</div>
                </div>
                <div className="text-sm text-gray-400">Custo: R$ {e.custo.toLocaleString()}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // EQUIPAMENTOS CRÍTICOS
  const EquipamentosProblema = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">⚠️ Equipamentos Críticos</h1>

        <div className="space-y-4">
          {[
            { nome: 'Mesa X32 #001', man: 8, custo: 4200, prob: 'Falha preamp canal 12' },
            { nome: 'Moving Head #005', man: 6, custo: 3800, prob: 'Motor pan com ruído' },
          ].map((e, i) => (
            <div key={i} className="bg-gray-800 p-4 rounded-lg border-l-4 border-red-500">
              <div className="flex justify-between mb-3">
                <div>
                  <div className="text-white font-bold">{e.nome}</div>
                  <div className="text-gray-400 text-sm mt-1">{e.prob}</div>
                </div>
                <div className="text-right">
                  <div className="bg-red-900 text-red-300 px-3 py-1 rounded text-sm mb-1">{e.man} manutenções</div>
                  <div className="text-white font-bold">R$ {e.custo.toLocaleString()}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button className="bg-blue-600 text-white py-2 rounded">Histórico</button>
                <button className="bg-yellow-600 text-white py-2 rounded">Preventiva</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // MANUTENÇÃO PREVENTIVA
  const ManutencaoPreventiva = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📅 Manutenção Preventiva</h1>

        <div className="bg-red-900 border-l-4 border-red-500 p-4 rounded mb-6">
          <div className="text-red-100 font-bold mb-1">⚠️ 3 equipamentos atrasados</div>
          <div className="text-red-200 text-sm">Agende manutenções</div>
        </div>

        <div className="space-y-4">
          {[
            { eq: 'Moving Head #002', status: 'atrasado', dias: 10 },
            { eq: 'Mesa X32 #001', status: 'agendado', dias: 25 },
          ].map((e, i) => (
            <div key={i} className={`bg-gray-800 p-4 rounded-lg border-l-4 ${e.status === 'atrasado' ? 'border-red-500' : 'border-yellow-500'}`}>
              <div className="flex justify-between mb-3">
                <div className="text-white font-bold">{e.eq}</div>
                <div className={`px-3 py-1 rounded text-sm ${e.status === 'atrasado' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>
                  {e.dias} dias
                </div>
              </div>
              <button className="w-full bg-blue-600 text-white py-2 rounded">Agendar</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // DASHBOARD OPERACIONAL
  const DashboardOperacional = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📦 Dashboard Operacional</h1>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-900 p-4 rounded-lg">
            <div className="text-blue-300 text-sm">Total</div>
            <div className="text-white text-2xl font-bold">342</div>
          </div>
          <div className="bg-green-900 p-4 rounded-lg">
            <div className="text-green-300 text-sm">Disponíveis</div>
            <div className="text-white text-2xl font-bold">289</div>
          </div>
          <div className="bg-orange-900 p-4 rounded-lg">
            <div className="text-orange-300 text-sm">Em Tour</div>
            <div className="text-white text-2xl font-bold">45</div>
          </div>
          <div className="bg-red-900 p-4 rounded-lg">
            <div className="text-red-300 text-sm">Manutenção</div>
            <div className="text-white text-2xl font-bold">8</div>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg mb-6">
          <h3 className="text-white font-bold mb-4">Taxa de Utilização</h3>
          <div className="bg-gray-700 h-12 rounded-full overflow-hidden">
            <div className="bg-gradient-to-r from-green-500 to-blue-500 h-full flex items-center justify-center text-white font-bold" style={{ width: '65%' }}>
              65%
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-purple-900 to-blue-900 p-6 rounded-lg">
          <div className="text-purple-200 text-sm mb-2">Patrimônio Total</div>
          <div className="text-white text-3xl font-bold">R$ 485.000</div>
        </div>
      </div>
    </div>
  );

  // RELATÓRIO UTILIZAÇÃO
  const RelatorioUtilizacao = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📊 Relatório Utilização</h1>

        <div className="bg-gray-800 p-6 rounded-lg mb-6">
          <h3 className="text-white font-bold mb-4">Resumo do Período</h3>
          <div className="space-y-3">
            {[
              { label: 'Tours realizadas', val: '8' },
              { label: 'Equipamentos utilizados', val: '156 (45%)' },
              { label: 'Taxa média ocupação', val: '72%' },
            ].map((i, idx) => (
              <div key={idx} className="flex justify-between bg-gray-700 p-3 rounded">
                <span className="text-gray-300">{i.label}</span>
                <span className="text-white font-bold">{i.val}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-white font-bold mb-4">Top 5 Mais Utilizados</h3>
          <div className="space-y-2">
            {[
              { nome: 'Mesa X32', uso: 8, perc: 100 },
              { nome: 'SM58', uso: 7, perc: 88 },
            ].map((e, i) => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-300">{e.nome}</span>
                  <span className="text-white font-bold">{e.uso}x ({e.perc}%)</span>
                </div>
                <div className="bg-gray-700 h-2 rounded-full overflow-hidden">
                  <div className="bg-green-500 h-full" style={{ width: `${e.perc}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  // DRE
  const DRE = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">📄 DRE</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <div className="space-y-4">
            <div>
              <div className="text-green-400 font-bold mb-2">RECEITAS</div>
              <div className="flex justify-between bg-gray-700 p-3 rounded">
                <span className="text-gray-300">Locações</span>
                <span className="text-white font-bold">R$ 58.000</span>
              </div>
            </div>
            <div>
              <div className="text-red-400 font-bold mb-2">DESPESAS</div>
              <div className="space-y-2">
                <div className="flex justify-between bg-gray-700 p-3 rounded">
                  <span className="text-gray-300">Folha</span>
                  <span className="text-white">R$ 18.500</span>
                </div>
                <div className="flex justify-between bg-gray-700 p-3 rounded">
                  <span className="text-gray-300">Contas</span>
                  <span className="text-white">R$ 9.200</span>
                </div>
              </div>
            </div>
            <div className="border-t border-gray-600 pt-4">
              <div className="flex justify-between text-lg">
                <span className="text-blue-300 font-bold">LUCRO LÍQUIDO</span>
                <span className="text-white font-bold">R$ 21.000</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // FLUXO DE CAIXA
  const FluxoCaixa = () => (
    <div className={containerClass}>
      <div className="p-6">
        <button onClick={() => setCurrentScreen('menu')} className="text-amber-500 mb-4">← Voltar</button>
        <h1 className="text-2xl font-bold text-white mb-6">💰 Fluxo de Caixa</h1>

        <div className="bg-gray-800 p-6 rounded-lg">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={fluxoCaixaData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" />
              <XAxis dataKey="mes" stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none' }} />
              <Line type="monotone" dataKey="receitas" stroke="#10b981" strokeWidth={3} />
              <Line type="monotone" dataKey="despesas" stroke="#ef4444" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );

  // RENDERIZAÇÃO CONDICIONAL
  const screens = {
    'menu': <MenuPrincipal />,
    'dash-financeiro': <DashboardFinanceiro />,
    'receitas': <Receitas />,
    'despesas': <Despesas />,
    'folha-clt': <FolhaCLT />,
    'freelancers': <Freelancers />,
    'contas-pagar': <ContasPagar />,
    'emitir-nfse': <EmitirNFSe />,
    'gerar-pix': <GerarPIX />,
    'dash-comercial': <DashboardComercial />,
    'leads-kanban': <LeadsKanban />,
    'lead-form': <LeadForm />,
    'dash-rh': <DashboardRH />,
    'funcionarios': <Funcionarios />,
    'cadastro-clt': <CadastroCLT />,
    'cadastro-freelancer': <CadastroFreelancer />,
    'dash-manutencao': <DashboardManutencao />,
    'equipamentos-problema': <EquipamentosProblema />,
    'manutencao-preventiva': <ManutencaoPreventiva />,
    'dash-operacional': <DashboardOperacional />,
    'relatorio-utilizacao': <RelatorioUtilizacao />,
    'dre': <DRE />,
    'fluxo-caixa': <FluxoCaixa />,
  };

  return (
    <div className="min-h-screen bg-black">
      {screens[currentScreen] || <MenuPrincipal />}
    </div>
  );
};

export default TourManagerMockups;