from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Routers existentes
from api.routes import projects, render, status, assets

# Nuevos routers
from api.routes import photo, characters, pipeline

app = FastAPI(title="LIA-CC Engine API")

# =========================
# CORS (IMPORTANTE para Flutter)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes restringir después
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# STATIC FILES (CRÍTICO)
# =========================

# 👉 sirve TODO el folder projects (characters, renders, etc)
app.mount("/assets_root", StaticFiles(directory="projects"), name="assets_root")

# =========================
# ROUTES BASE
# =========================
app.include_router(projects.router)                # /projects
app.include_router(render.router, prefix="/render")
app.include_router(status.router, prefix="/status")
app.include_router(assets.router, prefix="/assets")

# =========================
# NUEVAS FEATURES 🔥
# =========================

# 👉 PHOTO MODE
app.include_router(photo.router)

# 👉 CHARACTERS
app.include_router(characters.router)

# 👉 VIDEO PIPELINE
app.include_router(pipeline.router)

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"message": "LIA-CC Engine API Running 🚀"}