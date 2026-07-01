#!/usr/bin/env node
/**
 * fetch-iot-api.js — Fetch IoT device status from AiOO API
 * Replaces Puppeteer scraping with a simple HTTP call
 * Saves as /tmp/rmstatus-light/iot-admin-data.json (same format as scraper)
 */
const https = require('https');
const fs = require('fs');

const API_URL = 'https://apim-eu-1.aiootech.com/v1/iot/status/current';
const CLIENT_ID = 'b13b77ae-3d68-4560-9bf0-5de9780218b2';
const CLIENT_SECRET = 'hsdf2sdFE5g75ze2%sgD5s4dg';
const OUTPUT = '/tmp/rmstatus-light/iot-admin-data.json';

function ensureDir(p) {
  const d = require('path').dirname(p);
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}
ensureDir(OUTPUT);

function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: {
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET,
      'Accept': 'application/json',
    }}, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(new Error(`HTTP ${res.statusCode}: ${data.slice(0,200)}`));
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse error: ${e.message}`)); }
      });
    }).on('error', reject);
  });
}

async function main() {
  console.log('Fetching IoT status from API...');
  const devices = await fetch(API_URL);
  console.log(`   ${devices.length} devices received`);

  // Count by state
  const stateCount = {};
  for (const d of devices) {
    const s = d.state || 'Unknown';
    stateCount[s] = (stateCount[s] || 0) + 1;
  }
  console.log('   States:', Object.entries(stateCount).map(([s,c]) => `${s}=${c}`).join(', '));

  // Build locations from unique venues (simplified — first part before |)
  const venueMap = {};
  for (const d of devices) {
    const v = d.venue ? d.venue.split('|')[0].trim() : 'Unknown';
    if (!venueMap[v]) venueMap[v] = { venue: v, total: 0, j3011: 0, jnx30: 0, jnx42: 0 };
    venueMap[v].total++;
    const p = (d.platform || '').toLowerCase();
    if (p === 'j30' || p === 'j3011') venueMap[v].j3011++;
    else if (p === 'jnx30') venueMap[v].jnx30++;
    else if (p === 'jnx42') venueMap[v].jnx42++;
  }
  const locations = Object.values(venueMap).sort((a, b) => b.total - a.total);

  // Attention devices: offline + tracking state
  const attentionDevices = devices
    .filter(d => (d.state || '').toLowerCase() === 'offline')
    .slice(0, 50)
    .map(d => ({
      device: d.aioo_id,
      state: d.state || '',
      lastSeen: d.last_seen || '',
      cmds: '0',
    }));

  // Errors/warnings
  const errorsWarnings = devices
    .filter(d => (d.monitoring_status || '').toLowerCase() === 'error' || (d.logger_status || '').toLowerCase() === 'error')
    .slice(0, 50)
    .map(d => ({
      device: d.aioo_id,
      state: d.state || '',
      errors: (d.monitoring_status || '').toLowerCase() === 'error' ? 1 : 0,
      warnings: (d.logger_status || '').toLowerCase() === 'warning' ? 1 : 0,
    }));

  // Offline by venue (real venue names from API)
  const offlineByVenue = {};
  for (const d of devices) {
    if ((d.state || '').toLowerCase() === 'offline') {
      const v = d.venue || 'Unknown';
      if (!offlineByVenue[v]) offlineByVenue[v] = [];
      offlineByVenue[v].push({
        device: d.aioo_id,
        venue: v,
        state: d.state || '',
        lastSeen: d.last_seen || '',
      });
    }
  }

  const totalOffline = stateCount['Offline'] || stateCount['offline'] || 0;
  const totalOnline = devices.length - totalOffline;

  const data = {
    scrapedAt: new Date().toISOString(),
    locations,
    attentionDevices,
    errorsWarnings,
    totals: {
      errorsTotal: errorsWarnings.length,
      attentionTotal: attentionDevices.length,
      locationsTotal: locations.length,
    },
    deviceCounts: {
      total: devices.length,
      offline: totalOffline,
      online: totalOnline,
      attention: attentionDevices.length,
    },
    offlineByVenue,
  };

  fs.writeFileSync(OUTPUT, JSON.stringify(data, null, 2));
  console.log(`\n✅ Done: ${locations.length} locations, ${attentionDevices.length} attention, ${errorsWarnings.length} errors`);
  console.log(`   Total: ${devices.length}, Online: ${totalOnline}, Offline: ${totalOffline}`);
}

main().catch(err => {
  console.error('❌ Failed:', err.message);
  process.exit(1);
});
