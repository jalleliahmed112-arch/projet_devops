# Gestion des incidents informatiques

## Description

Application web simple pour déclarer et suivre les incidents informatiques d'un établissement. Chaque incident a un numéro, un titre, une description, un lieu, une priorité et un statut.

## Outils utilisés

- Python et Flask
- PostgreSQL 16
- Git et GitHub
- Docker et Docker Compose
- pytest et GitHub Actions
- GitHub Container Registry (GHCR)

Les versions et commandes Docker, Compose, Flask, PostgreSQL, GitHub Actions et GHCR reprennent les ateliers 2 à 5.

## Lancer l'application en local

1. Installer et démarrer Docker Desktop.
2. Dans un terminal, se placer dans le dossier du projet.
3. Créer le fichier local de configuration depuis le modèle :

   ```powershell
   Copy-Item .env.example .env
   ```

4. Démarrer l'application et la base :

   ```text
   docker compose up -d --build
   ```

5. Vérifier les services et les journaux :

   ```text
   docker compose ps
   docker compose logs web
   ```

6. Ouvrir `http://localhost:5000` dans le navigateur. La route `http://localhost:5000/health` doit retourner `{"status":"OK"}`.
7. Arrêter les services :

   ```text
   docker compose down
   ```

Les données sont conservées dans le volume PostgreSQL `db_data`. Pour supprimer aussi les données enregistrées, utiliser `docker compose down -v`.

## Tester l'application

Installer les dépendances Python puis lancer les tests :

```text
pip install -r requirements.txt
pytest -v
```

Les tests vérifient la page d'accueil, la route de santé, l'enregistrement d'un incident et le cas d'un incident inexistant.

## Git et GitHub

Le guide demande plusieurs commits, une branche `feature/gestion-incidents`, sa fusion dans `main` et l'envoi du dépôt sur GitHub. Le pipeline CI se lance sur un push vers `main` ou une Pull Request vers `main`.

## Publication et déploiement

Le workflow CD publie l'image après la réussite des tests, avec les tags `latest` et l'identifiant du commit. Avant le déploiement, remplacer `REMPLACER_PAR_VOTRE_COMPTE` dans `compose.deploy.yaml` par le nom du propriétaire du dépôt GitHub.

Puis récupérer l'image et démarrer l'application :

```text
docker compose -f compose.deploy.yaml pull
docker compose -f compose.deploy.yaml up -d
docker compose -f compose.deploy.yaml ps
docker compose -f compose.deploy.yaml logs
```

Ouvrir ensuite `http://localhost:5000`. Pour arrêter le déploiement :

```text
docker compose -f compose.deploy.yaml down
```

## Résultats attendus et captures à ajouter

- Application affichant la liste et le formulaire d'ajout d'incident.
- Au moins trois tests réussis avec `pytest -v`.
- Une exécution CI réussie dans l'onglet Actions.
- Une exécution CI échouée après une erreur volontaire, puis une capture de sa correction et de la réussite suivante.
- Image publiée et tags visibles dans la section Packages de GitHub.
- Application déployée et accessible dans le navigateur.

Ajouter dans le dépôt les captures réelles obtenues pendant ces étapes; ce README ne prétend pas qu'elles ont déjà été prises.
