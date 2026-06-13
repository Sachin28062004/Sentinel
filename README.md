# Sentinel

An end-to-end placement workflow built with CrewAI, Groq, Gmail API, Google Sheets API, and free/open-source Python libraries.

## What it does

1. Reads the newest Gmail messages first.
2. Uses conservative extraction rules to decide whether a mail is placement-related.
3. Extracts only the columns you asked for:
   - company name
   - date applied in `DD-MM-YYYY`
   - role
   - application link
   - status
   - job type
   - placement type
4. Appends the result to a Google Sheet.

## Why this stack

- `CrewAI` for orchestration
- `Groq` for the LLM layer
- Google official APIs for Gmail and Sheets
- `duckduckgo-search`, `requests`, and `beautifulsoup4` for recruiter lookup

Everything here is free/open-source except the optional Groq API usage, which has its own pricing/limits.

## Setup

### 1. Create a virtual environment and install

Use Python 3.12 or 3.13 for this project. CrewAI currently requires Python `<3.14`, so Python 3.14 will fail during install.
By default the app uses local heuristics so it can run even when Groq/network access is unavailable.

```bash
py -3.12 -m venv .venv
.venv\\Scripts\\activate
pip install -e .
```

### 2. Run setup

Run the CLI once and follow the onboarding prompts:

```bash
sentinel
```

Or start it directly:

```bash
sentinel setup
```

Sentinel stores its private config, token, and state files under your user profile by default, not in the project folder. That keeps one user from accidentally reusing another user's credentials.

### 3. Google Cloud setup

Enable the Gmail API and Sheets API in your Google Cloud project. Create an OAuth desktop client and download the JSON as `credentials.json`.

On first run, the app will open a browser for consent and store the resulting token in `token.json`.

### 4. Prepare the sheet

Create a tab with headers matching the row schema in `sentinel/sheets_service.py`, or let the agent append rows into an existing tab.

### 5. Run

```bash
sentinel
```

The default command is `run` after setup is complete, so these are equivalent:

```bash
sentinel
sentinel run
```

### Run automatically every 3 hours

```bash
sentinel daemon --interval-hours 3
```

### Dry run

```bash
sentinel run --dry-run
```

### Check local setup

```bash
sentinel doctor
```

### Security notes

- OAuth tokens and processed-message state live in your private Sentinel directory, usually `~/.sentinel`.
- If you want separate data isolation on a shared machine, set `SENTINEL_PROFILE` before setup.
- Do not commit your OAuth client file, token file, or private `.env` file.

## Notes

- The Gmail flow reads the latest messages first by sorting on `internalDate`.
- If you want this to run on a schedule, we can add a small scheduler or Windows Task Scheduler setup next.

## Release

Build locally:

```bash
python -m build
```

Publish is handled by the GitHub Actions workflow on tagged releases (`v*.*.*`).

After the first public release, users can install it with:

```bash
pip install sentinel
```


