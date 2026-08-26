# CDDA Meeting Manager (Dash)

Pro-code port of the `CDDA_Meeting_Manager_V2_DEV` Power App, built as a Python
Dash app for **Posit Connect**. The visual language comes from the Claude Design
mockup (`CDDA_Meeting_Manager_claude_design.html`); the behaviour comes from the
Power Fx in the `.msapp`.

---

## Repository layout

| File | Purpose | Required? |
| --- | --- | --- |
| `app.py` | The app: layout, screens, callbacks. Exposes `server = app.server`. | Yes |
| `sharepoint_client.py` | Microsoft Graph reads/writes against the four SharePoint lists. | Yes |
| `ad_access.py` | AD-group access enforcement (`enforce_access(server)`). No-op locally. | Yes |
| `config.py` | Every env-driven setting in one place, plus the list GUIDs. | Yes |
| `theme.py` | Design tokens and shared style dicts from the mockup. | Yes |
| `requirements.txt` | Python dependencies Posit installs. | Yes |
| `gunicorn.conf.py` | Raises the worker timeout to 300s (default 30s is too short for the first Graph pull). | Recommended |
| `.gitignore` | Keeps `.env` and caches out of Git. Must exist **before** the first commit. | Recommended |
| `.env.example` | Template for local development. Copy to `.env`; never commit `.env`. | Optional |
| `manifest.json` | **Generated, not committed from here.** See "Deploy" below. | Yes, before deploy |

Deploy entrypoint: **`app:server`**, app mode **python-dash**.

---

## Data model

The app reads the same SharePoint site the Power App used:
`https://collab.lilly.com/sites/CDDAMeetingMgt`. List GUIDs were taken from
`References/DataSources.json` inside the `.msapp`, so they are correct for DEV
and are overridable by env var for other environments.

| List | Fields used | Role |
| --- | --- | --- |
| `CDDAMeetings` | `Title`, `MeetingDescription`, `MeetingDuration`, `MeetingOwner`, `MeetingAdmin` | The forums on the home screen |
| `MeetingInstances` | `Title`, `MeetingDate`, `DisplayText`, `IsAvailable`, `MeetingName` (lookup → CDDAMeetings) | The meeting dates |
| `AgendaItems` | `Title`, `TopicDescription`, `Speakers` (person), `TimeRequired`, `MeetingText`, `MeetingDateCol`, `Status` | The agenda rows |
| `Documents` | `Title`, `AgendaID` (number), `DocumentType` | Attachments per agenda item |

Behaviour carried over from the Power Fx:

* dates for a forum — `Filter(MeetingInstances, MeetingName.Id = forum.ID)`
* agenda for a date — `Filter(AgendaItems, MeetingDateCol = instance.'Meeting Date')`
  (the join is on the **date value**, not on a lookup id — both sides are
  normalised to a `date` before comparison)
* time remaining — `forum.MeetingDuration − Sum(items, TimeRequired)`
* duration choices — `colTimes` (15/30/45/60) capped at the time still available
* approve — `Patch(AgendaItems, …, {Status:"Approved"})`, shown only to
  `APPROVER_EMAILS` (was hard-coded to two addresses in the Power App)
* delete an item — removes its `Documents` rows first, then the item

Reads are pulled whole and filtered in Python rather than with Graph `$filter`.
Filtering on lookup ids and unindexed columns needs the
`HonorNonIndexedQueriesWarningMayFailRandomly` preference and fails
intermittently; these lists are small enough that this is the safer trade.

---

## Local development

```bash
cp .env.example .env          # fill in FABRIC_CLIENT_SECRET
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:8050
```

`ad_access` sees no Posit identity header locally, so it skips the group check
and the app runs normally.

Lilly policy: pip must resolve through **JFrog Artifactory**, not public PyPI.
Set your index once (see Artifactory | Developer Platform Front Door for the URL
and token) before installing.

---

## Posit Connect Vars

Settings → Vars. Nothing here belongs in Git.

```
FABRIC_TENANT_ID     = 18a59a81-eea8-4c30-948a-d8824cdc2580
FABRIC_CLIENT_ID     = 0899ab84-2358-40d5-b82b-4dc1ca82bbcd
FABRIC_CLIENT_SECRET = <secret VALUE, not the secret ID>
SP_HOSTNAME          = collab.lilly.com
SP_SITE_PATH         = /sites/CDDAMeetingMgt
SP_WRITE_ENABLED     = false          # flip to true only after write is granted
APPROVER_EMAILS      = overstreet_kevin@lilly.com,meganfarrell@lilly.com
REQUIRED_AD_GROUP    = <AD group allowed to open the app>
RLS_ADMINS           = <comma-separated admin login ids>
ENVIRONMENT_LABEL    = Development
```

Pasting the secret **ID** instead of the **VALUE** produces
`AADSTS7000215: Invalid client secret`.

Set the app's **Access** to "All users — login required" so Connect populates the
identity header that `ad_access` reads.

---

## Deploy

1. Generate the manifest from **inside** the app folder — the trailing `.` is
   required, and `.env` must not be in the folder or it lands in the bundle:

   ```bash
   rsconnect write-manifest dash --entrypoint app:server --overwrite .
   ```

   Regenerate after **any** file change. Never hand-edit checksums and never
   reuse another app's manifest.

2. Commit and push to the `EliLillyCo` org:

   ```bash
   git init && git add . && git commit -m "CDDA Meeting Manager: Dash port"
   git remote add origin https://github.com/EliLillyCo/<repo>.git
   git push -u origin main
   ```

   Classic PATs are rejected for EliLillyCo repos (403). Use a **fine-grained**
   token issued for the EliLillyCo resource owner, or skip Git and deploy
   directly:

   ```bash
   rsconnect deploy dash --entrypoint app:server \
     --server https://connect-0001.am.lilly.com --api-key <key> .
   ```

3. In Posit Connect: Publish → Import from Git → point at the repo and branch.
4. Set the Vars, set Access, then open the app.

`/health` returns the site id and forum count — a quick way to confirm the Vars
took effect after a deploy.

---

## Known blockers and things to verify

**1. SharePoint writes are currently blocked.** `SVC-DPA-DataPlatform` holds
Sites.Selected **read-only**, so `POST`/`PATCH`/`DELETE` return 403. The app
ships with `SP_WRITE_ENABLED=false`: it renders fully, the mutating controls are
disabled, and a banner explains why — instead of throwing 500s. Two ways
forward, and this is the main decision to make before the app is useful:

* ask the CDDAMeetingMgt site owner to grant the service principal **write** on
  that site, then set `SP_WRITE_ENABLED=true`; or
* keep writes on the existing Power Automate flows, which run under the flow
  owner's connection. For uploads that path is already wired — set
  `UPLOAD_FLOW_URL` to an HTTP-triggered version of
  `CDDAMeetingManager-UploadDocuments` and uploads work without site write.

**2. Person-column shapes.** Graph returns `Speakers` either expanded or as
`SpeakersLookupId` depending on how the column is configured.
`sharepoint_client.person_name()` reads both shapes; confirm against live data
which one this site returns before trusting the presenter names on screen.

**3. Writing a presenter.** Person columns are written by *site user id*, not by
email. `resolve_site_user_id()` queries the hidden User Information List, which
can be refused if it isn't indexed on `EMail`. When it can't resolve, the item
saves without a presenter and says so rather than failing.

**4. Approver identity.** Connect does not always supply an email. `ad_access`
falls back to `<loginid>@lilly.com`; verify that mapping holds in this tenant,
otherwise switch `APPROVER_EMAILS` to login ids and compare against
`get_current_user()`.

**5. The mockup HTML is not servable.** `CDDA_Meeting_Manager_claude_design.html`
is a Claude Design export using that tool's own template syntax (`<sc-for>`,
`<sc-if>`, `{{ }}`). Jinja would try to evaluate every `{{ }}` and throw
`UndefinedError`. Its design decisions were transcribed into `theme.py`; the file
itself is deliberately not in this repo.

---

## Debugging

A 500 or "Internal Server Error" page tells you nothing on its own — it just
means an unhandled exception. The real cause is in the app's **Logs** tab in
Posit Connect:

1. Open Logs. 2. Reload the page to trigger the error. 3. Read the traceback —
it names the file, line and exception. 4. Fix that one cause.

Common signatures here: a missing Var → `os.getenv` returns `None` → the token
call fails; a 403 from Graph → the read-only service principal; a worker timeout
→ raise `timeout` in `gunicorn.conf.py`; stale code after a fix → regenerate the
manifest and redeploy.
