# 🚀 DevOps - Быстрый Старт (5-15 минут)

**Дата**: 18 октября 2025  
**Статус**: ✅ Ready  
**Язык**: Русский  
**Shell**: Git Bash

---

## ⚡ За 5 Минут: Самое Важное

### 1️⃣ Мониторинг Ошибок (прямо сейчас!)

```bash
# Быстрая диагностика (30 сек)
./k8s/monitoring/pod-error-checker.sh default

# Глубокий анализ (2 мин)
python3 k8s/monitoring/error_monitor.py -n default -o /tmp/errors.json -l

# Смотреть Grafana (5 мин)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 (admin/admin)
```

### 2️⃣ Развернуть Monitoring (10 мин)

```bash
# Применить Prometheus Rules
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml

# Применить Grafana Dashboard
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# Дать права на исполнение скриптам
chmod +x k8s/monitoring/pod-error-checker.sh
chmod +x k8s/monitoring/error_monitor.py

# Тестировать
./k8s/monitoring/pod-error-checker.sh kube-prometheus-stack
```

---

## 🎯 Выбери Свою Задачу

### 📋 Я DevOps Engineer (развертывание)

#### ШАГ 1: Установить ArgoCD (15 мин)

```bash
# Создать namespace
kubectl create namespace argocd

# Установить ArgoCD через Helm
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm install argocd argo/argo-cd -n argocd --set server.insecure=true

# Получить пароль
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo

# Открыть UI (в браузере)
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080
# Логин: admin
# Пароль: <из предыдущей команды>
```

#### ШАГ 2: Настроить GitOps (20 мин)

1. **Создать файл**: `argocd/applications/adv-bot-app.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: adv-bot
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://your-gitlab.com/your-group/adv-bot.git
    targetRevision: master
    path: k8s/deployments
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

2. **Применить Application**:

```bash
kubectl apply -f argocd/applications/adv-bot-app.yaml
```

3. **Проверить статус**:

```bash
argocd app list
argocd app get adv-bot
```

#### ШАГ 3: Настроить CI/CD (20 мин)

**Файл**: `.gitlab-ci.yml`

```yaml
stages:
  - build
  - test
  - push
  - deploy

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t harbor.your-domain.com/adv-bot:${CI_COMMIT_SHA} .

test:
  stage: test
  image: python:3.11
  script:
    - pytest tests/

push:
  stage: push
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker push harbor.your-domain.com/adv-bot:${CI_COMMIT_SHA}

deploy:
  stage: deploy
  image: alpine/git:latest
  script:
    - sed -i "s|image:.*|image: harbor.your-domain.com/adv-bot:${CI_COMMIT_SHA}|" k8s/deployments/*.yaml
    - git config user.email "ci@gitlab.com"
    - git config user.name "GitLab CI"
    - git add k8s/deployments/
    - git commit -m "Update image" || true
    - git push
```

#### ШАГ 4: Тестировать GitOps (5 мин)

```bash
# Измени что-то в k8s/deployments/
# Заккоммить и push
git add k8s/deployments/
git commit -m "Test GitOps"
git push origin master

# Смотри в ArgoCD UI как он автоматически синхронизируется!
```

---

### 🔍 Я On-Call Engineer (мониторинг)

#### Алерт пришел в Slack! (3-5 мин)

```bash
# 1. Срочная проверка (30 сек)
./k8s/monitoring/pod-error-checker.sh default

# Увидишь какие поды в проблеме:
# ⚠ pod-name: 5 рестартов
# ❌ CrashLoopBackOff: pod-xyz
```

#### Нужны подробности (2 мин)

```bash
# Глубокий анализ
python3 k8s/monitoring/error_monitor.py -n default -o /tmp/errors.json -l

# Посмотреть только критичные
cat /tmp/errors.json | jq '.errors[] | select(.severity=="CRITICAL")'
```

#### Найти проблему в коде (5 мин)

```bash
# Посмотреть логи проблемного пода
kubectl logs -n default POD_NAME --tail=200

# Описание пода (ищи Events)
kubectl describe pod -n default POD_NAME

# События namespace
kubectl get events -n default --sort-by='.lastTimestamp' | tail -20
```

#### Специальные типы проблем

**CrashLoop**:
```bash
# Найти и посмотреть логи (последние до краша)
kubectl logs -n default POD_NAME --previous
```

**OOMKilled** (нехватает памяти):
```bash
# Увеличить лимит
kubectl set resources deployment POD_NAME \
  -n default --limits=memory=2Gi
```

**ImagePullBackOff** (не может загрузить образ):
```bash
# Проверить доступ к registry
kubectl describe pod -n default POD_NAME | grep -A 5 "image:"
```

**Pending** (завис):
```bash
# Проверить почему ждет
kubectl describe pod -n default POD_NAME
```

---

### 📊 Я Team Lead (обучение команды)

#### Покажи Dashboards (5 мин)

```bash
# Prometheus Alerts
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/alerts
# Покажи где видны CRITICAL алерты

# Grafana Dashboard
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 → Pod Error Monitoring
# Покажи графики рестартов и ошибок
```

#### Научи Быстрому Старту (10 мин)

1. **Bash скрипт** (для быстрой проверки):
   ```bash
   ./k8s/monitoring/pod-error-checker.sh default
   ```
   Покажи красивый цветной вывод, объясни каждую секцию.

2. **Python скрипт** (для глубокого анализа):
   ```bash
   python3 k8s/monitoring/error_monitor.py -n default -l
   ```
   Покажи как логи помогают разобраться.

3. **kubectl команды**:
   ```bash
   kubectl logs -n default POD_NAME --tail=100
   kubectl describe pod -n default POD_NAME
   ```

#### Определи On-Call Workflow (15 мин)

Процесс при алерте:
1. `./pod-error-checker.sh` → 30 сек
2. `error_monitor.py` → 2 мин
3. `kubectl logs` → 1 мин
4. `kubectl describe` → 1 мин
5. Документировать в Slack

---

## 🔗 Структура Команд

### Все Команды (от быстрых к подробным)

```bash
# 🚨 СРОЧНО (30 сек)
./k8s/monitoring/pod-error-checker.sh default

# ⚠️ ПОДРОБНЕЕ (2 мин)
python3 k8s/monitoring/error_monitor.py -n default -l

# 📊 ДАШБОРДЫ (5 мин)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# 🔍 КОНКРЕТНЫЙ ПОД (1-2 мин)
kubectl logs -n default POD_NAME --tail=100
kubectl describe pod -n default POD_NAME
kubectl get events -n default --field-selector involvedObject.name=POD_NAME

# 📈 МЕТРИКИ (в Prometheus)
increase(kube_pod_container_status_restarts_total[1h]) > 0
```

---

## 📁 Файлы Которые Нужны

| Файл | Для кого | Где | Время |
|------|---------|-----|-------|
| `k8s/GITOPS_SETUP_PLAN.md` | DevOps | GitOps setup | 30 мин |
| `k8s/monitoring/00-START-HERE.md` | Все | Ориентация | 5 мин |
| `k8s/monitoring/QUICK_REFERENCE.md` | On-Call | Шпаргалка | 2 мин |
| `k8s/monitoring/ERROR_MONITORING_GUIDE.md` | Team Lead | Обучение | 30 мин |
| `k8s/monitoring/DEPLOYMENT_SUMMARY.md` | DevOps | Детали | 20 мин |
| `k8s/monitoring/pod-error-checker.sh` | On-Call | Быстрая проверка | - |
| `k8s/monitoring/error_monitor.py` | On-Call | Глубокий анализ | - |

---

## 🎯 Типичные Ситуации

### Ситуация 1: Поды постоянно рестартуются

```bash
# 1. Найти проблему
./k8s/monitoring/pod-error-checker.sh default

# 2. Посмотреть логи
kubectl logs -n default POD_NAME --tail=50 --previous

# 3. Увеличить timeout/memory
kubectl set resources deployment POD_NAME \
  -n default --requests=memory=512Mi --limits=memory=1Gi
```

### Ситуация 2: Новый образ не деплоится

```bash
# 1. Проверить статус
kubectl get deployment -n default POD_NAME

# 2. Посмотреть события
kubectl describe deployment -n default POD_NAME

# 3. Если ImagePullBackOff
kubectl logs -n default POD_NAME

# 4. Проверить registry credentials
kubectl get secrets -n default
```

### Ситуация 3: Ноды перегружены

```bash
# 1. Быстрая проверка
./k8s/monitoring/pod-error-checker.sh default

# 2. Увидишь Pending поды
# 3. Просмотреть узлы
kubectl get nodes
kubectl top nodes

# 4. Масштабировать или добавить ресурсов
kubectl scale deployment POD_NAME --replicas=2
```

---

## 🔧 Git Bash Специфика

Все команды работают в **Git Bash на Windows**!

```bash
# Правильно ✅
./k8s/monitoring/pod-error-checker.sh default

# Правильно ✅
python3 k8s/monitoring/error_monitor.py -n default

# Правильно ✅
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# ❌ Не используй PowerShell синтаксис
# ❌ Не используй Windows paths (C:\Users\...)
```

---

## 📞 Когда Что Использовать

### На Production Проблема → 30 сек
```bash
./k8s/monitoring/pod-error-checker.sh prod
```

### Нужны Логи → 2 мин
```bash
python3 k8s/monitoring/error_monitor.py -n prod -l
```

### Нужен Отчет → 5 мин
```bash
python3 k8s/monitoring/error_monitor.py -n prod -o /tmp/report.json
cat /tmp/report.json | jq '.summary'
```

### Нужна Визуализация → 10 мин
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# Открыть http://localhost:3000 в браузере
```

### Нужна История → 30 мин
```bash
# Prometheus хранит 15 дней данных
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/graph
# Выбрать метрику и период времени
```

---

## ✅ Чек-лист После Прочтения

- [ ] Прочитал документ про мою роль (выше)
- [ ] Протестировал `pod-error-checker.sh` в своем namespace
- [ ] Понимаю разницу между bash и python скриптом
- [ ] Могу открыть Grafana dashboard
- [ ] Знаю как получить логи пода
- [ ] Знаю как увеличить memory/cpu limits
- [ ] Понимаю что такое CrashLoop vs Pending vs ImagePull

---

## 🚀 Дальше (Если Есть Время)

### На следующий день:
- [ ] Настроить alerts в Slack
- [ ] Добавить custom dashboard
- [ ] Написать runbook для каждого типа ошибки

### На неделю:
- [ ] Настроить ArgoCD с GitOps
- [ ] Интегрировать в CI/CD pipeline
- [ ] Обучить всю команду

### На месяц:
- [ ] Оптимизировать alerting rules
- [ ] Добавить custom metrics
- [ ] Настроить SLA

---

## 📚 Документация

**Полное описание всех компонентов**:
```bash
# DevOps Полный гайд
cat DEVOPS_INSTRUCTIONS_SUMMARY.md

# Мониторинг быстрая справка
cat k8s/monitoring/QUICK_REFERENCE.md

# GitOps детально
cat k8s/GITOPS_SETUP_PLAN.md
```

---

## 🎓 Помощь

### Если не работает скрипт:
```bash
# Проверить bash
bash --version

# Дать права
chmod +x k8s/monitoring/pod-error-checker.sh

# Установить jq (нужен для скрипта)
apt-get install jq    # Linux
brew install jq       # macOS
choco install jq      # Windows (через Chocolatey)
```

### Если не работает Python:
```bash
python3 --version    # Должно быть 3.7+

chmod +x k8s/monitoring/error_monitor.py

# Проверить kubectl
kubectl version
```

### Если не работает kubectl:
```bash
kubectl config view     # Проверить конфиг
kubectl auth can-i get pods   # Проверить права
```

---

**Status**: ✅ Ready to Use  
**Last Updated**: 2025-10-18  
**Author**: DevOps Team

