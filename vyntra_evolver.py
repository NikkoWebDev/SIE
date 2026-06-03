"""
VYNTRA Academic — Self-Evolving UI Agent

WARNING: This agent modifies source files. Use with --dry-run to preview changes.
Always review diffs before committing. Requires OPENROUTER_API_KEY in environment.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Configuration (from environment) ──
OPENROUTER_API_KEY = os.environ.get("VYNTRA_EVOLVER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("ERROR: Set VYNTRA_EVOLVER_API_KEY or OPENROUTER_API_KEY in environment.")
    sys.exit(1)

# Models
MODEL_ESTRATEGA = os.environ.get("VYNTRA_EVOLVER_STRATEGIST", "nvidia/nemotron-3-super-120b-a12b:free")
MODEL_CODER = os.environ.get("VYNTRA_EVOLVER_CODER", "qwen/qwen3-coder-480b-a35b:free")

MAX_ITERATIONS = int(os.environ.get("VYNTRA_EVOLVER_MAX_ITERATIONS", "3"))
DRY_RUN = os.environ.get("VYNTRA_EVOLVER_DRY_RUN", "false").lower() == "true"

PROJECT_DIR = Path(__file__).resolve().parent

# Allowlist of files the agent may modify
ALLOWED_TARGETS = {
    "src/pages/login.astro",
    "src/pages/dashboard.astro",
    "src/components/AIChat.astro",
    "src/styles/theme.css",
}


def _load_openai_client():
    import openai
    return openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "http://localhost:4321",
            "X-Title": "VYNTRA Core Autonomous Evolver",
        },
    )


def analizar_ui_con_ia(client, html_content, errores_consola):
    print(f"\n  Strategist ({MODEL_ESTRATEGA}) analysing UI...")
    prompt = f"""
    You are the Principal Interaction Designer for VYNTRA Academic.
    Inspect the current DOM HTML and propose a critical UI improvement
    following Apple-level design (clean layout, balanced spacing, elegant hover states).

    Current HTML:
    {html_content[:4000]}

    Console errors:
    {errores_consola if errores_consola else "None"}

    Choose a target file from this allowlist: {', '.join(sorted(ALLOWED_TARGETS))}

    RULE: Respond ONLY with valid JSON. No markdown. No explanations.

    {{
      "idea": "Short description of the optimisation",
      "target_file": "src/pages/...",
      "prompt_for_frontend": "Specific technical instructions for the developer"
    }}
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_ESTRATEGA,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.split("```json")[-1].split("```")[0].strip()
        elif raw.startswith("```"):
            raw = raw.split("```")[-1].split("```")[0].strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  Failed to parse strategist output: {e}")
        return None


def ejecutar_refactor_frontend(client, prompt_frontend, target_file):
    print(f"  Coder ({MODEL_CODER}) implementing changes for {target_file}...")
    target_path = PROJECT_DIR / target_file
    if not target_path.exists():
        print(f"  Target file not found: {target_path}")
        return None

    codigo_actual = target_path.read_text(encoding="utf-8")
    prompt = f"""
    You are a Senior Frontend Developer for VYNTRA Academic.

    Apply this improvement to `{target_file}`:
    {prompt_frontend}

    Current code:
    ```astro
    {codigo_actual}
    ```

    RULES:
    1. Return the COMPLETE rewritten file. No ellipsis or placeholders.
    2. Preserve imports, frontmatter, and existing logic.
    3. Wrap response ONLY in ```astro ... ```. No extra text.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_CODER,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        if "```astro" in raw:
            code = raw.split("```astro")[-1].split("```")[0].strip()
        elif "```" in raw:
            code = raw.split("```")[-1].split("```")[0].strip()
        else:
            code = raw.strip()
        if len(code) < 40 or "---" not in code:
            print("  Generated code too short or corrupt — aborting")
            return None
        return code
    except Exception as e:
        print(f"  Error during code generation: {e}")
        return None


def validar_build_astro():
    print("  Running build validation...")
    result = subprocess.run(
        "npm run build", capture_output=True, text=True, shell=True,
        cwd=str(PROJECT_DIR),
    )
    return result.returncode == 0, result.stderr


def ejecutar_ecosistema_autonomo(args):
    client = _load_openai_client()

    with sync_playwright() as p:
        print("Launching Playwright browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        errores_consola = []
        page.on("console", lambda msg: errores_consola.append(msg.text) if msg.type == "error" else None)

        rutas = [
            "http://localhost:4321/login",
            "http://localhost:4321/dashboard",
            "http://localhost:4321/estudiante",
            "http://localhost:4321/docente",
        ]

        for ciclo in range(1, MAX_ITERATIONS + 1):
            for ruta in rutas:
                print(f"\n{'='*60}")
                print(f"Cycle {ciclo}/{MAX_ITERATIONS} | Auditing: {ruta}")
                print(f"{'='*60}")

                try:
                    page.goto(ruta, timeout=10000)
                    time.sleep(3)
                    html = page.content()

                    analysis = analizar_ui_con_ia(client, html, errores_consola)
                    if not analysis or "target_file" not in analysis:
                        print("  No valid proposal — skipping")
                        errores_consola.clear()
                        continue

                    target = analysis["target_file"]
                    allowed = any(target.endswith(a) for a in ALLOWED_TARGETS)
                    if not allowed:
                        print(f"  Target '{target}' not in allowlist — skipping")
                        errores_consola.clear()
                        continue

                    full_path = PROJECT_DIR / target
                    if not full_path.exists():
                        print(f"  File not found: {full_path} — skipping")
                        errores_consola.clear()
                        continue

                    print(f"  Idea: {analysis['idea']}")
                    print(f"  Target: {target}")

                    backup = full_path.read_text(encoding="utf-8")
                    new_code = ejecutar_refactor_frontend(client, analysis["prompt_for_frontend"], target)

                    if new_code is None:
                        errores_consola.clear()
                        continue

                    if DRY_RUN or args.dry_run:
                        print("  [DRY RUN] Would write:", full_path)
                        print(f"  [DRY RUN] Diff preview ({len(new_code)} chars)")
                        errores_consola.clear()
                        continue

                    full_path.write_text(new_code, encoding="utf-8")

                    ok, err = validar_build_astro()
                    if ok:
                        print(f"  Build OK — changes applied to {target}")
                    else:
                        print(f"  Build FAILED — rolling back {target}")
                        full_path.write_text(backup, encoding="utf-8")
                        print(f"  Stderr excerpt: {err[:300]}")

                except Exception as e:
                    print(f"  Error during audit: {e}")

                errores_consola.clear()
                if ciclo < MAX_ITERATIONS:
                    print("  Sleeping 25s before next scan...")
                    time.sleep(25)

        browser.close()

    print(f"\nFinished {MAX_ITERATIONS} cycle(s).")


def main():
    parser = argparse.ArgumentParser(description="VYNTRA Self-Evolving UI Agent")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    parser.add_argument("--cycles", type=int, default=0, help="Override MAX_ITERATIONS")
    parser.add_argument("--url", type=str, default="http://localhost:4321", help="Astro dev server URL")
    args = parser.parse_args()

    if args.cycles:
        global MAX_ITERATIONS
        MAX_ITERATIONS = args.cycles

    print(f"VYNTRA Evolver — {'DRY RUN' if (DRY_RUN or args.dry_run) else 'LIVE'}")
    print(f"Max cycles: {MAX_ITERATIONS}")
    print(f"Targets allowed: {len(ALLOWED_TARGETS)}")
    print(f"Strategist: {MODEL_ESTRATEGA}")
    print(f"Coder: {MODEL_CODER}")
    print()

    ejecutar_ecosistema_autonomo(args)


if __name__ == "__main__":
    main()
