"""Plane members in the host's people directory: plane:<member id>, and you as core:me."""
from core.server import people, settings
from modules.plane.tests.fakeplane import MEMBERS


def test_members_are_people_and_you_are_core_me(pulled, client):
    found = client.get("/api/people", params={"q": "sa"}).json()
    assert [p["ref"] for p in found["people"]] == [f"plane:{MEMBERS['sam']}"]
    assert found["people"][0] == {"ref": f"plane:{MEMBERS['sam']}", "name": "Sam",
                                  "email": "sam@acme-team.example", "detail": "Plane · @sam", "module": "plane"}
    mark = client.get("/api/people", params={"q": "mark"}).json()["people"]
    assert [p["ref"] for p in mark] == ["core:me"]                # never as plane:<Mark's member id>
    assert mark[0]["email"] == "mark@acme-team.example"


def test_assigning_offers_alex_and_sam_from_plane(pulled, client):
    names = {p["name"] for q in ("e", "m") for p in client.get("/api/people", params={"q": q}).json()["people"]}
    assert {"Alex Rivera", "Sam"} <= names
    assert not any("Plane" == n or "MCP" in n for n in names)     # the workspace's bots aren't people


def test_an_empty_search_offers_you_then_the_team(pulled):
    settings.update({"core.your_name": "Mark"})
    try:
        assert [(p["ref"], p["name"]) for p in people.find("")["people"]] == [
            ("core:me", "Mark"), (f"plane:{MEMBERS['alex']}", "Alex Rivera"),
            (f"plane:{MEMBERS['sam']}", "Sam")]
    finally:
        settings.update({"core.your_name": ""})


def test_the_member_chosen_as_you_comes_back_as_core_me(pulled):
    settings.update({"plane.me": MEMBERS["alex"]})
    refs = [p["ref"] for p in people.find("alex")["people"]]
    assert refs == ["core:me"]
    assert f"plane:{MEMBERS['mark']}" in [p["ref"] for p in people.find("mark")["people"]]
    assert people.by_email("sam@acme-team.example") == f"plane:{MEMBERS['sam']}"
