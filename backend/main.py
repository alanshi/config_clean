from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
from .database import engine, Base
from .api.api import api_router

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="配置文件预处理系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 明确列出允许的方法
    allow_headers=["*"],
)

# app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static", StaticFiles(directory="backend/static",
          html=True), name="static")


def custom_swagger_ui_html():
    return HTMLResponse(
        """
            <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="/static/swagger-ui/swagger-ui.css">
    <link rel="shortcut icon" href="/static/favicon.png">
    <title>配置文件预处理系统 - Swagger UI</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({
        url: '/openapi.json',
    "dom_id": "#swagger-ui",
"layout": "BaseLayout",
"deepLinking": true,
"showExtensions": true,
"showCommonExtensions": true,
oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
    })
    </script>
    </body>
    </html>
        """
    )


# 自定义ReDoc文档
def custom_redoc_html():
    return HTMLResponse(
        """


    <!DOCTYPE html>
    <html>
    <head>
    <title>配置文件预处理系统 - ReDoc</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link href="/css/font-awesome.min.css" rel="stylesheet">

    <link rel="shortcut icon" href="/static/favicon.png">
    <!--
    ReDoc doesn't change outer page styles
    -->
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
    </head>
    <body>
    <noscript>
        ReDoc requires Javascript to function. Please enable it to browse the documentation.
    </noscript>
    <redoc spec-url="/openapi.json"></redoc>
    <script src="/static/redoc/redoc.standalone.js"> </script>
    </body>
    </html>

        """
    )


# 将自定义HTML绑定到文档路径
app.get("/docs_1", response_class=HTMLResponse)(custom_swagger_ui_html)
app.get("/redoc_1", response_class=HTMLResponse)(custom_redoc_html)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/file-manager", response_class=HTMLResponse)
async def file_manager(request: Request):
    # 直接返回file-manager.html内容
    try:
        with open(os.path.join(frontend_dir, "file-manager.html"), "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File manager not found")

# 注册API路由
app.include_router(api_router, prefix="/api")


# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 挂载前端文件
frontend_dir = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "templates")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="templates")
