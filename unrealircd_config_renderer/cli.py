import hashlib
import os
import random
import string
import sys
import socket
import ssl

from kubernetes import client, config, watch
from jinja2 import Environment, PackageLoader


NS_FILENAME = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"


def get_namespace():
    if os.environ.get("POD_NAMESPACE", None):
        return os.environ["POD_NAMESPACE"]
    else:
        with open(NS_FILENAME) as f:
            return f.read()


def get_app_name():
    return os.environ["APP_NAME"]


def get_config_path():
    return os.environ["CONFIG_PATH"]


def get_pod_name():
    return os.environ["POD_NAME"]


def generate_server_id(server_uid):
    # needs to be 3 decimal characters, per UnrealIRCd docs
    return (
        int.from_bytes(
            hashlib.sha1(server_uid.encode("ascii")).digest()[:2], sys.byteorder
        )
        % 1000
    )


def generate_oper_credentials(password_length=24):
    password = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(password_length)
    )
    return password


template_environment = Environment(
    loader=PackageLoader("unrealircd_config_renderer", "templates")
)

template = template_environment.get_template("links.conf.j2")


def render_links_template(current_server, server_id, config):
    return template.render(
        current_server=current_server, server_id=str(server_id).zfill(3), config=config
    )


def write_config(path, new_config):
    with open(path, "w") as f:
        f.write(new_config)


ssl_context = ssl.create_default_context()


def send_rehash(
    oper_credentials,
    server_address="127.0.0.1:6697",
    nick="rehasher",
    user="rehasher",
    sni=None,
):
    payload = f"""
    NICK {nick}
    USER {user} * * :Rehashes the IRCd!
    OPER rehash {oper_credentials}
    REHASH
    """

    with socket.create_connection(server_address) as conn:
        with ssl_context.wrap_socket(conn, server_hostname=sni) as conn_tls:
            conn_tls.send(payload.encode("ascii"))


def main():
    config.load_incluster_config()
    # config.load_kube_config()
    v1 = client.CoreV1Api()
    w = watch.Watch()

    server_config = {
        "oper_password": generate_oper_credentials(),
        "oper_user_class": "clients",
        "other_servers": dict(),
        "rehasher_nick": "rehasher",
        "rehasher_user": "rehasher",
        "server_info": "Hashbang IRC Network",
    }
    current_server = get_namespace() + "." + get_pod_name()
    old_config = None
    for event in w.stream(
        v1.list_namespaced_pod,
        namespace=get_namespace(),
        label_selector=f"app=={get_app_name()}",
        # Don't want to include ourselves
        field_selector=f"metadata.name!={get_pod_name()}",
    ):
        # check event.status.phase
        obj = event["object"]
        if obj.status.phase == "Running":
            server_config["other_servers"][obj.metadata.uid] = obj.status.pod_ip
        elif obj.metadata.uid in server_config["other_servers"]:
            del server_config["other_servers"][obj.metadata.uid]
        # get list of servers, get attached server
        new_config = render_links_template(
            current_server, generate_server_id(current_server), config=server_config
        )
        if new_config == old_config:
            continue
        write_config(get_config_path(), new_config)
        send_rehash(
            oper_credentials=server_config["oper_password"],
            nick=server_config["rehasher_nick"],
            user=server_config["rehasher_user"],
        )
        old_config = new_config
