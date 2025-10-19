# 🚀 GitOps Setup План (ArgoCD)

## Цель

Когда ты делаешь `git push`, поды **автоматически обновляются**, если нет ошибок.

```
git push на ветку
    ↓
GitLab CI pipeline (проверка синтаксиса, тесты)
    ↓
Образ в Harbor
    ↓
ArgoCD видит изменения
    ↓
ArgoCD разворачивает поды
    ↓
✅ Приложение обновлено
```

---

## 📋 Текущий Статус

| Компонент | Статус | Заметка |
|-----------|--------|---------|
| **Git** | ✅ GitLab | Используется |
| **Registry** | ✅ Harbor | Есть в кластере |
| **GitOps** | ❌ ArgoCD | Нет, нужно установить |
| **K8s Manifests** | ✅ Есть | В папке `k8s/` |
| **CI/CD** | ? | Нужно проверить |

---

## 🛠️ ШАГ 1: Установить ArgoCD

### 1.1 Создать namespace

```bash
kubectl create namespace argocd
```

### 1.2 Установить ArgoCD

```bash
# Скачать последнюю версию
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Или через Helm (рекомендуется)
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm install argocd argo/argo-cd -n argocd --set server.insecure=true
```

### 1.3 Получить пароль Admin

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

### 1.4 Открыть UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Перейти в браузер: https://localhost:8080
# Логин: admin
# Пароль: <из шага 1.3>
```

---

## 🔄 ШАГ 2: Подготовить Git Repo

### 2.1 Структура папок

```
your-repo/
├── app/                    # Исходный код (как сейчас)
├── k8s/                    # Kubernetes manifests ✅ (уже есть)
│   ├── deployments/        # Новая папка для manifests
│   │   ├── adv-bot.yaml
│   │   ├── predict-ctr.yaml
│   │   └── ...
│   ├── services/
│   └── ingress/
├── .gitlab-ci.yml          # Pipeline (нужно создать/обновить)
└── argocd/                 # Новая папка
    └── applications/
        └── adv-bot-app.yaml  # ArgoCD Application manifest
```

### 2.2 Создать ArgoCD Application

**Файл:** `argocd/applications/adv-bot-app.yaml`

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
    targetRevision: master  # Или dev/stage/prod
    path: k8s/deployments   # Папка с manifests
  
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  
  syncPolicy:
    automated:
      prune: true      # Удаляет ресурсы, которых нет в git
      selfHeal: true   # Переприменяет, если что-то изменилось вручную
    syncOptions:
    - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

---

## 🔐 ШАГ 3: Добавить Git Credentials в ArgoCD

### 3.1 Через UI ArgoCD

1. Перейти в **Settings** → **Repositories**
2. Нажать **Connect Repo Using HTTPS** или **SSH**
3. Заполнить:
   - Repository URL: `https://your-gitlab.com/your-group/adv-bot.git`
   - Username: `your-gitlab-user`
   - Password: `your-gitlab-token` (Personal Access Token)

### 3.2 Или через kubectl secret

```bash
kubectl create secret generic repo-creds \
  --from-literal=type=git \
  --from-literal=url=https://your-gitlab.com/your-group/adv-bot.git \
  --from-literal=password=<YOUR_TOKEN> \
  --from-literal=username=<YOUR_USERNAME> \
  -n argocd

# Потом добавить в Application:
# source:
#   repoURL: https://your-gitlab.com/your-group/adv-bot.git
```

---

## ✅ ШАГ 4: Создать Kubernetes Manifests

Перенести текущие deployments в `k8s/deployments/`:

**Пример:** `k8s/deployments/adv-bot-updater.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adv-bot-updater
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: adv-bot-updater
  template:
    metadata:
      labels:
        app: adv-bot-updater
    spec:
      containers:
      - name: adv-bot-updater
        image: harbor.your-domain.com/your-project/adv-bot:latest
        imagePullPolicy: Always
        env:
        - name: ENVIRONMENT
          value: production
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

---

## 🔨 ШАГ 5: Обновить CI/CD Pipeline

**Файл:** `.gitlab-ci.yml`

```yaml
stages:
  - build
  - test
  - push
  - deploy

variables:
  REGISTRY: "harbor.your-domain.com"
  PROJECT_NAME: "adv-bot"
  IMAGE_TAG: "${CI_COMMIT_SHA}"

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t ${REGISTRY}/${PROJECT_NAME}/adv-bot:${IMAGE_TAG} .
    - docker tag ${REGISTRY}/${PROJECT_NAME}/adv-bot:${IMAGE_TAG} ${REGISTRY}/${PROJECT_NAME}/adv-bot:latest
  only:
    - master
    - develop

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest tests/
  only:
    - master
    - develop

push:
  stage: push
  image: docker:latest
  services:
    - docker:dind
  script:
    - echo "$HARBOR_PASSWORD" | docker login -u "$HARBOR_USER" --password-stdin ${REGISTRY}
    - docker push ${REGISTRY}/${PROJECT_NAME}/adv-bot:${IMAGE_TAG}
    - docker push ${REGISTRY}/${PROJECT_NAME}/adv-bot:latest
  only:
    - master
    - develop
  when: on_success

deploy:
  stage: deploy
  image: alpine/git:latest
  script:
    # Обновить image tag в manifests
    - sed -i "s|image:.*|image: ${REGISTRY}/${PROJECT_NAME}/adv-bot:${IMAGE_TAG}|g" k8s/deployments/*.yaml
    - git config user.email "ci@gitlab.com"
    - git config user.name "GitLab CI"
    - git add k8s/deployments/
    - git commit -m "Update image to ${IMAGE_TAG}" || true
    - git push https://oauth2:${CI_JOB_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git HEAD:${CI_COMMIT_REF_NAME}
  only:
    - master
    - develop
  when: on_success

# ArgoCD автоматически видит изменения и деплоит!
```

---

## 🔍 ШАГ 6: Проверка и Синхронизация

### 6.1 Создать Application в ArgoCD

```bash
# Применить Application manifest
kubectl apply -f argocd/applications/adv-bot-app.yaml
```

### 6.2 Проверить статус

```bash
# Через kubectl
kubectl get application -n argocd

# Через ArgoCD CLI (установить: https://argoproj.github.io/argo-cd/cli_installation/)
argocd app list
argocd app get adv-bot
```

### 6.3 Синхронизировать вручную (если нужно)

```bash
argocd app sync adv-bot
```

---

## 🚀 ШАГ 7: Тестирование GitOps

### 7.1 Сделать изменение и push

```bash
# Измени что-то в k8s/deployments/adv-bot-updater.yaml
git add k8s/deployments/adv-bot-updater.yaml
git commit -m "Update adv-bot-updater replicas to 2"
git push origin master
```

### 7.2 Наблюдать процесс

```bash
# Смотри, как GitLab CI собирает образ
# Смотри в Harbor, как новый образ появился
# Смотри в ArgoCD UI, как идет синхронизация
# Смотри поды:
kubectl get pods -n default -w

# Проверь логи:
kubectl logs -f deployment/adv-bot-updater -n default
```

---

## 🔐 Надежность & Проверки

### Встроенные проверки ArgoCD:

1. ✅ **Синтаксис YAML** - ArgoCD валидирует все manifests
2. ✅ **Health Checks** - Проверяет, что поды healthy
3. ✅ **Dry-run** - Можно посмотреть, что будет применено
4. ✅ **Rollback** - Если что-то сломалось, легко откатить
5. ✅ **GitOps Audit Trail** - Все изменения в git

### Дополнительные проверки:

```yaml
# В Application manifest:
spec:
  syncPolicy:
    syncOptions:
    - Validate=true  # Валидация перед применением
    retry:
      limit: 5       # Повторять 5 раз если ошибка
      backoff:
        maxDuration: 3m  # Макс 3 минуты между попытками
```

### Pre-deployment проверки в CI/CD:

```bash
# В .gitlab-ci.yml добавить:
- kubeval k8s/deployments/*.yaml  # Проверка схемы K8s
- helm lint k8s/helm/             # Если используешь Helm
- pytest tests/integration/       # Integration тесты
```

---

## 📊 Структура После Setup

```
Repo structure:
├── app/
│   ├── modules/
│   └── ...
├── k8s/
│   ├── deployments/         ← Kubernetes manifests
│   │   ├── adv-bot.yaml
│   │   ├── predict-ctr.yaml
│   │   └── ...
│   ├── services/
│   └── ingress/
├── argocd/
│   └── applications/
│       └── adv-bot-app.yaml  ← ArgoCD Application
├── .gitlab-ci.yml           ← CI/CD Pipeline
└── tests/

Flow:
git push master
  ↓ (webhook)
GitLab CI builds & tests
  ↓ (if success)
Pushes image to Harbor
  ↓
Updates k8s/deployments/*.yaml with new image tag
  ↓ (git push)
ArgoCD detects changes
  ↓ (automated sync)
kubectl apply на новые manifests
  ↓
✅ Поды обновлены!
```

---

## ⚠️ Важные Замечания

1. **Branches** - Используй разные branches для разных окружений:
   - `master` → production
   - `develop` → staging
   - `feature/...` → review

2. **Image Tags** - Всегда используй конкретные теги, не `latest`:
   ```yaml
   image: harbor.../adv-bot:v1.2.3-abc123def456
   ```

3. **Secrets** - Не коммитить secrets в git! Использовать:
   - Sealed Secrets (ArgoCD + sealed-secrets)
   - Или External Secrets Operator
   - Или Vault

4. **Notifications** - Можно настроить уведомления:
   ```bash
   # ArgoCD → Slack/Discord/Email когда синхронизация завершена
   ```

---

## 🎯 Следующие Шаги

1. ✅ Создать namespace `argocd`
2. ✅ Установить ArgoCD
3. ✅ Создать `k8s/deployments/` с manifests
4. ✅ Создать `argocd/applications/adv-bot-app.yaml`
5. ✅ Обновить `.gitlab-ci.yml`
6. ✅ Добавить Git credentials в ArgoCD
7. ✅ Тестировать: `git push` → автоматический deploy!

---

**Версия:** 1.0  
**Дата:** 2025-10-18  
**Статус:** Ready for Implementation




