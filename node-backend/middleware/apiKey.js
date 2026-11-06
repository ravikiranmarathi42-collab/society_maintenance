module.exports = function apiKey(req, res, next) {
  const expected = process.env.INTERNAL_API_KEY;
  const supplied = (req.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!expected || !supplied || supplied.length !== expected.length || !require('crypto').timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) {
    return res.status(401).json({ error: 'Unauthorized', message: 'A valid API bearer token is required.' });
  }
  next();
};
