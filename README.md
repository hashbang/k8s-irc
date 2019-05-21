# TODO:

  - add serviceAccount so that rehasher can read pods
  - rename dockerhub image
  - set up CI testing for python program
  - add argparse/cli for python program
  - add link.key secret mounting/rendering
  - rehash on config change as separate operation?


# Generate and apply a config with kustomize

```
kubectl kustomize base | kubectl apply -f -
```


# Development

## Build the rehasher docker image:

```
docker build . -f Dockerfile.rehasher -t rehasher:latest
```
