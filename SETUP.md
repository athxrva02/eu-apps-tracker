# Your local workspace

The local `.env` is configured for a separate live database at `.data/live.sqlite`. Your previous synthetic demo database is preserved. Python dependencies and the production frontend are installed and built. OpenRouter is configured with the existing key and `openai/gpt-4o`; the earlier one-request check passed.

Your CV v6 is imported as an editable draft. The workspace contains the 25 target employer entry pages, the 24 distinct title aliases and country defaults NL, DE, GB, CH, FR and BE. Employer entries are disabled until a working connector is configured and tested. There are no synthetic jobs in this live workspace.

## Launch

From a normal macOS terminal:

```sh
cd /path/to/eu-apps-tracker
./start-local.sh
```

Open **http://localhost:8000**. This starts the web app and scheduler together without Docker. Keep the terminal open and the laptop awake; Ctrl+C stops both. The coding sandbox does not permit binding a localhost port, so the server could not be left running from here.

## What you need to fill or confirm

1. **Profile → Save & approve:** review the imported CV excerpts and correct extraction before approval. Work authorization and salary stay unknown until you supply them.
2. **Email, if wanted:** enter the fields below in the private root `.env`, restart the app, then set the recipient address and enable notifications in **Settings**. Use your provider's SMTP/app password; do not paste passwords into chat.

   | `.env` field | Fill with |
   |---|---|
   | `SMTP_HOST` | Your email provider's SMTP hostname |
   | `SMTP_PORT` | Provider's submission port; defaults to 587 |
   | `SMTP_USERNAME` | Sender account/login |
   | `SMTP_PASSWORD` | SMTP credential or app password |
   | `SMTP_FROM` | Verified sender email address |
   | `SMTP_STARTTLS` | `true` for STARTTLS submission on port 587 |

   **Settings → Recipient:** the address that should receive job alerts. Email remains disabled until you configure and enable it. The test action sends only to that recipient.
3. **OpenRouter matching, if wanted:** the key, model, attribution headers and prices are already filled. In **Settings**, consent to sending selected CV evidence/job descriptions to OpenRouter and enable model matching. The monthly budget defaults to $10. Without this, local deterministic matching works after profile approval. Rotate the key previously pasted into chat by replacing `OPENROUTER_API_KEY` in `.env`.
4. **Sources:** a careers homepage alone is not a working monitor. Each company needs a verified Greenhouse/Lever board identifier or a supported public HTML configuration, access-review notes and a passing connection test before enabling it. See [source setup](docs/sources.md). Manual job JSON and `.eml` imports work without a live connector. No source credentials or technical identifiers have been invented.

The country list, ranking thresholds, digest at 08:00 Europe/Berlin, quiet hours 22:00–08:00 and retention settings are already filled and remain editable. No admin token is needed for this localhost setup. External hosting needs a separate authenticated HTTPS deployment.

`.env` and the live database are private and ignored by Git. Do not commit or share them.
