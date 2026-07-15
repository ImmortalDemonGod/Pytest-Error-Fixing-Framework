# Bug Catalog — pef-p34-correct-api-key-env-var-in-u

- **Symptom:** README.md's "Configure Your API Key" quick-start instructs users to write
  `OPENAI_API_KEY` into `.env`.
  **Location:** `README.md:52`
  **Wrong:** `echo "OPENAI_API_KEY='your-api-key-here'" > .env`
  **Correct:** The CLI's `--api-key` option (`src/branch_fixer/utils/run_cli.py:37`) reads its
  value from the `OPENROUTER_API_KEY` environment variable (via LiteLLM/OpenRouter, per
  CLAUDE.md). A user who follows the README literally sets an env var the CLI never reads,
  the `--api-key` option's `required=True` constraint is not satisfied by envvar lookup, and
  the run fails with a "Missing option '--api-key'" error instead of authenticating.

- **Symptom:** `docs/developer-guide/04-execution-flow.md`'s "CLI Entry" code example shows the
  `--api-key` click option bound to `envvar='OPENAI_API_KEY'`.
  **Location:** `docs/developer-guide/04-execution-flow.md:19`
  **Wrong:** `@click.option('--api-key', envvar='OPENAI_API_KEY', required=True)`
  **Correct:** The actual option in `src/branch_fixer/utils/run_cli.py:35-39` is
  `envvar="OPENROUTER_API_KEY"`. The doc example diverges from the real source it claims to
  quote, teaching contributors the wrong environment variable name.
