const path = require('path');
const fs = require('fs');
require('dotenv').config();

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const MODELS_CONFIG_PATH = process.env.CONFIG_PATH || path.join(ROOT_DIR, 'config', 'models.json');

let modelsConfig = { models: {}, modes: {} };
if (fs.existsSync(MODELS_CONFIG_PATH)) {
  try {
    modelsConfig = JSON.parse(fs.readFileSync(MODELS_CONFIG_PATH, 'utf-8'));
  } catch (err) {
    console.warn(`[Config] Failed to parse models.json from ${MODELS_CONFIG_PATH}: ${err.message}`);
  }
}

module.exports = {
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  mlServiceUrl: process.env.ML_SERVICE_URL || 'http://localhost:8000',
  mlTimeoutMs: parseInt(process.env.ML_TIMEOUT_MS || '6000', 10),
  mlInternalToken: process.env.ML_INTERNAL_TOKEN || '',
  maxPromptLength: parseInt(process.env.MAX_PROMPT_LENGTH || '20000', 10),
  corsOrigin: process.env.CORS_ORIGIN || '*',
  apiKey: process.env.TOKENTRIM_API_KEY || '',
  rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10),
  rateLimitMaxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10),
  enablePromptLogging: process.env.ENABLE_PROMPT_LOGGING === 'true',
  modelsConfig
};
