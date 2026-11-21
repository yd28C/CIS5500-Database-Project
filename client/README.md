# Flight Insights frontend

Start the API server on port 8080 with its database configured. Then run:

```sh
cd client
npm install
npm run dev
```

Open the URL printed by Vite. `/api` requests are proxied to the local server. Fares are historical. Airline reliability awaits an API; weather provides monthly high temperatures. For production, configure a reverse proxy for `/api`.
