# Time logger

## Create env file

```
make env_new
```

And fill variables

## Build image

```
make docker_image
```

## Run selenium

```
docker compose up -d selenium
```

## Go selenium view

http://localhost:7900/?autoconnect=1&resize=scale&password=secret

## Examples

```
docker compose run --rm logger --format csv --src "data/some_file.csv"
docker compose run --rm logger --format csv --src "data/some_file.csv" --show_only
docker compose run --rm logger --format py --src "data.sanecum.log_days" --show_only
```
