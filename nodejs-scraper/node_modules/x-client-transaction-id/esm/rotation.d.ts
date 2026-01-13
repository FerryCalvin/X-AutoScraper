/**
 * Rotation utility functions
 *
 * This module provides functions for converting rotation values to matrices,
 * used in the animation key generation process.
 */
/**
 * Converts a rotation angle in degrees to a 2D transformation matrix
 * @param rotation Angle in degrees
 * @returns Array of 4 values representing the transformation matrix [a, b, c, d]
 */
declare function convertRotationToMatrix(rotation: number): number[];
/**
 * Alternative implementation for converting rotation to matrix
 * Note: This implementation returns a 6-value matrix in the format [a, b, c, d, tx, ty]
 * @param degrees Angle in degrees
 * @returns Array of 6 values representing the transformation matrix
 * @private
 */
declare function convertRotationToMatrix2(degrees: number): number[];
export { convertRotationToMatrix, convertRotationToMatrix2 };
//# sourceMappingURL=rotation.d.ts.map