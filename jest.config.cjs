/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  transform: {
    "^.+\\.tsx?$": "ts-jest"
  },
  collectCoverage: true,
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}", // Only include source files
    "!**/dist/**",       // Exclude the dist directory
    "!**/node_modules/**"
  ],
  coverageReporters: ["text", "lcov"], // Include lcov for IDE integration
  coveragePathIgnorePatterns: [
    "/node_modules/",
    "<rootDir>/dist/"
  ],
  modulePathIgnorePatterns: ["<rootDir>/dist/"],
  coverageProvider: "v8",
};
