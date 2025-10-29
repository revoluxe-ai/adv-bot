import json
import sys
from typing import Dict, Any, List


def parse_memory_string(memory_str: str) -> float:
    """Parses a memory string (e.g., '100Mi', '10Gi') into MiB."""
    if not memory_str:
        return 0
    memory_str = memory_str.strip()
    if memory_str.endswith("Mi"):
        return int(memory_str[:-2])
    elif memory_str.endswith("Gi"):
        return int(memory_str[:-2]) * 1024
    elif memory_str.endswith("Ki"):
        return int(memory_str[:-2]) / 1024
    elif memory_str.endswith("M"):
        return int(memory_str[:-1])
    elif memory_str.endswith("G"):
        return int(memory_str[:-1]) * 1024
    elif memory_str.endswith("m"):  # Добавляем обработку для 'm' (миллибайты)
        # Преобразуем миллибайты в MiB
        return int(memory_str[:-1]) / 1024
    elif memory_str.endswith("K"):
        return int(memory_str[:-1]) / 1024
    return int(memory_str) / (1024 * 1024)  # Assume bytes if no suffix


def analyze_pods_memory_from_stdin() -> List[Dict[str, Any]]:
    anomalous_pods: List[Dict[str, Any]] = []
    data = json.load(sys.stdin)

    for item in data["items"]:
        pod_name = item["metadata"]["name"]
        for container in item["spec"]["containers"]:
            container_name = container["name"]
            if (
                "resources" in container
                and "requests" in container["resources"]
                and "memory" in container["resources"]["requests"]
            ):
                memory_request_str = container["resources"]["requests"]["memory"]
                memory_mib = parse_memory_string(memory_request_str)
                # Определяем порог для аномально большого запроса (например, более 50Gi)
                if memory_mib > (50 * 1024):  # 50 GiB in MiB
                    anomalous_pods.append(
                        {
                            "pod_name": pod_name,
                            "container_name": container_name,
                            "requested_memory": memory_request_str,
                            "requested_memory_mib": memory_mib,
                        }
                    )
    return anomalous_pods


if __name__ == "__main__":
    anomalies = analyze_pods_memory_from_stdin()
    if anomalies:
        print("Найдены поды с аномально большими запросами на память:")
        for anomaly in anomalies:
            print(
                f"  Под: {anomaly['pod_name']}, Контейнер: {anomaly['container_name']}, Запрошено: {anomaly['requested_memory']} ({anomaly['requested_memory_mib']} MiB)"
            )
    else:
        print("Аномально больших запросов на память не найдено.")
