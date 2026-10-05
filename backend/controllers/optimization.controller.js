const mlService = require('../services/ml.service');
const config = require('../config');

class OptimizationController {
  async optimize(req, res, next) {
    try {
      const { prompt, model, mode, customKeywords } = req.body || {};

      if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
        return res.status(400).json({
          error: 'Bad Request',
          code: 'INVALID_PROMPT',
          message: 'Field "prompt" is required and must be a non-empty string.',
          requestId: req.requestId
        });
      }

      if (prompt.length > config.maxPromptLength) {
        return res.status(400).json({
          error: 'Bad Request',
          code: 'PROMPT_TOO_LARGE',
          message: `Prompt exceeds maximum supported payload length (${config.maxPromptLength} characters).`,
          requestId: req.requestId
        });
      }

      const selectedModel = model || config.modelsConfig.defaultModel || 'gpt-4o';
      const selectedMode = mode || 'balanced';

      if (config.enablePromptLogging) {
        console.log(`[ReqID: ${req.requestId}] Optimizing prompt (${prompt.length} chars) with model=${selectedModel}, mode=${selectedMode}`);
      } else {
        console.log(`[ReqID: ${req.requestId}] Optimizing prompt (${prompt.length} chars) with model=${selectedModel}, mode=${selectedMode} (prompt text omitted)`);
      }

      const result = await mlService.optimizePrompt({
        prompt,
        model: selectedModel,
        mode: selectedMode,
        customKeywords: Array.isArray(customKeywords) ? customKeywords : [],
        requestId: req.requestId
      });

      return res.status(200).json({
        ...result,
        requestId: req.requestId
      });
    } catch (err) {
      next(err);
    }
  }

  async evaluate(req, res, next) {
    try {
      const { originalPrompt, optimizedPrompt, model, mode } = req.body || {};

      if (!originalPrompt || !optimizedPrompt) {
        return res.status(400).json({
          error: 'Bad Request',
          code: 'MISSING_EVALUATION_PAIRS',
          message: 'Both "originalPrompt" and "optimizedPrompt" are required fields.',
          requestId: req.requestId
        });
      }

      const result = await mlService.evaluatePair({
        originalPrompt,
        optimizedPrompt,
        model: model || 'gpt-4o',
        mode: mode || 'balanced',
        requestId: req.requestId
      });

      return res.status(200).json({
        ...result,
        requestId: req.requestId
      });
    } catch (err) {
      next(err);
    }
  }

  async getModels(req, res) {
    return res.status(200).json({
      defaultModel: config.modelsConfig.defaultModel || 'gpt-4o',
      models: config.modelsConfig.models || {},
      modes: config.modelsConfig.modes || {},
      requestId: req.requestId
    });
  }

  async getModelInfo(req, res, next) {
    try {
      const info = await mlService.getModelInfo();
      return res.status(200).json({
        ...info,
        requestId: req.requestId
      });
    } catch (err) {
      next(err);
    }
  }
}

module.exports = new OptimizationController();
