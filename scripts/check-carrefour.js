const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox','--disable-setuid-sandbox','--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto('https://iotadmin-2.eu.aiootech.com/aioo_iot_admin_console/app/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.waitForSelector('input[name="dashboard_login"]', { timeout: 10000 });
  await page.type('input[name="dashboard_login"]', 'Riad');
  await page.type('input[name="dashboard_password"]', 'LKLJ54jPOHLKH');
  await page.evaluate(() => {
    for (const b of document.querySelectorAll('button')) { if (b.textContent.includes('Authentication')) { b.click(); break; } }
  });
  await new Promise(r => setTimeout(r, 10000));
  
  // Go to Devices section
  await page.evaluate(() => {
    const links = document.querySelectorAll('a');
    for (const l of links) {
      if (l.textContent.trim() === 'Devices') { l.click(); break; }
    }
  });
  await new Promise(r => setTimeout(r, 8000));
  
  // Type "Carrefour" in the location filter input (it's an autocomplete)
  const inputs = await page.$$('input[placeholder="Filter by location"]');
  if (inputs.length > 0) {
    await inputs[0].click();
    await inputs[0].type('Carrefour', { delay: 100 });
    await new Promise(r => setTimeout(r, 3000));
    
    // Check if any autocomplete options appeared
    const options = await page.evaluate(() => {
      const panels = document.querySelectorAll('.mat-autocomplete-panel, mat-option, .cdk-overlay-pane mat-option');
      return [...panels].map(o => o.textContent.trim()).filter(t => t.length > 0);
    });
    console.log('Autocomplete options after typing "Carrefour":');
    options.forEach(o => console.log('  -', o));
    
    // Get full page text
    const text = await page.evaluate(() => document.body.innerText);
    const lines = text.split('\n');
    const carrefourLines = lines.filter(l => /carrefour|carrfour/i.test(l));
    console.log('\nCarrefour mentions in page:', carrefourLines.length);
    carrefourLines.forEach(l => console.log('  =>', l));
    
    // Check the device table for any new results
    const deviceText = await page.evaluate(() => {
      const table = document.querySelector('table') || document.querySelector('.device-table') || document.querySelector('tbody');
      return table ? table.textContent.substring(0, 2000) : 'no table found';
    });
    console.log('\nDevice table text:\n', deviceText);
  } else {
    console.log('No Filter by location input found');
  }
  
  // Also try the Dashboard section Device by location 
  // Go back to Dashboard
  await page.evaluate(() => {
    const links = document.querySelectorAll('a');
    for (const l of links) {
      if (l.textContent.trim() === 'Dashboard') { l.click(); break; }
    }
  });
  await new Promise(r => setTimeout(r, 5000));
  
  // Check if there's a search/input on Dashboard
  const dashInputs = await page.evaluate(() => {
    const inputs = document.querySelectorAll('input[type="text"], input:not([type="password"])');
    return [...inputs].map(i => ({
      placeholder: i.placeholder,
      id: i.id,
      value: i.value.substring(0, 50)
    }));
  });
  console.log('\n=== Dashboard inputs ===');
  dashInputs.forEach(i => console.log('  placeholder:', i.placeholder, 'value:', i.value));
  
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
