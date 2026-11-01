"""Optional host-side research API using the existing auth and Postgres store.

No trading scheduler, migrations at startup, model warmup or broker imports.
"""

from fastapi import Depends, FastAPI

from api.middleware.auth import get_api_key
from api.routes.research import router

app = FastAPI(title="Kepler Research", dependencies=[Depends(get_api_key)])
app.include_router(router, prefix="/research")
