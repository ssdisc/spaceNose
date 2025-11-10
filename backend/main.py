from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# 静态文件目录，指向Vue项目的dist目录
static_folder = os.path.join(os.path.dirname(__file__), "..", "web", "dist")

# 挂载静态文件
static_dirs = ["assets", "css", "js", "img"]
for static_dir in static_dirs:
    path = os.path.join(static_folder, static_dir)
    if os.path.exists(path) and os.path.isdir(path):
        app.mount(f"/{static_dir}", StaticFiles(directory=path), name=static_dir)


@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    捕获所有路由，并返回index.html，让Vue Router处理。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}

@app.get("/")
async def root():
    """
    根路由，返回index.html。
    """
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Run 'npm run build' in the 'web' directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
