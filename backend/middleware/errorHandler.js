function errorHandler(err, req, res, next) {
  const requestId = req.requestId || 'unknown';
  const statusCode = err.status || err.statusCode || 500;

  console.error(`[Error] [ReqID: ${requestId}] Status: ${statusCode} - ${err.message}`, err.stack);

  let userMessage = 'An unexpected internal server error occurred.';
  let errorCode = 'INTERNAL_ERROR';

  if (statusCode === 400) {
    errorCode = 'BAD_REQUEST';
    userMessage = err.message || 'Invalid request payload or parameters.';
  } else if (statusCode === 401) {
    errorCode = 'UNAUTHORIZED';
    userMessage = 'Authentication credentials missing or invalid.';
  } else if (statusCode === 403) {
    errorCode = 'FORBIDDEN';
    userMessage = 'You do not have permission to access this resource.';
  } else if (statusCode === 408 || err.code === 'ECONNABORTED' || (err.message && err.message.includes('timeout'))) {
    errorCode = 'REQUEST_TIMEOUT';
    userMessage = 'The prompt optimization request timed out. Please try again.';
    return res.status(408).json({
      error: 'Request Timeout',
      code: errorCode,
      message: userMessage,
      requestId: requestId
    });
  } else if (statusCode === 429) {
    errorCode = 'TOO_MANY_REQUESTS';
    userMessage = err.message || 'Too many requests. Please slow down.';
  } else if (statusCode === 502 || err.code === 'ECONNREFUSED' || err.isMlServiceError) {
    errorCode = 'ML_SERVICE_ERROR';
    userMessage = 'The Python ML optimization engine is currently unreachable or failed to respond.';
    return res.status(502).json({
      error: 'Bad Gateway',
      code: errorCode,
      message: userMessage,
      requestId: requestId
    });
  } else if (statusCode === 503) {
    errorCode = 'SERVICE_UNAVAILABLE';
    userMessage = 'TokenTrim service is temporarily unavailable.';
  }

  res.status(statusCode >= 400 && statusCode < 600 ? statusCode : 500).json({
    error: err.name || 'Error',
    code: errorCode,
    message: userMessage,
    requestId: requestId
  });
}

module.exports = errorHandler;
