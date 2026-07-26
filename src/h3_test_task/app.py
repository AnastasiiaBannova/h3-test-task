import fastapi
from starlette.middleware.cors import CORSMiddleware

from h3_test_task.api.api import router
from h3_test_task.core.settings import settings


def get_app() -> fastapi.FastAPI:
    app_ = fastapi.FastAPI(
        title=settings.microservice_name,
        debug=settings.debug,
    )

    app_.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app_.include_router(router)

    return app_


app = get_app()
