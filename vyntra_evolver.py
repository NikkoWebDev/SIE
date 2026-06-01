import os
import time
import json
import subprocess
from playwright.sync_api import sync_playwright
import requests

if os.path.exists("Vyntra"):
    os.chdir("Vyntra")
    print("[Evolución] Directorio: Vyntra")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", OPENROUTER_API_KEY)
DEEPSEEK_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO_DEEPSEEK = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

def analizar_ui_con_deepseek(html_content, errores_consola, ruta_url):
    print(f"\n[Estratega] Evaluando UI/UX...")
    prompt = f"""
    Eres el Diseñador Principal de UI de VYNTRA Academic.
    Audita el HTML y propón una optimización de diseño siguiendo estándares premium.

    URL: {ruta_url}

    REGLA DE ASIGNACIÓN:
    - /docente → 'target_file': 'src/pages/docente.astro'
    - /estudiante → 'target_file': 'src/pages/estudiante.astro'
    - /admin → 'target_file': 'src/pages/admin.astro'

    HTML:
    {html_content[:6000]}

    Errores: {errores_consola if errores_consola else "Ninguno"}

    Responde SOLO JSON:
    {{"idea": "descripción", "target_file": "ruta", "prompt_for_frontend": "directivas técnicas"}}
    """
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODELO_DEEPSEEK, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "response_format": {"type": "json_object"}}
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print(f"Error análisis: {e}")
        return None

def ejecutar_refactor_frontend(prompt_frontend, target_file):
    print(f"[Coder] Aplicando optimización en: {target_file}...")
    if not os.path.exists(target_file):
        print(f"Archivo no existe: {target_file}")
        return False
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            codigo_actual = f.read()
        partes = codigo_actual.split("---")
        frontmatter_original = ""
        html_original = codigo_actual
        if len(partes) >= 3:
            frontmatter_original = f"---{partes[1]}---"
            html_original = "---".join(partes[2:])
        prompt = f"""
        Eres Desarrollador Senior UI en VYNTRA Academic.
        Refactoriza el HTML/Astro siguiendo estas directivas:

        {prompt_frontend}

        Código actual:
        ```astro
        {html_original[:10000]}
        ```

        Devuelve SOLO el marcado mejorado en ```astro ... ``` sin frontmatter.
        """
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": MODELO_DEEPSEEK, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()
        if "```astro" in raw:
            nuevo_html = raw.split("```astro")[-1].split("```")[0].strip()
        elif "```" in raw:
            nuevo_html = raw.split("```")[-1].split("```")[0].strip()
        else:
            nuevo_html = raw
        if len(nuevo_html) > 40:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(f"{frontmatter_original}\n\n{nuevo_html}" if frontmatter_original else nuevo_html)
            print(f"Refactor aplicado.")
            return True
        print("Código generado insuficiente.")
        return False
    except Exception as e:
        print(f"Error refactor: {e}")
        return False

def validar_build_astro():
    print("[QA] Ejecutando npm run build...")
    resultado = subprocess.run("npm run build", capture_output=True, text=True, shell=True)
    return resultado.returncode == 0, resultado.stderr

def ejecutar_login_playwright(page, usuario, clave):
    print(f"[Auth] Iniciando sesión: '{usuario}'...")
    try:
        page.goto("http://localhost:4321/login", timeout=10000)
        time.sleep(2)
        input_user = page.locator("input[name='login_credential'], input[type='text']").first
        input_pass = page.locator("input[name='password'], input[type='password']").first
        btn_submit = page.locator("button[type='submit']").first
        input_user.fill(usuario)
        input_pass.fill(clave)
        btn_submit.click()
        time.sleep(4)
        return True
    except Exception as e:
        print(f"Error login: {e}")
        return False

def ejecutar_ecosistema_autonomo():
    perfiles = [
        {"usuario": "11",  "clave": "profe",  "ruta": "http://localhost:4321/docente"},
        {"usuario": "101", "clave": "alumno", "ruta": "http://localhost:4321/estudiante"},
        {"usuario": "1",   "clave": "admin",  "ruta": "http://localhost:4321/admin"},
    ]
    with sync_playwright() as p:
        print("[VYNTRA] Lanzando navegador...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        errores = []
        page.on("console", lambda msg: errores.append(msg.text) if msg.type == "error" else None)
        ciclo = 1
        while True:
            for perfil in perfiles:
                print(f"\n[Ciclo {ciclo}] Perfil: {perfil['usuario']}")
                if ejecutar_login_playwright(page, perfil['usuario'], perfil['clave']):
                    try:
                        page.goto(perfil['ruta'], timeout=10000)
                        time.sleep(3)
                        html_vista = page.content()
                        if "login" not in page.url:
                            analisis = analizar_ui_con_deepseek(html_vista, errores, perfil['ruta'])
                            if analisis and "target_file" in analisis:
                                print(f"Idea: {analisis['idea']}")
                                target_file = analisis['target_file']
                                if os.path.exists(target_file):
                                    with open(target_file, 'r', encoding='utf-8') as f:
                                        backup = f.read()
                                    if ejecutar_refactor_frontend(analisis['prompt_for_frontend'], target_file):
                                        ok, _ = validar_build_astro()
                                        if not ok:
                                            print("Build falló. Restaurando...")
                                            with open(target_file, 'w', encoding='utf-8') as f:
                                                f.write(backup)
                                        else:
                                            print("Cambios compilados correctamente.")
                    except Exception as e:
                        print(f"Error ciclo: {e}")
                errores.clear()
                try:
                    context.clear_cookies()
                    page.evaluate("() => localStorage.clear()")
                except Exception:
                    pass
                ciclo += 1
                time.sleep(20)

if __name__ == "__main__":
    ejecutar_ecosistema_autonomo()
