param(
    [string]$ProjectId = "1nefi_cap_01"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor DarkCyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor DarkCyan
}

function Require-File($path) {
    if (-not (Test-Path $path)) {
        throw "No existe el archivo requerido: $path"
    }
}

function Run-PythonStep($label, $scriptPath, $projectId) {
    Write-Step $label

    if (-not (Test-Path $scriptPath)) {
        throw "No existe el script: $scriptPath"
    }

    & python $scriptPath $projectId
    if ($LASTEXITCODE -ne 0) {
        throw "Falló el script: $scriptPath"
    }
}

function Show-ExpectedFile($label, $path) {
    if (Test-Path $path) {
        Write-Host "[OK] $label -> $path" -ForegroundColor Green
    } else {
        Write-Host "[WARN] No se encontró todavía: $path" -ForegroundColor Yellow
    }
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$ChapterInput = Join-Path $Root "input\chapters\chapter_input.txt"

$ProjectRoot = Join-Path $Root "projects\$ProjectId"
$ParsedChapter = Join-Path $ProjectRoot "scenes\parsed_chapter.json"
$ScenesJson = Join-Path $ProjectRoot "scenes\scenes.json"
$PromptsJson = Join-Path $ProjectRoot "prompts\scene_prompts.json"
$RenderQueue = Join-Path $Root "output\render_queue.json"
$LastComfyRun = Join-Path $Root "output\last_comfy_run.json"
$VoiceManifest = Join-Path $ProjectRoot "audio\voice_manifest.json"
$TimelineJson = Join-Path $ProjectRoot "final\timeline.json"
$FinalVideo = Join-Path $ProjectRoot "final\lia_cc_final.mp4"

Write-Step "LIA-CC :: Inicio de pipeline"
Write-Host "Proyecto: $ProjectId" -ForegroundColor White
Write-Host "Root: $Root" -ForegroundColor Gray

Require-File $ChapterInput

# ==================================================
# 1) Parsear capítulo
# ==================================================
Run-PythonStep "01 :: Parsear capítulo" "scripts\01_parse_chapter.py" $ProjectId
Show-ExpectedFile "parsed_chapter.json" $ParsedChapter

# ==================================================
# 2) Construir escenas
# ==================================================
Run-PythonStep "02 :: Construir escenas" "scripts\02_build_scenes.py" $ProjectId
Show-ExpectedFile "scenes.json" $ScenesJson

# ==================================================
# 3) Construir prompts
# ==================================================
Run-PythonStep "03 :: Construir prompts" "scripts\03_build_prompts.py" $ProjectId
Show-ExpectedFile "scene_prompts.json" $PromptsJson

# ==================================================
# 4) Preparar cola de render
# ==================================================
Run-PythonStep "04 :: Preparar render queue" "scripts\04_prepare_render_queue.py" $ProjectId
Show-ExpectedFile "render_queue.json" $RenderQueue

# ==================================================
# 5) Enviar a ComfyUI
# ==================================================
Run-PythonStep "05 :: Enviar escenas a ComfyUI" "scripts\05_run_comfy_queue.py" $ProjectId
Show-ExpectedFile "last_comfy_run.json" $LastComfyRun

Write-Host ""
Write-Host "[INFO] Los trabajos ya fueron enviados a ComfyUI." -ForegroundColor Cyan
Write-Host "[INFO] El avance real del render se ve en la ventana/consola de ComfyUI." -ForegroundColor Cyan
Write-Host ""

# ==================================================
# 6) Generar voces
# ==================================================
Run-PythonStep "07 :: Generar voces" "scripts\07_generate_voices.py" $ProjectId
Show-ExpectedFile "voice_manifest.json" $VoiceManifest

# ==================================================
# 7) Construir timeline
# ==================================================
Run-PythonStep "08 :: Construir timeline" "scripts\08_build_timeline.py" $ProjectId
Show-ExpectedFile "timeline.json" $TimelineJson

# ==================================================
# 8) Esperar a que ComfyUI termine
# ==================================================
Write-Step "Espera de ComfyUI"
Write-Host "Cuando ComfyUI termine de renderizar TODAS las escenas, presiona ENTER para continuar al merge final." -ForegroundColor Yellow
Write-Host "Si todavía está renderizando, déjalo trabajando y vuelve aquí después." -ForegroundColor Yellow
Read-Host "Presiona ENTER cuando ComfyUI ya haya terminado"

# ==================================================
# 9) Merge audio + video
# ==================================================
Run-PythonStep "09 :: Unir audio y video final" "scripts\09_merge_audio_video.py" $ProjectId
Show-ExpectedFile "Video final" $FinalVideo

Write-Step "Pipeline completado"
Write-Host "[OK] Proyecto finalizado: $ProjectId" -ForegroundColor Green
Write-Host "[OK] Video final: $FinalVideo" -ForegroundColor Green