const path = require("node:path");
const nextJest = require("next/jest");

const frontendDir = __dirname;
const createJestConfig = nextJest({ dir: frontendDir });

module.exports = createJestConfig({
  testEnvironment: "node",
  setupFilesAfterEnv: [path.join(frontendDir, "jest.setup.js")],
  moduleNameMapper: { "^@/(.*)$": path.join(frontendDir, "$1") },
});
