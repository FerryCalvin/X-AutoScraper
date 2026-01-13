/**
 * Cubic Bezier interpolation implementation
 *
 * This class implements cubic bezier curve interpolation
 * used for animation key generation.
 */
declare class Cubic {
    private curves;
    /**
     * Creates a new Cubic instance
     * @param curves Array of curve control points
     */
    constructor(curves: number[]);
    /**
     * Calculates the interpolated value at a specific time point
     * @param time Normalized time value (0.0 to 1.0)
     * @returns Interpolated value
     */
    getValue(time: number): number;
    /**
     * Calculates cubic bezier value with given control points
     * @param a First control point
     * @param b Second control point
     * @param m Parametric value (0.0 to 1.0)
     * @returns Calculated cubic bezier value
     * @private
     */
    private calculate;
}
export default Cubic;
//# sourceMappingURL=cubic.d.ts.map