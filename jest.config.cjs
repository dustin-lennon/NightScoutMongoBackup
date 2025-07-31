/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  transform: {
    "^.+\\.tsx?$": "ts-jest"
  },
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json"],
  moduleNameMapper: {
    "^#lib/(.*)$": "<rootDir>/src/lib/$1",
    "^#listeners/(.*)$": "<rootDir>/src/listeners/$1",
    "^#commands/(.*)$": "<rootDir>/src/commands/$1",
    "^#events/(.*)$": "<rootDir>/src/events/$1",
    "^#preconditions/(.*)$": "<rootDir>/src/preconditions/$1",
    "^#tests/(.*)$": "<rootDir>/src/tests/$1",
    "^#root/(.*)$": "<rootDir>/src/$1",
    "^#scheduled\\-tasks/(.*)$": "<rootDir>/src/scheduled-tasks/$1"
  },
  collectCoverage: true,
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}", // Only include source files
    "!**/dist/**",       // Exclude the dist directory
    "!**/node_modules/**",
    "!src/commands/admin/**" // Exclude Discord command files (UI layer - business logic tested in services)
  ],
  coverageReporters: ["text", "lcov"], // Include lcov for IDE integration
  coveragePathIgnorePatterns: [
    "/node_modules/",
    "<rootDir>/dist/"
  ],
  modulePathIgnorePatterns: ["<rootDir>/dist/"],
  coverageProvider: "v8",
};
