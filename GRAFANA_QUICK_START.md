# 📊 Grafana - Быстрый Старт

**Дата**: 18 октября 2025  
**Статус**: ✅ Ready  
**Язык**: Русский  
**Shell**: Git Bash

---

## ⚡ За 1 минуту: Откройте Grafana

### САМЫЙ БЫСТРЫЙ СПОСОБ:

```bash
# Просто выполни эту команду в Git Bash:
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
```

### Потом откройте в браузере:
```
http://localhost:3000
```

### Логин:
```
Username: admin
Password: admin
```

---

## 📖 Что Вы Увидите в Grafana

### 1. Home Page (Главная страница)
После входа вы попадете на главную страницу со всеми available dashboards

### 2. Поиск Dashboards
Слева в боковом меню → **Dashboards** → найдите:
- **Pod Error Monitoring** - Наш пользовательский dashboard
- **Kubernetes / Nodes** - Статистика нод
- **Kubernetes / Pods** - Статистика подов
- И многое другое...

### 3. Наш Dashboard: Pod Error Monitoring
Это то, что мы развернули. Содержит:

**Панель 1: Pod Restarts Trend**
- График рестартов подов за последний час
- Видны все поды с проблемами

**Панель 2: Pod Status Overview (Top 20)**
- Таблица с 20 топ подами
- Показывает статус каждого

**Панель 3: Error Distribution by Type**
- Гистограмма типов ошибок
- Видны: CrashLoop, OOMKilled, ImagePull, etc

**Панель 4: Deployment Health Metrics**
- Метрика здоровья deployments
- Зеленая = все OK
- Красная = проблема

---

## 🔧 Как Это Работает (технически)

### Что происходит когда вы открываете Grafana:

```
1. Вы открываете http://localhost:3000
   ↓
2. kubectl port-forward перенаправляет порт 3000 на Pod Grafana
   ↓
3. Grafana подключается к Prometheus data source
   ↓
4. Prometheus имеет данные метрик от Kubernetes
   ↓
5. Grafana показывает красивые графики и таблицы
```

### Поток данных:

```
Kubernetes Nodes
    ↓ (metrics собираются)
Prometheus (хранит метрики 15 дней)
    ↓ (Grafana запрашивает данные)
Grafana (показывает красиво)
    ↓
Вы видите информацию в браузере
```

---

## 📊 Пошагово: Откройте Grafana и Посмотрите Dashboard

### ШАГ 1: Запустите Port Forwarding

В **Git Bash** выполните:

```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
```

**Вывод должен быть**:
```
Forwarding from 127.0.0.1:3000 -> 3000
Forwarding from [::1]:3000 -> 3000
Handling connection for 3000
```

⚠️ **Важно**: Оставьте этот терминал открытым! Если закрыть, port forwarding прекратится.

### ШАГ 2: Откройте Grafana в Браузере

1. Откройте браузер (Chrome, Firefox, Edge, etc)
2. Перейдите на: **http://localhost:3000**
3. Должна открыться страница входа Grafana

### ШАГ 3: Авторизуйтесь

```
Username: admin
Password: admin
```

Нажми **Sign in**

**На первый раз вас могут попросить изменить пароль:**
- Введите новый пароль (или пропустите, нажав Skip)

### ШАГ 4: Откройте Dashboard

После входа:

1. **В левом боковом меню** → нажми **Dashboards** (значок квадратика)
2. **Поищи** "Pod Error Monitoring" (или прокрути список)
3. **Кликни** на него

### ШАГ 5: Посмотрите Графики

Теперь вы видите 4 панели:

| Панель | Что Показывает | Зачем |
|--------|----------------|-------|
| **Pod Restarts Trend** | График рестартов | Видно какие поды падают |
| **Pod Status** | Таблица со статусами | Быстро найти проблемный под |
| **Error Distribution** | Гистограмма ошибок | Типы проблем |
| **Deployment Health** | Метрика здоровья | Общее состояние |

---

## 🔍 Что Можно Делать в Grafana

### 1. Смотреть Тренды
- Кликнуть на график
- Выбрать период времени (Last 1h, Last 24h, Last 7d, etc)
- Увидеть как менялась ситуация

### 2. Видеть Реал-тайм Данные
- Панели обновляются каждые 10 секунд
- Видно текущее состояние подов
- Видно новые ошибки

### 3. Искать Конкретный Pod
- Кликнуть на название пода в таблице
- Увидеть его подробную информацию
- Увидеть его logstream (если интегрирована Loki)

### 4. Экспортировать Данные
- Кликнуть на панель → Menu (три точки)
- Выбрать **Inspect**
- Скопировать данные или выгрузить CSV

### 5. Создать Свой Dashboard
- Нажать **+** (Create)
- Выбрать **Dashboard**
- Добавить панели (добавить уже готовые или создать новые)

---

## 🎨 Типичные Сценарии

### Сценарий 1: "В Slack алерт, как быстро посмотреть?"

```bash
# 1. Откройте Grafana (если еще не открыто)
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# 2. Откройте в браузере
# http://localhost:3000

# 3. Авторизуйтесь (admin/admin)

# 4. Откройте Dashboard "Pod Error Monitoring"

# 5. Увидите все проблемные поды прямо там!
```

### Сценарий 2: "Какие ошибки были за последние 24 часа?"

```
1. Откройте Dashboard (см выше)
2. В левом верхнем углу → Time Range → Last 24 hours
3. Увидите график за сутки
4. Видны все рестарты, ошибки, тренды
```

### Сценарий 3: "Мне нужен отчет для начальника"

```
1. Откройте Dashboard
2. Выбрать период (Last 7 days, Last 30 days)
3. Скриншот (Cmd+Shift+S или Print Screen)
4. Или экспортировать (Inspect → Download)
```

---

## 🛠️ Если Что-то Не Работает

### Проблема: "http://localhost:3000 не открывается"

**Решение**:
```bash
# Убедитесь что port-forward команда выполняется
# Должно быть видно в терминале:
# Forwarding from 127.0.0.1:3000 -> 3000

# Если ничего не видно, выполните еще раз:
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
```

### Проблема: "Логин admin/admin не работает" 🆘

**БЫСТРОЕ РЕШЕНИЕ (Вариант 1 - Скрипт)**:

```powershell
# Запустите скрипт PowerShell (самый простой способ):
powershell ./k8s/grafana-fix.ps1 -FixPassword

# Скрипт автоматически:
# 1. Пересоздаст pod Grafana
# 2. Получит правильный пароль
# 3. Покажет учетные данные
```

**БЫСТРОЕ РЕШЕНИЕ (Вариант 2 - Команды)**:

```bash
# 1. Пересоздайте pod Grafana
kubectl delete pod -n kube-prometheus-stack -l app.kubernetes.io/name=grafana

# 2. Подождите 30 секунд (pod перезагружается)
kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -w
# Нажмите Ctrl+C когда статус станет: 3/3 Running

# 3. Получите пароль
kubectl get secret -n kube-prometheus-stack kube-prometheus-stack-grafana \
  -o jsonpath="{.data.admin-password}" | powershell -Command \
  "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((Read-Host)))"

# 4. Запустите port-forward
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# 5. Откройте в браузере: http://localhost:3000
# Используйте: Username: admin, Password: (то что вывелось выше)
```

**ЕСЛИ СКРИПТ НЕ РАБОТАЕТ - ПОЛНАЯ ДИАГНОСТИКА**:

```bash
# 1. Проверьте что Grafana pod работает:
kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana

# Должно быть: NAME ... 3/3 Running
# Если статус не 3/3 Running, подождите еще

# 2. Проверьте логи Grafana:
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=grafana --tail=50

# Ищите в логах "authentication" или "password" ошибки
# Если видите ошибки - пересоздайте pod (команда выше)

# 3. Проверьте Secret с паролем:
kubectl get secret -n kube-prometheus-stack kube-prometheus-stack-grafana -o yaml

# Должны быть поля: admin-password и admin-user
```

### Проблема: "Нет данных на графиках"

**Решение**:
```bash
# 1. Проверьте что Prometheus работает:
kubectl get pods -n kube-prometheus-stack | grep prometheus

# 2. Проверьте что metrics собираются:
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090 → Status → Targets

# 3. Дождитесь чтобы данные собрались (может быть задержка)
```

### Проблема: "Dashboard 'Pod Error Monitoring' не видно"

**Решение**:
```bash
# Он должен быть загружен при деплое
# Если нет, разверните его:
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# И перезагрузите Grafana в браузере (Ctrl+Shift+R)
```

---

## 📱 Альтернативные Способы Подключения

### Способ 1: Через localhost:3000 (самый простой)
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000
```

### Способ 2: Через другой порт (если 3000 занят)
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3001:80
# http://localhost:3001
```

### Способ 3: Через Ingress (если настроен)
```
http://grafana.your-domain.com
```

### Способ 4: Через kubectl proxy (продвинутый)
```bash
kubectl proxy
# http://localhost:8001/api/v1/namespaces/kube-prometheus-stack/services/kube-prometheus-stack-grafana:80/proxy/
```

---

## 🔔 Что Еще Можно Посмотреть

### Prometheus (меtrики)
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090
# Здесь видны raw метрики и можно писать PromQL запросы
```

### AlertManager (алерты)
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
# http://localhost:9093
# Здесь видны все срабатывающие алерты
```

### Loki (логи) - если установлена
```bash
kubectl port-forward -n kube-prometheus-stack svc/loki 3100:3100
# http://localhost:3100
# Здесь видны логи из подов
```

---

## 💾 Быстрый Скрипт: Откройте Всё

Создайте файл `open-dashboards.sh`:

```bash
#!/bin/bash

echo "🚀 Открываем Dashboard..."

# Prometheus
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090 &
PROM_PID=$!

# Grafana
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80 &
GRAFANA_PID=$!

# AlertManager
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093 &
ALERT_PID=$!

echo ""
echo "✅ Все dashboards запущены!"
echo ""
echo "📊 Grafana:      http://localhost:3000"
echo "📈 Prometheus:   http://localhost:9090"
echo "🔔 AlertManager: http://localhost:9093"
echo ""
echo "Нажми Ctrl+C для остановки"
echo ""

# Ждем пока пользователь нажмет Ctrl+C
wait

# При выходе, убиваем все процессы
kill $PROM_PID $GRAFANA_PID $ALERT_PID 2>/dev/null
```

Запустите:
```bash
chmod +x open-dashboards.sh
./open-dashboards.sh
```

---

## 🎓 Дальше

После того как посмотрите Grafana:

1. **Откройте Prometheus** (http://localhost:9090)
   - Там видны raw метрики
   - Можно писать PromQL запросы

2. **Откройте AlertManager** (http://localhost:9093)
   - Видны все активные алерты
   - Видны история срабатываний

3. **Используйте CLI инструменты** (параллельно с Grafana)
   ```bash
   ./k8s/monitoring/pod-error-checker.sh default
   python3 k8s/monitoring/error_monitor.py -n default -l
   ```

---

## ✅ Чек-лист

- [ ] Git Bash открыт
- [ ] Выполнена команда `kubectl port-forward ...`
- [ ] Открыт браузер
- [ ] Введен URL http://localhost:3000
- [ ] Авторизован (admin/admin)
- [ ] Открыт Dashboard "Pod Error Monitoring"
- [ ] Видны 4 панели с данными
- [ ] Попробовал изменить время (Time Range)

---

**Status**: ✅ Ready  
**Updated**: 2025-10-18  
**Language**: Русский

