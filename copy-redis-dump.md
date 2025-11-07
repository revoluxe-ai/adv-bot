
1. Создаем хелпер-под для доступа к PVC с данными Redis:

kubectl delete pod redis-dump-helper -n prod-analytics --ignore-not-found
kubectl run redis-dump-helper -n prod-analytics \
  --image=busybox:1.36 \
  --restart=Never \
  --overrides='{
    "spec": {
      "volumes": [
        {
          "name": "redis-data",
          "persistentVolumeClaim": {
            "claimName": "redis-data-redis-master-0"
          }
        }
      ],
      "containers": [
        {
          "name": "busybox",
          "image": "busybox:1.36",
          "command": ["sleep", "3600"],
          "volumeMounts": [
            {
              "mountPath": "/data",
              "name": "redis-data"
            }
          ]
        }
      ]
    }
  }'


Шаг 2. Создать архив дампа прямо внутри PVC

(без стримов наружу)

kubectl exec -n prod-analytics redis-dump-helper -- \
  tar czf /data/dump.tar.gz -C /data dump.rdb


