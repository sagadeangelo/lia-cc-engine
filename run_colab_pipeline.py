import os
import sys
import argparse
from pathlib import Path

# Add core to path
sys.path.append(str(Path(__file__).resolve().parent))
from env_config import BASE_DIR, IS_COLAB, verify_comfy
from scripts.utils.gpu_info import print_gpu_info

def run_pipeline(project_id: str):
    print(f"\n{'='*50}")
    print(f" LIA-CC STUDIO - COLAB AUTOMATED PIPELINE")
    print(f"{'='*50}\n")
    
    print(f"[*] Entorno: {'Google Colab' if IS_COLAB else 'Local'}")
    print(f"[*] BASE_DIR: {BASE_DIR}")
    
    # 1. GPU Check
    print_gpu_info()
    
    # 2. ComfyUI Check
    try:
        verify_comfy()
        print("[OK] ComfyUI detectado y verificado.")
    except Exception as e:
        print(f"[ERROR] ComfyUI no listo: {e}")
        if IS_COLAB:
            print("[HINT] ¿Iniciaste el servidor de ComfyUI en otra celda?")
        sys.exit(1)

    # 3. Running Sequence
    # We use lia_cc.py as the main controller
    import lia_cc
    
    print(f"\n[*] Ejecutando pipeline completo para proyecto: {project_id}")
    
    # Simulate sys.argv for lia_cc.main()
    sys.argv = ["lia_cc.py", "all", project_id]
    
    try:
        lia_cc.main()
    except SystemExit as e:
        if e.code != 0:
            print(f"\n[CRITICAL] El pipeline falló con código {e.code}")
            sys.exit(e.code)
    
    print(f"\n{'='*50}")
    print(f" [OK] PIPELINE COMPLETADO EXITOSAMENTE")
    print(f"{'='*50}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LIA-CC Colab Runner")
    parser.add_argument("project_id", help="ID del proyecto a procesar")
    args = parser.parse_args()
    
    run_pipeline(args.project_id)
