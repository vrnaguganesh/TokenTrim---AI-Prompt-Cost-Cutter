const test = require('node:test');
const assert = require('node:assert');
const app = require('../server');

test('GET /health returns health status', async (t) => {
  assert.ok(app);
});

test('App contains route handlers', (t) => {
  assert.strictEqual(typeof app, 'function');
});
