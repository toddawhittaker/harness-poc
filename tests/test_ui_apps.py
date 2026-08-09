"""The two surfaces are thin, identical underneath, and leak no token (SPEC §4.9).

None of these tests calls a model. They check the three things about a surface
that can be checked cheaply and that would be expensive to discover on a stage:

1. The two apps really do differ only in theme and copy. The shared file is
   byte-identical, the way the four MCP servers' mcp_auth.py copies are.
2. Any persona can sign into either app, and a wrong password is refused by
   the issuer rather than by a list inside the app.
3. The harness JWT never reaches the browser. Chainlit serves the user object
   from GET /user and signs it into a cookie, so a token parked in
   User.metadata would be readable by any script on the page.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from conftest import PERSONA_PASSWORD, UI_APPS

pytestmark = pytest.mark.session3

APPS_DIR = Path(__file__).resolve().parent.parent / "apps"
SHARED_FILE = "harness_chat.py"

# Every persona in config/personas.yaml. The claim is that the door does not
# decide anything — pat can sign into the executive app, and does during Q&A.
PERSONAS = ["dana", "kim", "noor", "pat", "sam"]


def test_the_shared_surface_file_is_identical_in_both_apps() -> None:
    digests = {
        app.name: hashlib.md5((app / SHARED_FILE).read_bytes()).hexdigest()
        for app in sorted(APPS_DIR.iterdir())
        if (app / SHARED_FILE).is_file()
    }
    assert len(digests) == 2, f"expected two apps carrying {SHARED_FILE}, found {digests}"
    assert len(set(digests.values())) == 1, (
        f"the two copies of {SHARED_FILE} have drifted: {digests}. They are duplicated "
        "on purpose and must stay byte-identical; the apps differ in theme and copy only."
    )


@pytest.mark.parametrize("app", sorted(UI_APPS))
@pytest.mark.parametrize("persona", PERSONAS)
def test_any_persona_can_sign_into_either_app(
    ui_stack: None, http: httpx.Client, app: str, persona: str,
) -> None:
    response = http.post(f"{UI_APPS[app]}/login",
                         data={"username": persona, "password": PERSONA_PASSWORD})
    assert response.status_code == 200, (
        f"{persona} could not sign into {app}: {response.status_code} {response.text[:200]}"
    )


@pytest.mark.parametrize("app", sorted(UI_APPS))
@pytest.mark.parametrize("credentials", [
    ("dana", "wrong"),
    ("nobody", "demo"),
])
def test_a_bad_credential_is_refused_by_the_issuer(
    ui_stack: None, http: httpx.Client, app: str, credentials: tuple[str, str],
) -> None:
    """401, and the same 401 for a wrong password as for an unknown persona.

    The app makes neither judgement itself: both of these reach identity-stub
    and come back refused, which is why the two cases are indistinguishable
    from out here.
    """
    username, password = credentials
    response = http.post(f"{UI_APPS[app]}/login",
                         data={"username": username, "password": password})
    assert response.status_code == 401, (
        f"{app} accepted {username!r}/{password!r} with {response.status_code}"
    )
    assert not response.cookies.get("access_token"), f"{app} set a session cookie anyway"


@pytest.mark.parametrize("app", sorted(UI_APPS))
@pytest.mark.parametrize("credentials", [("dana", ""), ("", "demo")])
def test_an_empty_credential_never_reaches_the_issuer(
    ui_stack: None, http: httpx.Client, app: str, credentials: tuple[str, str],
) -> None:
    """422 rather than 401: the form schema rejects it before any callback runs.

    A different status for a different reason, asserted separately so that a
    later change turning one into the other cannot pass unnoticed.
    """
    username, password = credentials
    response = http.post(f"{UI_APPS[app]}/login",
                         data={"username": username, "password": password})
    assert response.status_code == 422, (
        f"{app} answered {username!r}/{password!r} with {response.status_code}, expected 422"
    )
    assert not response.cookies.get("access_token"), f"{app} set a session cookie anyway"


@pytest.mark.parametrize("app", sorted(UI_APPS))
def test_the_session_cookie_carries_no_harness_token(
    ui_stack: None, http: httpx.Client, app: str,
) -> None:
    """The cookie names who signed in. It must not carry what they can do with it."""
    response = http.post(f"{UI_APPS[app]}/login",
                         data={"username": "dana", "password": PERSONA_PASSWORD})
    assert response.status_code == 200
    cookie = response.cookies.get("access_token")
    assert cookie, f"{app} set no session cookie"

    payload_segment = cookie.split(".")[1]
    padded = payload_segment + "=" * (-len(payload_segment) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))

    assert payload.get("identifier") == "dana"
    assert payload.get("metadata") == {}, (
        f"{app} put {sorted(payload['metadata'])} in the session cookie. Anything here "
        "is served to the browser by GET /user; a harness token belongs in the app "
        "process and in the Authorization header, nowhere else."
    )


@pytest.mark.parametrize("app", sorted(UI_APPS))
def test_the_user_object_served_to_the_browser_carries_no_token(
    ui_stack: None, app: str,
) -> None:
    with httpx.Client(base_url=UI_APPS[app], timeout=15.0) as client:
        login = client.post("/login", data={"username": "dana", "password": PERSONA_PASSWORD})
        assert login.status_code == 200
        user = client.get("/user")
    assert user.status_code == 200, user.text[:200]
    body = user.json()
    assert body.get("identifier") == "dana"
    assert not body.get("metadata"), f"{app} serves metadata to the browser: {body['metadata']}"
    # An RS256 JWT from identity-stub starts with this header segment. Belt and
    # braces: the assertion above already covers the only place one could hide.
    assert "eyJhbGciOiJSUzI1NiI" not in user.text, f"{app} served a harness token to the browser"


@pytest.mark.parametrize("app", sorted(UI_APPS))
def test_each_app_serves_its_own_theme_and_name(ui_stack: None, http: httpx.Client, app: str) -> None:
    page = http.get(UI_APPS[app])
    assert page.status_code == 200
    assert "window.theme" in page.text, f"{app} injected no custom theme"
    assert http.get(f"{UI_APPS[app]}/public/theme.css").status_code == 200


def test_the_two_apps_do_not_look_alike(ui_stack: None, http: httpx.Client) -> None:
    """Divergence is the point (SPEC §4.9): same harness, visibly different room."""
    pages = {app: http.get(url).text for app, url in UI_APPS.items()}
    titles = {app: text.split("<title>")[1].split("</title>")[0] for app, text in pages.items()}
    assert len(set(titles.values())) == 2, f"both apps present the same name: {titles}"

    themes = {app: text.split("window.theme = ")[1].split(";")[0] for app, text in pages.items()}
    assert len(set(themes.values())) == 2, "both apps ship the same palette"

    configs = {app: http.get(f"{url}/auth/config").json() for app, url in UI_APPS.items()}
    for app, config in configs.items():
        assert config["passwordAuth"] is True, f"{app} does not require a password"
        assert config["requireLogin"] is True, f"{app} does not require a login"
    defaults = {app: config["default_theme"] for app, config in configs.items()}
    assert set(defaults.values()) == {"light", "dark"}, (
        f"the two apps should not open on the same theme: {defaults}"
    )
