const express = require('express');
const router = express.Router();
const controller = require('../controllers/optimization.controller');
const authMiddleware = require('../middleware/auth');
const rateLimiter = require('../middleware/rateLimit');

router.post('/optimize', rateLimiter, authMiddleware, (req, res, next) => {
  controller.optimize(req, res, next);
});

router.post('/evaluate', rateLimiter, authMiddleware, (req, res, next) => {
  controller.evaluate(req, res, next);
});

router.get('/models', (req, res, next) => {
  controller.getModels(req, res, next);
});

router.get('/model-info', (req, res, next) => {
  controller.getModelInfo(req, res, next);
});

module.exports = router;
