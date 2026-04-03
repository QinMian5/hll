// abstract: Commit message lint configuration enforcing conventional commits with required scope.
// out_of_scope: Git hook wiring, CI integration, and branch workflow policy.
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "scope-empty": [2, "never"],
    "type-case": [2, "always", "lower-case"],
    "scope-case": [2, "always", "lower-case"],
    "subject-empty": [2, "never"],
  },
};
