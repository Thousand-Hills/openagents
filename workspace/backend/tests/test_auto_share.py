# -*- coding: utf-8 -*-
"""Thousand Hills: AUTO_SHARE_AGENTS_WITH_EVERYONE grants new agents to "everyone"."""

from app.config import config
from app.services.access_model import active_grants, get_or_create_builtin_groups


def _join(client, workspace, agent_name):
    return client.post("/v1/join", json={
        "agent_name": agent_name, "token": workspace["token"], "network": workspace["id"],
    })


def _everyone_grants(db, workspace, agent_name):
    everyone = get_or_create_builtin_groups(db, workspace["id"])["everyone"]
    return active_grants(db, workspace["id"], "agent", agent_name, ("group", everyone.id))


def test_new_agent_shared_with_everyone_when_on(client, workspace, db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHARE_AGENTS_WITH_EVERYONE", True)
    assert _join(client, workspace, "hire-one").status_code == 200
    grants = _everyone_grants(db, workspace, "hire-one")
    assert len(grants) == 1 and sorted(grants[0].rights) == ["act", "read"]
    # A rejoin (reconnect / restart) must not add a second grant.
    assert _join(client, workspace, "hire-one").status_code == 200
    assert len(_everyone_grants(db, workspace, "hire-one")) == 1


def test_new_agent_not_shared_when_off(client, workspace, db, monkeypatch):
    monkeypatch.setattr(config, "AUTO_SHARE_AGENTS_WITH_EVERYONE", False)
    assert _join(client, workspace, "hire-two").status_code == 200
    assert _everyone_grants(db, workspace, "hire-two") == []
