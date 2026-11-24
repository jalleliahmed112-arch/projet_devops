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
  <title>Gestion des incidents</title>
  <style>
    body { max-width: 900px; margin: 2rem auto; padding: 0 1rem; font-family: Arial, sans-serif; }
    input, textarea, select, button { margin: .3rem 0; padding: .5rem; }
    input, textarea { width: min(100%, 34rem); }
    li { margin: .8rem 0; }
    .bloc { padding: 1rem; border: 1px solid #bbb; border-radius: 8px; margin: 1rem 0; }
  </style>
</head>
<body>
  <h1>Gestion des incidents informatiques</h1>
  <section class="bloc">
    <h2>Signaler un incident</h2>
    <form method="post" action="{{ url_for('create_incident') }}">
      <label>Titre<br><input name="title" required maxlength="150"></label><br>
      <label>Description<br><textarea name="description" required rows="3"></textarea></label><br>
      <label>Salle ou laboratoire<br><input name="location" required maxlength="100"></label><br>
      <label>Priorité<br><select name="priority"><option>Faible</option><option selected>Moyenne</option><option>Élevée</option></select></label><br>
      <button type="submit">Ajouter l’incident</button>
    </form>
  </section>
  <h2>Incidents déclarés</h2>
  {% if incidents %}
  <ul>
    {% for incident in incidents %}
    <li><a href="{{ url_for('incident_detail', incident_id=incident['id']) }}">#{{ incident['id'] }} — {{ incident['title'] }}</a>
      | {{ incident['location'] }} | priorité {{ incident['priority'] }} | {{ incident['status'] }}</li>
    {% endfor %}
  </ul>
  {% else %}<p>Aucun incident pour le moment.</p>{% endif %}
</body>
</html>
"""

DETAIL_PAGE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Incident #{{ incident['id'] }}</title></head>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:2rem auto">
  <p><a href="{{ url_for('home') }}">← Retour à la liste</a></p>
  <h1>Incident #{{ incident['id'] }} : {{ incident['title'] }}</h1>
  <p><strong>Description :</strong> {{ incident['description'] }}</p>
  <p><strong>Lieu :</strong> {{ incident['location'] }}</p>
  <p><strong>Priorité :</strong> {{ incident['priority'] }}</p>
  <p><strong>Statut :</strong> {{ incident['status'] }}</p>
  <form method="post" action="{{ url_for('update_status', incident_id=incident['id']) }}">
    <label>Nouveau statut
      <select name="status"><option>Nouveau</option><option>En cours</option><option>Résolu</option></select>
    </label><button type="submit">Modifier le statut</button>
  </form>
  <form method="post" action="{{ url_for('delete_incident', incident_id=incident['id']) }}">
    <button type="submit">Supprimer l’incident</button>
  </form>
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
