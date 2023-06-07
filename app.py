from multiprocessing import Process
import shutil
import time, os
import docker
import logging

from prometheus_client import start_http_server, multiprocess, CollectorRegistry, Gauge

logger = logging.getLogger(__name__)

docker_container_running_state = Gauge(
    'docker_container_running_state',
    'Whether the container is running, or exited.',
    ['name']
)

docker_container_cpu_used_total = Gauge(
    'docker_container_cpu_used_total',
    'The CPU utilization currently in use by this container.',
    ['name']
)

docker_container_cpu_capacity_total = Gauge(
    'docker_container_cpu_capacity_total',
    'The CPU utilization currently in use by Docker service.',
    ['name']
)

docker_container_memory_used_bytes = Gauge(
    'docker_container_memory_used_bytes',
    'Amount of Memory in megabytes currently in use by this container.',
    ['name']
)

docker_container_disk_read_bytes = Gauge(
    'docker_container_disk_read_bytes',
    'Amount of I/O read operations performed by this container.',
    ['name']
)

docker_container_disk_write_bytes = Gauge(
    'docker_container_disk_write_bytes',
    'Amount of I/O write operations performed by this container.',
    ['name']
)

docker_container_network_in_bytes = Gauge(
    'docker_container_network_in_bytes',
    'Total bytes received by the container\'s network interfaces.',
    ['name']
)

docker_container_network_out_bytes = Gauge(
    'docker_container_network_out_bytes',
    'Total bytes transmitted by the container\'s network interfaces.',
    ['name']
)

# ensure variable exists, and ensure defined folder is clean on start
prome_stats = os.environ["PROMETHEUS_MULTIPROC_DIR"]
if os.path.exists(prome_stats):
    shutil.rmtree(prome_stats)
os.mkdir(prome_stats)

client = docker.from_env()

# client = docker.DockerClient(base_url='unix://var/run/docker.sock')

def f(container):
    containerStats = {}
    container_disk_read_bytes = 0
    container_disk_write_bytes = 0
    container_network_rx = 0
    container_network_x = 0
    containerStats = container.stats(stream=False)
    name = container.name
    memoryUsage = containerStats['memory_stats']['usage']
    container_cpu_total = containerStats['cpu_stats']['cpu_usage']['total_usage']
    container_cpu_kernel = containerStats['cpu_stats']['cpu_usage']['usage_in_kernelmode']
    container_cpu_user = containerStats['cpu_stats']['cpu_usage']['usage_in_usermode']

    if len(containerStats['blkio_stats']['io_service_bytes_recursive']) == 0:
        container_disk_read_bytes = 0
        container_disk_write_bytes = 0
    else:
        for volume in containerStats['blkio_stats']['io_service_bytes_recursive']:
            if volume['op'] == "read":
                container_disk_read_bytes = container_disk_read_bytes + volume['value']
            elif volume['op'] == "write":
                container_disk_write_bytes = container_disk_write_bytes + volume['value']
            else:
                container_disk_read_bytes = 0
                container_disk_write_bytes = 0
    if 'networks' in containerStats:
        container_network_rx = containerStats['networks']['eth0']['rx_bytes']
        container_network_tx = containerStats['networks']['eth0']['tx_bytes']

    # logger.warning("name: {}\n \
    #                 \t container_disk_read_bytes:{}\n \
    #                 \t container_disk_write_bytes: {}\n \
    #                 \t container_network_rx: {}\n \
    #                 \t container_network_tx: {}\n \
    #                 \t memoryUsage: {}\n \
    #                 \t memlimit: {}".format(name,container_disk_read_bytes,container_disk_write_bytes,container_network_rx,container_network_tx,memoryUsage, memory_limit))


    # Get container running status
    # try:
    #     if container.status == 'running':
    #         docker_container_running_state.labels(name).set(1)
    #     else:
    #         docker_container_running_state.labels(name).set(0)
    # except Exception as e:
    #     logger.error("Failed to update the container status. Exception: {}".format(e))

    # # Get CPU data for this container
    # try:
    #     docker_container_cpu_used_total.labels(name).set(container_cpu_total)
    # except Exception as e:
    #     logger.error("Failed to update cpu metric from docker SDK. Exception: {}".format(e))

    # # Get CPU data for docker service
    # try:
    #     with open('/docker/cpu/cpuacct.usage', 'r') as cpuCapacityFile:
    #         cpu = cpuCapacityFile.read()
    #         docker_container_cpu_capacity_total.labels(name).set(cpu)
    # except Exception as e:
    #     logger.error("Failed to update host total cpu from cgroup. Exception: {}".format(e))
        
    # # Get memory data for this container
    # try:    
    #     docker_container_memory_used_bytes.labels(name).set(memoryUsage)
    # except Exception as e:
    #     logger.error("Failed to update memory metric from docker SDK. Exception: {}".format(e))

    # # Get disk I/O data for this container
    # try:
    #     docker_container_disk_read_bytes.labels(name).set(container_disk_read_bytes)
    # except Exception as e:
    #     logger.error("Failed to update disk read I/O metric from docker SDK. Exception: {}".format(e))

    # # Get disk I/O write data for this container
    # try:
    #     docker_container_disk_write_bytes.labels(name).set(container_disk_write_bytes)
    # except Exception as e:
    #     logger.error("Failed to update disk write I/O metric from docker SDK. Exception: {}".format(e))

    # # Get disk I/O data for this container
    # try:
    #     docker_container_network_in_bytes.labels(name).set(container_network_rx)
    # except Exception as e:
    #     logger.error("Failed to update network in metric from docker SDK. Exception: {}".format(e))

    # # Get disk I/O data for this container
    # try:
    #     docker_container_network_out_bytes.labels(name).set(container_network_tx)
    # except Exception as e:
    #     logger.error("Failed to update network out metric from docker SDK. Exception: {}".format(e))

if __name__ == '__main__':

    # pass the registry to server
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    start_http_server(9417, registry=registry)

    containers = client.containers.list()
    for container in containers:
        logger.warning("name: {}".format(container.name))
        p = Process(target=f, args=(container,))
        a = p.start()
    while True:
        time.sleep(1)
