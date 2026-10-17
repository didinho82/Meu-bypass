import re
from fastapi import FastAPI
from playwright.async_api import async_playwright

app = FastAPI()

async def bypass_cloudflare(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        try:
            await page.goto(url, timeout=45000)
            await page.wait_for_timeout(5000) # Espera inicial
            
            # Tenta clicar na caixinha do Cloudflare / Captcha
            try:
                # Procura frames do Cloudflare ou o texto "humano"
                for frame in page.frames:
                    if "challenges.cloudflare.com" in frame.url:
                        checkbox = await frame.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await checkbox.click()
                            await page.wait_for_timeout(3000)
                
                # Tenta clicar no botão de Resgatar Recompensa se ele estiver ativo
                btn_resgatar = await page.query_selector('text="REIVINDIQUE A RECOMPENSA"')
                if btn_resgatar:
                    await btn_resgatar.click()
                    await page.wait_for_timeout(5000)
            except:
                pass

            # Espera mais um tempo para ver se o Lootlabs redireciona
            await page.wait_for_timeout(10000) 

            final_url = page.url
            html = await page.content()
            
            # Se ainda estiver no Lootlabs, não deu certo
            if "lootlabs" in final_url or "loot-link" in final_url:
                return None, "O Lootlabs exigiu verificação manual (Captcha/Vídeo)."
                
            return final_url, html
        except Exception as e:
            return None, str(e)
        finally:
            await browser.close()

@app.get("/bypass")
async def process_bypass(url: str):
    final_url, html = await bypass_cloudflare(url)
    
    if not final_url:
        return {"success": False, "error": f"Falha: {html}"}

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
