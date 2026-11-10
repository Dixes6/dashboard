import re

from app.main import app
from fastapi.testclient import TestClient


def test_all_routes_unauthorized_return_401(client: TestClient):
    """Обходит все маршруты приложения (app.routes) без cookie и проверяет 401 везде,

    кроме белого списка.
    """
    client.cookies.clear()

    whitelist = {
        "/api/health",
        "/api/auth/login",
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
    }

    routes: list[tuple[str, set[str]]] = []
    for r in app.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            routes.append((r.path, r.methods))
        elif hasattr(r, "original_router") and hasattr(r, "include_context"):
            prefix = r.include_context.prefix or ""
            for sub_r in r.original_router.routes:
                sub_path = prefix + getattr(sub_r, "path", "")
                sub_methods = getattr(sub_r, "methods", set())
                routes.append((sub_path, sub_methods))

    assert len(routes) > 0, "Маршруты в приложении не найдены"

    for raw_path, methods in routes:
        if raw_path in whitelist:
            continue

        # Подставляем dummy-параметры вместо {param}
        formatted_path = re.sub(r"\{day_date\}", "2026-11-10", raw_path)
        formatted_path = re.sub(r"\{[^}]+\}", "1", formatted_path)

        for method in methods:
            if method == "HEAD":
                continue
            response = client.request(method, formatted_path)
            assert response.status_code == 401, (
                f"Маршрут {method} {raw_path} без куки вернул {response.status_code}, "
                f"ожидался 401. Ответ: {response.text}"
            )
