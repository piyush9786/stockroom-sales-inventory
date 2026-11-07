'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const currency = value => Number(value || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const badge = value => `<span class="badge ${escapeHTML(String(value).toLowerCase())}">${escapeHTML(value)}</span>`;
let csrf = '', user = null, pageNumber = 1;
const currentPage = document.body.dataset.page;
const descriptions = {orders:'Create orders, track their status, and keep stock in sync.', customers:'Keep your customer records accurate and up to date.', products:'Manage your catalogue, pricing, and available stock.', reports:'Review confirmed sales and follow every stock movement.'};

function showMessage(message, success = false, target = '#message') {
  const element = $(target);
  if (!element) return;
  element.textContent = message;
  element.className = `message${success ? ' success' : ''}`;
  element.hidden = !message;
}

async function api(path, options = {}) {
  const headers = {'X-CSRF-Token': csrf, ...options.headers};
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch('/api' + path, {...options, headers, credentials:'same-origin'});
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && currentPage !== 'login') window.location.assign('/login');
    const rows = data.details?.map(row => `Row ${row.row}: ${row.reason}`).join('\n');
    throw new Error(data.error + (rows ? '\n' + rows : ''));
  }
  return data;
}

async function busy(button, work, target = '#message') {
  button.disabled = true;
  try { await work(); } catch (error) { showMessage(error.message, false, target); }
  finally { button.disabled = false; }
}

function table(columns, rows) {
  if (!rows.length) return '<p class="empty">No records found. Try changing your filters.</p>';
  return `<table><thead><tr>${columns.map(c => `<th class="${c.numeric ? 'numeric' : ''}">${escapeHTML(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${columns.map(c => `<td class="${c.numeric ? 'numeric' : ''}">${c.render ? c.render(row) : escapeHTML(row[c.key] ?? '—')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function field(name, title, value = '', type = 'text', extra = '') {
  return `<label>${escapeHTML(title)}<input name="${name}" type="${type}" value="${escapeHTML(value)}" ${extra}></label>`;
}

function statusSelect(value = 'Active', all = false) {
  return `<label>Status<select name="status">${(all ? ['Active','Inactive','All'] : ['Active','Inactive']).map(status => `<option ${value === status ? 'selected' : ''}>${status}</option>`).join('')}</select></label>`;
}

function openDialog(title, subtitle, contents) {
  $('#editor-content').innerHTML = `<div class="dialog-head"><div><h2 id="editor-title">${escapeHTML(title)}</h2><p class="muted">${escapeHTML(subtitle)}</p></div><button type="button" class="close" aria-label="Close dialog">×</button></div><div id="dialog-message" class="message" role="alert" hidden></div>${contents}`;
  $('.close', $('#editor')).addEventListener('click', () => $('#editor').close());
  if (!$('#editor').open) $('#editor').showModal();
}

function filtersParams() {
  const params = new URLSearchParams(new FormData($('#filters')));
  for (const [key, value] of [...params]) if (!value) params.delete(key);
  params.set('page', pageNumber);
  params.set('per_page', 10);
  return params;
}

function pagination(data) {
  const element = $('#pagination');
  if (data.total === undefined) { element.innerHTML = ''; return; }
  element.innerHTML = `<span class="count">${data.total} record${data.total === 1 ? '' : 's'}</span><button id="previous-page" ${pageNumber <= 1 ? 'disabled' : ''}>Previous</button><span>Page ${pageNumber} of ${Math.max(1, Math.ceil(data.total / data.per_page))}</span><button id="next-page" ${pageNumber * data.per_page >= data.total ? 'disabled' : ''}>Next</button>`;
  $('#previous-page').onclick = () => { pageNumber--; loadRecords().catch(error => showMessage(error.message)); };
  $('#next-page').onclick = () => { pageNumber++; loadRecords().catch(error => showMessage(error.message)); };
}

async function loadRecords() {
  const params = filtersParams();
  let data, columns;
  if (currentPage === 'reports') {
    const kind = params.get('report');
    params.delete('report');
    data = await api(`/reports/${kind}?${params}`);
    const mapping = {
      'customer-sales':[['customer','Customer'],['confirmed_order_count','Confirmed orders'],['total_sales','Sales after discount (INR)',true]],
      'product-sales':[['product_code','Code'],['product','Product'],['quantity_sold','Quantity sold'],['gross_item_value','Gross item value (INR)',true]],
      'low-stock':[['product_code','Code'],['product','Product'],['category','Category'],['stock_quantity','Stock'],['status','Status']],
      'stock-movements':[['product','Product'],['movement_type','Movement'],['quantity_change','Change'],['order_number','Order'],['reason','Reason'],['created_at','Timestamp (UTC)'],['created_by','Created by']]
    };
    columns = mapping[kind].map(([key,label,money]) => ({key,label,numeric:money,render:money ? row => currency(row[key]) : undefined}));
  } else {
    data = await api(`/${currentPage}?${params}`);
    const edit = row => `<button class="link edit-record" data-id="${row.id}">${currentPage === 'orders' ? 'Open' : user.role === 'Admin' ? 'Edit' : 'View'}</button>`;
    if (currentPage === 'orders') columns = [
      {label:'Order',render:row => `<strong class="order-number">${escapeHTML(row.order_number)}</strong>`},
      {key:'customer_name',label:'Customer'}, {key:'order_date',label:'Date'},
      {label:'Status',render:row => badge(row.status)}, {key:'owner_name',label:'Created by'},
      {label:'Total (INR)',numeric:true,render:row => currency(row.grand_total)}, {label:'',render:edit}
    ];
    else if (currentPage === 'customers') columns = [
      {label:'Customer',render:row => `<strong>${escapeHTML(row.name)}</strong><small>${escapeHTML(row.email)}</small>`},
      {key:'mobile',label:'Mobile'}, {key:'city',label:'City'}, {label:'Status',render:row => badge(row.status)}, {label:'',render:edit}
    ];
    else columns = [
      {label:'Product',render:row => `<strong>${escapeHTML(row.name)}</strong><small>${escapeHTML(row.product_code)}</small>`},
      {key:'category',label:'Category'}, {label:'Price (INR)',numeric:true,render:row => currency(row.price)},
      {label:'In stock',numeric:true,render:row => `<span class="${row.stock_quantity < 10 ? 'low' : ''}">${row.stock_quantity}</span>`},
      {label:'Status',render:row => badge(row.status)},
      {label:'',render:row => edit(row) + (user.role === 'Admin' ? `<button class="link adjust-stock" data-id="${row.id}">Adjust stock</button>` : '')}
    ];
  }
  $('#content').innerHTML = table(columns, data.items);
  pagination(data);
  $$('.edit-record').forEach(button => button.onclick = () => busy(button, () => currentPage === 'orders' ? orderEditor(button.dataset.id) : masterEditor(button.dataset.id)));
  $$('.adjust-stock').forEach(button => button.onclick = () => busy(button, () => stockEditor(button.dataset.id)));
}

async function masterEditor(id) {
  const product = currentPage === 'products', editable = user.role === 'Admin';
  const record = id ? await api(`/${currentPage}/${id}`) : {status:'Active',stock_quantity:0};
  const inputs = product ? [field('product_code','Product code',record.product_code,'text','required maxlength="50" pattern="[A-Za-z0-9_-]+"'),field('name','Product name',record.name,'text','required maxlength="160"'),field('category','Category',record.category,'text','required maxlength="100"'),field('price','Price (INR)',record.price,'number','required min="0" max="999999999999.99" step="0.01"'),!id ? field('stock_quantity','Opening stock',0,'number','required min="0" max="2000000000" step="1"') : '',statusSelect(record.status)] : [field('name','Name',record.name,'text','required maxlength="120"'),field('email','Email',record.email,'email','required maxlength="254"'),field('mobile','Mobile',record.mobile,'tel','required maxlength="30"'),field('city','City',record.city,'text','required maxlength="120"'),statusSelect(record.status)];
  openDialog(`${id ? editable ? 'Edit' : 'View' : 'New'} ${product ? 'product' : 'customer'}`, 'Deactivate referenced records to retain their history.', `<form id="master-form"><div class="form-grid">${inputs.join('')}</div><div class="dialog-foot">${id && editable ? '<button type="button" class="danger" id="delete-master">Delete</button>' : ''}${editable ? '<button class="primary" type="submit">Save changes</button>' : ''}</div></form>`);
  if (!editable) $$('#master-form input, #master-form select').forEach(input => input.disabled = true);
  $('#master-form').onsubmit = event => {
    event.preventDefault();
    busy($('button[type=submit]', event.target), async () => {
      const data = Object.fromEntries(new FormData(event.target));
      await api(`/${currentPage}${id ? '/' + id : ''}`, {method:id ? 'PUT' : 'POST',body:data});
      $('#editor').close(); showMessage('Saved successfully.', true); await loadRecords();
    }, '#dialog-message');
  };
  if ($('#delete-master')) $('#delete-master').onclick = event => busy(event.target, async () => {
    if (!window.confirm('Delete this record? Referenced records must be deactivated instead.')) return;
    await api(`/${currentPage}/${id}`, {method:'DELETE'});
    $('#editor').close(); showMessage('Record deleted.',true); await loadRecords();
  }, '#dialog-message');
}

async function stockEditor(id) {
  const product = await api(`/products/${id}`);
  openDialog('Adjust stock', `${product.name} · ${product.stock_quantity} currently in stock`, `<form id="stock-form"><div class="form-grid">${field('quantity_change','Quantity change (use minus to decrease)','','number','required step="1" min="-2000000000" max="2000000000"')}${field('reason','Reason','','text','required maxlength="255"')}</div><div class="dialog-foot"><button class="primary" type="submit">Apply adjustment</button></div></form>`);
  $('#stock-form').onsubmit = event => {
    event.preventDefault(); busy($('button[type=submit]',event.target), async () => {
      await api(`/products/${id}/stock-adjustments`,{method:'POST',body:Object.fromEntries(new FormData(event.target))});
      $('#editor').close(); showMessage('Stock adjusted and movement recorded.',true); await loadRecords();
    },'#dialog-message');
  };
}

function importEditor() {
  openDialog('Import products', 'All rows must be valid. If any row fails, nothing is imported.', '<p class="section-note">Required columns: product_code, product_name, category, price, stock_quantity, status. UTF-8 CSV; maximum 2 MB / 5000 rows.</p><form id="import-form"><label class="file-input">CSV file<input name="file" type="file" accept=".csv,text/csv" required></label><div class="dialog-foot"><button type="submit" class="primary">Import CSV</button></div></form>');
  $('#import-form').onsubmit = event => {
    event.preventDefault(); busy($('button[type=submit]',event.target),async () => {
      const result = await api('/products/import',{method:'POST',body:new FormData(event.target)});
      $('#editor').close(); showMessage(`${result.imported} products imported successfully.`,true); await loadRecords();
    },'#dialog-message');
  };
}

async function allActive(kind) {
  const rows = [];
  let page = 1, total;
  do {
    const result = await api(`/${kind}?status=Active&per_page=100&page=${page++}`);
    rows.push(...result.items); total = result.total;
  } while (rows.length < total);
  return rows;
}

// Preview arithmetic uses integer cents; the server independently recalculates every saved value.
function cents(value) {
  if (!/^\d+(\.\d{0,2})?$/.test(String(value))) return 0n;
  const [whole, fraction = ''] = String(value).split('.');
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2,'0'));
}
const displayCents = value => currency(String(value / 100n) + '.' + String(value % 100n).padStart(2,'0'));

async function orderEditor(id) {
  const order = id ? await api(`/orders/${id}`) : {status:'Draft',order_date:new Date().toLocaleDateString('en-CA'),discount_percentage:'0.00',items:[]};
  const editable = order.status === 'Draft';
  const [products, customers] = editable ? await Promise.all([allActive('products'),allActive('customers')]) : [[],[]];
  if (editable && !customers.some(c => c.id === order.customer_id) && order.customer_id) customers.push({id:order.customer_id,name:order.customer_name + ' (inactive)'});
  const option = (value,label,selected) => `<option value="${value}" ${selected ? 'selected' : ''}>${escapeHTML(label)}</option>`;
  const customerInput = editable ? `<label>Customer<select name="customer_id" required><option value="">Select customer</option>${customers.map(c => option(c.id,c.name,c.id === order.customer_id)).join('')}</select></label>` : field('customer_name','Customer',order.customer_name,'text','disabled');
  openDialog(id ? 'Order details' : 'New sales order', id ? `${order.order_number} · ${order.status}` : 'Save a Draft, then confirm it to deduct stock.', `<form id="order-form"><div class="form-grid three">${customerInput}${field('order_date','Order date',order.order_date,'date',editable ? 'required' : 'disabled')}<label>Status<span>${badge(order.status)}</span></label></div><div class="table-wrap"><table class="item-table"><thead><tr><th>Product</th><th>Quantity</th><th class="numeric">Rate (INR)</th><th class="numeric">Amount (INR)</th><th></th></tr></thead><tbody id="order-items"></tbody></table></div>${editable ? '<button type="button" id="add-item">+ Add product</button>' : ''}<div class="totals"><div><span>Subtotal</span><strong id="subtotal">0.00</strong></div><div><label class="discount-label">Discount % <input id="discount" name="discount_percentage" type="number" min="0" max="20" step="0.01" value="${escapeHTML(order.discount_percentage)}" ${editable ? 'required' : 'disabled'}></label><span id="discount-amount">0.00</span></div><div class="grand"><span>Total · INR</span><span id="grand-total">0.00</span></div></div><div class="dialog-foot">${id && order.status !== 'Cancelled' ? '<button type="button" id="cancel-order" class="danger">Cancel order</button>' : ''}${editable ? '<button type="submit" class="primary">Save Draft</button>' : ''}${id && editable ? '<button type="button" id="confirm-order" class="primary">Confirm order</button>' : ''}</div></form>`);
  const productMap = new Map(products.map(p => [p.id,p]));
  function recalculate() {
    let subtotal = 0n;
    $$('#order-items tr').forEach(row => {
      const quantity = $('.quantity',row).value;
      const amount = /^\d+$/.test(quantity) ? BigInt(quantity) * cents(row.dataset.rate || '0') : 0n;
      $('.amount',row).textContent = displayCents(amount); subtotal += amount;
    });
    const enteredPercentage = cents($('#discount').value);
    const percentage = enteredPercentage > 2000n ? 2000n : enteredPercentage;
    const discount = (subtotal * percentage + 5000n) / 10000n;
    $('#subtotal').textContent = displayCents(subtotal);
    $('#discount-amount').textContent = displayCents(discount);
    $('#grand-total').textContent = displayCents(subtotal - discount);
  }
  function addRow(item = {}) {
    const tr = document.createElement('tr');
    tr.dataset.rate = item.rate || '0';
    const options = products.map(p => option(p.id,`${p.product_code} · ${p.name}`,p.id === item.product_id)).join('');
    const inactive = item.product_id && !productMap.has(item.product_id) ? option(item.product_id,`${item.product_code} · ${item.product_name} (inactive)`,true) : '';
    tr.innerHTML = `<td>${editable ? `<select class="product-select" aria-label="Product" required><option value="">Select product</option>${options}${inactive}</select>` : `<strong>${escapeHTML(item.product_name)}</strong><small>${escapeHTML(item.product_code)}</small>`}<span class="row-stock">${item.stock_quantity !== undefined ? `${item.stock_quantity} in stock` : 'Select a product to check stock'}</span></td><td><input class="quantity" aria-label="Quantity" type="number" min="1" max="2000000000" step="1" required value="${item.quantity || 1}" ${editable ? '' : 'disabled'}></td><td class="numeric rate">${currency(item.rate)}</td><td class="numeric amount">0.00</td><td>${editable ? '<button type="button" class="link remove-item" aria-label="Remove product">Remove</button>' : ''}</td>`;
    $('#order-items').append(tr);
    $('.quantity',tr).oninput = recalculate;
    if (editable) {
      $('.remove-item',tr).onclick = () => { tr.remove(); recalculate(); };
      $('.product-select',tr).onchange = async event => {
        tr.dataset.loading = 'true';
        // Ignore an older response if the selection changes while the fetch is in flight.
        const selected = event.target.value;
        tr.dataset.selection = selected;
        try {
          const product = selected ? await api(`/products/${selected}`) : null;
          if (tr.dataset.selection !== selected || !tr.isConnected) return;
          tr.dataset.rate = item.product_id === product?.id ? item.rate : product?.price || '0';
          $('.rate',tr).textContent = currency(tr.dataset.rate);
          $('.row-stock',tr).textContent = product ? `${product.stock_quantity} in stock` : 'Select a product to check stock';
          recalculate();
        } catch (error) { showMessage(error.message,false,'#dialog-message'); }
        finally { if (tr.dataset.selection === selected) tr.dataset.loading = 'false'; }
      };
    }
    recalculate();
  }
  order.items.forEach(addRow);
  if (!order.items.length) addRow();
  if (editable) $('#add-item').onclick = () => addRow();
  $('#discount').oninput = recalculate;
  $('#order-form').onsubmit = event => {
    event.preventDefault(); busy($('button[type=submit]',event.target),async () => {
      if ($$('#order-items tr').some(row => row.dataset.loading === 'true')) throw new Error('Please wait for product details to finish loading.');
      const items = $$('#order-items tr').map(row => ({product_id:$('.product-select',row).value,quantity:$('.quantity',row).value}));
      if (!items.length) throw new Error('Add at least one product.');
      if (new Set(items.map(i => i.product_id)).size !== items.length) throw new Error('Duplicate products are not allowed.');
      const data = Object.fromEntries(new FormData(event.target)); data.items = items;
      const saved = await api(`/orders${id ? '/' + id : ''}`,{method:id ? 'PUT' : 'POST',body:data});
      await orderEditor(saved.id); showMessage('Draft saved. Stock has not changed.',true,'#dialog-message'); await loadRecords();
    },'#dialog-message');
  };
  for (const action of ['confirm','cancel']) {
    const button = $(`#${action}-order`);
    if (button) button.onclick = () => busy(button, async () => {
      if (!window.confirm(`${action === 'confirm' ? 'Confirm the saved order and deduct stock? Unsaved edits will not be included.' : 'Cancel this order? Stock will be restored if it was Confirmed.'}`)) return;
      await api(`/orders/${id}/${action}`,{method:'POST'});
      await orderEditor(id); showMessage(`Order ${action === 'confirm' ? 'confirmed' : 'cancelled'}.`,true,'#dialog-message'); await loadRecords();
    },'#dialog-message');
  }
}

async function start() {
  const session = await api('/session'); csrf = session.csrf_token; user = session.user;
  if (currentPage === 'login') {
    $('#login-form').onsubmit = event => {
      event.preventDefault(); busy($('button[type=submit]',event.target),async () => {
        await api('/login',{method:'POST',body:Object.fromEntries(new FormData(event.target))});
        window.location.assign('/orders');
      });
    };
    return;
  }
  if (!user) { window.location.assign('/login'); return; }
  $('#logout').onclick = event => busy(event.target,async () => { await api('/logout',{method:'POST'}); window.location.assign('/login'); });
  $('#page-description').textContent = descriptions[currentPage];
  if (currentPage === 'reports') {
    $('#filters').innerHTML = '<label>Report<select name="report"><option value="customer-sales">Customer sales</option><option value="product-sales">Product sales</option><option value="low-stock">Low stock</option><option value="stock-movements">Stock movements</option></select></label>' + field('start_date','From','','date') + field('end_date','To','','date') + field('threshold','Stock threshold',10,'number','min="0" step="1"') + '<button type="submit">Run report</button>';
  } else {
    $('#filters').innerHTML = `<input type="search" name="q" placeholder="${currentPage === 'orders' ? 'Search order or customer' : currentPage === 'products' ? 'Search code or name' : 'Search name, email, mobile'}" aria-label="Search">` + (currentPage === 'orders' ? '<label>Status<select name="status"><option value="">All statuses</option><option>Draft</option><option>Confirmed</option><option>Cancelled</option></select></label>' : user.role === 'Admin' ? statusSelect('Active',true) : '') + (currentPage === 'products' ? field('category','Category') : '') + '<button type="submit">Apply filters</button>';
    if (currentPage === 'orders' || user.role === 'Admin') {
      $('#page-actions').innerHTML = (currentPage === 'products' ? '<button id="import-products">Import CSV</button>' : '') + `<button id="new-record" class="primary">+ New ${currentPage === 'orders' ? 'order' : currentPage === 'customers' ? 'customer' : 'product'}</button>`;
      $('#new-record').onclick = event => busy(event.target,() => currentPage === 'orders' ? orderEditor() : masterEditor());
      if ($('#import-products')) $('#import-products').onclick = importEditor;
    }
  }
  $('#filters').onsubmit = event => { event.preventDefault(); pageNumber = 1; busy($('button[type=submit]',event.target),loadRecords); };
  await loadRecords();
}
start().catch(error => showMessage(error.message));
