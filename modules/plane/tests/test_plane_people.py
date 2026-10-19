"""Plane members in the host's people directory: plane:<member id>, and you as core:me."""
from core.server import people, settings
from modules.plane.tests.fakeplane import MEMBERS


def test_members_are_people_and_you_are_core_me(pulled, client):
    found = client.get("/api/people", params={"q": "mi"}).json()
    assert [p["ref"] for p in found["people"]] == [f"plane:{MEMBERS['robin']}"]
    assert found["people"][0] == {"ref": f"plane:{MEMBERS['robin']}", "name": "Robin",
                                  "email": "robin@northwind.example", "detail": "Plane · @robin", "module": "plane"}
    dale = client.get("/api/people", params={"q": "dale"}).json()["people"]
    assert [p["ref"] for p in dale] == ["core:me"]                # never as plane:<Dale's member id>
    assert dale[0]["email"] == "casey@northwind.example"


def test_assigning_offers_jordan_and_robin_from_plane(pulled, client):
    names = {p["name"] for q in ("e", "m") for p in client.get("/api/people", params={"q": q}).json()["people"]}
    assert {"Elena Ashworth", "Robin"} <= names
    assert not any("Plane" == n or "MCP" in n for n in names)     # the workspace's bots aren't people


def test_an_empty_search_offers_you_then_the_team(pulled):
    settings.update({"core.your_name": "Dale"})
    try:
        assert [(p["ref"], p["name"]) for p in people.find("")["people"]] == [
            ("core:me", "Dale"), (f"plane:{MEMBERS['eli']}", "Elena Ashworth"),
            (f"plane:{MEMBERS['robin']}", "Robin")]
    finally:
        settings.update({"core.your_name": ""})


def test_the_member_chosen_as_you_comes_back_as_core_me(pulled):
    settings.update({"plane.me": MEMBERS["eli"]})
    refs = [p["ref"] for p in people.find("eli")["people"]]
    assert refs == ["core:me"]
    assert f"plane:{MEMBERS['dale']}" in [p["ref"] for p in people.find("dale")["people"]]
    assert people.by_email("robin@northwind.example") == f"plane:{MEMBERS['robin']}"
