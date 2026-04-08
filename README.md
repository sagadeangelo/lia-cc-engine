# LIA-CC

LIA-CC (Cuenta Cuentos) es un pipeline para convertir capítulos o textos narrativos
en escenas, prompts, renders, clips, subtítulos y video final.

## Flujo base
1. Pegar capítulo en `input/chapters/chapter_input.txt`
2. Ejecutar parser de escenas
3. Generar prompts positivos y negativos
4. Mandar prompts a ComfyUI
5. Generar clips / imágenes
6. Agregar voz, subtítulos y música
7. Exportar video final
