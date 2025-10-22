import json
import sys
from typing import Dict, Any, List, Set

def parse_resource_string(resource_string: str, resource_type: str) -> float:
    """
    Parses a resource string (e.g., '100m', '1Gi', '500Mi') into a standardized float value.
    - For CPU: returns value in millicores.
    - For Memory: returns value in MiB.
    """
    if resource_string is None:
        return 0.0

    resource_string = resource_string.strip()

    if resource_type == 'cpu':
        if resource_string.endswith('m'):
            return float(resource_string[:-1])
        else:
            try:
                return float(resource_string) * 1000  # Convert cores to millicores
            except ValueError:
                return 0.0  # Should not happen for valid CPU strings
    elif resource_type == 'memory':
        if resource_string.endswith('m'):  # Millibytes
            return float(resource_string[:-1]) / (1024 * 1024)  # Convert millibytes to MiB
        elif resource_string.endswith('Ki'):
            return float(resource_string[:-2]) / 1024  # KiB to MiB
        elif resource_string.endswith('Mi'):
            return float(resource_string[:-2])
        elif resource_string.endswith('Gi'):
            return float(resource_string[:-2]) * 1024  # GiB to MiB
        elif resource_string.endswith('T'):  # Not common for k8s memory
            return float(resource_string[:-1]) * 1024 * 1024  # TB to MiB (assuming TiB)
        elif resource_string.endswith('G'):  # Convert GB to MiB (assuming GiB)
            return float(resource_string[:-1]) * 1024
        elif resource_string.endswith('M'):  # Convert MB to MiB (assuming MiB)
            return float(resource_string[:-1])
        else:  # Assume bytes
            try:
                return float(resource_string) / (1024 * 1024)  # Bytes to MiB
            except ValueError:
                return 0.0  # Should not happen for valid memory strings
    return 0.0

def calculate_total_resources(data: Dict[str, Any]) -> Dict[str, float]:
    """Calculates total CPU and memory requests and limits for Deployments and DaemonSets."""
    total_cpu_requests = 0.0
    total_cpu_limits = 0.0
    total_mem_requests = 0.0
    total_mem_limits = 0.0

    for item in data.get('items', []):
        for container in item['spec']['template']['spec'].get('containers', []):
            resources = container.get('resources', {})
            requests = resources.get('requests', {})
            limits = resources.get('limits', {})

            total_cpu_requests += parse_resource_string(requests.get('cpu'), 'cpu')
            total_cpu_limits += parse_resource_string(limits.get('cpu'), 'cpu')
            total_mem_requests += parse_resource_string(requests.get('memory'), 'memory')
            total_mem_limits += parse_resource_string(limits.get('memory'), 'memory')
        
        for init_container in item['spec']['template']['spec'].get('initContainers', []):
            resources = init_container.get('resources', {})
            requests = resources.get('requests', {})
            limits = resources.get('limits', {})

            total_cpu_requests += parse_resource_string(requests.get('cpu'), 'cpu')
            total_cpu_limits += parse_resource_string(limits.get('cpu'), 'cpu')
            total_mem_requests += parse_resource_string(requests.get('memory'), 'memory')
            total_mem_limits += parse_resource_string(limits.get('memory'), 'memory')

    return {
        'total_cpu_requests_m': total_cpu_requests,
        'total_cpu_limits_m': total_cpu_limits,
        'total_mem_requests_mib': total_mem_requests,
        'total_mem_limits_mib': total_mem_limits,
    }

def analyze_resources(data: Dict[str, Any]) -> None:
    print(f"{'TYPE':<10} {'NAMESPACE':<20} {'NAME':<30} {'CONTAINER':<30} {'CPU_REQ':<10} {'CPU_LIM':<10} {'MEM_REQ':<10} {'MEM_LIM':<10}")
    print("-" * 150)

    for item in data.get('items', []):
        kind = item.get('kind', 'Unknown')
        metadata = item.get('metadata', {})
        namespace = metadata.get('namespace', 'N/A')
        name = metadata.get('name', 'N/A')
        
        template_spec = item.get('spec', {}).get('template', {}).get('spec', {})
        containers = template_spec.get('containers', [])

        for container in containers:
            container_name = container.get('name', 'N/A')
            resources = container.get('resources', {})
            requests = resources.get('requests', {})
            limits = resources.get('limits', {})

            cpu_req = requests.get('cpu')
            cpu_lim = limits.get('cpu')
            mem_req = requests.get('memory')
            mem_lim = limits.get('memory')

            cpu_req_val = parse_resource_string(cpu_req, 'cpu')
            cpu_lim_val = parse_resource_string(cpu_lim, 'cpu')
            mem_req_val = parse_resource_string(mem_req, 'memory')
            mem_lim_val = parse_resource_string(mem_lim, 'memory')
            
            # For CPU, output in millicores; for Memory, output in MiB
            print(f"{kind:<10} {namespace:<20} {name:<30} {container_name:<30} {cpu_req_val:<10.0f} {cpu_lim_val:<10.0f} {mem_req_val:<10.0f} {mem_lim_val:<10.0f}")

def analyze_services_without_endpoints(data: Dict[str, Any]) -> None:
    """Analyzes Kubernetes Services to find those without active Endpoints."""
    services_without_endpoints: List[Dict[str, Any]] = []

    for item in data.get('items', []):
        service_name = item['metadata']['name']
        namespace = item['metadata']['namespace']

        # A service without a selector usually indicates it's an external service
        # or a headless service, which might not have direct endpoints managed by K8s.
        # We are primarily interested in ClusterIP/NodePort services that *should* have pods backing them.
        if 'selector' not in item['spec']:
            continue

        # To check if a service has endpoints, we need to query endpoints resource
        # However, this script currently only reads the services.json file.
        # For a full check, we would need to fetch endpoints dynamically or have an endpoints.json file.
        # For now, we'll make a simplifying assumption: if a service has a selector,
        # but no pods match that selector (which we can't directly check here), it will eventually have no endpoints.
        # A more direct approach would be to get endpoints for each service.
        # As a placeholder, we'll assume services with a selector and no associated pods (which we can't determine here)
        # might be candidates. A more robust solution involves `kubectl get endpoints <service-name> -o json`
        # and checking `subsets` field.

        # Given the current data, we can't definitively determine if a service has no endpoints
        # without additional information about active pods or a separate endpoints dump.
        # We will simply report all services for manual inspection that have a selector.
        services_without_endpoints.append({
            'service_name': service_name,
            'namespace': namespace,
            'selector': item['spec']['selector']
        })

    if services_without_endpoints:
        print("Найдены Service'ы, которые могут не иметь активных Endpoint'ов (требуется ручная проверка):")
        for service in services_without_endpoints:
            print(f"  Service: {service['service_name']}, Namespace: {service['namespace']}, Selector: {service['selector']}")
    else:
        print("Не найдено Service'ов, которые могли бы не иметь активных Endpoint'ов (или не применимо).")

def analyze_pvcs(pvc_data: Dict[str, Any]) -> None:
    """Analyzes PersistentVolumeClaims to find unused or pending ones."""
    print("\n--- Анализ PersistentVolumeClaims (PVC) ---")
    print(f"{'NAMESPACE':<20} {'PVC_NAME':<30} {'STATUS':<10} {'CAPACITY':<10}")
    print("-" * 70)

    for item in pvc_data.get('items', []):
        name = item['metadata']['name']
        namespace = item['metadata']['namespace']
        status = item['status'].get('phase', 'Unknown')
        capacity = item['status'].get('capacity', {}).get('storage', 'N/A')

        if status == 'Pending':
            print(f"{namespace:<20} {name:<30} {status:<10} {capacity:<10} (Не используется, ожидает привязки)")
        elif status == 'Bound':
            # Для Bound PVC нужна дополнительная проверка на использование подами
            print(f"{namespace:<20} {name:<30} {status:<10} {capacity:<10} (Bound - требуется дальнейшая проверка на использование)")

    print("\nДля Bound PVC требуется дополнительная проверка на то, используется ли PersistentVolumeClaim активным подом.")

def analyze_pvcs_with_pods(pvc_data: Dict[str, Any], pods_data: Dict[str, Any]) -> None:
    print("\n--- Анализ PersistentVolumeClaims (PVC) с учетом подов ---")
    print(f"{'NAMESPACE':<20} {'PVC_NAME':<30} {'STATUS':<10} {'CAPACITY':<10} {'USED_BY_POD':<30}")
    print("-" * 120)

    used_pvcs: Set[str] = set()

    # Собираем информацию о том, какие PVC используются подами
    for pod_item in pods_data.get('items', []):
        pod_namespace = pod_item['metadata']['namespace']
        for volume in pod_item['spec'].get('volumes', []):
            if 'persistentVolumeClaim' in volume:
                pvc_name = volume['persistentVolumeClaim']['claimName']
                used_pvcs.add(f"{pod_namespace}/{pvc_name}")

    for item in pvc_data.get('items', []):
        name = item['metadata']['name']
        namespace = item['metadata']['namespace']
        status = item['status'].get('phase', 'Unknown')
        capacity = item['status'].get('capacity', {}).get('storage', 'N/A')
        
        full_pvc_name = f"{namespace}/{name}"
        used_by_pod_status = "-"

        if status == 'Pending':
            used_by_pod_status = "Не используется (Pending)"
        elif status == 'Bound':
            if full_pvc_name in used_pvcs:
                used_by_pod_status = "Используется активным подом"
            else:
                used_by_pod_status = "Не используется (Bound, но нет активных подов)"
        
        print(f"{namespace:<20} {name:<30} {status:<10} {capacity:<10} {used_by_pod_status:<30}")

    print("\nРекомендации:")
    print("1. PVC со статусом 'Pending' и 'Не используется (Bound, но нет активных подов)' являются кандидатами на удаление.")
    print("2. Для PVC, используемых активными подами, убедитесь, что их размер соответствует реальным потребностям.")

if __name__ == '__main__':
    try:
        with open('deployments.json', 'r', encoding='utf-16') as f:
            deployments_data = json.load(f)
        with open('daemonsets.json', 'r', encoding='utf-16') as f:
            daemonsets_data = json.load(f)
   
        all_items: List[Dict[str, Any]] = []
        all_items.extend(deployments_data.get('items', []))
        all_items.extend(daemonsets_data.get('items', []))
   
        combined_data = {'items': all_items}
        analyze_resources(combined_data)

        total_resources = calculate_total_resources(combined_data)
        print("\n--- Суммарные ресурсы (Deployments и DaemonSets) ---")
        print(f"Общий CPU запрошено: {total_resources['total_cpu_requests_m'] / 1000:.2f} ядер ({total_resources['total_cpu_requests_m']:.0f}m)")
        print(f"Общий CPU лимиты:    {total_resources['total_cpu_limits_m'] / 1000:.2f} ядер ({total_resources['total_cpu_limits_m']:.0f}m)")
        print(f"Общая память запрошено: {total_resources['total_mem_requests_mib'] / 1024:.2f} GiB ({total_resources['total_mem_requests_mib']:.0f} MiB)")
        print(f"Общая память лимиты:    {total_resources['total_mem_limits_mib'] / 1024:.2f} GiB ({total_resources['total_mem_limits_mib']:.0f} MiB)")
   
        print("\n--- Анализ Service'ов без Endpoint'ов ---")
        with open('services.json', 'r', encoding='utf-16') as f:
            services_data = json.load(f)
            analyze_services_without_endpoints(services_data)

        print("\n--- Анализ PersistentVolumeClaims (PVC) ---")
        with open('pvcs.json', 'r', encoding='utf-16') as f:
            pvcs_data = json.load(f)
            analyze_pvcs(pvcs_data)

        print("\n--- Анализ PersistentVolumeClaims (PVC) с учетом подов ---")
        with open('pods.json', 'r', encoding='utf-16') as f:
            pods_data = json.load(f)
        with open('pvcs.json', 'r', encoding='utf-16') as f:
            pvcs_data = json.load(f)
            analyze_pvcs_with_pods(pvcs_data, pods_data)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
