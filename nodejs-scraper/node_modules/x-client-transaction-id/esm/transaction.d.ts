/**
 * Main class responsible for generating client transaction IDs
 * used in authenticated API requests to X
 */
declare class ClientTransaction {
    private static ADDITIONAL_RANDOM_NUMBER;
    private static DEFAULT_KEYWORD;
    private DEFAULT_ROW_INDEX;
    private DEFAULT_KEY_BYTES_INDICES;
    private homePageDocument;
    private key;
    private keyBytes;
    private animationKey;
    private isInitialized;
    /**
     * Creates a new ClientTransaction instance
     * @param homePageDocument DOM Document object from X's homepage
     */
    constructor(homePageDocument: Document);
    /**
     * Initializes the ClientTransaction instance
     * Must be called after constructor and before using other methods
     * @returns Promise that resolves when initialization is complete
     * @throws Error if initialization fails
     */
    initialize(): Promise<void>;
    /**
     * Static factory method that creates and initializes a ClientTransaction instance
     * @param homePageDocument DOM Document object from X's homepage
     * @returns Initialized ClientTransaction instance
     */
    static create(homePageDocument: Document): Promise<ClientTransaction>;
    /**
     * Extracts key byte indices from homepage document
     * @param homePageDocument Optional document to use instead of stored one
     * @returns Tuple of [rowIndex, keyByteIndices]
     * @private
     */
    private getIndices;
    /**
     * Extracts verification key from document
     * @param response Optional document to use instead of stored one
     * @returns X site verification key
     * @private
     */
    private getKey;
    /**
     * Converts key string to byte array
     * @param key Base64 encoded key string
     * @returns Array of byte values
     * @private
     */
    private getKeyBytes;
    /**
     * Gets animation frames from document
     * @param response Optional document to use instead of stored one
     * @returns Array of frame elements
     * @private
     */
    private getFrames;
    /**
     * Parses SVG paths to extract coordinate arrays
     * @param keyBytes Key bytes from site verification
     * @param response Optional document to use
     * @param frames Optional frame elements if already fetched
     * @returns 2D array of frame coordinates
     * @private
     */
    private get2dArray;
    /**
     * Calculates value within specified range
     * @param value Input value (0-255)
     * @param minVal Minimum output value
     * @param maxVal Maximum output value
     * @param rounding Whether to use floor (true) or round (false)
     * @returns Calculated value
     * @private
     */
    private solve;
    /**
     * Generates animation key from frame data
     * @param frames Array of frame values
     * @param targetTime Target time for animation
     * @returns Animation key string
     * @private
     */
    private animate;
    /**
     * Generates animation key used in transaction ID
     * @param keyBytes Key bytes from site verification
     * @param response Optional document to use
     * @returns Animation key string
     * @private
     */
    private getAnimationKey;
    /**
     * Generates a transaction ID for X API requests
     * @param method HTTP method (GET, POST, etc.)
     * @param path API endpoint path
     * @param response Optional document to use
     * @param key Optional key to use
     * @param animationKey Optional animation key to use
     * @param timeNow Optional timestamp (defaults to current time)
     * @returns Base64 encoded transaction ID
     */
    generateTransactionId(method: string, path: string, response?: Document, key?: string, animationKey?: string, timeNow?: number): Promise<string>;
}
export default ClientTransaction;
//# sourceMappingURL=transaction.d.ts.map