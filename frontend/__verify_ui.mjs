import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true, executablePath: String.raw`C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe` });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const consoleMessages = [];
page.on('console', (msg) => consoleMessages.push(`[${msg.type()}] ${msg.text()}`));
page.on('pageerror', (err) => consoleMessages.push(`[pageerror] ${err.message}`));

await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
await page.waitForSelector('text=Sacred Guidance for', { timeout: 15000 });

await page.screenshot({ path: 'C:/Users/LENOVO/AppData/Local/Temp/claude/C--Users-LENOVO-Music-assists-music-assist/97c1ddc6-12a8-41fa-b843-89bdf4d271dd/scratchpad/01-empty-state.png', fullPage: true });

// Check sidebar elements
const newConsultationBtn = await page.locator('text=New Consultation').count();
const signInBtn = await page.locator('text=Sign In to Account').count();
const promptCards = await page.locator('text=Consultation').count(); // label on each card + sidebar heading text overlap check separately
const suggestedPrompts = await page.locator('text=Standard policy on ward choir auditions').count();

console.log('RESULT new_consultation_btn_count=' + newConsultationBtn);
console.log('RESULT sign_in_btn_count=' + signInBtn);
console.log('RESULT suggested_prompt_count=' + suggestedPrompts);

// Open login modal
await page.locator('text=Sign In to Account').click();
await page.waitForSelector('text=Continue with Google', { timeout: 5000 });
await page.screenshot({ path: 'C:/Users/LENOVO/AppData/Local/Temp/claude/C--Users-LENOVO-Music-assists-music-assist/97c1ddc6-12a8-41fa-b843-89bdf4d271dd/scratchpad/02-login-modal.png', fullPage: true });

const dialogRole = await page.locator('[role="dialog"]').count();
console.log('RESULT dialog_role_count=' + dialogRole);

// Close via Escape
await page.keyboard.press('Escape');
await page.waitForTimeout(300);
const modalGoneAfterEscape = await page.locator('text=Continue with Google').count();
console.log('RESULT modal_visible_after_escape=' + modalGoneAfterEscape);

// Type in chat input
const textarea = page.locator('textarea');
await textarea.fill('Hello, testing the input box');
const inputValue = await textarea.inputValue();
console.log('RESULT textarea_value=' + JSON.stringify(inputValue));

const sendBtnDisabled = await page.locator('button[type="submit"]').isDisabled();
console.log('RESULT send_button_disabled_with_text=' + sendBtnDisabled);

await textarea.fill('');
const sendBtnDisabledEmpty = await page.locator('button[type="submit"]').isDisabled();
console.log('RESULT send_button_disabled_when_empty=' + sendBtnDisabledEmpty);

await page.screenshot({ path: 'C:/Users/LENOVO/AppData/Local/Temp/claude/C--Users-LENOVO-Music-assists-music-assist/97c1ddc6-12a8-41fa-b843-89bdf4d271dd/scratchpad/03-final.png', fullPage: true });

console.log('---CONSOLE MESSAGES---');
console.log(consoleMessages.join('\n'));

await browser.close();
