# Analogy-Engine

[![Qualité · Doc · Sécurité](https://github.com/HELALI-Amin-24005915/Analogy-Engine/actions/workflows/quality.yml/badge.svg)](https://github.com/HELALI-Amin-24005915/Analogy-Engine/actions/workflows/quality.yml)

Moteur d’analogies basé sur des agents spécialisés (Scout, Matcher, Critic, Architect) et le graphe de propriétés logiques.

## Structure du projet

- **Racine**
  - `requirements.txt` — Dépendances Python (Agent Framework, Pydantic, MCP, etc.)
  - `.cursorrules` — Règles d’architecture et de qualité pour Cursor
- **config/** : fichiers de configuration
  - `pre-commit-config.yaml` — Hooks pre-commit (qualité, sécurité, pas de .env)
- **scripts/** : outils de qualité et d’environnement
  - `verify_quality.sh` — Vérification syntaxe Python et détection de secrets
  - `.gitignore` — Fichiers/dossiers à ignorer (env, cache, logs, etc.)
- **.github/workflows/** — CI (qualité, doc, sécurité)

### GitHub Actions

Le workflow **Qualité · Doc · Sécurité** s’exécute sur chaque push et pull request vers `main`. Voir [Actions](https://github.com/HELALI-Amin-24005915/Analogy-Engine/actions).

### Pre-commit

La config pre-commit est dans `config/`. À l’installation des hooks :

```bash
pre-commit install --config config/pre-commit-config.yaml
```
