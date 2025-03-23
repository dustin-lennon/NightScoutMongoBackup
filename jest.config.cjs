/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  transform: {
    "^.+\\.(t|j)sx?$": "ts-jest"
  },
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
    "ansi-regex": require.resolve("ansi-regex")
  },
  extensionsToTreatAsEsm: [".ts"],
  testMatch: ["**/src/tests/**/*.test.ts", "**/src/tests/**/*.spec.ts"]
};
