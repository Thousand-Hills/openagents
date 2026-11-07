# -*- coding: utf-8 -*-
"""
Identity providers must be opt-in.

A project id is all firebase_auth._init_firebase() needs to verify tokens (no
service account required), so a baked-in default would make every deployment
trust identity tokens minted by that tenant. That matters because
POST /v1/workspaces/{id}/claim accepts a bearer with no workspace token and
claims any workspace whose creator_email is unset, after which
_verify_workspace_access grants that email full access.
"""

import importlib
import os


def _fresh_config(monkeypatch, **env):
    """Re-import the config module with a controlled environment."""
    for key in ("FIREBASE_PROJECT_ID", "APPLE_CLIENT_IDS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.config as config_module
    return importlib.reload(config_module).config


def test_firebase_project_id_defaults_to_empty(monkeypatch):
    assert _fresh_config(monkeypatch).FIREBASE_PROJECT_ID == ""


def test_apple_client_ids_defaults_to_empty(monkeypatch):
    assert _fresh_config(monkeypatch).APPLE_CLIENT_IDS == ""


def test_identity_providers_still_configurable(monkeypatch):
    cfg = _fresh_config(
        monkeypatch,
        FIREBASE_PROJECT_ID="my-project",
        APPLE_CLIENT_IDS="com.example.app,com.example.svc",
    )
    assert cfg.FIREBASE_PROJECT_ID == "my-project"
    assert cfg.APPLE_CLIENT_IDS == "com.example.app,com.example.svc"


def test_firebase_verification_fails_closed_without_a_project(monkeypatch):
    """With no project configured, token verification must not initialize."""
    _fresh_config(monkeypatch)
    import app.firebase_auth as firebase_auth
    importlib.reload(firebase_auth)
    monkeypatch.setattr(firebase_auth, "_firebase_initialized", False, raising=False)
    assert firebase_auth.verify_firebase_token("any.token.value") is None


def test_allowed_email_domain_gate(monkeypatch):
    """Thousand Hills: only verified addresses at ALLOWED_EMAIL_DOMAIN pass."""
    _fresh_config(monkeypatch, ALLOWED_EMAIL_DOMAIN="Thousandhills.app")
    import app.firebase_auth as firebase_auth
    importlib.reload(firebase_auth)
    ok = firebase_auth._email_domain_allowed
    assert ok({"email": "a@thousandhills.app", "email_verified": True})
    assert not ok({"email": "a@thousandhills.app", "email_verified": False})
    assert not ok({"email": "a@gmail.com", "email_verified": True})
    assert not ok({"email": "a@evilthousandhills.app", "email_verified": True})
    monkeypatch.delenv("ALLOWED_EMAIL_DOMAIN")
    _fresh_config(monkeypatch)
    importlib.reload(firebase_auth)
    assert firebase_auth._email_domain_allowed({"email": "a@gmail.com"})


def test_anonymous_workspace_create_blocked_with_domain_allowlist(monkeypatch):
    """Thousand Hills: no anonymous POST /v1/workspaces under an allowlist."""
    import app.access
    from app.routers import workspaces
    monkeypatch.setattr(app.access, "resolve_current_user", lambda db, auth: None)
    monkeypatch.setattr(workspaces.config, "ALLOWED_EMAIL_DOMAIN", "thousandhills.app")
    body = workspaces.WorkspaceCreateRequest(name="x")
    resp = workspaces.create_workspace(body, db=None, authorization=None)
    assert resp.status_code == 401
