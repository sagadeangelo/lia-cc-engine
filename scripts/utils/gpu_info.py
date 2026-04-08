import torch

def print_gpu_info():
    print("-" * 40)
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        print(f"[*] Using GPU: {name}")
        vram_total = torch.cuda.get_device_properties(0).total_memory // 1024**2
        print(f"[*] VRAM Total: {vram_total} MB")
    else:
        print("[WARN] No se detectó GPU CUDA. El renderizado será lento (CPU).")
    print("-" * 40)

if __name__ == "__main__":
    print_gpu_info()
