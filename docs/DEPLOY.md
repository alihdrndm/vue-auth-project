# Deploying Eingang

## Mailbox intake (optional)

Eingang can read invoices from a mailbox. Every five minutes the schedule `mailbox-poll` runs `MailboxPollWorkflow`: it connects over IMAP (TLS), reads the unseen messages in `INBOX`, stores each PDF or XML attachment as a document of one organisation (`source = email`, with the sender's address), marks the message as read, and starts processing each new document. Attachments get the same checks as uploads: at most `MAX_UPLOAD_BYTES`, the type is decided by content (PDF, or a UBL/CII invoice XML without a DOCTYPE), and a file the organisation already has is skipped. Other attachments, and messages without a usable attachment, are marked as read and otherwise ignored.

The intake is **disabled in the public demo** (`MAILBOX_ENABLED=false`).

### Setting it up with Gmail

Use a mailbox that receives only invoices, because every unseen message in its inbox is read.

1. In the Google account of that mailbox, turn on **2-Step Verification** (Google Account → Security → 2-Step Verification). App passwords are only available with it.
2. Create an **app password** (Google Account → Security → 2-Step Verification → App passwords), for example named `eingang`. Google shows a 16-character password once; copy it. Your normal Google password does not work over IMAP.
3. Make sure IMAP access is on in Gmail (Settings → See all settings → Forwarding and POP/IMAP → IMAP access).
4. Set these variables for the **worker** (and for the process that runs `ensure_schedules`):

   | Variable | Value |
   |----------|-------|
   | `MAILBOX_ENABLED` | `true` |
   | `MAILBOX_HOST` | `imap.gmail.com` |
   | `MAILBOX_PORT` | `993` |
   | `MAILBOX_USER` | the full Gmail address |
   | `MAILBOX_PASSWORD` | the app password from step 2 (without spaces) |
   | `MAILBOX_ORG_SLUG` | the slug of the organisation that receives the documents |

   With `MAILBOX_ENABLED=true` the configuration check refuses to start until all of them are set.
5. Restart the worker, then create the schedule:

   ```sh
   cd backend
   uv run poe ensure-schedules
   ```

   It prints the schedules that now exist; `mailbox-poll` must be among them. Running it again is safe. To turn the intake off, set `MAILBOX_ENABLED=false` and run `ensure_schedules` again: it removes the `mailbox-poll` schedule.

To check the setup without waiting five minutes, trigger the schedule `mailbox-poll` in the Temporal Web UI. A wrong address or app password makes the run fail at once with "The mailbox refused MAILBOX_USER/MAILBOX_PASSWORD."; an unknown slug fails with a message naming `MAILBOX_ORG_SLUG`.

## OpenAI (LLM features)

Eingang uses the LLM for three things: reading plain-PDF invoices, comparing a hybrid PDF's visible text with its XML, and explaining validation rules once each. Everything works without it (`LLM_ENABLED=false`); the UI then says why a result is missing.

The spend is capped in the application, but the account itself should be a hard stop too:

1. Create a **separate API key** for this project (OpenAI dashboard → API keys).
2. Keep **auto-recharge off** (Billing → auto-recharge). The prepaid credit is then the final limit, whatever happens in the application.
3. Set these variables for the **api** and the **worker**:

   | Variable | Value |
   |----------|-------|
   | `LLM_ENABLED` | `true` |
   | `OPENAI_API_KEY` | the project's key |
   | `OPENAI_MODEL` | the confirmed model (see `docs/DECISIONS.md`) |
   | `OPENAI_REASONING_EFFORT` | the lowest effort the model accepts, or empty for a non-reasoning model |
   | `OPENAI_PRICE_INPUT_PER_MTOK`, `OPENAI_PRICE_CACHED_INPUT_PER_MTOK`, `OPENAI_PRICE_OUTPUT_PER_MTOK` | the model's prices in USD per million tokens, from the official pricing page |
   | `LLM_SPENT_ELSEWHERE_USD` | the spend recorded in the project's other database: run `uv run poe llm-spend` there and copy the number |
   | `LLM_BUDGET_USD_LIFETIME`, `LLM_BUDGET_USD_MONTHLY`, `LLM_BUDGET_USD_DAILY_PUBLIC`, `LLM_MAX_CALLS_PER_SANDBOX` | the budgets; defaults 2.00, 1.50, 0.10 and 3 |

   With `LLM_ENABLED=true` the configuration check refuses to start until the key, the model, the three prices and `LLM_SPENT_ELSEWHERE_USD` are set.

Every call, refused or not, is one row in `llm_calls` with its cost; nothing in the application deletes it.
