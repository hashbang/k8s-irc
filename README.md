# UnrealIRCD in Kubernetes

This project contains a python tool that manages an UnrealIRCD server's `link` configuration.
Whenever a new IRCD pod is started, all running IRCD pods will get their link configuration re-rendered and a `REHASH` command sent.


# TODO

  - set up CI testing for python program
  - rehash on config change as separate operation?


# Generate and apply a config with kustomize

```
kubectl kustomize base | kubectl apply -f -
```


# Development

## Build and tag the unrealircd docker image:

```
docker build -t hashbang/unrealircd:4.2.3-with-proxy - < Dockerfile.unrealircd
```


## Build and tag the rehasher docker image:

```
docker build -t hashbang/unrealircd-config-renderer:latest -f Dockerfile.rehasher .
```
