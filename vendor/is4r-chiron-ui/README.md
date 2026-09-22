# Chiron UI

Out of the box this should represent the base UI for a Chiron backed application.
It provides all the features that are present in the API code.

## Configuration

To change/update settings and how things are displayed you can modify defaults and
inject pages into the UI. To do this you will need to modify the `src/overrideConfig.tsx`
file. This will allow you to overwrite any setting you would like. To see what settings

## Local Development

### Prerequisites

should be running a chiron instance somewhere accessible, if not hosted on `http://127.0.0.1:8000`, then change the instances of this url where appropriate

### Installation

- clone this repo

- Install pnpm via one of the [recommended methods](https://pnpm.io/installation).

- install the packages you will need: from the directory containing package.json, run `pnpm install`

### Two ways of allowing cross origin requests to api in development

(handled by nginx in dev and prod)

#### Allowing cross origin in django

- You will have to update the `src/overrideConfig.tsx` file to set the apiBaseUrl parameter
  to be where you are serving the API (ie: http://localhost:8000)
- You will also need to allow cross origin requests on your demo api, so installing django-cors-headers and making the appropriate changes to your settings.py file. [directions on installation here](https://github.com/adamchainz/django-cors-headers#configuration)

#### Adding proxy settings for endpoints (my preferred way)

- If you don't feel like messing with the api settings, you can replace the server setting in `vite.config.ts` with this:

```
server: {
      port: 3000,
      headers: {
        "Access-Control-Allow-Origin": "*",
      },
      proxy: {
        "/admin": "http://127.0.0.1:8000",
        "/api": "http://127.0.0.1:8000",
        "/backend": "http://127.0.0.1:8000",
      },
    },
```

### Running

run server with
`pnpm vite`

should run be running on `localhost:3000`

### Note on headers

You'll need to normal sso headers for authenticating in chirons

## Testing

after installing dependencies, run
run `pnpm run cypress:open` to run tests with browser, or `pnpm cypress run`
