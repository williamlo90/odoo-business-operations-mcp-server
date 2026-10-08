import os
import socket
import subprocess
import sys
import time

import httpx
import pytest

from backend.manage import reset_test


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    reset_test()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    path = tmp_path_factory.mktemp("api") / "server.log"
    with path.open("w+") as logs:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app",
                                    "--host", "127.0.0.1", "--port", str(port),
                                    "--no-access-log", "--no-proxy-headers"],
                                   env=os.environ.copy(), stdout=logs, stderr=logs)
        url = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail("API process exited during startup; inspect isolated server log")
                try:
                    if httpx.get(url + "/health/ready").status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("API did not become ready")
            yield {"url": url, "log": path}
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


@pytest.fixture
def api(server):
    with httpx.Client(base_url=server["url"], timeout=10) as client:
        yield client


@pytest.fixture
def login(api):
    def sign_in(username="operator.a"):
        response = api.post("/auth/login", json={"username": username, "password": os.environ["DEMO_PASSWORD"]})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return sign_in
