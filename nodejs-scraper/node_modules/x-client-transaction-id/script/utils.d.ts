/**
 * Handles X.com domain migration process and returns the HTML document
 *
 * This function navigates through X's migration redirects and forms
 * to obtain the final HTML document needed for transaction ID generation.
 *
 * @returns Promise resolving to the Document object from X's homepage
 */
declare function handleXMigration(): Promise<Document>;
/**
 * Converts a floating point number to hexadecimal string representation
 *
 * @param x Floating point number to convert
 * @returns Hexadecimal string representation of the number
 */
declare function floatToHex(x: number): string;
/**
 * Determines if a number is odd and returns a specific value
 *
 * @param num Number to check
 * @returns -1.0 if odd, 0.0 if even
 */
declare function isOdd(num: number): number;
export { floatToHex, handleXMigration, isOdd };
//# sourceMappingURL=utils.d.ts.map