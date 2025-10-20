#!/bin/bash
# Скрипт настройки kubectl для Git Bash с автоматической загрузкой
# Запустить: bash k8s/monitoring/setup-git-bash-kubectl.sh

echo "🔧 Настройка kubectl для Git Bash..."

# Путь к kubectl в Windows
KUBECTL_WIN_PATH="/c/Program Files/Docker/Docker/resources/bin"

# Проверяем существует ли kubectl
if [ -f "$KUBECTL_WIN_PATH/kubectl.exe" ]; then
    echo "✅ kubectl найден: $KUBECTL_WIN_PATH/kubectl.exe"
else
    echo "❌ kubectl НЕ найден в $KUBECTL_WIN_PATH"
    echo "Проверьте путь с помощью: where.exe kubectl (в PowerShell)"
    exit 1
fi

# Определяем файл профиля bash
BASH_PROFILE="$HOME/.bashrc"
if [ ! -f "$BASH_PROFILE" ]; then
    BASH_PROFILE="$HOME/.bash_profile"
    touch "$BASH_PROFILE"
fi

echo "📝 Используем файл профиля: $BASH_PROFILE"

# Получаем абсолютный путь к auto-setup скрипту
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_SETUP_SCRIPT="$SCRIPT_DIR/auto-setup-kubectl.sh"

# Проверяем есть ли уже автозагрузка
if grep -q "auto-setup-kubectl.sh" "$BASH_PROFILE" 2>/dev/null; then
    echo "⚠️  Автозагрузка kubectl уже настроена в $BASH_PROFILE"
else
    # Добавляем автозагрузку в bashrc
    echo "" >> "$BASH_PROFILE"
    echo "# Автоматическая настройка kubectl для Kubernetes" >> "$BASH_PROFILE"
    echo "if [ -f \"$AUTO_SETUP_SCRIPT\" ]; then" >> "$BASH_PROFILE"
    echo "    source \"$AUTO_SETUP_SCRIPT\"" >> "$BASH_PROFILE"
    echo "fi" >> "$BASH_PROFILE"
    echo "✅ Автозагрузка kubectl добавлена в $BASH_PROFILE"
fi

# Применяем настройки сразу
source "$AUTO_SETUP_SCRIPT"

echo ""
echo "🎉 ГОТОВО!"
echo ""
echo "✅ kubectl настроен и доступен в текущей сессии"
echo "✅ kubectl будет автоматически доступен во всех новых Git Bash сессиях"
echo ""
echo "🧪 Проверка:"
kubectl version --client --short 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ kubectl работает!"
else
    echo "⚠️  kubectl может требовать перезапуск Git Bash"
fi
echo ""
echo "Доступные команды:"
echo "  kubectl get pods -n default"
echo "  k get pods  (короткий alias)"
echo ""
echo "Проверка подключения к кластеру:"
echo "  kubectl get nodes"

