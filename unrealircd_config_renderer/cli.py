import argparse
import hashlib
import os
import random
import string
import sys
import socket
import ssl

from kubernetes import client, config, watch
from jinja2 import Environment, PackageLoader

from . import __version__


NS_FILENAME = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"


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

main_template = template_environment.get_template("main.conf.j2")
links_template = template_environment.get_template("links.conf.j2")


def generate_main_config(
    k8s_namespace, pod_name, oper_password, rehasher_nick, rehasher_user, output_path
):
    current_server = k8s_namespace + "." + pod_name

    contents = main_template.render(
        current_server=current_server,
        server_id=str(generate_server_id(current_server)).zfill(3),
        config={
            "oper_password": oper_password,
            "oper_user_class": "clients",
            "rehasher_nick": rehasher_nick,
            "rehasher_user": rehasher_user,
            "server_info": "Hashbang IRC Network",
        },
    )
    with open(output_path, "w") as f:
        f.write(contents)


def generate_links_config(
    k8s_namespace, label_selector, pod_name, link_password, rehash_args, output_path
):
    # Touch file so that it is created and irc server can start...
    with open(output_path, "w") as f:
        pass

    v1 = client.CoreV1Api()

    server_links = {}
    old_config = ""
    w = watch.Watch()
    for event in w.stream(
        v1.list_namespaced_pod,
        namespace=k8s_namespace,
        label_selector=label_selector,
        # Don't want to include ourselves
        field_selector=f"metadata.name!={pod_name}",
    ):
        # check event.status.phase
        obj = event["object"]
        if obj.status.phase == "Running":
            server_links[obj.metadata.uid] = {
                "name": obj.metadata.namespace + "." + obj.metadata.name,
                "address": obj.status.pod_ip,
                "port": 6900,
                "password": link_password,
                "verify_certificate": False,
            }
        elif obj.metadata.uid in server_links:
            del server_links[obj.metadata.uid]

        new_config = links_template.render(server_links=server_links)
        if new_config == old_config:
            continue

        print("Different links, rerendering")

        with open(output_path, "w") as f:
            f.write(new_config)

        if rehash_args:
            send_rehash(**rehash_args)

        old_config = new_config


ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False


def send_rehash(
    oper_credentials,
    server_address=("127.0.0.1", 6697),
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "--k8s-config", type=str, default="incluster", choices=["incluster", "remote"]
    )
    parser.add_argument(
        "--k8s-namespace",
        type=str,
        help="The kubernetes namespace containing the irc servers",
    )
    parser.add_argument(
        "--pod-name",
        type=str,
        help="The kubernetes pod name for the current pod (can also be specified using the POD_NAME environment variable)",
    )
    parser.add_argument(
        "--rehasher-oper-password",
        type=str,
        help="The oper password for the rehasher connection. (can also be specified using the REHASHER_OPER_PASSWORD environment variable) default is to generate one",
    )
    parser.add_argument(
        "--rehasher-oper-password-file",
        type=argparse.FileType("w+", encoding="UTF=8"),
        help="Read/Write the rehasher oper password from/to this path",
    )
    subparsers = parser.add_subparsers(
        title="subcommands", dest="subcommand", required=True
    )

    main_conf = subparsers.add_parser("main")
    main_conf.add_argument(
        "--output-path",
        type=str,
        help="Location to write resulting configuration to (can also be specified using the CONFIG_PATH environment variable) defaults to 'main.conf'",
    )

    links_conf = subparsers.add_parser("links")
    links_conf.add_argument(
        "--output-path",
        type=str,
        help="Location to write resulting configuration to (can also be specified using the CONFIG_PATH environment variable) defaults to 'links.conf'",
    )
    links_conf.add_argument(
        "--label-selector",
        type=str,
        help="The kubernetes label selector for finding members of the IRC cluster (defaults to the 'app' specified in the APP_NAME environment variable)",
    )
    links_conf.add_argument(
        "--link-password",
        type=str,
        help="The password for linking servers (can also be specified using the LINK_PASSWORD environment variable)",
    )
    links_conf.add_argument(
        "--send-rehash",
        action="store_true",
        help="Should the tool connect to the IRC server and send REHASH?",
    )

    args = parser.parse_args(argv)

    if args.k8s_config == "incluster":
        config.load_incluster_config()
    else:
        config.load_kube_config()

    k8s_namespace = args.k8s_namespace
    if k8s_namespace is None:
        if args.k8s_config == "incluster":
            with open(NS_FILENAME) as f:
                k8s_namespace = f.read()
        else:
            raise Exception(
                "when operating on remote cluster, --k8s-namespace is required"
            )

    pod_name = args.pod_name
    if pod_name is None:
        pod_name = os.environ["POD_NAME"]

    rehasher_oper_password = args.rehasher_oper_password
    rehasher_oper_password_file = args.rehasher_oper_password_file
    if rehasher_oper_password is None:
        rehasher_oper_password = os.environ.get("REHASHER_OPER_PASSWORD")
    if rehasher_oper_password is None and rehasher_oper_password_file is not None:
        rehasher_oper_password = rehasher_oper_password_file.read()
        if rehasher_oper_password is "":
            rehasher_oper_password = None
        else:
            rehasher_oper_password_file.seek(0)
    if rehasher_oper_password is None:
        rehasher_oper_password = generate_oper_credentials()
    if rehasher_oper_password_file is not None:
        rehasher_oper_password_file.write(rehasher_oper_password)
        rehasher_oper_password_file.flush()
        rehasher_oper_password_file.truncate()
        rehasher_oper_password_file.close()

    rehasher_nick = "rehasher"
    rehasher_user = "rehasher"

    output_path = args.output_path
    if args.subcommand == "main":
        if output_path is None:
            output_path = os.environ.get("CONFIG_PATH", "main.conf")

        generate_main_config(
            k8s_namespace=k8s_namespace,
            pod_name=pod_name,
            output_path=output_path,
            oper_password=rehasher_oper_password,
            rehasher_nick=rehasher_nick,
            rehasher_user=rehasher_user,
        )
    else:
        if output_path is None:
            output_path = os.environ.get("CONFIG_PATH", "links.conf")

        label_selector = args.label_selector
        if label_selector is None:
            app_name = os.environ["APP_NAME"]
            label_selector = f"app=={app_name}"

        link_password = args.link_password
        if link_password is None:
            link_password = os.environ["LINK_PASSWORD"]

        if args.send_rehash:
            rehash_args = {
                "oper_credentials": rehasher_oper_password,
                "nick": rehasher_nick,
                "user": rehasher_user,
                "sni": None,
            }
        else:
            rehash_args = None

        generate_links_config(
            k8s_namespace=k8s_namespace,
            pod_name=pod_name,
            output_path=output_path,
            label_selector=label_selector,
            link_password=link_password,
            rehash_args=rehash_args,
        )
