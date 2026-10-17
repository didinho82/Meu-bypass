import re
from fastapi import FastAPI
from playwright.async_api import async_playwright

app = FastAPI()

async def bypass_cloudflare(url: str):
    async with async_playwright() as p:
        # Inicia o Chromium
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # INJEÇÃO MANUAL DE STEALTH (Substitui a biblioteca)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        try:
            await page.goto(url, timeout=45000)
            await page.wait_for_timeout(12000) # Espera o Cloudflare
            
            try:
                btn = await page.query_selector('button:has-text("Get Link"), button:has-text("Continue")')
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(5000)
            except:
                pass

            final_url = page.url
            html = await page.content()
            
            if "delta" in final_url or "key" in html.lower():
                return final_url, html
            return None, "Cloudflare bloqueou"
        except Exception as e:
            return None, str(e)
        finally:
            await browser.close()

@app.get("/bypass")
async def process_bypass(url: str):
    final_url, html = await bypass_cloudflare(url)
    
    if not final_url:
        return {"success": False, "error": "Falha no Cloudflare"}

    key = None
    m = re.search(r'(?:key|chave)[^A-Z0-9]{0,10}([A-Z0-9]{4,}(?:-[A-Z0-9]{4,})+)', html, re.IGNORECASE)
    if m: key = m.group(1).strip().upper()
    else:
        patterns = [r"\b[A-Z0-9]{8}-[A-Z0-9]{8}-[A-Z0-9]{8}-[A-Z0-9]{8}\b", r"\b[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}\b"]
        for pat in patterns:
            match = re.search(pat, html)
            if match:
                key = match.group(0)
                break

    return {"success": True, "final_url": final_url, "key": key}
