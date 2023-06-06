# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2023-06-02 10:52:35
# @Last Modified by:   Your name
# @Last Modified time: 2023-06-06 14:07:57
from flask import Flask, send_file, request, Response
from prometheus_client import start_http_server, Counter, generate_latest, Gauge
import docker
import logging
import os.path

logger = logging.getLogger(__name__)

app = Flask(__name__)

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
MBFACTOR = float(1 << 20)

docker_container_cpu_capacity_total = Gauge(
    'docker_container_cpu_capacity_total',
    'The CPU utilization currently in use by Docker service.',
    ['name']
)

docker_container_cpu_used_total = Gauge(
    'docker_container_cpu_used_total',
    'The CPU utilization currently in use by this container.',
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

docker_container_running_state = Gauge(
    'docker_container_running_state',
    'State of the container (running:1, any_other:0).',
    ['name']
)

client = docker.from_env(version='1.23')


@app.route('/metrics', methods=['GET'])
def get_data():
    """Returns all data as plaintext."""
    containers = client.containers.list()
    for container in containers:
        name = container.name

        # Get pids data to evaluate container state
        try:
            if os.path.exists('/sys/fs/cgroup/pids/docker/{}/pids.current'.format(container.id)):
                state = 1
                docker_container_running_state.labels(name).set(state)
            else:
                state = 0
                docker_container_running_state.labels(name).set(state)
        except Exception as e:
            logger.error("Failed to update state metric. Exception: {}".format(e))

        # Get CPU data for this container
        try:
            with open('/docker/cpu/cpuacct.usage', 'r') as cpuCapacityFile:
                cpu = cpuCapacityFile.read()
                docker_container_cpu_capacity_total.labels(name).set(cpu)
        except Exception as e:
            logger.error("Failed to update cpu metric. Exception: {}".format(e))

        # Get CPU data for this container
        try:
            with open('/docker/cpu/{}/cpuacct.usage'.format(container.id), 'r') as cpuFile:
                cpu = cpuFile.read()
                docker_container_cpu_used_total.labels(name).set(cpu)
        except Exception as e:
            logger.error("Failed to update cpu metric. Exception: {}".format(e))

        # Get memory data for this container
        try:
            with open('/docker/memory/{}/memory.usage_in_bytes'.format(container.id), 'r') as memFile:
                memory = memFile.read()
                memory = int(memory) / MBFACTOR
                docker_container_memory_used_bytes.labels(name).set(memory)
        except Exception as e:
            logger.error("Failed to update memory metric. Exception: {}".format(e))

        # Get disk I/O data for this container
        try:
            with open('/docker/blkio/{}/blkio.throttle.io_service_bytes'.format(container.id), 'r') as ioFile:
                # io_disk = ioFile.read()
                ioDiskRead = ioFile.readlines()[-7].split()
                # ioDiskRead = ioFile.readlines()[-1].split()
                logger.warning("READ {}".format(ioDiskRead))
                docker_container_disk_read_bytes.labels(name).set(ioDiskRead[2])
        except Exception as e:
            logger.error("Failed to update disk I/O metric. Exception: {}".format(e))

        # Get disk I/O write data for this container
        try:
            with open('/docker/blkio/{}/blkio.throttle.io_service_bytes'.format(container.id), 'r') as ioFile:
                ioDiskWrite = ioFile.readlines()[-6].split()
                logger.warning("WRITE {}".format(ioDiskWrite))
                docker_container_disk_write_bytes.labels(name).set(ioDiskWrite[2])
        except Exception as e:
            logger.error("Failed to update disk I/O metric. Exception: {}".format(e))

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9417)
