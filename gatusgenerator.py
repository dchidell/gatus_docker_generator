import docker
import yaml
import time
import os
import re
import logging

log = logging.getLogger(__name__)

class GatusGenerator:
    DEFAULT_CONDITIONS = {
        "icmp": [
            "[CONNECTED] == true"
        ],
        "tcp": [
            "[CONNECTED] == true"
        ],
        "http": [
             "[STATUS] == 200",
             "[RESPONSE_TIME] < 300"
        ],
        "https": [
             "[STATUS] == 200",
             "[RESPONSE_TIME] < 300"
        ]
    }

    container_config = [{'name':'placeholder'}]

    def __init__(self):
        self.setup_env()
        self.dkr = docker.from_env()
        self.read_config()

    def setup_env(self):
        self.base_config = os.environ.get("BASE_CONFIG", "gatus_config.yml")
        self.generated_config = os.environ.get("GENERATED_CONFIG", "gatus_config_generated.yml")
        self.gatus_label = os.environ.get("GATUS_LABEL")

    def read_config(self):
        gatus_config = {}
        try:
            f = open(self.base_config)
            gatus_config = yaml.load(f, Loader=yaml.FullLoader)
            f.close()
        except (IOError, TypeError) as e:
            log.error(f'Unable to open base config file. Ensure BASE_CONFIG env var is set and correct. Value: {self.base_config}')
            exit(1)
        return gatus_config

    def restart_gatus(self):
        gatus_list = self.dkr.containers.list(filters={"label":self.gatus_label})
        if len(gatus_list) != 1:
            return log.error(f'Found {len(gatus_list)} containers with label: {self.gatus_label}. Expected 1. Unable to update.')
        gatus = gatus_list[0]
        gatus.restart()
        return log.info('Restarted!')
           
            
    def get_gatus_defaults(self, container):
        gatus_info = {}
        gatus_info['conditions'] = []
        gatus_info['url'] = ''
        gatus_info['alerts'] = [{
            "type":"discord",
            "enabled": True,
            "send-on-resolved": True,
            "failure-threshold": 5,
            "success-threshold": 5,
        }]

        preset = container.labels.get('gatus.preset',None)
        if preset == "traefikweb":
            name = container.labels.get('com.docker.compose.service',None)
            
            try:
                host = [value for key, value in container.labels.items() if key.endswith('.rule')][0]
                regmatch = re.search("`([a-zA-Z0-9\.]+)`",host)
                if regmatch is not None:
                    gatus_info['url'] = f"https://{regmatch.group(1)}"     
            except IndexError:
                pass
            gatus_info['conditions'].append("[STATUS] == 200")
        elif preset == "traefiklocal":
            name = container.labels.get('com.docker.compose.service',None)
            try:
                port = [value for key, value in container.labels.items() if key.endswith('.port')][0]
                gatus_info['url'] = f"http://{container.name}:{port}"     
            except IndexError:
                pass
            gatus_info['conditions'].append("[STATUS] == 200")

        name = container.labels.get('com.docker.compose.service',None)
        if name is None:
            name = container.name
        gatus_info['name'] = name

        group = container.labels.get('com.docker.compose.project',None)
        if group is not None:
            gatus_info['group'] = group

        network_name = next(iter(container.attrs['NetworkSettings']['Networks']))
        if network_name not in ('none','host') and not gatus_info['url']:
            try:
                alias = container.attrs['NetworkSettings']['Networks'][network_name]['Aliases']
                ip = container.attrs['NetworkSettings']['Networks'][network_name]['IPAddress']
                if alias is None:
                    gatus_info['url'] = f"icmp://{ip}"
                else:
                    gatus_info['url'] = f"icmp://{alias[0]}"
            except IndexError:
                pass

        return gatus_info

    def write_docker_services(self,container_services):
        gatus_config = self.read_config()
        if type(gatus_config['endpoints']) == list:
            gatus_config['endpoints'] += container_services
        else:
            gatus_config['endpoints'] = container_services

        try:
            f = open(self.generated_config, "w")
            yaml.dump(gatus_config, f)
            f.close()
        except (IOError, TypeError):
            log.error(f'Unable to write to generated config file. Ensure GENERATED_CONFIG env var is set and correct. Value: {self.generated_config}')
            exit(1)

    def enter_update_loop(self):
        log.info("Listening for new containers...")
        while True:
            new_container_config = []
            containers = self.dkr.containers.list(all=True, filters={"label":"gatus.enabled=true"})
            for container in containers:
                if container.labels.get("gatus.enabled", "False").upper() == "TRUE":
                    gatus_service = self.process_container(container)
                    if gatus_service is not None:
                        new_container_config.append(gatus_service)
            if sorted(new_container_config, key=lambda x: x['name']) != sorted(self.container_config, key=lambda x: x['name'],):
                log.info('Detected container config change! Rewriting file...')
                self.write_docker_services(new_container_config)
                self.container_config = new_container_config
                log.info('Restarting gatus...')
                self.restart_gatus()
            
            time.sleep(60)                    

    def process_container(self, container):
        gatus_info = self.get_gatus_defaults(container)
        if gatus_info is None:
            return None
        for label, value in container.labels.items():
            if "gatus" not in label:
                continue
            label_split = label.split(".")

            if len(label_split) < 2:
                continue

            if label_split[1].lower() in ("enabled"):
                continue

            if label_split[1].lower() == "conditions":
                gatus_info['conditions'].append(str(value))
                continue

            gatus_info[label_split[1].lower()] = value


        if not gatus_info.get('conditions'):
            method = gatus_info.get('url','icmp://').split(':')[0].lower()
            gatus_info['conditions'] += self.DEFAULT_CONDITIONS[method]

        return gatus_info


# gatus.enable = true / false (default false)
# gatus.url (default container name)
# gatus.method (default GET)
# gatus.interval (default 60s)
# gatus.group (default name split 1st elem)
# gatus.name  (default name split 2nd elem)
# gatus.insecure (default false)
