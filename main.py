from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.lifespan import lifespan
from src.routes.annotated_images import router as annotated_images_router
from src.routes.api import router as api_router
from src.routes.camera import router as camera_router
from src.routes.logs import router as logs_router
from src.routes.spa import router as spa_router
from src.static_assets import configure_static

load_dotenv()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(logs_router)
app.include_router(camera_router)
app.include_router(annotated_images_router)
configure_static(app)
app.include_router(spa_router)


def main() -> None:
    print("Hello from system-wizyjny!")


if __name__ == "__main__":
    main()
