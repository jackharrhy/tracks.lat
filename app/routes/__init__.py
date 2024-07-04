from app.routes.admin import router as admin_router
from app.routes.homepage import router as homepage_router
from app.routes.login import router as login_router
from app.routes.logout import router as logout_router
from app.routes.profile import router as profile_router
from app.routes.register import router as register_router
from app.routes.upload import router as upload_router

__all__ = [
    admin_router,
    homepage_router,
    login_router,
    logout_router,
    profile_router,
    register_router,
    upload_router,
]
