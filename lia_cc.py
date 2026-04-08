from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Load environment
from env_config import BASE_DIR, IS_COLAB, IS_WINDOWS
from scripts.utils.gpu_info import print_gpu_info

SCRIPTS_DIR = BASE_DIR / "scripts"

SCRIPT_MAP = {
    "parse": SCRIPTS_DIR / "01_parse_chapter.py",
    "scenes": SCRIPTS_DIR / "02_build_scenes.py",
    "prompts": SCRIPTS_DIR / "03_build_prompts.py",
    "queue": SCRIPTS_DIR / "04_prepare_render_queue.py",
    "run": SCRIPTS_DIR / "05_run_comfy_queue.py",
    "assemble": SCRIPTS_DIR / "09_merge_audio_video.py",
    "voices": SCRIPTS_DIR / "07_generate_voices.py",
    "assign_voices": SCRIPTS_DIR / "08_list_and_assign_voices.py",
    "timeline": SCRIPTS_DIR / "08_build_timeline.py"
}

def run_python_script(script_path: Path, args: list[str] = []) -> int:
    if not script_path.exists():
        print(f"[ERROR] No existe el script: {script_path}")
        return 1

    print(f"\n[INFO] Ejecutando: {script_path.name} {' '.join(args)}")
    result = subprocess.run([sys.executable, str(script_path)] + args, cwd=str(BASE_DIR))
    return result.returncode

def cmd_init() -> int:
    print("\n[INFO] LIA-CC Inicializado (Hybrid Mode)")
    print(f"[*] Entorno: {'Colab' if IS_COLAB else 'Windows'}")
    print(f"[*] BASE_DIR: {BASE_DIR}")
    print_gpu_info()
    return 0

def cmd_status() -> int:
    print("\n[INFO] Estado rápido de LIA-CC\n")
    # Simplificado para evitar errores de demo_project
    print("[INFO] Verifica la carpeta projects/ para ver tus capítulos.")
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lia_cc.py",
        description="Launcher principal de LIA-CC (Cuenta Cuentos)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("init", help="Verifica estructura base.")
    subparsers.add_parser("parse", help="Lee el capítulo.")
    subparsers.add_parser("scenes", help="Genera escenas.")
    subparsers.add_parser("prompts", help="Genera prompts.")
    subparsers.add_parser("queue", help="Prepara cola.")
    subparsers.add_parser("run", help="Ejecuta ComfyUI.")
    subparsers.add_parser("voices", help="Genera voces.")
    subparsers.add_parser("timeline", help="Construye timeline.")
    subparsers.add_parser("assemble", help="Genera el video final.")
    subparsers.add_parser("all", help="Corre todo en secuencia.")
    subparsers.add_parser("status", help="Muestra estado.")
    
    return parser

def main() -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args()

    if args.command == "init":
        return cmd_init()
    if args.command == "status":
        return cmd_status()
    
    if not unknown:
        print(f"[ERROR] El comando '{args.command}' requiere un project_id.")
        print(f"Ejemplo: python lia_cc.py {args.command} 1nefi_cap_01")
        return 1

    if args.command == "all":
        # Nota: 'run' (paso 05) está incluido aquí por defecto
        ordered_steps = ["parse", "scenes", "prompts", "queue", "run", "voices", "timeline", "assemble"]
        for step in ordered_steps:
            code = run_python_script(SCRIPT_MAP[step], unknown)
            if code != 0:
                print(f"\n[ERROR] El paso '{step}' falló con código {code}.")
                return code
        return 0

    if args.command in SCRIPT_MAP:
        return run_python_script(SCRIPT_MAP[args.command], unknown)

    parser.print_help()
    return 1

if __name__ == "__main__":
    raise SystemExit(main())