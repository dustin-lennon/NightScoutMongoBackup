/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  transform: {
    "^.+\\.(t|j)sx?$": "ts-jest"
  },
  moduleNameMapper: {
    "^@sentry/node$": "<rootDir>/src/tests/__mocks__/@sentry/node.ts",
    "^(\\.{1,2}/.*)\\.js$": "$1",
    "ansi-regex": require.resolve("ansi-regex")
  },
  extensionsToTreatAsEsm: [".ts"],
  testMatch: ["**/src/tests/**/*.test.ts", "**/src/tests/**/*.spec.ts"],
  modulePathIgnorePatterns: ['<rootDir>/dist/'],
  transformIgnorePatterns: ['<rootDir>/dist/', '/node_modules/'],
  collectCoverageFrom: [
    "**/src/**/*.{ts,tsx}", // Only include files in the src directory
    "!**/dist/**"           // Explicitly exclude the dist directory
  ],
};
