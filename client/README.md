# Flight Insights frontend

Start the API server on port 8080 with its database configured. Then run:

```sh
cd client
npm install
npm run dev
```

Open the URL printed by Vite. `/api` requests are proxied to the local server. Fares are historical. Flight operations and weather use 2025 data, and fare references use 2022 quotes. The airline reliability endpoint returns one object. The airport chart shows monthly high temperatures alongside departure delay and cancellation rates. For production, configure a reverse proxy for `/api`.
