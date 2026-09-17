import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:4173';
const outputDir = path.resolve('artifacts/ui-audit');
await mkdir(outputDir, { recursive: true });

const requiredNames = [
  'desktop-stock',
  'desktop-matrix',
  'desktop-flow',
  'desktop-vulnerability',
  'mobile-stock',
  'mobile-matrix',
  'mobile-flow',
  'mobile-vulnerability',
];

async function assertProductSurface(page, expectedViewport) {
  await page.waitForFunction(() => document.querySelectorAll('#map-nodes .node').length === 6);
  const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
  if (viewport.width !== expectedViewport.width || viewport.height !== expectedViewport.height) {
    throw new Error(`Viewport contract failed: expected ${expectedViewport.width}x${expectedViewport.height}, got ${viewport.width}x${viewport.height}`);
  }
  const bodyText = await page.locator('body').innerText();
  if (bodyText.includes('Alpha 0.6') || bodyText.includes('ALL LAYERS') || bodyText.includes('TOATE STRATURILE')) {
    throw new Error('Normal product surface exposes forbidden Alpha/all-layer metadata');
  }
  const nodeCodeCount = await page.locator('.node-code').count();
  if (nodeCodeCount !== 0) throw new Error('Internal sector codes are visible on the map');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 3) throw new Error(`Unexpected horizontal overflow: ${overflow}px`);
}

async function capture(browser, name, viewport, action) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await assertProductSurface(page, viewport);
  if (action) await action(page);
  await page.waitForTimeout(250);
  await assertProductSurface(page, viewport);
  await page.screenshot({ path: path.join(outputDir, `${name}.png`), fullPage: true });
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  const desktop = { width: 1440, height: 1100 };
  const mobile = { width: 390, height: 844 };

  await capture(browser, 'desktop-stock', desktop, async page => {
    await page.locator('#stock-tab').click();
    await page.getByRole('button', { name: 'General government' }).first().click();
  });

  await capture(browser, 'desktop-matrix', desktop, async page => {
    await page.locator('#stock-tab').click();
    await page.locator('#matrix-tab').click();
    await page.locator('#flow-matrix').waitFor({ state: 'visible' });
  });

  await capture(browser, 'desktop-flow', desktop, async page => {
    await page.locator('#flow-tab').click();
    if (await page.locator('#stock-subview-controls').isVisible()) throw new Error('Stock-only matrix controls are visible in FLOW VIEW');
    await page.locator('[data-layer="fiscal"]').click();
    await page.getByRole('button', { name: 'General government' }).first().click();
  });

  await capture(browser, 'desktop-vulnerability', desktop, async page => {
    await page.getByRole('button', { name: /Public debt and refinancing pressure/ }).click();
  });

  await capture(browser, 'mobile-stock', mobile, async page => {
    await page.locator('#stock-tab').click();
    await page.getByRole('button', { name: 'General government' }).first().click();
  });

  await capture(browser, 'mobile-matrix', mobile, async page => {
    await page.locator('#stock-tab').click();
    await page.locator('#matrix-tab').click();
    await page.locator('#flow-matrix').waitFor({ state: 'visible' });
  });

  await capture(browser, 'mobile-flow', mobile, async page => {
    await page.locator('#flow-tab').click();
    if (await page.locator('#stock-subview-controls').isVisible()) throw new Error('Stock-only matrix controls are visible in FLOW VIEW');
    await page.locator('[data-layer="fiscal"]').click();
    await page.getByRole('button', { name: 'General government' }).first().click();
  });

  await capture(browser, 'mobile-vulnerability', mobile, async page => {
    await page.getByRole('button', { name: /Public debt and refinancing pressure/ }).click();
  });

  console.log(`Created ${requiredNames.length} viewport-verified visual-audit captures in ${outputDir}`);
} finally {
  await browser.close();
}
