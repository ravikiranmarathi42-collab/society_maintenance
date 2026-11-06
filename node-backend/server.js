require('dotenv').config();
const express = require('express');
const cors = require('cors');
const pool = require('./config/db');
const complaints = require('./routes/complaints');
const app = express();
app.disable('x-powered-by');
app.use(cors({ origin: process.env.CORS_ORIGIN || 'http://localhost' }));
app.use(express.json({ limit: '32kb' }));
app.get('/api/health', async (_req, res, next) => {
  try { await pool.query('SELECT 1'); res.json({ status: 'ok', service: 'society-node-api', database: 'connected' }); }
  catch (err) { next(err); }
});
app.use('/api/complaints', complaints);
app.use((err, _req, res, _next) => {
  console.error(err.message);
  res.status(500).json({ error: 'Internal server error' });
});
const port = Number(process.env.PORT || 3001);
app.listen(port, () => console.log(`Society Node API listening on http://localhost:${port}`));
