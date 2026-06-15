// Copy of /tmp/build-branded.js — generates rmstatus.html
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const IMG_DIR = '/home/iots/.openclaw/workspace/iot-camera';
const JPG_QUALITY = 20;
const MAX_WIDTH = 400;

const VENUES = {
  'Umm Suqeim': { parent: 'Union Coop', dir: 'ummu-suqeim', totalDevices: 27, warningDevices: 2, errorDevices: 0, macs: ['ba','b9','b8','b7','b5','b4','b3','b2','ae','ad','ac','ab','a4','9e','96'] },
  'Al Warqa': { parent: 'Union Coop', dir: 'al-warqa', totalDevices: 33, warningDevices: 0, errorDevices: 1, macs: ['be','bc','bb','b0','92','91','90','8f','8e','8d','8c','89','88','86','84'] },
  'Lulu Al Wahda': { parent: 'Lulu', dir: 'lulu', totalDevices: 37, warningDevices: 0, errorDevices: 0, macs: ['af','a8','a7','a5','a3','a2','a1','a0','9f','98','97','28','27','26','25'] }
};

const BRANDS = {
  'Union Coop': {
    logo: `<svg viewBox="0 0 160 40" xmlns="http://www.w3.org/2000/svg" style="height:36px"><rect x="0" y="0" width="40" height="40" rx="8" fill="#16a34a"/><text x="20" y="28" font-family="Arial,sans-serif" font-size="24" font-weight="900" fill="#fff" text-anchor="middle">UC</text><text x="50" y="27" font-family="Arial,sans-serif" font-size="20" font-weight="800" fill="#e2e8f0" letter-spacing="-.3">Union Coop</text></svg>`,
    color: '#22c55e'
  },
  'Lulu': {
    logo: `<svg viewBox="0 0 120 40" xmlns="http://www.w3.org/2000/svg" style="height:36px"><rect x="0" y="0" width="40" height="40" rx="8" fill="#dc2626"/><text x="20" y="28" font-family="Arial,sans-serif" font-size="24" font-weight="900" fill="#fff" text-anchor="middle">L</text><text x="50" y="27" font-family="Arial,sans-serif" font-size="20" font-weight="800" fill="#e2e8f0" letter-spacing="-.3">Lulu</text></svg>`,
    color: '#ef4444'
  }
};

function getLatestImages(venueDir, macs) {
  const dir = path.join(IMG_DIR, venueDir);
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.jpg'));
  const results = [];
  for (const mac of macs) {
    const matching = files.filter(f => f.includes('_a1_00_5e_ed_02_' + mac + '.jpg'));
    if (!matching.length) continue;
    matching.sort().reverse();
    const fileName = matching[0];
    const jsonFile = path.join(dir, fileName.substring(0, 19) + '_a1_00_5e_ed_02_' + mac + '.json');
    let meta = { device: 'a1:00:5e:ed:02:' + mac, deviceId: '—', captureTime: fileName.substring(0, 19) };
    try { meta = JSON.parse(fs.readFileSync(jsonFile, 'utf8')); } catch(e) {}
    results.push({ mac, file: fileName, path: path.join(dir, fileName), timestamp: fileName.substring(0, 19), meta });
  }
  return results;
}

async function build() {
  const dateStr = new Date().toLocaleDateString('en-GB');
  const timeStr = new Date().toLocaleTimeString('en-GB');
  const groups = {};
  for (const [name, data] of Object.entries(VENUES)) {
    const parent = data.parent;
    if (!groups[parent]) groups[parent] = { brand: parent, venues: [] };
    groups[parent].venues.push({ name, data });
  }

  let groupHtml = '';
  let allKf = '';
  let animN = 0;
  let totalDevices = 0, totalWarnings = 0, totalErrors = 0;

  for (const [brand, group] of Object.entries(groups)) {
    const logo = BRANDS[brand].logo;
    let brandTotal = 0, brandWarn = 0, brandErr = 0;
    let venueCardsHtml = '';

    for (const { name, data } of group.venues) {
      totalDevices += data.totalDevices;
      totalWarnings += data.warningDevices;
      totalErrors += data.errorDevices;
      brandTotal += data.totalDevices;
      brandWarn += data.warningDevices;
      brandErr += data.errorDevices;

      const images = data.dir ? getLatestImages(data.dir, data.macs) : [];
      let slides = '';
      let kf = '';

      if (images.length) {
        const t = images.length;
        const dur = t * 3.5;
        const pp = 100 / t;
        for (let i = 0; i < images.length; i++) {
          const img = images[i];
          try {
            const buf = fs.readFileSync(img.path);
            const compressed = await sharp(buf).resize(MAX_WIDTH, undefined, { fit: 'inside', withoutEnlargement: true }).jpeg({ quality: JPG_QUALITY }).toBuffer();
            const b64 = compressed.toString('base64');
            const label = img.meta.captureTime || img.timestamp;
            slides += '<div class="s"><img src="data:image/jpeg;base64,' + b64 + '" alt=""><div class="sl">' + label + '</div></div>';
            const s = i * pp, pe = s + pp * 0.72, te = s + pp;
            kf += '@keyframes a' + animN + '{0%,' + s.toFixed(1) + '%{transform:translateX(-' + (i*100) + '%)}' + pe.toFixed(1) + '%{transform:translateX(-' + (i*100) + '%)}' + te.toFixed(1) + '%{transform:translateX(-' + ((i+1)%t*100) + '%)}}';
            animN++;
          } catch(e) {}
        }
        allKf += kf + '.t' + (animN-images.length) + '{animation:a' + (animN-images.length) + ' ' + dur + 's infinite}\n';
      }

      const warn = data.warningDevices > 0;
      const err = data.errorDevices > 0;
      let cls = 'vin';
      if (err) cls += ' er';
      else if (warn) cls += ' wa';

      const carousel = images.length
        ? '<div class="cr"><div class="tr t' + (animN-images.length) + '">' + slides + '</div></div>'
        : '<div class="nocam">Camera not configured</div>';

      venueCardsHtml += '<div class="vsub ' + cls + '"><div class="vh2"><div class="vn2">' + name + '</div><span class="vm2">' + data.totalDevices + '</span></div><div class="vg3"><div class="vi"><span class="il">tracking</span><span class="iv ig">' + data.totalDevices + '</span></div><div class="vi"><span class="il">warnings</span><span class="iv ' + (warn?'iy':'ig') + '">' + data.warningDevices + '</span></div><div class="vi"><span class="il">errors</span><span class="iv ' + (err?'ir':'ig') + '">' + data.errorDevices + '</span></div></div>' + carousel + '</div>';
    }

    const hasErr = brandErr > 0;
    const hasWarn = brandWarn > 0;
    const borderCls = hasErr ? 'be' : hasWarn ? 'bw' : 'bg';

    groupHtml += '<div class="brand-card ' + borderCls + '"><div class="brand-hdr"><div class="brand-logo">' + logo + '</div><div class="brand-stats"><span class="bs"><span class="bv">' + brandTotal + '</span> devices</span><span class="bs"><span class="bv" style="color:#4ade80">' + (brandTotal - brandWarn - brandErr) + '</span> ok</span>' + (brandWarn > 0 ? '<span class="bs"><span class="bv" style="color:#facc15">' + brandWarn + '</span> warn</span>' : '') + (brandErr > 0 ? '<span class="bs"><span class="bv" style="color:#f87171">' + brandErr + '</span> err</span>' : '') + '</div></div><div class="brand-body"><div class="sub-venues">' + venueCardsHtml + '</div></div></div>';
  }

  const html = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1.0">\n<title>RM · IoT</title>\n<style>\n*{margin:0;padding:0;box-sizing:border-box}\nbody{font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;background:#09090b;color:#f1f5f9;min-height:100vh;padding:0 0 30px}\n.hdr{padding:18px 20px 10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}\n.hdr h1{font-size:16px;font-weight:700;color:#e2e8f0}\n.hdr h1 span{color:#52525b;font-weight:400}\n.hdr .ts{font-size:10px;color:#52525b;font-family:.SF Mono.,Consolas,monospace}\n.live{display:inline-flex;align-items:center;gap:6px;background:#052e16;color:#4ade80;padding:0 10px;border-radius:20px;font-size:9px;font-weight:700;height:20px}\n.live::before{content:"";width:6px;height:6px;background:#4ade80;border-radius:50%;animation:pulse 2s infinite}\n@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}\n.mr{display:flex;gap:4px;padding:0 20px 10px;flex-wrap:wrap}\n.mi{padding:8px 14px;background:#18181b;border-radius:8px;border:1px solid #27272a;font-size:11px;display:flex;align-items:center;gap:8px}\n.mi .mv{font-weight:800;font-size:18px}\n.mi .ml{color:#52525b;font-weight:500}\n.mi .mv.b{color:#60a5fa}.mi .mv.g{color:#4ade80}.mi .mv.y{color:#facc15}.mi .mv.r{color:#f87171}.mi .mv.p{color:#a78bfa}\n.bc{display:flex;flex-direction:column;gap:10px;padding:0 20px}\n.brand-card{background:#18181b;border-radius:12px;overflow:hidden;border:1px solid #27272a}\n.brand-card.be{border-left:4px solid #ef4444}\n.brand-card.bw{border-left:4px solid #eab308}\n.brand-card.bg{border-left:4px solid #22c55e}\n.brand-hdr{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #27272a;flex-wrap:wrap;gap:8px}\n.brand-logo{display:flex;align-items:center}\n.brand-stats{display:flex;gap:10px;flex-wrap:wrap}\n.bs{font-size:10px;color:#52525b;display:flex;align-items:center;gap:4px}\n.bs .bv{font-size:13px;font-weight:700;color:#e2e8f0}\n.brand-body{padding:10px 14px 14px}\n.sub-venues{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px}\n.vsub{background:#131316;border-radius:8px;overflow:hidden;border:1px solid #27272a}\n.vsub.er{border-left:2px solid #ef4444}\n.vsub.wa{border-left:2px solid #eab308}\n.vh2{display:flex;justify-content:space-between;align-items:center;padding:8px 10px}\n.vn2{font-size:12px;font-weight:600;color:#e2e8f0}\n.vm2{font-size:13px;font-weight:700;color:#e2e8f0}\n.vg3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:3px;padding:0 10px 8px}\n.vi{text-align:center;padding:5px 3px;background:#09090b;border-radius:5px}\n.il{font-size:7px;text-transform:uppercase;color:#52525b;letter-spacing:.5px;display:block;margin-bottom:1px}\n.iv{font-size:16px;font-weight:800;line-height:1}\n.iv.ig{color:#4ade80}.iv.iy{color:#facc15}.iv.ir{color:#f87171}\n.cr{border-radius:5px;overflow:hidden;background:#09090b;aspect-ratio:16/6;margin:0 10px 8px}\n.tr{display:flex;height:100%;will-change:transform}\n.s{min-width:100%;height:100%;position:relative;flex-shrink:0}\n.s img{width:100%;height:100%;object-fit:cover;display:block}\n.sl{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.8));padding:14px 8px 4px;font-size:8px;color:#52525b;font-family:.SF Mono.,Consolas,monospace;pointer-events:none}\n.nocam{padding:24px;text-align:center;color:#52525b;font-size:10px;margin:0 10px 8px;background:#09090b;border-radius:5px}\n.ax{margin:0 20px;margin-top:10px}\n.ac{background:#18181b;border-radius:10px;overflow:hidden;border:1px solid #27272a}\n.axh{padding:10px 14px;background:#1c1917;border-bottom:1px solid #292524;display:flex;justify-content:space-between;align-items:center}\n.axh h3{font-size:11px;color:#a1a1aa;font-weight:600}\n.axh .an{background:#292524;color:#a1a1aa;padding:1px 8px;border-radius:8px;font-size:10px;font-weight:600}\n.at{width:100%;border-collapse:collapse;font-size:11px}\n.at th{padding:7px 12px;color:#52525b;font-size:8px;text-transform:uppercase;letter-spacing:.5px;text-align:left;background:#18181b;border-bottom:1px solid #27272a}\n.at td{padding:7px 12px;border-bottom:1px solid #27272a}\n.at tr:last-child td{border-bottom:none}\n.at .mc{font-family:.SF Mono.,Consolas,monospace;color:#52525b;font-size:10px}\n.at .er{color:#f87171;font-weight:700}\n.at .wr{color:#facc15;font-weight:700}\n.at .st{color:#60a5fa;font-weight:600}\n.ft{text-align:center;padding:24px;color:#27272a;font-size:9px}\n' + allKf + '@media(max-width:600px){.sub-venues{grid-template-columns:1fr}.mr{padding:0 12px 8px}.hdr{padding:14px 12px 8px}.bc{padding:0 12px}.ax{margin:0 12px;margin-top:10px}}\n</style>\n</head>\n<body>\n<div class="hdr"><h1><img src="aioo-logo.jpg" alt="AiOO" style="height:22px;vertical-align:middle;margin-right:6px;border-radius:4px">RM <span>· Retail Media IoT</span></h1><div style="display:flex;align-items:center;gap:8px"><div class="ts">' + dateStr + ' ' + timeStr + '</div><div class="live">Live</div></div></div>\n<div class="mr"><div class="mi"><span class="mv b">' + totalDevices + '</span><span class="ml">total</span></div><div class="mi"><span class="mv g">' + (totalDevices - totalWarnings - totalErrors) + '</span><span class="ml">ok</span></div><div class="mi"><span class="mv y">' + totalWarnings + '</span><span class="ml">warnings</span></div><div class="mi"><span class="mv r">' + totalErrors + '</span><span class="ml">errors</span></div><div class="mi"><span class="mv p">J30</span><span class="ml">platform</span></div><div class="mi"><span class="mv">~13h</span><span class="ml">uptime</span></div></div>\n<div class="bc">' + groupHtml + '</div>\n<div class="ax"><div class="ac"><div class="axh"><h3>Devices needing attention</h3><span class="an">3</span></div><table class="at"><tr><th>mac</th><th>venue</th><th>state</th><th>errors</th><th>warnings</th></tr><tr><td><span class="mc">a1:00:5e:ed:02:bb</span></td><td>Union Coop · Al Warqa</td><td><span class="st">TRACKING</span></td><td><span class="er">575</span></td><td><span class="wr">383</span></td></tr><tr><td><span class="mc">a1:00:5e:ed:02:b7</span></td><td>Union Coop · Umm Suqeim</td><td><span class="st">TRACKING</span></td><td><span class="er">52</span></td><td><span class="wr">30</span></td></tr><tr><td><span class="mc">a1:00:5e:ed:02:b5</span></td><td>Union Coop · Umm Suqeim</td><td><span class="st">TRACKING</span></td><td><span class="er">43</span></td><td><span class="wr">25</span></td></tr></table></div></div>\n<div class="ft">AiOO Tech Dubai</div>\n</body>\n</html>';

  fs.writeFileSync('/tmp/rmstatus-light/rmstatus.html', html);
  console.log('OK - ' + (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB');
}

build().catch(e => { console.error(e); process.exit(1); });
