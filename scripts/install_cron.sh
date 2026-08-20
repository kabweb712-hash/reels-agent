#!/bin/bash
# Script pour installer le cron job sur le VPS OVH
# À exécuter depuis la racine du projet (reels-agent/)

set -e

echo "=== Installation du cron pour Reels Agent ==="

# Vérifier que le script est lancé depuis le bon répertoire
if [ ! -f "src/batch_processor.py" ]; then
    echo "❌ Erreur: Lancez ce script depuis la racine du projet (reels-agent/)"
    exit 1
fi

# Créer le répertoire logs s'il n'existe pas
mkdir -p logs

# Récupérer le chemin absolu du projet
PROJECT_PATH=$(pwd)
echo "📁 Chemin du projet: $PROJECT_PATH"

# Vérifier que venv existe
if [ ! -d "venv/bin" ]; then
    echo "⚠️  Avertissement: Le virtualenv (venv/) n'existe pas."
    echo "   Créez-le d'abord avec: python3 -m venv venv"
    exit 1
fi

# Chemin vers l'interpréteur Python du venv
PYTHON_PATH="$PROJECT_PATH/venv/bin/python"
BATCH_SCRIPT="$PROJECT_PATH/src/batch_processor.py"
LOG_DIR="$PROJECT_PATH/logs"

# Créer la ligne cron (exécutée tous les jours à 3h)
CRON_LINE="0 3 * * * $PYTHON_PATH $BATCH_SCRIPT >> $LOG_DIR/batch_\$(date +\%Y\%m\%d).log 2>&1"

echo "📝 Ligne cron à ajouter:"
echo "   $CRON_LINE"

# Ajouter au crontab de l'utilisateur actuel
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo "✅ Cron installé avec succès!"
echo "📊 Vérifiez avec: crontab -l"
echo "📝 Les logs seront stockés dans: $LOG_DIR/"
echo ""
echo "Pour tester manuellement le batch: $PYTHON_PATH $BATCH_SCRIPT"
