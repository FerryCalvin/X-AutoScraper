"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isOdd = exports.interpolateNum = exports.interpolate = exports.handleXMigration = exports.floatToHex = exports.encodeBase64 = exports.decodeBase64 = exports.Cubic = exports.convertRotationToMatrix = exports.ClientTransaction = void 0;
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
const transaction_js_1 = __importDefault(require("./transaction.js"));
exports.ClientTransaction = transaction_js_1.default;
const cubic_js_1 = __importDefault(require("./cubic.js"));
exports.Cubic = cubic_js_1.default;
const interpolate_js_1 = require("./interpolate.js");
Object.defineProperty(exports, "interpolate", { enumerable: true, get: function () { return interpolate_js_1.interpolate; } });
Object.defineProperty(exports, "interpolateNum", { enumerable: true, get: function () { return interpolate_js_1.interpolateNum; } });
const rotation_js_1 = require("./rotation.js");
Object.defineProperty(exports, "convertRotationToMatrix", { enumerable: true, get: function () { return rotation_js_1.convertRotationToMatrix; } });
const utils_js_1 = require("./utils.js");
Object.defineProperty(exports, "floatToHex", { enumerable: true, get: function () { return utils_js_1.floatToHex; } });
Object.defineProperty(exports, "handleXMigration", { enumerable: true, get: function () { return utils_js_1.handleXMigration; } });
Object.defineProperty(exports, "isOdd", { enumerable: true, get: function () { return utils_js_1.isOdd; } });
const mod_js_1 = require("./deps/jsr.io/@std/encoding/1.0.10/mod.js");
Object.defineProperty(exports, "decodeBase64", { enumerable: true, get: function () { return mod_js_1.decodeBase64; } });
Object.defineProperty(exports, "encodeBase64", { enumerable: true, get: function () { return mod_js_1.encodeBase64; } });
exports.default = transaction_js_1.default;
