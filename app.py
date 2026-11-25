"""Petite application web pour suivre les incidents informatiques."""

import os
from contextlib import contextmanager

import psycopg2
from flask import Flask, abort, redirect, render_template_string, request, url_for

app = Flask(__name__)

# Les paramètres viennent de Docker Compose; les valeurs par défaut servent au TP.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "dbname": os.environ.get("DB_NAME", "incidents"),
    "user": os.environ.get("DB_USER", "app_user"),
    "password": os.environ.get("DB_PASSWORD", "app_password"),
}

PAGE = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gestion des incidents</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="page">
  <main class="container">
  <header class="hero">
    <p class="eyebrow">Espace de support informatique</p>
    <h1>Gestion des incidents</h1>
    <p class="hero-text">Signalez un problème et suivez son traitement.</p>
  </header>
  <section class="panel form-panel">
    <h2>Signaler un incident</h2>
    <form class="incident-form" method="post" action="{{ url_for('create_incident') }}">
      <label class="field">Titre<input name="title" required maxlength="150" placeholder="Ex. Ordinateur en panne"></label>
      <label class="field">Description<textarea name="description" required rows="3" placeholder="Décrivez le problème rencontré"></textarea></label>
      <div class="form-row">
        <label class="field">Salle ou laboratoire<input name="location" required maxlength="100" placeholder="Ex. Salle B12"></label>
        <label class="field">Priorité<select name="priority"><option>Faible</option><option selected>Moyenne</option><option>Élevée</option></select></label>
      </div>
      <button class="button" type="submit">Ajouter l’incident</button>
    </form>
  </section>
  <section class="incidents-section">
  <div class="section-heading"><div><p class="eyebrow">Suivi</p><h2>Incidents déclarés</h2></div></div>
  {% if incidents %}
  <ul class="incident-list">
    {% for incident in incidents %}
    <li class="incident-card">
      <div class="incident-card-top"><span class="incident-number">Incident #{{ incident['id'] }}</span><span class="badge">{{ incident['status'] }}</span></div>
      <h3><a href="{{ url_for('incident_detail', incident_id=incident['id']) }}">{{ incident['title'] }}</a></h3>
      <p class="incident-meta">{{ incident['location'] }} <span aria-hidden="true">·</span> Priorité {{ incident['priority'] }}</p>
    </li>
    {% endfor %}
  </ul>
  {% else %}<div class="empty-state"><span class="empty-icon" aria-hidden="true">✓</span><p>Aucun incident pour le moment.</p><small>Les nouveaux signalements apparaîtront ici.</small></div>{% endif %}
  </section>
  </main>
</body>
</html>
"""

DETAIL_PAGE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Incident #{{ incident['id'] }}</title><link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}"></head>
<body class="page">
  <main class="container detail-container">
  <p class="back-link"><a href="{{ url_for('home') }}">← Retour à la liste</a></p>
  <section class="panel detail-panel">
  <p class="eyebrow">Fiche de suivi · Incident #{{ incident['id'] }}</p>
  <h1>{{ incident['title'] }}</h1>
  <div class="detail-grid">
    <p><strong>Description</strong><span>{{ incident['description'] }}</span></p>
    <p><strong>Lieu</strong><span>{{ incident['location'] }}</span></p>
    <p><strong>Priorité</strong><span>{{ incident['priority'] }}</span></p>
    <p><strong>Statut actuel</strong><span class="badge">{{ incident['status'] }}</span></p>
  </div>
  </section>
  <section class="panel actions-panel">
    <h2>Mettre à jour le suivi</h2>
  <form class="action-form" method="post" action="{{ url_for('update_status', incident_id=incident['id']) }}">
    <label class="field">Nouveau statut
      <select name="status"><option>Nouveau</option><option>En cours</option><option>Résolu</option></select>
    </label><button class="button" type="submit">Modifier le statut</button>
  </form>
  <form class="delete-form" method="post" action="{{ url_for('delete_incident', incident_id=incident['id']) }}">
    <button class="button button-danger" type="submit">Supprimer l’incident</button>
  </form>
  </section>
  </main>
</body></html>
"""


def get_connection():
    """Ouvre une connexion à PostgreSQL avec les paramètres de Compose."""
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def database_connection():
    """Valide la transaction puis ferme toujours la connexion PostgreSQL."""
    connection = get_connection()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    """Crée la table au premier démarrage de l'application."""
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS incidents (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(150) NOT NULL,
                    description TEXT NOT NULL,
                    location VARCHAR(100) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'Nouveau'
                )"""
            )


def list_incidents():
    """Retourne les incidents du plus récent au plus ancien."""
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, description, location, priority, status "
                "FROM incidents ORDER BY id DESC"
            )
            rows = cursor.fetchall()
    columns = ("id", "title", "description", "location", "priority", "status")
    return [dict(zip(columns, row)) for row in rows]


def find_incident(incident_id):
    """Recherche un incident à partir de son numéro."""
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, description, location, priority, status "
                "FROM incidents WHERE id = %s",
                (incident_id,),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(("id", "title", "description", "location", "priority", "status"), row))


@app.route("/")
def home():
    """Affiche le formulaire et la liste des incidents."""
    return render_template_string(PAGE, incidents=list_incidents())


@app.route("/health")
def health():
    """Indique que le serveur web répond, pour le contrôle CI."""
    return {"status": "OK"}


@app.route("/incidents", methods=["POST"])
def create_incident():
    """Vérifie le formulaire puis enregistre un nouvel incident."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    priority = request.form.get("priority", "Moyenne")
    if not title or not description or not location:
        abort(400, "Le titre, la description et le lieu sont obligatoires.")
    if priority not in ("Faible", "Moyenne", "Élevée"):
        abort(400, "La priorité est invalide.")
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO incidents (title, description, location, priority) "
                "VALUES (%s, %s, %s, %s)",
                (title, description, location, priority),
            )
    return redirect(url_for("home"))


@app.route("/incidents/<int:incident_id>")
def incident_detail(incident_id):
    """Affiche la fiche complète d'un incident."""
    incident = find_incident(incident_id)
    if incident is None:
        abort(404)
    return render_template_string(DETAIL_PAGE, incident=incident)


@app.route("/incidents/<int:incident_id>/status", methods=["POST"])
def update_status(incident_id):
    """Met à jour le statut avec l'une des trois valeurs prévues."""
    status = request.form.get("status", "")
    if status not in ("Nouveau", "En cours", "Résolu"):
        abort(400, "Le statut est invalide.")
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE incidents SET status = %s WHERE id = %s",
                (status, incident_id),
            )
            if cursor.rowcount == 0:
                abort(404)
    return redirect(url_for("incident_detail", incident_id=incident_id))


@app.route("/incidents/<int:incident_id>/delete", methods=["POST"])
def delete_incident(incident_id):
    """Supprime un incident et retourne à la liste."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM incidents WHERE id = %s", (incident_id,))
            if cursor.rowcount == 0:
                abort(404)
    return redirect(url_for("home"))


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)
