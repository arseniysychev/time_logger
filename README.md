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
docker compose run --rm logger --platform kimai --format csv --src "data/some_file.csv"
docker compose run --rm logger --platform kimai --format csv --src "data/some_file.csv" --show_only
docker compose run --rm logger --platform kimai --format py --src "data.sanecum.log_days" --show_only
```

## CSV file example

| date       | start | end   | description |
|------------|-------|-------|-------------|
| 01.09.2025 | 9:00  | 14:00 | Part 1      |
| 01.09.2025 | 15:00 | 17:00 | Part 2      |
