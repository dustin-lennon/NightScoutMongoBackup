/** @type {import('eslint').FlatConfigItem[]} */
module.exports = [
  {
    files: ["**/*.{js,mjs,cjs,ts}"],
    languageOptions: {
      globals: require("globals").node
    },
    plugins: {
      "@typescript-eslint": require("typescript-eslint").plugin,
      jest: require("eslint-plugin-jest")
    },
    rules: {
      ...require("@eslint/js").configs.recommended.rules,
      ...require("typescript-eslint").configs.recommended.rules,
      ...require("eslint-plugin-jest").configs.recommended.rules,
      "no-console": "warn",
      "@typescript-eslint/no-unused-vars": "warn"
    }
  },
  {
    files: ["src/tests/**/*.ts"], // ✅ Ensures Jest globals apply only to test files
    languageOptions: {
      globals: {
        test: "readonly",
        expect: "readonly",
        describe: "readonly",
        it: "readonly"
      }
    },
    plugins: {
      jest: require("eslint-plugin-jest")
    },
    rules: {
      ...require("eslint-plugin-jest").configs.recommended.rules
    }
  },
  {
    ignores: ["node_modules/", "dist/"]
  }
];
