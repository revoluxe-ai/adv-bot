Краткое руководство по включению SSL для внешних подключений к Spilo (Zalando)

- Файлы манифестов:
  - `k8s/databases/postgres/pg_ssl_hba.yaml` — включает `ssl: on` и настраивает `patroni.pg_hba` (замените `<YOUR_IP_CIDR>` на ваш IP/диапазон)
  - `k8s/databases/postgres/postgres-external.yaml` — NodePort service для внешнего доступа (временное решение)
  - `k8s/databases/postgres/jobs/enable-pgtrgm.yaml` — Job для включения расширения `pg_trgm`

- Как применить (PowerShell):
  ```powershell
  kubectl apply -f .\k8s\databases\postgres\pg_ssl_hba.yaml
  kubectl apply -f .\k8s\databases\postgres\postgres-external.yaml
  kubectl apply -f .\k8s\databases\postgres\jobs\enable-pgtrgm.yaml
  kubectl get postgresql -n prod-adv-bot
  kubectl get svc -n prod-adv-bot
  kubectl get job -n prod-adv-bot
  kubectl logs job/enable-pgtrgm -n prod-adv-bot
  ```

- Локальная проверка psql через SSL:
  ```powershell
  psql "host=<NODE_PUBLIC_IP> port=30432 dbname=adv_updater user=advupdater sslmode=require"
  ```

- В коде:
  - `app/utils/db/session_maker.py` теперь использует `ssl.SSLContext` и передаёт его в `create_async_engine(..., connect_args={"ssl": ssl_ctx})`
  - См. `scripts/test_pg_conn.py` — простой smoke тест


