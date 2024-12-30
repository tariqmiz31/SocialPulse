res.json = function (bodyJson, ...args) {
    capturedJsonResponse = typeof bodyJson === 'object' ? 
      { type: bodyJson?.constructor?.name, length: JSON.stringify(bodyJson).length } : 
      bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };