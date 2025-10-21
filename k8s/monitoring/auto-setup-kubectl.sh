#!/bin/bash
# Автоматическая настройка kubectl для Git Bash
# Этот скрипт добавляется в ~/.bashrc и выполняется при каждом запуске Git Bash

# Путь к kubectl в Windows
KUBECTL_WIN_PATH="/c/Program Files/Docker/Docker/resources/bin"

# Проверяем, есть ли kubectl в PATH
if ! command -v kubectl &> /dev/null; then
    # kubectl не найден, добавляем в PATH
    if [ -f "$KUBECTL_WIN_PATH/kubectl.exe" ]; then
        export PATH="$PATH:$KUBECTL_WIN_PATH"
        # Создаем alias для удобства
        alias k='kubectl'
    fi
fi

