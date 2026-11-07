# AI-assisted development disclosure

## Tools used

OpenAI Codex (this development session). AI assistance was used extensively to build
the submitted solution. This must not be represented as unaided candidate work.

## Tasks assisted

- Read the provided assignment and map all requirements to implementation/deliverables.
- Design the six-entity MySQL schema, constraints, indexes and transaction strategy.
- Write the Flask application, parameterized SQL, validation/calculations, authentication,
  role/ownership checks, order and stock services, CSV import and reporting.
- Write the HTML/CSS/plain JavaScript interface and REST documentation.
- Write/run automated tests, prepare sample data/CSV files, maintain meaningful Git
  commits with a feature-branch merge, and prepare the demo recording/submission archive.

## Representative prompts (up to three)

1. User request: "make a project based on their instruction follow their whole instructions
   and make this project do not add any new tech or remove any info go based on the
   guidenline they have given follow all instructions and complete the project"

This was the only project-generation user prompt; development proceeded within the
same Codex session rather than through additional external AI tools.

## Review and verification

Generated code was reviewed against the full assignment, checked for Python/JavaScript
syntax, and exercised with calculation tests and real-MySQL API/integration tests.
Concurrency checks use separate connections in simultaneous threads, not mocked stock.
Browser checks cover form behavior, live totals, validation, confirmation/cancellation,
master data, reports, CSV and role-specific screens. Results are documented in
`docs/VERIFICATION.md`. The application uses the required MySQL backend throughout.

## Corrections identified

- Startup verification caught unquoted hyphenated Flask route-converter values in the
  report routes; those values were quoted before application/integration verification.
- The supplied debugging function overwrote the total instead of accumulating it; the
  corrected shared Decimal function is covered by dedicated tests.
- MySQL's SUM of integer quantities can be returned as Decimal; the product sales API
  explicitly casts quantity totals to an integer so quantities remain whole-number JSON values.
- Validation was tightened to reject boolean numeric inputs and overlong integer values
  instead of allowing them to reach conversion/database failures.
- Product-detail fetching in the editor checks that the response still matches the selected
  product, preventing a slow older response from replacing the latest selection's price.

## Candidate responsibility

The candidate must personally read, run, explain and be able to modify this solution.
Automated/AI review does not establish the candidate's independent understanding. Study
the Decimal calculations, foreign keys, ownership checks, row-lock order, rollback behavior,
SQL LEFT JOIN date filtering, CSV atomicity and tests before the interview.
