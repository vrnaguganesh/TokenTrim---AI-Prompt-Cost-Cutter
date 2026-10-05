const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const { v4: uuidv4 } = require('uuid');
const config = require('./config');
const routes = require('./routes/optimization.routes');
const errorHandler = require('./middleware/errorHandler');

const app = express();
app.disable('x-powered-by');
app.use(helmet());
app.use(cors({
  origin: config.corsOrigin === '*' ? true : config.corsOrigin.split(',').map(value => value.trim()),
  methods: ['GET', 'POST'],
}));
app.use(express.json({ limit: `${Math.ceil(config.maxPromptLength / 1000) + 20}kb` }));
app.use((req, res, next) => {
  req.requestId = req.headers['x-request-id'] || uuidv4();
  res.setHeader('X-Request-ID', req.requestId);
  next();
});

app.get('/health', (req, res) => res.json({ status: 'healthy', service: 'tokentrim-api' }));
app.use('/api/v1', routes);
app.use('/api', routes);
app.use(errorHandler);

if (require.main === module) {
  app.listen(config.port, () => console.log(`TokenTrim API listening on port ${config.port}`));
}

module.exports = app;