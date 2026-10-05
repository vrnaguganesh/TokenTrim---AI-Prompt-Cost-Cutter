const config = require('../config');

function authMiddleware(req, res, next) {
  if (!config.apiKey) {
    return next();
  }

  const authHeader = req.headers['authorization'];
  const apiKeyHeader = req.headers['x-api-key'];

  let token = '';
  if (authHeader && authHeader.startsWith('Bearer ')) {
    token = authHeader.substring(7).trim();
  } else if (apiKeyHeader) {
    token = apiKeyHeader.trim();
  }

  if (!token) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Authentication required. Please provide a valid API key via Authorization header or x-api-key.',
      requestId: req.requestId
    });
  }

  if (token !== config.apiKey) {
    return res.status(403).json({
      error: 'Forbidden',
      message: 'Invalid API key or insufficient permissions.',
      requestId: req.requestId
    });
  }

  next();
}

module.exports = authMiddleware;
