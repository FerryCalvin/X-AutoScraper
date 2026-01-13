/**
 * Interpolation utility functions
 *
 * This module provides functions for interpolating between values,
 * used in the animation key generation process.
 */
/**
 * Interpolates between two arrays of numbers
 * @param fromList Starting values
 * @param toList Ending values
 * @param f Interpolation factor (0.0 to 1.0)
 * @returns Array of interpolated values
 */
declare function interpolate(fromList: number[], toList: number[], f: number): number[];
/**
 * Interpolates between two values (numeric or boolean)
 * @param fromVal Starting value
 * @param toVal Ending value
 * @param f Interpolation factor (0.0 to 1.0)
 * @returns Interpolated value
 */
declare function interpolateNum(fromVal: number | boolean, toVal: number | boolean, f: number): number;
export { interpolate, interpolateNum };
//# sourceMappingURL=interpolate.d.ts.map