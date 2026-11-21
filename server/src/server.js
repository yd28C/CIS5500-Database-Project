require('dotenv').config({ quiet: true });
const express = require('express');
const cors = require('cors');
const routes = require('./routes');

const app = express();
app.use(cors()); // allow the frontend (different port) to call the API
app.use(express.json());
app.use(routes);

const port = process.env.PORT || 8080;
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
