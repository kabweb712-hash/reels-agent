# Reels Agent

> **Un système automatique pour capturer, transcrire, analyser et classer les Reels via Hermès/Jarvis 4**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 À propos du projet

**Reels Agent** est un pipeline automatisé qui permet de:
1. **Capturer** des liens de reels (Instagram, TikTok, YouTube, X, Facebook) via Telegram
2. **Les stocker** dans une queue SQLite en attendant le traitement
3. **Les traiter** par batch (toutes les nuits à 3h) :
   - Téléchargement de l'audio via `yt-dlp`
   - Transcription automatique via **Groq Whisper Large v3 Turbo**
   - Analyse sémantique via **Groq Llama 3.3 70B** (résumé, tags, catégorie)
4. **Stocker** les résultats dans SQLite (source of truth)
5. **Synchroniser** avec Notion (miroir pour consultation humaine)
6. **Requêter** les reels via Hermès (Jarvis 4) avec recherche plein-texte

**Cas d'usage typique** :
Utilisateur → Partage un reel Instagram à Hermès (Telegram) → Hermès enqueue le reel dans SQLite → Batch (cron 3h) traite le reel → Résultat disponible dans SQLite + Notion → Utilisateur demande à Hermès : "Montre-moi les reels sur le RAG"

---

## ✨ Fonctionnalités

| Fonctionnalité | Statut | Détails |
|----------------|--------|---------|
| Capture via Telegram | ✅ | Enqueue automatique des URLs |
| Transcription audio | ✅ | Groq Whisper (20 req/min gratuit) |
| Analyse LLM | ✅ | Groq Llama 3.3 70B (JSON structuré) |
| Stockage SQLite | ✅ | Source of truth avec FTS5 |
| Sync Notion | ✅ | Miroir consultable |
| Recherche plein-texte | ✅ | FTS5 sur transcript + résumé |
| Taxonomie évolutive | ✅ | Catégories fixes + suggérées par IA |
| Multi-plateforme | ✅ | Instagram, TikTok, YouTube, X, **Facebook** |
| Anti-doublon | ✅ | `UNIQUE(url)` natif |
| Batch cron | ✅ | Traitement nocturne économique |

---

## 🏗️ Architecture

```
┌──────────────┐   share reel    ┌──────────────────┐
│  Mobile       │ ──────────────▶ │  Hermès/Jarvis 4 │ ◀── OpenRouter
│  (User)       │                 │  (Bot Telegram)  │
└──────────────┘                 └────────┬─────────┘
                                 │
                                 │ enqueue_reel()
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SQLite (source of truth)                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ pending_reels │    │    reels     │    │   categories     │   │
│  │ (queue)       │    │ (traités)    │    │ + suggestions     │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ cron 03h
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Batch Processor (Python)                         │
│  yt-dlp ────▶ audio.mp3 ────▶ Groq Whisper ────▶ texte            │
│                                      │                              │
│                                      ▼                              ▼
│                              Groq Llama 3.3 ────▶ JSON (analyse)     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ sync périodique
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Notion (miroir)                             │
│  1 page par reel traité (15 propriétés)                            │
└─────────────────────────────────────────────────────────────────┘
```

**Principes clés** :
- Hermès = cerveau (point d'entrée Telegram + requêtes via OpenRouter)
- Batch worker = bras (cron Python qui traite la queue à 3h)
- SQLite = source of truth (stockage local rapide et illimité)
- Notion = miroir (pour consultation humaine, 1 page/reel)
- 100% gratuit : Groq (Whisper + Llama) + OpenRouter

---

## 📦 Prérequis

### Système
- VPS : Ubuntu 22.04+ (testé sur OVH)
- Python : 3.10+
- ffmpeg : Obligatoire pour yt-dlp
- yt-dlp : Pour télécharger les vidéos/audios

### APIs (100% gratuit)
| Service | Clé requise | Quota gratuit |
|---------|-------------|----------------|
| [Groq](https://groq.com) | `GROQ_API_KEY` | 20 req/min, 2000 req/jour |
| [OpenRouter](https://openrouter.ai) | `OPENROUTER_API_KEY` | Modèles gratuits illimités |
| [Notion](https://notion.so) | `NOTION_TOKEN` | 3 req/s |

---

## 🚀 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/TON_GITHUB/reels-agent.git
cd reels-agent
```

### 2. Installer les dépendances système
```bash
# Sur Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv ffmpeg

# Installer yt-dlp
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod +x /usr/local/bin/yt-dlp
```

### 3. Créer l'environnement virtuel
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows (PowerShell)
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
nano .env  # Remplir avec vos clés
```

**Variables dans `.env`** :
```env
# Database
DB_PATH=/home/ubuntu/reels-agent/reels.db

# OpenRouter (pour Hermès/Jarvis 4)
OPENROUTER_API_KEY=sk-or-v1-...
HERMES_MODEL=nvidia/nemotron-3-super-120b-a12b:free

# Groq (pour le batch)
GROQ_API_KEY=gsk_...
WHISPER_MODEL=whisper-large-v3-turbo
LLM_MODEL=llama-3.3-70b-versatile
FALLBACK_LLM_MODEL=llama-3.1-8b-instant

# Notion (miroir)
NOTION_TOKEN=secret_...
NOTION_DB_ID=...

# Batch
BATCH_LIMIT=50
MAX_RETRIES=3
```

> ⚠️ **Ne jamais commiter `.env`** (il contient des secrets) ! Il est dans `.gitignore`.

### 5. Initialiser la base de données
```bash
sqlite3 reels.db < db/reels_schema.sql
```

### 6. Installer le cron job
```bash
chmod +x scripts/install_cron.sh
./scripts/install_cron.sh
```

Vérifiez avec : `crontab -l`

---

## 🛠️ Configuration Notion

1. **Créer une intégration** :
   - [https://www.notion.so/profile/integrations](https://www.notion.so/profile/integrations)
   - Copier le token (`secret_...`) → `NOTION_TOKEN`

2. **Créer la base "Reels Agent"** avec ces 15 propriétés :

| Nom | Type | Options |
|-----|------|---------|
| Nom | Titre | - |
| URL | URL | - |
| Plateforme | Sélection | Instagram, TikTok, YouTube, X, Facebook |
| Créateur | Texte riche | - |
| Catégorie | Sélection | Dev / IA, Business, Motivation, Lifestyle, Sorties / Adresses, Fitness, Autre |
| Tags | Sélection multiple | - |
| Résumé | Texte riche | - |
| Points clés | Texte riche | - |
| Transcription | Texte riche | - |
| Langue | Sélection | Fr, En, Autre |
| Vision ? | Case à cocher | - |
| ID Reel | Nombre | - |
| Date de traitement | Date | - |

3. **Partager la base** avec l'intégration (Connections)
4. **Récupérer `NOTION_DB_ID`** depuis l'URL de la base

---

## 🤖 Intégration avec Hermès/Jarvis 4

### Les 7 tools disponibles

| Tool | Description | Exemple |
|------|-------------|---------|
| `enqueue_reel(url, note?, platform?)` | Enqueue un reel | `enqueue_reel("https://instagram.com/reel/...")` |
| `query_reels(keywords?, category?, tags?, since_days?, limit?)` | Recherche | `query_reels(keywords="RAG", limit=5)` |
| `list_pending_reels()` | État de la queue | `list_pending_reels()` |
| `list_categories()` | Liste catégories + suggestions | `list_categories()` |
| `accept_category(name, suggestion_id?)` | Valider une catégorie | `accept_category(name="Recettes")` |
| `trigger_batch()` | Lancer le batch manuellement | `trigger_batch()` |
| `get_reel_detail(reel_id)` | Détails d'un reel | `get_reel_detail(reel_id=1)` |

**Fichier de spécification** : `tools/hermes_tools_spec.json` (format OpenRouter compatible)

---

## 🧪 Tests

### Enqueuer un reel
```bash
python -c "from src.hermes_tools import enqueue_reel; print(enqueue_reel('URL_DU_REEL'))"
```

### Rechercher des reels
```bash
python -c "from src.hermes_tools import query_reels; print(query_reels(keywords='IA', limit=3))"
```

### Lancer le batch manuellement
```bash
python src/batch_processor.py
```

---

## 📁 Structure du projet

```
reels-agent/
├── .env.example              # Modèle de configuration
├── .gitignore                # Exclut secrets, DB, logs
├── README.md                 # Ce fichier
├── requirements.txt          # Dépendances Python
├── db/
│   └── reels_schema.sql      # Schéma SQLite (FTS5, triggers)
├── src/
│   ├── __init__.py
│   ├── config.py             # Variables et constantes
│   ├── db.py                 # Connexion SQLite + requêtes
│   ├── downloader.py         # Wrapper yt-dlp
│   ├── transcriber.py        # Appel Groq Whisper
│   ├── analyzer.py           # Appel Groq Llama 3.3
│   ├── notion_sync.py        # Synchronisation Notion
│   ├── batch_processor.py    # Worker cron principal
│   └── hermes_tools.py        # 7 outils pour Hermès/Jarvis 4
├── scripts/
│   └── install_cron.sh       # Installation du cron job
└── tools/
    └── hermes_tools_spec.json # Spécifications OpenRouter
```

---

## 🔄 Workflow

1. Utilisateur partage un reel via Telegram → Hermès appelle `enqueue_reel(url)`
2. Hermès insère dans `pending_reels` (status=pending)
3. Cron lance `batch_processor.py` à 3h
4. Pour chaque reel :
   - Anti-doublon (UNIQUE(url))
   - yt-dlp → métadonnées + audio.mp3
   - Groq Whisper → transcription
   - Groq Llama 3.3 → JSON (summary, key_points, category, tags, needs_vision, language)
   - INSERT dans `reels` + sync Notion
   - UPDATE `pending_reels` (status=done)
5. Utilisateur peut requêter via Hermès

---

## 🎯 Roadmap

- [x] MVP : Pipeline complet (capture → traitement → stockage → requête)
- [x] Support multi-plateforme (Instagram, TikTok, YouTube, X, Facebook)
- [x] Taxonomie évolutive avec validation humaine
- [x] Recherche plein-texte (FTS5)
- [x] Sync Notion (miroir)
- [x] Batch cron pour économiser les APIs
- [ ] v2 : Analyse visuelle (VLM) pour `needs_vision=true`
- [ ] v2 : Recherche sémantique (embeddings)
- [ ] v2 : Récap matinal Telegram

---

## 🤝 Contributing

1. Fork le projet
2. Crée une branche (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit (`git commit -m 'Ajout de la nouvelle fonctionnalité'`)
4. Push (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvre une Pull Request

---

## 📄 License

MIT © kabweb712-hash

---

## 🙏 Remerciements

- [Groq](https://groq.com) - Transcription et LLM gratuits
- [OpenRouter](https://openrouter.ai) - Accès aux modèles LLM
- [Notion](https://notion.so) - Organisation et miroir des données
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Téléchargement multi-plateforme
