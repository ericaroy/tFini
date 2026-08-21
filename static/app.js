const sampleTransactions = [
  { id: 'sample-1', timestamp: 1787184000, category: 'Bazaar', event: 'Sold Xanax x4', amount: 3380000, balance: 125500000 },
  { id: 'sample-2', timestamp: 1787175000, category: 'Bank', event: 'Bank investment payout', amount: 8100000, balance: 122120000 },
  { id: 'sample-3', timestamp: 1787169000, category: 'Items', event: 'Bought Donator Pack', amount: -24200000, balance: 114020000 },
  { id: 'sample-4', timestamp: 1787161200, category: 'Faction', event: 'Faction vault deposit', amount: -10000000, balance: 138220000 },
];

let transactions = [];
let usingDemo = false;

const elements = {
  form: document.querySelector('#sync-form'),
  apiKey: document.querySelector('#api-key'),
  from: document.querySelector('#from'),
  to: document.querySelector('#to'),
  search: document.querySelector('#search'),
  status: document.querySelector('#status'),
  income: document.querySelector('#income'),
  expenses: document.querySelector('#expenses'),
  net: document.querySelector('#net'),
  table: document.querySelector('#transactions'),
  button: document.querySelector('#sync-button'),
};

function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0);
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value * 1000));
}

function findNumber(source, keys) {
  for (const key of keys) {
    const value = source?.[key];
    if (value !== undefined && value !== null && value !== '') {
      const number = Number(value);
      if (Number.isFinite(number)) return number;
    }
  }
  return null;
}

function normalizeItemMarketLog(entry) {
  if (entry.details?.category !== 'Item market') return null;

  const data = entry.data || {};
  const isBuy = /buy/i.test(entry.details?.title || '');
  const isSale = /sell|sold/i.test(entry.details?.title || '');
  const item = data.items?.[0];

  if ((!isBuy && !isSale) || !item) return null;

  const grossTotal = Number(data.cost_total || 0);
  const fee = Number(data.fee || 0);
  const counterpartyId = isBuy ? data.seller : data.buyer;

  return {
    id: entry.id,
    timestamp: Number(entry.timestamp),
    category: 'Item Market',
    event: `${isBuy ? 'Bought' : 'Sold'} ${item.qty}× Item #${item.id}`,
    itemId: item.id,
    quantity: Number(item.qty || 0),
    priceEach: Number(data.cost_each || 0),
    fee,
    amount: isBuy ? -grossTotal : grossTotal - fee,
    counterpartyLabel: isBuy ? 'Bought from' : 'Sold to',
    counterparty: data.anonymous ? 'Anonymous player' : `Player #${counterpartyId}`,
    balance: 0,
  };
}

function normalizeAbroadPurchaseLog(entry) {
  if (entry.details?.id !== 4201) return null;

  const data = entry.data || {};

  return {
    id: entry.id,
    timestamp: Number(entry.timestamp),
    category: 'Abroad Purchase',
    event: `Bought ${data.quantity || 0}× Item #${data.item || 'unknown'}`,
    itemId: data.item,
    quantity: Number(data.quantity || 0),
    priceEach: Number(data.cost_each || 0),
    amount: -Number(data.cost_total || 0),
    counterpartyLabel: 'Purchased abroad',
    counterparty: `Area ${data.area || 'unknown'}`,
    balance: 0,
  };
}

function normalizeShopSaleLog(entry) {
  if (entry.details?.id !== 4210) return null;

  const data = entry.data || {};
  const shopName = String(data.area || 'Shop').replace(/^to\s+/i, '');

  return {
    id: entry.id,
    timestamp: Number(entry.timestamp),
    category: 'City Shop',
    event: `Sold ${data.quantity || 0}× Item #${data.item || 'unknown'}`,
    itemId: data.item,
    quantity: Number(data.quantity || 0),
    priceEach: Number(data.value_each || 0),
    amount: Number(data.total_value || 0),
    counterpartyLabel: 'Sold to',
    counterparty: shopName,
    balance: 0,
  };
}

function flattenLogs(logs) {
  return (logs || [])
    .map((entry) =>
      normalizeItemMarketLog(entry) ||
      normalizeAbroadPurchaseLog(entry) ||
      normalizeShopSaleLog(entry)
    )
    .filter(Boolean)
    .sort((a, b) => b.timestamp - a.timestamp);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function filteredTransactions() {
  const needle = elements.search.value.toLowerCase();
  return transactions.filter((tx) => `${tx.category} ${tx.event}`.toLowerCase().includes(needle));
}

function render() {
  const rows = filteredTransactions();
  const totals = rows.reduce((acc, tx) => {
    if (tx.amount >= 0) acc.income += tx.amount;
    else acc.expenses += Math.abs(tx.amount);
    acc.net += tx.amount;
    return acc;
  }, { income: 0, expenses: 0, net: 0 });

  elements.income.textContent = money(totals.income);
  elements.expenses.textContent = money(totals.expenses);
  elements.net.textContent = money(totals.net);
  elements.net.className = totals.net >= 0 ? 'positive' : 'negative';

  elements.table.innerHTML = rows.length ? rows.map((tx) => `
    <div class="row">
      <div class="icon ${tx.amount >= 0 ? 'in' : 'out'}">${tx.amount >= 0 ? '↙' : '↗'}</div>
      <div><strong>${escapeHtml(tx.event)}</strong><span>${escapeHtml(tx.category)} · ${formatDate(tx.timestamp)}</span></div>
      <div class="amount"><strong class="${tx.amount >= 0 ? 'positive' : 'negative'}">${money(tx.amount)}</strong>${tx.balance ? `<span>Balance ${money(tx.balance)}</span>` : ''}</div>
    </div>`).join('') : '<p class="empty">No matching transactions.</p>';
}

function setStatus(message) {
  elements.status.textContent = '';
  if (usingDemo) {
    const strong = document.createElement('strong');
    strong.textContent = 'Demo mode.';
    elements.status.append(strong, ' ');
  }
  elements.status.append(document.createTextNode(message));
}

async function syncTransactions(event) {
  event.preventDefault();
  elements.button.disabled = true;
  elements.button.textContent = '↻ Syncing';
  setStatus('Syncing Torn logs...');

  const params = new URLSearchParams();
  if (elements.apiKey.value) params.set('key', elements.apiKey.value);
  if (elements.from.value) params.set('from', Math.floor(new Date(elements.from.value).getTime() / 1000));
  if (elements.to.value) {
  const endOfDay = new Date(`${elements.to.value}T23:59:59`);
  params.set('to', Math.floor(endOfDay.getTime() / 1000));
}

  try {
    const response = await fetch(`/api/torn/transactions?${params}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Unable to sync transactions.');
    transactions = flattenLogs(payload.logs);
    usingDemo = false;
    setStatus(`Synced ${transactions.length} transactions from Torn at ${new Date(payload.fetchedAt).toLocaleString()}.`);
    render();
  } catch (error) {
    setStatus(error.message);
  } finally {
    elements.button.disabled = false;
    elements.button.textContent = '↻ Sync transactions';
  }
}

elements.form.addEventListener('submit', syncTransactions);
elements.search.addEventListener('input', render);
render();
