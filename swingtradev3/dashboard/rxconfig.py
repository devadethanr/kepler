import reflex as rx

config = rx.Config(
    app_name="dashboard",
    env=rx.Env.DEV,
    cors_allowed_origins=["*"],
    frontend_port=3000,
    backend_port=8000,
    api_url="http://localhost:8002",
)
