/**
 * @lami/x-client-transaction-id
 *
 * A library for generating client transaction IDs required for
 * authenticated API requests to X (formerly Twitter).
 *
 * This module exports the main ClientTransaction class and utility functions
 * needed to generate valid x-client-transaction-id headers for X API requests.
 *
 * @module
 */
import ClientTransaction from "./transaction.js";
import Cubic from "./cubic.js";
import { interpolate, interpolateNum } from "./interpolate.js";
import { convertRotationToMatrix } from "./rotation.js";
import { floatToHex, handleXMigration, isOdd } from "./utils.js";
import { decodeBase64, encodeBase64 } from "./deps/jsr.io/@std/encoding/1.0.10/mod.js";
export { ClientTransaction, convertRotationToMatrix, Cubic, decodeBase64, encodeBase64, floatToHex, handleXMigration, interpolate, interpolateNum, isOdd, };
export default ClientTransaction;
