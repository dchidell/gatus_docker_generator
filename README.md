# gatus_docker_generator

Generates gatus (https://gatus.io/) configuration dynamically from running docker docker containers by adding labels.

Example:

simple web check:
```
  labels:
   - "gatus.enabled=true"
   - "gatus.url=https://example.com"
   - "gatus.conditions.1=[STATUS]  == 200"
   - "gatus.conditions.2=[BODY]  == pat(*This domain is for use in illustrative examples*)"
```

mysql dabatase tcp check:
```
    labels:
     - "gatus.enabled=true"
     - "gatus.url=tcp://polemarchdb:3306"
```

You'll need to pass the docker socket through to this container so it can read the docker labels.

Requires use of some ENV vars:
BASE_CONFIG - Sets the template for gatus config generation (included in this repo is an example, gatus_config.yml)
GENERATED_CONFIG - This is the config gatus will actually look for and use, this should be shared with gatus itself.
GATUS_LABEL - Set this to some unique value, and add this to the gatus container, that's how this service knows which container to restart to apply the changes.

You must use "gatus.enabled=true" for this tool to process containers, this is the minimum you need for the tool to work. With only this defined, it'll create an ICMP check to the container in question.

There is a special label "gatus.preset" which can be one of "traefikweb" or "traefiklocal". These labels allow automatic definition of gatus config based on existing labels defined for traefik.


 "traefikweb" looks at the URL defined in traefik enabled containers as per traefiks "rule" router directive. "traefiklocal" bypasses the URL used by traefik and uses the container name directly (useful if there's some auth mechanism you want to bypass for gatus checks.)
 Otherwise these traefik presets do the following:
    * Add a HTTPS check for "traefikweb" or HTTP for "traefiklocal"
    * Sets the port to the loadbalancer config in the traefik label
    * Checks for response code 200


With no defined config, this will attempt to use the docker compose default labels to define the name and grouping of the service via:
 * com.docker.compose.service (name)
 * com.docker.compose.project (group)

All options are:
 * gatus.enable = true / false (default false)
 * gatus.url (default container name)
 * gatus.method (default GET)
 * gatus.interval (default 60s)
 * gatus.group (default name split 1st elem)
 * gatus.name  (default name split 2nd elem)
 * gatus.insecure (default false)

I'm sure there's more to mention...I wrote this a long time ago with 0 documentation
