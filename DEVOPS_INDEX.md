# 🚀 DevOps Документация - Индекс

**Дата**: 18 октября 2025  
**Версия**: 1.0  
**Статус**: ✅ Ready  
**Язык**: Русский

---

## 📍 Начни Отсюда

### 🎯 Выбери Свою Роль

| Роль | Как Начать | Время |
|------|-----------|-------|
| 🔥 **У меня срочная проблема!** | [5-15 мин Quick Start](#-быстрый-старт-5-15-минут) | 5 мин |
| 👨‍💼 **DevOps Engineer** (развертывание) | [GitOps Setup](#-gitops-setup-argocd) | 30 мин |
| 🔍 **On-Call Engineer** (мониторинг) | [Error Monitoring](#-error-monitoring-system) | 10 мин |
| 📚 **Team Lead** (обучение) | [Full Documentation](#-полная-документация) | 30 мин |

---

## ⚡ БЫСТРЫЙ СТАРТ (5-15 минут)

### 🚨 Есть Алерт в Slack?

```bash
# 30 сек - срочная проверка
./k8s/monitoring/pod-error-checker.sh default

# 2 мин - подробный анализ
python3 k8s/monitoring/error_monitor.py -n default -l -o /tmp/errors.json

# 5 мин - смотреть в Grafana
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 (admin/admin)
```

**Подробнее**: [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md)

> Важно: CSI-драйверы управляются провайдером. Не применять файлы `k8s/**csi**.yaml`. См. постмортем: [`docs/reports/CSI_DRIVER_POSTMORTEM_2025-10-20.md`](docs/reports/CSI_DRIVER_POSTMORTEM_2025-10-20.md)

---

## 📚 ПОЛНАЯ ДОКУМЕНТАЦИЯ

### 🚀 1. GitOps Setup (ArgoCD)

**Что это**: Автоматизация развертывания через Git push

**Файл**: [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md)

**Для**: DevOps Engineers

**Содержит**:
- ✅ Установка ArgoCD (7 шагов)
- ✅ Настройка CI/CD pipeline
- ✅ Git credentials
- ✅ Application manifests
- ✅ Тестирование GitOps

**Быстрый старт**:
```bash
# 1. Установить ArgoCD
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd

# 2. Получить пароль
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# 3. Открыть UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080
```

---

### 🚨 2. Error Monitoring System

**Что это**: 4-tier система обнаружения и анализа ошибок в Kubernetes

**Основные файлы**:

#### 📖 Документация
| Файл | Для кого | Время | Содержит |
|------|---------|-------|---------|
| [`k8s/monitoring/00-START-HERE.md`](k8s/monitoring/00-START-HERE.md) | Все | 5 мин | Ориентация по ролям |
| [`k8s/monitoring/DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md) | DevOps | 20 мин | Архитектура и детали |
| [`k8s/monitoring/QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md) | On-Call | 5 мин | Шпаргалка команд |
| [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md) | Team Lead | 30 мин | Полное руководство |
| [`k8s/monitoring/IMPLEMENTATION_STATUS.md`](k8s/monitoring/IMPLEMENTATION_STATUS.md) | DevOps | 15 мин | Чек-лист развертывания |

#### 🔧 Инструменты

| Инструмент | Тип | Использование | Время |
|-----------|-----|---------------|-------|
| **Prometheus Rules** [`prometheusrule-error-alerts.yaml`](k8s/monitoring/prometheusrule-error-alerts.yaml) | YAML | `kubectl apply -f` | - |
| **Grafana Dashboard** [`error-monitoring-dashboard.yaml`](k8s/monitoring/error-monitoring-dashboard.yaml) | YAML | `kubectl apply -f` | - |
| **Bash CLI** [`pod-error-checker.sh`](k8s/monitoring/pod-error-checker.sh) | Script | `./pod-error-checker.sh ns` | 30 сек |
| **Python CLI** [`error_monitor.py`](k8s/monitoring/error_monitor.py) | Script | `python3 error_monitor.py -n ns` | 2 мин |

#### 🚀 Быстрый Старт (10 мин)

```bash
# 1. Применить Prometheus Rules
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml

# 2. Применить Grafana Dashboard
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# 3. Дать права на исполнение
chmod +x k8s/monitoring/pod-error-checker.sh
chmod +x k8s/monitoring/error_monitor.py

# 4. Тестировать bash скрипт
./k8s/monitoring/pod-error-checker.sh default

# 5. Тестировать python скрипт
python3 k8s/monitoring/error_monitor.py -n default -o /tmp/errors.json

# 6. Открыть dashboards
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
```

---

## 🎯 ПО РОЛЯМ

### 👨‍💼 DevOps Engineer (Развертывание)

**Что делать**:
1. Установить ArgoCD
2. Настроить GitOps workflow
3. Развернуть мониторинг
4. Настроить CI/CD pipeline

**Документация**:
- [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md) - GitOps детально
- [`k8s/monitoring/DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md) - Мониторинг детально
- [`k8s/monitoring/IMPLEMENTATION_STATUS.md`](k8s/monitoring/IMPLEMENTATION_STATUS.md) - Чек-лист

**Команды**:
```bash
# GitOps
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd

# Monitoring
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# Проверка
kubectl get application -n argocd
kubectl get prometheusrules -n kube-prometheus-stack
```

---

### 🔍 On-Call Engineer (Использование)

**Что делать**:
1. Обнаруживать проблемы
2. Диагностировать корень
3. Фиксить или эскалировать
4. Документировать

**Документация**:
- [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md) - Быстрый старт
- [`k8s/monitoring/QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md) - Шпаргалка
- [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md) - Полный гайд

**Команды** (от быстрых к подробным):
```bash
# 🚨 Срочно (30 сек)
./k8s/monitoring/pod-error-checker.sh default

# ⚠️ Подробнее (2 мин)
python3 k8s/monitoring/error_monitor.py -n default -l

# 📊 Dashboard (5 мин)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# 🔍 Конкретный под (1-2 мин)
kubectl logs -n default POD_NAME --tail=100
kubectl describe pod -n default POD_NAME
```

---

### 📚 Team Lead (Обучение)

**Что делать**:
1. Обучить команду инструментам
2. Определить on-call workflow
3. Создать runbooks
4. Настроить alerts

**Документация**:
- [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md) - Практический гайд
- [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md) - Для обучения
- [`DEVOPS_INSTRUCTIONS_SUMMARY.md`](DEVOPS_INSTRUCTIONS_SUMMARY.md) - Полный обзор

**Демо**:
```bash
# 1. Bash инструмент
./k8s/monitoring/pod-error-checker.sh default

# 2. Python инструмент
python3 k8s/monitoring/error_monitor.py -n default -l

# 3. Dashboards
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000
```

---

## 📁 СТРУКТУРА ФАЙЛОВ

```
adv-bot/
├── DEVOPS_INDEX.md                           ← Ты здесь
├── DEVOPS_QUICK_START.md                     ← Быстрый старт (5-15 мин)
├── DEVOPS_INSTRUCTIONS_SUMMARY.md            ← Полный обзор всех инструкций
│
├── k8s/                                      ← Kubernetes манифесты и скрипты (от корня проекта)
│   ├── GITOPS_SETUP_PLAN.md                  ← GitOps setup (ArgoCD)
│   │
│   └── monitoring/                            ← Мониторинг, правила и утилиты
│       ├── 00-START-HERE.md                  ← Начало (ориентация)
│       ├── QUICK_REFERENCE.md                ← Шпаргалка команд
│       ├── ERROR_MONITORING_GUIDE.md         ← Полное руководство
│       ├── DEPLOYMENT_SUMMARY.md             ← Техдетали архитектуры
│       ├── IMPLEMENTATION_STATUS.md          ← Чек-листы развертывания
│       ├── README_CTR_DEBUG.md               ← CTR диагностика
│       ├── CLICKHOUSE_DISK_ISSUE.md          ← Знаемые проблемы
│       ├── CTR_v2_ISSUE_SUMMARY.md           ← CTR v2 проблемы
│       │
│       ├── prometheusrule-error-alerts.yaml  ← Prometheus Rules (15+ алертов)
│       ├── error-monitoring-dashboard.yaml   ← Grafana Dashboard
│       │
│       ├── pod-error-checker.sh              ← Bash CLI (быстрая проверка)
│       ├── pod-error-checker.ps1             ← PowerShell версия
│       ├── error_monitor.py                  ← Python CLI (глубокий анализ)
│       │
│       ├── access-monitoring-ui.sh           ← Открыть dashboard
│       ├── view-logs.sh / .ps1               ← Просмотр логов
│       ├── ctr-status.sh                     ← CTR статус
│       ├── ctr-final-diagnosis.sh            ← CTR диагностика
│       ├── fix-ctr-vectors.sh                ← Фикс CTR
│       ├── cleanup-clickhouse.sh             ← Очистка ClickHouse
│       ├── debug-ctr.sh                      ← Отладка CTR
│       └── ...
└── ...
```

---

## 🔗 БЫСТРЫЕ ССЫЛКИ

### Документация

| Документ | Быстро | Средне | Подробно |
|----------|--------|--------|----------|
| **GitOps** | - | [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md) | - |
| **Мониторинг** | [`k8s/monitoring/QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md) | [`k8s/monitoring/DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md) | [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md) |
| **Быстрый старт** | [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md) | - | - |
| **Полный обзор** | - | - | [`DEVOPS_INSTRUCTIONS_SUMMARY.md`](DEVOPS_INSTRUCTIONS_SUMMARY.md) |

### Инструменты

| Инструмент | Использование | Документация |
|-----------|--------------|--------------|
| **Bash CLI** | `./k8s/monitoring/pod-error-checker.sh default` | [`QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md) |
| **Python CLI** | `python3 k8s/monitoring/error_monitor.py -n default` | [`DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md) |
| **Prometheus** | `kubectl port-forward ... prometheus 9090:9090` | [`DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md) |
| **Grafana** | `kubectl port-forward ... grafana 3000:80` | [`ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md) |

---

## 🎯 ТИПИЧНЫЕ СЦЕНАРИИ

### 🚨 Сценарий 1: Критичная Проблема (3-5 мин)

```bash
# 1. Срочная проверка
./k8s/monitoring/pod-error-checker.sh prod

# 2. Если критично
python3 k8s/monitoring/error_monitor.py -n prod -l -o /tmp/errors.json

# 3. Посмотреть конкретный под
kubectl logs -n prod PROBLEM_POD --tail=200

# 4. Описание проблемы
kubectl describe pod -n prod PROBLEM_POD
```

**Документация**: [`DEVOPS_QUICK_START.md` → On-Call](#-я-on-call-engineer-мониторинг)

---

### 📊 Сценарий 2: Регулярная Проверка (10 мин)

```bash
# 1. Смотреть Grafana
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 → Pod Error Monitoring

# 2. Проверить Prometheus алерты
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/alerts

# 3. Экспортировать отчет
python3 k8s/monitoring/error_monitor.py -n prod -o /reports/daily.json
```

**Документация**: [`QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md)

---

### 🚀 Сценарий 3: Развертывание Мониторинга (15 мин)

```bash
# 1. Применить Prometheus
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml

# 2. Применить Grafana
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# 3. Дать права
chmod +x k8s/monitoring/pod-error-checker.sh
chmod +x k8s/monitoring/error_monitor.py

# 4. Тестировать
./k8s/monitoring/pod-error-checker.sh default
python3 k8s/monitoring/error_monitor.py -n default
```

**Документация**: [`DEPLOYMENT_SUMMARY.md`](k8s/monitoring/DEPLOYMENT_SUMMARY.md)

---

### 🔐 Сценарий 4: Настройка GitOps (45 мин)

```bash
# 1. Установить ArgoCD
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd

# 2. Создать Application manifest
# Файл: argocd/applications/adv-bot-app.yaml
kubectl apply -f argocd/applications/adv-bot-app.yaml

# 3. Настроить CI/CD
# Файл: .gitlab-ci.yml
git push origin master

# 4. Тестировать
argocd app list
```

**Документация**: [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md)

---

## 💡 ПОЛЕЗНЫЕ КОМАНДЫ

### Мониторинг (On-Call)

```bash
# Быстрая проверка
./k8s/monitoring/pod-error-checker.sh default

# Глубокий анализ
python3 k8s/monitoring/error_monitor.py -n default -l

# Логи пода
kubectl logs -n default POD_NAME --tail=200

# Описание пода
kubectl describe pod -n default POD_NAME

# События
kubectl get events -n default --sort-by='.lastTimestamp' | tail -20

# По рестартам
kubectl get pods -n default --sort-by='.status.containerStatuses[0].restartCount'
```

### GitOps (DevOps)

```bash
# Статус ArgoCD
argocd app list
argocd app get adv-bot

# Синхронизировать
argocd app sync adv-bot

# Проверить resources
kubectl get application -n argocd
kubectl get deployment -n default
```

### Dashboards (Все)

```bash
# Prometheus Alerts
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/alerts

# Grafana
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 (admin/admin)

# AlertManager
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
# http://localhost:9093
```

---

## ✅ ЧЕК-ЛИСТЫ

### Для DevOps Engineers

- [ ] Прочитать [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md)
- [ ] Установить ArgoCD
- [ ] Создать Application manifest
- [ ] Настроить CI/CD pipeline
- [ ] Развернуть мониторинг Prometheus
- [ ] Развернуть Grafana Dashboard
- [ ] Протестировать GitOps workflow
- [ ] Обучить team

### Для On-Call Engineers

- [ ] Прочитать [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md)
- [ ] Прочитать [`k8s/monitoring/QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md)
- [ ] Дать права на исполнение скриптам
- [ ] Протестировать `pod-error-checker.sh`
- [ ] Протестировать `error_monitor.py`
- [ ] Открыть Grafana dashboard
- [ ] Практика с kubectl командами
- [ ] Понимать типы ошибок (CrashLoop, OOMKilled, etc)

### Для Team Leads

- [ ] Прочитать [`DEVOPS_INSTRUCTIONS_SUMMARY.md`](DEVOPS_INSTRUCTIONS_SUMMARY.md)
- [ ] Прочитать [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md)
- [ ] Провести демо для team
- [ ] Определить on-call workflow
- [ ] Написать runbooks
- [ ] Установить SLA
- [ ] Настроить notifications (Slack/Telegram)

---

## 🔧 ТРЕБОВАНИЯ

| Компонент | Версия | Обязательный |
|-----------|--------|------------|
| Kubernetes | 1.20+ | ✅ |
| kubectl | 1.20+ | ✅ |
| Prometheus | Any | ✅ |
| Grafana | 8.0+ | ✅ |
| Python | 3.7+ | ✅ (для error_monitor.py) |
| Bash/Git Bash | Any | ✅ |
| jq | Any | ✅ (для pod-error-checker.sh) |
| Helm | 3.0+ | ✅ (для ArgoCD) |

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### Прямо Сейчас (5-15 мин)
1. Выбрать свою роль (DevOps/On-Call/Team Lead)
2. Прочитать соответствующую документацию
3. Запустить первую команду

### Сегодня (1-2 часа)
1. Развернуть мониторинг
2. Протестировать инструменты
3. Открыть dashboards

### На Неделю (4-8 часов)
1. Интегрировать ArgoCD
2. Настроить CI/CD pipeline
3. Обучить team
4. Настроить notifications

### На Месяц (16+ часов)
1. Оптимизировать rules
2. Добавить custom metrics
3. Написать runbooks
4. Настроить SLA

---

## 📞 ПОМОЩЬ

### Быстрая помощь
- **Срочная проблема**: [`DEVOPS_QUICK_START.md`](DEVOPS_QUICK_START.md)
- **Команда не работает**: [`k8s/monitoring/QUICK_REFERENCE.md`](k8s/monitoring/QUICK_REFERENCE.md) → Troubleshooting
- **Не знаю где начать**: Эта страница (выше выбери свою роль)

### Подробная помощь
- **GitOps**: [`k8s/GITOPS_SETUP_PLAN.md`](k8s/GITOPS_SETUP_PLAN.md)
- **Мониторинг**: [`k8s/monitoring/ERROR_MONITORING_GUIDE.md`](k8s/monitoring/ERROR_MONITORING_GUIDE.md)
- **Все вместе**: [`DEVOPS_INSTRUCTIONS_SUMMARY.md`](DEVOPS_INSTRUCTIONS_SUMMARY.md)

---

## 📊 СТАТИСТИКА

| Компонент | Количество | Детали |
|-----------|-----------|--------|
| **Документов** | 6 | Markdown гайды |
| **Скриптов** | 12+ | Bash + Python + PowerShell |
| **Prometheus Алертов** | 15+ | По категориям |
| **Grafana Панелей** | 5+ | Dashboards |
| **Kubernetes Manifests** | 2 | YAML конфиги |
| **Примеров Команд** | 50+ | Практических примеров |

---

## 🎉 ГОТОВО!

Выбери свою роль выше и начни работу!

```bash
# За 30 сек проверить что все работает
./k8s/monitoring/pod-error-checker.sh default
```

---

**Версия**: 1.0  
**Дата**: 18.10.2025  
**Статус**: ✅ Production Ready  
**Язык**: Русский  
**Shell**: Git Bash


