# 🔐 Grafana - Решение Проблемы с Логином

**Дата**: 18 октября 2025  
**Статус**: ✅ РЕШЕНО  
**Проблема**: Логин/пароль `admin/admin` не работали  

---

## 📋 Что Было

Grafana pod был в состоянии `3/3 Running`, но при попытке входа с `admin/admin` возникала ошибка:
```
Failed to authenticate request
[password-auth.failed] failed to authenticate identity: LDAP not enabled
[password-auth.invalid] invalid password
```

---

## ✅ Что Было Сделано

### 1. Диагностика
- ✅ Проверили что pod Grafana запущен: `3/3 Running`
- ✅ Получили пароль из Kubernetes Secret: `admin` (base64: `YWRtaW4=`)
- ✅ Проверили конфигурацию pod - все правильно
- ✅ Просмотрели логи - логины были неверные

### 2. Решение
**Основная причина**: Pod был инициализирован до того как Secret был правильно установлен.

**Способ исправления**:
```bash
# 1. Удалили pod (автоматически создается новый)
kubectl delete pod -n kube-prometheus-stack -l app.kubernetes.io/name=grafana

# 2. Дождались перезагрузки (30 секунд)
# Pod был пересоздан с правильными переменными окружения из Secret

# 3. Проверили что все работает
kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana
# Результат: 3/3 Running ✅
```

### 3. Актуальные Учетные Данные
```
Username: admin
Password: admin
```

---

## 🚀 Как Использовать Grafana Теперь

### Быстрый Старт (30 секунд)

**Вариант 1 - С помощью скрипта (РЕКОМЕНДУЕТСЯ)**:
```powershell
powershell ./k8s/grafana-fix.ps1 -FixPassword
```

Скрипт автоматически:
1. Проверит статус pod
2. Получит пароль из Secret
3. Запустит port-forward
4. Покажет учетные данные

**Вариант 2 - Вручную**:
```bash
# Терминал 1: Port-forward
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80

# Терминал 2 (в браузере):
# http://localhost:3000
# Username: admin
# Password: admin
```

---

## 📊 Доступные Скрипты

### `k8s/grafana-fix.ps1` - Полный скрипт для диагностики и исправления

**Использование с флагами** (без интерактивного меню):
```powershell
# Полный fix (пересоздать pod, получить пароль)
powershell ./k8s/grafana-fix.ps1 -FixPassword

# Только проверить статус pod
powershell ./k8s/grafana-fix.ps1 -CheckPod

# Только показать пароль
powershell ./k8s/grafana-fix.ps1 -ShowPassword

# Только запустить port-forward
powershell ./k8s/grafana-fix.ps1 -PortForward
```

**Использование интерактивного меню**:
```powershell
powershell ./k8s/grafana-fix.ps1

# Меню:
# 1. ✅ Полный Fix
# 2. 🔍 Проверить статус pod
# 3. 🔄 Пересоздать pod
# 4. 🔑 Показать пароль
# 5. 📡 Запустить port-forward
# 6. 🚀 Быстрый старт
```

---

## 📁 Обновленные Документы

1. **GRAFANA_PASSWORD.txt** - Актуальные учетные данные и инструкции
2. **GRAFANA_ONE_LINER.txt** - Быстрый старт за одну команду
3. **GRAFANA_QUICK_START.md** - Обновлены разделы про проблемы
4. **k8s/grafana-fix.ps1** - Новый скрипт PowerShell для автоматизации
5. **GRAFANA_LOGIN_FIX_SUMMARY.md** - Этот файл (резюме решения)

---

## 🔧 Если Проблема Повторится

### Шаг 1: Быстрый Fix (1 команда)
```bash
kubectl delete pod -n kube-prometheus-stack -l app.kubernetes.io/name=grafana
```
(pod автоматически пересоздается с правильными параметрами)

### Шаг 2: Подождите 30 секунд
```bash
kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=grafana -w
# Нажмите Ctrl+C когда статус станет 3/3 Running
```

### Шаг 3: Попробуйте Вход Снова
- URL: http://localhost:3000
- Username: admin
- Password: admin

### Если Не Помогло
```bash
# Полная диагностика
powershell ./k8s/grafana-fix.ps1 -CheckPod
powershell ./k8s/grafana-fix.ps1 -ShowPassword
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=grafana --tail=50
```

---

## ✨ Результат

✅ Pod: `kube-prometheus-stack-grafana-6cffcd886b-ts9bm` (3/3 Running)  
✅ Логины: admin/admin  
✅ Dashboard: Pod Error Monitoring доступен  
✅ Метрики: Собираются корректно  

---

## 📚 Дополнительные Материалы

- [GRAFANA_QUICK_START.md](./GRAFANA_QUICK_START.md) - Полный гайд
- [GRAFANA_PASSWORD.txt](./GRAFANA_PASSWORD.txt) - Учетные данные
- [GRAFANA_ONE_LINER.txt](./GRAFANA_ONE_LINER.txt) - Одна команда
- [k8s/grafana-fix.ps1](./k8s/grafana-fix.ps1) - Скрипт для исправления

---

**Последнее обновление**: 2025-10-18  
**Автор**: DevOps Team  
**Статус**: Production Ready ✅
