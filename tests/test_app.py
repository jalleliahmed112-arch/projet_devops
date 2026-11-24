from app import app


def test_home_page_displays_incidents(monkeypatch):
    """La page d'accueil affiche la liste renvoyée par l'application."""
    monkeypatch.setattr(
        "app.list_incidents",
        lambda: [
            {
                "id": 1,
                "title": "PC en panne",
                "description": "Ne démarre plus",
                "location": "Salle B12",
                "priority": "Élevée",
                "status": "Nouveau",
            }
        ],
    )
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert "PC en panne" in response.get_data(as_text=True)


def test_health_route_returns_ok():
    """La route de santé répond comme prévu par le TP CI."""
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "OK"}


def test_create_incident_saves_form(monkeypatch):
    """Un formulaire complet est transmis à la fonction qui enregistre l'incident."""
    saved = {}

    class FakeCursor:
        def execute(self, query, values):
            saved["values"] = values

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.get_connection", lambda: FakeConnection())
    response = app.test_client().post(
        "/incidents",
        data={
            "title": "Écran cassé",
            "description": "L'écran ne s'allume plus.",
            "location": "Laboratoire 2",
            "priority": "Moyenne",
        },
    )
    assert response.status_code == 302
    assert saved["values"] == (
        "Écran cassé",
        "L'écran ne s'allume plus.",
        "Laboratoire 2",
        "Moyenne",
    )


def test_incident_detail_shows_not_found_for_missing_incident(monkeypatch):
    """Un numéro absent retourne une page 404."""
    monkeypatch.setattr("app.find_incident", lambda incident_id: None)
    response = app.test_client().get("/incidents/999")
    assert response.status_code == 404
