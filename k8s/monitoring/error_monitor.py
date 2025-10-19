#!/usr/bin/env python3
"""
🚨 Advanced Pod Error Monitoring Tool

Система быстрого мониторинга ошибок в Kubernetes:
- Анализ ошибок в подах
- Мониторинг рестартов
- Анализ логов
- Интеграция с Prometheus
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import re

# Цвета для терминала
class Color:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'


class Severity(Enum):
    """Уровень серьезности ошибки"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"


@dataclass
class PodError:
    """Ошибка в поде"""
    namespace: str
    pod_name: str
    container: str
    error_type: str
    severity: Severity
    message: str
    timestamp: str
    restarts: int = 0
    last_exit_code: Optional[int] = None


class KubernetesMonitor:
    """Мониторинг Kubernetes подов"""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.errors: List[PodError] = []
    
    def run_kubectl(self, cmd: List[str]) -> Dict[Any, Any]:
        """Выполнить kubectl команду и получить JSON"""
        try:
            result = subprocess.run(
                ["kubectl"] + cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"{Color.RED}✗ Ошибка kubectl: {e.stderr}{Color.NC}")
            return {}
        except json.JSONDecodeError:
            return {}
    
    def get_pods(self) -> Dict[Any, Any]:
        """Получить все поды в namespace"""
        return self.run_kubectl([
            "get", "pods", "-n", self.namespace, "-o", "json"
        ])
    
    def get_events(self) -> Dict[Any, Any]:
        """Получить события namespace"""
        return self.run_kubectl([
            "get", "events", "-n", self.namespace, "-o", "json",
            "--sort-by=.lastTimestamp"
        ])
    
    def analyze_pod(self, pod_data: Dict[Any, Any]) -> None:
        """Анализировать один pod"""
        pod_name = pod_data.get("metadata", {}).get("name", "unknown")
        namespace = pod_data.get("metadata", {}).get("namespace", self.namespace)
        phase = pod_data.get("status", {}).get("phase", "Unknown")
        
        # Анализ контейнеров
        containers = pod_data.get("status", {}).get("containerStatuses", [])
        for container_status in containers:
            container_name = container_status.get("name", "unknown")
            restart_count = container_status.get("restartCount", 0)
            
            # Проверка состояния
            if container_status.get("ready", False) is False:
                self._check_waiting_state(
                    pod_name, namespace, container_name,
                    container_status, restart_count
                )
            
            if phase == "Failed" or container_status.get("state", {}).get("terminated"):
                self._check_terminated_state(
                    pod_name, namespace, container_name,
                    container_status, restart_count
                )
            
            # Проверка на частые рестарты
            if restart_count > 3:
                self.errors.append(PodError(
                    namespace=namespace,
                    pod_name=pod_name,
                    container=container_name,
                    error_type="FREQUENT_RESTARTS",
                    severity=Severity.WARNING,
                    message=f"Pod перезагружен {restart_count} раз",
                    timestamp=datetime.now().isoformat(),
                    restarts=restart_count
                ))
    
    def _check_waiting_state(
        self, pod_name: str, namespace: str, container_name: str,
        status: Dict[Any, Any], restart_count: int
    ) -> None:
        """Проверить состояние ожидания контейнера"""
        waiting = status.get("state", {}).get("waiting", {})
        reason = waiting.get("reason", "Unknown")
        message = waiting.get("message", "")
        
        severity_map = {
            "ImagePullBackOff": Severity.CRITICAL,
            "ErrImagePull": Severity.CRITICAL,
            "ImageInspectError": Severity.CRITICAL,
            "ErrImageNeverPull": Severity.CRITICAL,
            "RegistryUnavailable": Severity.WARNING,
            "ContainerCreating": Severity.INFO,
            "CrashLoopBackOff": Severity.CRITICAL,
        }
        
        if reason:
            severity = severity_map.get(reason, Severity.WARNING)
            self.errors.append(PodError(
                namespace=namespace,
                pod_name=pod_name,
                container=container_name,
                error_type=reason,
                severity=severity,
                message=message or f"Container в состоянии {reason}",
                timestamp=datetime.now().isoformat(),
                restarts=restart_count
            ))
    
    def _check_terminated_state(
        self, pod_name: str, namespace: str, container_name: str,
        status: Dict[Any, Any], restart_count: int
    ) -> None:
        """Проверить состояние завершения контейнера"""
        terminated = status.get("state", {}).get("terminated", {})
        reason = terminated.get("reason", "Unknown")
        exit_code = terminated.get("exitCode", 0)
        message = terminated.get("message", "")
        
        severity_map = {
            "OOMKilled": Severity.CRITICAL,
            "Completed": Severity.INFO,
            "Error": Severity.CRITICAL,
            "ContainerCannotRun": Severity.CRITICAL,
            "DeadlineExceeded": Severity.WARNING,
        }
        
        severity = severity_map.get(reason, Severity.WARNING)
        
        # OOMKilled всегда критичный
        if reason == "OOMKilled":
            severity = Severity.CRITICAL
        elif exit_code != 0 and reason != "Completed":
            severity = Severity.CRITICAL
        
        self.errors.append(PodError(
            namespace=namespace,
            pod_name=pod_name,
            container=container_name,
            error_type=reason,
            severity=severity,
            message=message or f"Container завершился с кодом {exit_code}",
            timestamp=datetime.now().isoformat(),
            restarts=restart_count,
            last_exit_code=exit_code
        ))
    
    def get_pod_logs(self, pod_name: str, tail: int = 50) -> str:
        """Получить логи пода"""
        try:
            result = subprocess.run([
                "kubectl", "logs", "-n", self.namespace, pod_name,
                "--tail", str(tail), "--timestamps=true"
            ], capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return f"Ошибка получения логов: {e}"
    
    def analyze(self) -> None:
        """Провести полный анализ"""
        pods = self.get_pods()
        
        for pod in pods.get("items", []):
            self.analyze_pod(pod)
    
    def print_summary(self) -> None:
        """Вывести сводку"""
        print(f"\n{Color.CYAN}════════════════════════════════════════{Color.NC}")
        print(f"{Color.WHITE}🚨 ERROR MONITORING SUMMARY{Color.NC}")
        print(f"{Color.CYAN}════════════════════════════════════════{Color.NC}")
        print(f"Namespace: {Color.BOLD}{self.namespace}{Color.NC}")
        print(f"Всего ошибок: {len(self.errors)}")
        print()
        
        # Группировка по серьезности
        by_severity = defaultdict(list)
        for error in self.errors:
            by_severity[error.severity].append(error)
        
        # CRITICAL
        if by_severity[Severity.CRITICAL]:
            print(f"{Color.RED}🔴 CRITICAL ({len(by_severity[Severity.CRITICAL])}){Color.NC}")
            for error in by_severity[Severity.CRITICAL]:
                self._print_error(error)
        
        # WARNING
        if by_severity[Severity.WARNING]:
            print(f"\n{Color.YELLOW}🟡 WARNING ({len(by_severity[Severity.WARNING])}){Color.NC}")
            for error in by_severity[Severity.WARNING]:
                self._print_error(error)
        
        # INFO
        if by_severity[Severity.INFO]:
            print(f"\n{Color.BLUE}ℹ️ INFO ({len(by_severity[Severity.INFO])}){Color.NC}")
            for error in by_severity[Severity.INFO]:
                self._print_error(error)
    
    def _print_error(self, error: PodError) -> None:
        """Вывести одну ошибку"""
        color = {
            Severity.CRITICAL: Color.RED,
            Severity.WARNING: Color.YELLOW,
            Severity.INFO: Color.BLUE,
            Severity.OK: Color.GREEN
        }[error.severity]
        
        print(f"{color}  • {error.pod_name}/{error.container}{Color.NC}")
        print(f"    Type: {error.error_type}")
        print(f"    Message: {error.message}")
        if error.restarts > 0:
            print(f"    Restarts: {error.restarts}")
        if error.last_exit_code is not None:
            print(f"    Exit Code: {error.last_exit_code}")
        print()
    
    def export_json(self, filename: str) -> None:
        """Экспортировать ошибки в JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "namespace": self.namespace,
            "errors": [asdict(e) for e in self.errors],
            "summary": {
                "total": len(self.errors),
                "critical": sum(1 for e in self.errors if e.severity == Severity.CRITICAL),
                "warning": sum(1 for e in self.errors if e.severity == Severity.WARNING),
                "info": sum(1 for e in self.errors if e.severity == Severity.INFO),
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✓ Ошибки экспортированы в {filename}")
    
    def get_critical_pods(self) -> List[str]:
        """Получить список критичных подов"""
        return list(set(
            e.pod_name for e in self.errors
            if e.severity == Severity.CRITICAL
        ))


def main():
    parser = argparse.ArgumentParser(
        description="🚨 Advanced Pod Error Monitoring Tool"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="default",
        help="Kubernetes namespace (default: default)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Export to JSON file"
    )
    parser.add_argument(
        "-l", "--logs",
        action="store_true",
        help="Show logs for critical pods"
    )
    
    args = parser.parse_args()
    
    monitor = KubernetesMonitor(namespace=args.namespace)
    monitor.analyze()
    monitor.print_summary()
    
    if args.output:
        monitor.export_json(args.output)
    
    if args.logs:
        critical_pods = monitor.get_critical_pods()
        if critical_pods:
            print(f"\n{Color.CYAN}════════════════════════════════════════{Color.NC}")
            print(f"{Color.WHITE}📋 LOGS FOR CRITICAL PODS{Color.NC}")
            print(f"{Color.CYAN}════════════════════════════════════════{Color.NC}")
            for pod in critical_pods[:5]:  # Макс 5 подов
                print(f"\n{Color.BOLD}Pod: {pod}{Color.NC}")
                logs = monitor.get_pod_logs(pod)
                print(logs[-500:])  # Последние 500 символов


if __name__ == "__main__":
    main()


