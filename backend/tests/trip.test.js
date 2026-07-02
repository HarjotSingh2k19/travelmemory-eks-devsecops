const request = require('supertest');
const app = require('../index');

describe('Trip API', () => {
  it('GET /hello returns Hello World!', async () => {
    const res = await request(app).get('/api/hello');
    expect(res.statusCode).toBe(200);
    expect(res.text).toBe('Hello World!');
  });
});
