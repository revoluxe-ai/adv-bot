import json
import sys
from typing import Dict, Any, Set, List

def analyze_ingresses(ingresses_data: Dict[str, Any], services_data: Dict[str, Any]) -> None:
    """Analyzes Ingresses to find those pointing to non-existent Services."""
    existing_services: Set[str] = set()

    for item in services_data.get('items', []):
        service_name = item['metadata']['name']
        namespace = item['metadata']['namespace']
        existing_services.add(f"{namespace}/{service_name}")

    ingresses_with_missing_services: List[Dict[str, Any]] = []

    for item in ingresses_data.get('items', []):
        ingress_name = item['metadata']['name']
        namespace = item['metadata']['namespace']
        rules = item['spec'].get('rules', [])
        
        for rule in rules:
            if 'http' in rule and 'paths' in rule['http']:
                for path in rule['http']['paths']:
                    if 'backend' in path and 'service' in path['backend']:
                        service_ref_name = path['backend']['service']['name']
                        full_service_name = f"{namespace}/{service_ref_name}"

                        if full_service_name not in existing_services:
                            ingresses_with_missing_services.append({
                                'ingress_name': ingress_name,
                                'namespace': namespace,
                                'missing_service': service_ref_name
                            })
        
        if 'defaultBackend' in item['spec'] and 'service' in item['spec']['defaultBackend']:
            service_ref_name = item['spec']['defaultBackend']['service']['name']
            full_service_name = f"{namespace}/{service_ref_name}"
            if full_service_name not in existing_services:
                ingresses_with_missing_services.append({
                    'ingress_name': ingress_name,
                    'namespace': namespace,
                    'missing_service': service_ref_name
                })


    if ingresses_with_missing_services:
        print("Найдены Ingress'ы, указывающие на несуществующие Service'ы:")
        for ingress in ingresses_with_missing_services:
            print(f"  Ingress: {ingress['ingress_name']}, Namespace: {ingress['namespace']}, Ссылается на несуществующий Service: {ingress['missing_service']}")
    else:
        print("Не найдено Ingress'ов, указывающих на несуществующие Service'ы.")

if __name__ == '__main__':
    try:
        with open('ingresses.json', 'r', encoding='utf-16') as f:
            ingresses_data = json.load(f)
        with open('services.json', 'r', encoding='utf-16') as f:
            services_data = json.load(f)
        
        analyze_ingresses(ingresses_data, services_data)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
