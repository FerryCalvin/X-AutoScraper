/**
 * Cleanup the CycleTLS instance. Call this when you're done making requests.
 */
declare function cycleTLSExit(): void;
/**
 * A fetch-compatible wrapper around CycleTLS that mimics Chrome's TLS fingerprint
 * to bypass Cloudflare and other bot detection systems.
 */
declare function cycleTLSFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;

export { cycleTLSExit, cycleTLSFetch };
