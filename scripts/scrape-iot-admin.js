/**
 * scrape-iot-admin.js — v3. Proper order: parse attention + errors FIRST, then paginate locations.
 */
const puppeteer = require('puppeteer');
const fs = require('fs');

const URL = 'https://iotadmin-2.eu.aiootech.com/aioo_iot_admin_console/app/login';
const USER = 'Riad';
const PASS = 'LKLJ54jPOHLKH';
const OUTPUT = '/tmp/rmstatus-light/iot-admin-data.json';

function ensureDir(p) { if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true }); }
ensureDir('/tmp/rmstatus-light');
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function scrape() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });

  // Login
  await page.waitForSelector('input[name="dashboard_login"]', { timeout: 10000 });
  await page.type('input[name="dashboard_login"]', USER);
  await page.type('input[name="dashboard_password"]', PASS);
  await page.evaluate(() => {
    for (const b of document.querySelectorAll('button')) {
      if (b.textContent.includes('Authentication')) { b.click(); break; }
    }
  });
  await sleep(5000);

  // === STEP 1: Parse attention + errors from page 1 (BEFORE any pagination) ===
  let text = await page.evaluate(() => document.body.innerText);

  // Totals
  function getTotals(t) {
    const results = { errorsTotal: 0, attentionTotal: 0, locationsTotal: 81 };
    const sections = [
      { key: 'errorsTotal', marker: 'Last 4 hours errors' },
      { key: 'attentionTotal', marker: 'need attention' },
    ];
    for (const sec of sections) {
      const idx = t.indexOf(sec.marker);
      if (idx >= 0) {
        const m = t.substring(idx, idx + 200).match(/of\s+(\d+)/);
        if (m) results[sec.key] = parseInt(m[1]) || 0;
      }
    }
    return results;
  }
  const totals = getTotals(text);

  // Parse attention devices (first page, complete — only 12 total)
  const attentionDevices = [];
  const attStart = text.indexOf('Devices that may need attention');
  const attMid = text.indexOf('Device by location', attStart);
  if (attStart >= 0 && attMid >= 0) {
    const section = text.substring(attStart, attMid);
    const lines = section.split('\n');
    let inData = false;
    for (const line of lines) {
      const t = line.trim();
      // Header check: the line has 'Device' AND contains tab chars (header row)
      if (!inData && t.includes('Device') && (t.includes('Cmds') || t.includes('Last seen'))) { 
        inData = true; continue; 
      }
      if (!inData && t === 'Device') { inData = true; continue; }
      if (inData && t) {
        if (t.startsWith('Items per page') || t.match(/^\d+ – \d+/)) break;
        const parts = line.split('\t');
        if (parts.length >= 4 && parts[0].trim().length > 5) {
          attentionDevices.push({
            device: parts[0].trim(),
            state: parts[1].trim(),
            lastSeen: parts[2].trim(),
            cmds: parts[3].trim(),
          });
        }
      }
    }
  }

  // Parse errors (first page only, 12 rows)
  const errorsWarnings = [];
  const errStart = text.indexOf('Last 4 hours errors');
  const errEnd = text.indexOf('Devices that may need attention', errStart);
  if (errStart >= 0 && errEnd >= 0) {
    const section = text.substring(errStart, errEnd);
    const lines = section.split('\n');
    let inData = false;
    for (const line of lines) {
      const t = line.trim();
      // Look for any line in the header area that contains key column names
      if (!inData && t.includes('Device') && (t.includes('Total errors') || t.includes('errors_count'))) { 
        inData = true; continue; 
      }
      if (!inData && t === 'Device') { inData = true; continue; }
      if (inData && t) {
        if (t.startsWith('Items per page') || t.match(/^\d+ – \d+/)) break;
        const parts = line.split('\t');
        if (parts.length >= 4 && parts[0].trim().length > 5) {
          errorsWarnings.push({
            device: parts[0].trim(),
            state: parts[1].trim(),
            errors: parseInt(parts[2]) || 0,
            warnings: parseInt(parts[3]) || 0,
          });
        }
      }
    }
  }

  console.log(`Attention: ${attentionDevices.length}, Errors: ${errorsWarnings.length}, Totals: ${JSON.stringify(totals)}`);

  // === STEP 2: Collect all location pages ===
  function parseLocations(t) {
    const idx = t.indexOf('Device by location');
    if (idx < 0) return [];
    const chunk = t.substring(idx);
    const lines = chunk.split('\n');
    const locs = [];
    for (const line of lines) {
      const parts = line.split('\t');
      if (parts.length >= 5 && parts[0].trim().length > 1
          && !parts[0].trim().startsWith('Venue')
          && !parts[0].trim().startsWith('Change')
          && !parts[0].trim().startsWith('Item')
          && !parts[0].trim().startsWith('Device by')) {
        locs.push({
          venue: parts[0].trim(),
          j3011: parseInt(parts[1]) || 0,
          jnx30: parseInt(parts[2]) || 0,
          jnx42: parseInt(parts[3]) || 0,
          total: parseInt(parts[4]) || 0,
        });
      }
    }
    return locs;
  }

  // Get page 1 locations
  let allLocations = parseLocations(text);
  const seen = new Set(allLocations.map(l => l.venue));
  console.log(`Page 1: ${allLocations.length} locations`);

  // Paginate: click location section's Next button (3rd group of icon buttons)
  for (let i = 0; i < 20; i++) {
    const r = await page.evaluate(() => {
      const allBtns = document.querySelectorAll('button');
      const iconBtns = [];
      for (const b of allBtns) {
        if (!b.textContent.trim()) iconBtns.push(b);
      }
      // Group = 3 for location section (indices 8-11)
      // The location table's "Next" button should be enabled if more pages
      if (iconBtns.length >= 12) {
        const next = iconBtns[10]; // index 10 = Next button for 3rd section
        if (next && !next.disabled) { next.click(); return true; }
      }
      // Fallback: try other icon buttons
      // We're looking for the 3rd enabled icon button
      let enabledCount = 0;
      for (let j = 0; j < iconBtns.length; j += 4) {
        // Each section has 4 buttons: First(0), Prev(1), Next(2), Last(3)
        const group = iconBtns.slice(j, j + 4);
        if (group.length === 4) {
          // The "Next" button is index 2 of each group
          const nb = group[2];
          if (nb && !nb.disabled) {
            enabledCount++;
            if (enabledCount === 3) { // 3rd group = location section
              nb.click();
              return true;
            }
          }
        }
      }
      return false;
    });
    if (!r) {
      console.log(`   Pagination ended at attempt ${i + 1}`);
      break;
    }
    await sleep(2000);
    text = await page.evaluate(() => document.body.innerText);
    const locs = parseLocations(text);
    let added = 0;
    for (const l of locs) {
      if (!seen.has(l.venue)) {
        seen.add(l.venue);
        allLocations.push(l);
        added++;
      }
    }
    console.log(`   Page ${i + 2}: ${locs.length} venues (${added} new, ${allLocations.length} total)`);
    if (added === 0) break;
  }

  // === STEP 3: Get true offline count from Devices page ===
  // Navigate to devices page, paginate through, count "Offline" in State column
  let offlineCount = 0;
  let totalDeviceCount = 0;
  const offlineByVenue = {};
  try {
    await page.goto('https://iotadmin-2.eu.aiootech.com/aioo_iot_admin_console/app/operator/home/devices', { waitUntil: 'networkidle0', timeout: 30000 });
    await sleep(3000);

    // Get total from pagination
    let t = await page.evaluate(() => document.body.innerText);
    const m = t.match(/(\d+)\s*[–-]\s*(\d+)\s+of\s+(\d+)/);
    if (m) totalDeviceCount = parseInt(m[3]) || 0;

    // Change items per page to 100
    await page.evaluate(() => {
      // Click the items-per-page listbox (last mat-select)
      const selects = document.querySelectorAll('mat-select');
      const pp = selects[selects.length - 1];
      if (pp) { pp.click(); return true; }
      return false;
    });
    await sleep(1500);
    await page.evaluate(() => {
      const opts = document.querySelectorAll('mat-option');
      for (const o of opts) {
        if (o.textContent.trim() === '100') { o.click(); return true; }
      }
      return false;
    });
    await sleep(2000);

    // Reset pagination: click "First page" (first icon button)
    await page.evaluate(() => {
      const btns = [...document.querySelectorAll('button')];
      let iconIdx = 0;
      for (const b of btns) {
        if (!b.textContent.trim()) {
          iconIdx++;
          if (iconIdx === 1 && !b.disabled) { b.click(); return; }
        }
      }
    });
    await sleep(2000);

    // Count offline + collect MAC→venue mapping
    let offlineList = [];
    const scanOfflineGrid = async () => {
      return await page.evaluate(() => {
        const cells = [...document.querySelectorAll('[role="gridcell"]')];
        const list = [];
        // Each row = 11 cells: 0=MAC, 1=Venue, 2=Platform, 3=Version, 4=Camera, 5=State, 6=Status, 7=Age, 8=LastSeen, 9=Queue, 10=Menu
        for (let i = 0; i + 10 < cells.length; i += 11) {
          // Make sure cells[i+5] exists and has text - State column
          if (!cells[i+5]) continue;
          if (cells[i+5].textContent.trim() === 'Offline') {
            list.push({
              device: cells[i].textContent.trim(),
              venue: cells[i+1].textContent.trim(),
              state: cells[i+5].textContent.trim(),
              lastSeen: cells[i+8] ? cells[i+8].textContent.trim() : '',
            });
          }
        }
        return list;
      });
    };

    const page1 = await scanOfflineGrid();
    offlineCount += page1.length;
    offlineList.push(...page1);
    const totalPages = Math.ceil(totalDeviceCount / 100);
    console.log(`   Page 1: ${offlineCount} offline (${totalPages} pages)`);

    for (let p = 1; p < totalPages; p++) {
      const clicked = await page.evaluate(() => {
        const btns = [...document.querySelectorAll('button')];
        let iconIdx = 0;
        for (const b of btns) {
          if (!b.textContent.trim()) {
            iconIdx++;
            if (iconIdx === 3 && !b.disabled) { b.click(); return true; }
          }
        }
        return false;
      });
      if (!clicked) break;
      await sleep(2000);
      const pageN = await scanOfflineGrid();
      offlineCount += pageN.length;
      offlineList.push(...pageN);
      console.log(`   Page ${p + 1}: ${offlineCount} offline (+${pageN.length})`);
      if (pageN.length === 0 && offlineCount > 10) break;
    }

    // Group offline by venue for the wall dashboard
    
    for (const o of offlineList) {
      const v = o.venue || 'Unknown';
      if (!offlineByVenue[v]) offlineByVenue[v] = [];
      offlineByVenue[v].push(o);
    }

    console.log(`   Offline: ${offlineCount} / Total: ${totalDeviceCount}`);
    console.log(`   Top venues offline: ${Object.entries(offlineByVenue).sort((a,b)=>b[1].length-a[1].length).slice(0,5).map(([v,c])=>`${v.substring(0,30)}:${c.length}`).join(', ')}`);
  } catch (e) {
    console.log(`   ⚠ Offline count scrape failed: ${e.message}`);
  }

  await browser.close();

  const totalDevices = allLocations.reduce((s, l) => s + (l.total || 0), 0);
  const data = {
    scrapedAt: new Date().toISOString(),
    locations: allLocations,
    attentionDevices,
    errorsWarnings,
    totals,
    deviceCounts: {
      total: totalDeviceCount || totalDevices,
      offline: offlineCount,
      attention: attentionDevices.length,
    },
    offlineByVenue,
  };

  fs.writeFileSync(OUTPUT, JSON.stringify(data, null, 2));
  console.log(`\n✅ Done: ${allLocations.length} locations, ${attentionDevices.length} attention, ${errorsWarnings.length} errors`);
  console.log(`   Total devices: ${totalDevices}, Errors: ${totals.errorsTotal}, Attention total: ${totals.attentionTotal}`);
}

scrape().catch(err => {
  console.error('❌ Scrape failed:', err.message);
  process.exit(1);
});
