(() => {
  const script = document.querySelector('script[src$="app.js"]');
  const BASE = script ? script.getAttribute('src').replace(/\/app\.js$/, '') : '';
  const RENT_URL = 'https://cloud.vast.ai/?ref_id=471952';
  let OFFERS = null;

  const $ = (id) => document.getElementById(id);
  const unitPrice = (o) => o.num_gpus ? o.dph_total / o.num_gpus : o.dph_total;

  const load = () =>
    OFFERS ? Promise.resolve(OFFERS)
           : fetch(`${BASE}/data/offers.json`).then(r => r.json())
               .then(d => (OFFERS = d.offers.filter(o => o.dph_total)));

  function row(o) {
    const rel = ((o.reliability2 || 0) * 100).toFixed(1);
    const bid = o.min_bid && o.num_gpus ? '$' + (o.min_bid / o.num_gpus).toFixed(3) : '—';
    return `<tr><td class="gpu">${o.gpu_name}<span class="xn">×${o.num_gpus}</span></td>
      <td class="num price">$${unitPrice(o).toFixed(3)}</td>
      <td class="num dim">${bid}</td>
      <td class="num">$${o.dph_total.toFixed(3)}</td>
      <td class="num">${Math.floor((o.gpu_ram || 0) / 1024)} GB</td>
      <td class="num">${Math.round(o.dlperf || 0)}</td>
      <td class="num">${rel}%</td>
      <td>${o.geolocation || '—'}</td>
      <td><a class="rent" href="${RENT_URL}" target="_blank" rel="sponsored noopener">Rent →</a></td></tr>`;
  }

  // ---- offers table with filters (index page) ----
  function initTable() {
    const table = $('offers');
    if (!table) return;
    load().then(offers => {
      const names = [...new Set(offers.map(o => o.gpu_name))].sort();
      $('f-gpu').innerHTML += names.map(n => `<option>${n}</option>`).join('');
      const apply = () => {
        const gpu = $('f-gpu').value;
        const vram = +$('f-vram').value * 1024;
        const price = +$('f-price').value || Infinity;
        const ngpu = +$('f-ngpu').value;
        const rows = offers
          .filter(o => (!gpu || o.gpu_name === gpu)
            && (o.gpu_ram || 0) >= vram
            && unitPrice(o) <= price
            && (ngpu === 2 ? o.num_gpus >= 2 : ngpu === 4 ? o.num_gpus >= 4
               : ngpu ? o.num_gpus === ngpu : true))
          .sort((a, b) => unitPrice(a) - unitPrice(b));
        table.tBodies[0].innerHTML =
          rows.slice(0, 100).map(row).join('') ||
          '<tr><td colspan="9" class="note">No offers match those filters.</td></tr>';
        $('offers-note').textContent = rows.length > 100
          ? `Showing 100 of ${rows.length} matching offers (cheapest first).`
          : `${rows.length} matching offers.`;
      };
      ['f-gpu', 'f-vram', 'f-price', 'f-ngpu'].forEach(id =>
        $(id).addEventListener('input', apply));
      apply();
    });
  }

  // ---- "will my model fit" calculator ----
  function initFit() {
    const out = $('fit-result');
    if (!out) return;
    const calc = () => load().then(offers => {
      const params = +$('fit-params').value;
      const bpp = +$('fit-quant').value;
      const needGB = Math.ceil(params * bpp * 1.2 + 2);
      const fitting = offers
        .filter(o => (o.gpu_ram || 0) >= needGB * 1024)
        .sort((a, b) => unitPrice(a) - unitPrice(b));
      const seen = new Set();
      const picks = [];
      for (const o of fitting) {
        if (seen.has(o.gpu_name)) continue;
        seen.add(o.gpu_name);
        picks.push(o);
        if (picks.length === 3) break;
      }
      out.innerHTML = `<p>Estimated VRAM needed: <strong>~${needGB} GB</strong>
        (weights + overhead; long contexts need more).</p>` +
        (picks.length
          ? `<ol>${picks.map(o =>
              `<li><strong>${o.gpu_name}</strong> — ${Math.floor(o.gpu_ram / 1024)} GB
               from <strong>$${unitPrice(o).toFixed(3)}/hr</strong>
               <a class="rent" href="${RENT_URL}" target="_blank" rel="sponsored noopener">Rent →</a></li>`
            ).join('')}</ol>`
          : '<p>No single GPU fits — consider multi-GPU offers or a smaller quant.</p>');
    });
    ['fit-params', 'fit-quant'].forEach(id => $(id).addEventListener('input', calc));
    calc();
  }

  // ---- price history sparkline (GPU pages) ----
  function initSpark() {
    const sec = document.getElementById('history');
    if (!sec) return;
    const gpu = sec.dataset.gpu;
    fetch(`${BASE}/data/history.json`).then(r => r.json()).then(h => {
      const pts = (h[gpu] || []);
      if (pts.length < 2) return;
      const w = 640, ht = 120, pad = 6;
      const vals = pts.map(p => p.min);
      const lo = Math.min(...vals), hi = Math.max(...vals) || 1;
      const x = i => pad + i * (w - 2 * pad) / (pts.length - 1);
      const y = v => ht - pad - (hi === lo ? 0.5 : (v - lo) / (hi - lo)) * (ht - 2 * pad);
      const line = vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
      $('spark').innerHTML =
        `<svg viewBox="0 0 ${w} ${ht}" preserveAspectRatio="none">
           <polyline points="${line}" fill="none" stroke="#4ade80" stroke-width="2"/>
         </svg>
         <p class="note">Daily minimum $/hr per GPU · ${pts[0].d} → ${pts[pts.length - 1].d}
         · low $${lo.toFixed(3)} / high $${hi.toFixed(3)}</p>`;
    }).catch(() => {});
  }

  initTable();
  initFit();
  initSpark();
})();
