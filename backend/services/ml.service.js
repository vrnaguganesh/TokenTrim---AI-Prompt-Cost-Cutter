const axios = require('axios');
const config = require('../config');

class MLService {
  constructor() {
    this.client = axios.create({
      baseURL: config.mlServiceUrl,
      timeout: config.mlTimeoutMs,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(config.mlInternalToken ? { 'X-Internal-Token': config.mlInternalToken } : {})
      }
    });
  }

  async optimizePrompt({ prompt, model = 'gpt-4o', mode = 'balanced', customKeywords = [], requestId }) {
    try {
      const response = await this.client.post('/internal/optimize', {
        prompt,
        model,
        mode,
        customKeywords
      }, {
        headers: {
          'X-Request-ID': requestId || ''
        }
      });
      return response.data;
    } catch (err) {
      this._handleAxiosError(err, 'optimizePrompt');
    }
  }

  async evaluatePair({ originalPrompt, optimizedPrompt, model = 'gpt-4o', mode = 'balanced', requestId }) {
    try {
      const response = await this.client.post('/evaluate', {
        originalPrompt,
        optimizedPrompt,
        model,
        mode
      }, {
        headers: {
          'X-Request-ID': requestId || ''
        }
      });
      return response.data;
    } catch (err) {
      this._handleAxiosError(err, 'evaluatePair');
    }
  }

  async checkHealth() {
    try {
      const response = await this.client.get('/health', { timeout: 3000 });
      return response.data;
    } catch (err) {
      return {
        status: 'unreachable',
        model_loaded: false,
        error: err.message
      };
    }
  }

  async getModelInfo() {
    try {
      const response = await this.client.get('/model-info', { timeout: 3000 });
      return response.data;
    } catch (err) {
      this._handleAxiosError(err, 'getModelInfo');
    }
  }

  _handleAxiosError(err, actionName) {
    if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
      const error = new Error(`Cannot connect to Python ML Service at ${config.mlServiceUrl}`);
      error.status = 502;
      error.isMlServiceError = true;
      throw error;
    }

    if (err.code === 'ECONNABORTED' || (err.message && err.message.includes('timeout'))) {
      const error = new Error(`Python ML Service request timed out after ${config.mlTimeoutMs}ms`);
      error.status = 408;
      throw error;
    }

    if (err.response) {
      const error = new Error(err.response.data?.detail || `ML Service failed during ${actionName}`);
      error.status = err.response.status >= 500 ? 502 : err.response.status;
      error.isMlServiceError = true;
      throw error;
    }

    const genericError = new Error(`Failed to communicate with ML optimization engine: ${err.message}`);
    genericError.status = 502;
    genericError.isMlServiceError = true;
    throw genericError;
  }
}

module.exports = new MLService();
