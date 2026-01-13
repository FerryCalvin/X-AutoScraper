'use strict';

var initCycleTLS = require('cycletls');
var headersPolyfill = require('headers-polyfill');
var debug = require('debug');

const log = debug("twitter-scraper:cycletls");
let cycleTLSInstance = null;
async function initCycleTLSFetch() {
  if (!cycleTLSInstance) {
    log("Initializing CycleTLS...");
    cycleTLSInstance = await initCycleTLS();
    log("CycleTLS initialized successfully");
  }
  return cycleTLSInstance;
}
function cycleTLSExit() {
  if (cycleTLSInstance) {
    log("Exiting CycleTLS...");
    cycleTLSInstance.exit();
    cycleTLSInstance = null;
  }
}
async function cycleTLSFetch(input, init) {
  const instance = await initCycleTLSFetch();
  const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  const method = (init?.method || "GET").toUpperCase();
  log(`Making ${method} request to ${url}`);
  const headers = {};
  if (init?.headers) {
    if (init.headers instanceof headersPolyfill.Headers) {
      init.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(init.headers)) {
      init.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, init.headers);
    }
  }
  let body;
  if (init?.body) {
    if (typeof init.body === "string") {
      body = init.body;
    } else if (init.body instanceof URLSearchParams) {
      body = init.body.toString();
    } else {
      body = init.body.toString();
    }
  }
  const options = {
    body,
    headers,
    // Chrome 120 on Windows 10
    ja3: "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
    userAgent: headers["user-agent"] || "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
  };
  try {
    const response = await instance(
      url,
      options,
      method.toLowerCase()
    );
    const responseHeaders = new headersPolyfill.Headers();
    if (response.headers) {
      Object.entries(response.headers).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((v) => {
            responseHeaders.append(key, v);
          });
        } else if (typeof value === "string") {
          responseHeaders.set(key, value);
        }
      });
    }
    let responseBody = "";
    if (typeof response.text === "function") {
      responseBody = await response.text();
    } else if (response.body) {
      responseBody = response.body;
    }
    const fetchResponse = new Response(responseBody, {
      status: response.status,
      statusText: "",
      // CycleTLS doesn't provide status text
      headers: responseHeaders
    });
    return fetchResponse;
  } catch (error) {
    log(`CycleTLS request failed: ${error}`);
    throw error;
  }
}

exports.cycleTLSExit = cycleTLSExit;
exports.cycleTLSFetch = cycleTLSFetch;
//# sourceMappingURL=index.cjs.map
