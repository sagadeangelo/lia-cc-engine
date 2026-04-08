from fastapi import FastAPI
from api.routes import projects, render, status, assets

app = FastAPI(title="LIA-CC Engine API")

app.include_router(projects.router, prefix="/projects")
app.include_router(render.router, prefix="/render")
app.include_router(status.router, prefix="/status")
app.include_router(assets.router, prefix="/assets")

@app.get("/")
def root():
    return {"message": "LIA-CC Backend Running 🚀"}
