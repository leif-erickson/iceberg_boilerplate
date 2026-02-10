import time
import requests
import docker
import os
import statistics

PROM_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
CPU_THRESHOLD = float(os.getenv('THRESHOLD_CPU', 80))
MEM_THRESHOLD = float(os.getenv('THRESHOLD_MEM', 70))
COMPOSE_FILE = '/app/docker-compose.yml'
SERVICE_NAME = 'farm-stack-boilerplate_backend'  # Adjust to your compose project name + service

client = docker.from_env()

def query_prom(query):
    response = requests.get(f'{PROM_URL}/api/v1/query', params={'query': query})
    return float(response.json()['data']['result'][0]['value'][1]) if response.ok else None

def baseline_metrics(duration=300):  # 5 min average
    cpu_samples = []
    mem_samples = []
    for _ in range(duration // 60):
        cpu = query_prom('rate(container_cpu_usage_seconds_total{container="backend"}[1m]) * 100')
        mem = query_prom('container_memory_usage_bytes{container="backend"} / container_memory_limit_bytes{container="backend"} * 100')
        if cpu and mem:
            cpu_samples.append(cpu)
            mem_samples.append(mem)
        time.sleep(60)
    return statistics.mean(cpu_samples), statistics.mean(mem_samples)

def check_and_act(base_cpu, base_mem):
    while True:
        curr_cpu = query_prom('rate(container_cpu_usage_seconds_total{container="backend"}[1m]) * 100')
        curr_mem = query_prom('container_memory_usage_bytes{container="backend"} / container_memory_limit_bytes{container="backend"} * 100')
        
        if curr_cpu > base_cpu + CPU_THRESHOLD or curr_mem > base_mem + MEM_THRESHOLD:
            print("Threshold exceeded, scaling up...")
            try:
                service = client.services.get(SERVICE_NAME)
                service.scale(service.scale + 1)  # Swarm scale
            except:
                print("Swarm not enabled, restarting instead...")
                os.system(f'docker compose -f {COMPOSE_FILE} restart backend')
        else:
            print("Metrics normal.")
        
        time.sleep(60)

if __name__ == '__main__':
    print("Baselining...")
    base_cpu, base_mem = baseline_metrics()
    print(f"Baselines: CPU {base_cpu}%, Mem {base_mem}%")
    check_and_act(base_cpu, base_mem)