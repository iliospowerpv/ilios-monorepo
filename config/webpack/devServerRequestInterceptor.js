const express = require('express');
const requestInterceptor = express.Router();
const dataMocks = require('./data-mocks.json');

requestInterceptor.post('/login', (req, res) => {
  res.json(dataMocks[`[${req.method}]${req.url}`]);
});

module.exports = requestInterceptor;