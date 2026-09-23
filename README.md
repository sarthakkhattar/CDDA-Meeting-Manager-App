# CDDA Meeting Manager

A Python Dash application for managing CDDA meeting agendas, approvals, and scheduling. Deployed on **Posit Connect** as a `python-dash` app with data stored in **Microsoft Fabric Lakehouse** (Delta tables).

---

## Features

- **Two meeting forums**: CDDA Open Office Hours and Clinical Design & Statistics Review
- **Calendar sidebar** with meeting dates highlighted, month navigation, and click-to-add/remove dates
- **Agenda management** with status badges (Pending / Approved / Rejected)
- **Role-based UI**: admins see Archive, Restore, and Manage Dates; approvers see Approve
- **Soft-delete archive** with restore capability
- **Date management**: recurring schedule generator, manual date picker, calendar click-to-add/remove
- **Time budget tracker** with progress bar per meeting instance
- **Document attachment display** linked to agenda items

---

## Architecture

```
Browser  -->  Posit Connect (python-dash)  -->  Microsoft Fabric Lakehouse
                   |                                   |
                app.py (Dash)                   Delta tables via deltalake
                config.py                       (authenticated with service principal)
                fabric_graph.py
```

**Auth**: User identity comes from Posit Connect headers (`RStudio-Connect-Credentials`). For local development, `DEV_USER_EMAIL` overrides this.

**Roles** (comma-separated emails in env vars):
- `RLS_ADMINS` -- admin access (archive, restore, manage dates)
- `APPROVER_EMAILS` -- approver access (approve/reject agenda items)

---

## Data Model

Five Delta tables in a Fabric Lakehouse:

| Table | Purpose |
|-------|---------|
| `cdda_meetings` | Meeting forums (title, description, duration, owner) |
| `meeting_instances` | Scheduled dates per forum (date, display text, availability) |
| `agenda_items` | Agenda rows with status, time required, speakers (soft-delete via status) |
| `documents` | File attachments linked to agenda items |
| `approvals` | Approval/rejection records with timestamps |

All table access goes through `fabric_graph.py`, which reads and writes Delta tables using the `deltalake` library with Azure service principal authentication.

---

## Repository Layout

| File | Purpose |
|------|---------|
| `app.py` | Dash layout, callbacks, calendar views, role-based UI |
| `config.py` | All env-driven settings (Fabric connection, roles, feature flags) |
| `fabric_graph.py` | Fabric Lakehouse data layer (Delta table CRUD) |
| `fabric_setup.py` | Fabric notebook to create and seed all five tables |
| `requirements.txt` | Python dependencies |
| `manifest.json` | Posit Connect deployment manifest |
| `make_manifest.py` | Generates `manifest.json` |
| `.env.example` | Template for local development |
| `test_features.py` | Automated test suite (56 tests) |

Deploy entrypoint: **`app:server`**, app mode **python-dash**.

---

## Fabric Notebook Setup

`fabric_setup.py` is a notebook intended to run inside a Microsoft Fabric environment. It creates the Lakehouse and seeds the five Delta tables with the correct schemas. Run it once when setting up a new environment:

1. Open a Fabric workspace and create a new Lakehouse (or use an existing one).
2. Import `fabric_setup.py` as a notebook in the workspace.
3. Run it -- it will create the `cdda_meetings`, `meeting_instances`, `agenda_items`, `documents`, and `approvals` tables under `/Tables/dbo/`.
4. Note the **Workspace ID** and **Lakehouse ID** from the Fabric URL for your env vars.

Tables are accessed at the path pattern:
```
abfss://<workspace_id>@onelake.dfs.fabric.microsoft.com/<lakehouse_id>/Tables/dbo/<table_name>
```

---

## Local Development

```bash
cp .env.example .env
# Set DEMO_MODE=1 and DEV_USER_EMAIL=your.email@lilly.com
pip install -r requirements.txt
python app.py                  # http://127.0.0.1:8050
```

With `DEMO_MODE=1`, the app uses built-in sample data and does not require Fabric credentials.

With `DEMO_MODE=0`, fill in the Fabric credentials in `.env` to connect to a live Lakehouse.

---

## Environment Variables

Set these in Posit Connect under Settings > Vars (never commit secrets to Git):

| Variable | Description |
|----------|-------------|
| `FABRIC_WORKSPACE_ID` | Fabric Lakehouse workspace GUID |
| `FABRIC_LAKEHOUSE_ID` | Fabric Lakehouse GUID |
| `FABRIC_CLIENT_ID` | Azure service principal client ID |
| `FABRIC_CLIENT_SECRET` | Azure service principal client secret (the value, not the secret ID) |
| `FABRIC_TENANT_ID` | Azure AD tenant GUID |
| `DEMO_MODE` | `1` for demo data, `0` for live Fabric connection |
| `DEV_USER_EMAIL` | Override user identity for local dev or Posit workaround |
| `RLS_ADMINS` | Comma-separated admin emails |
| `APPROVER_EMAILS` | Comma-separated approver emails |
| `APP_ENVIRONMENT` | `Development` or `Production` |

---

## Deployment

The app is deployed to Posit Connect via the **bundle upload API** (git-based deploy is not used because the Connect server lacks network access to GitHub).

Steps:

1. Generate the manifest:
   ```bash
   python make_manifest.py
   ```

2. Create the deployment bundle:
   ```bash
   tar -czf cdda-bundle.tar.gz app.py config.py fabric_graph.py requirements.txt manifest.json
   ```

3. Upload and deploy via the Posit Connect API:
   ```bash
   # Upload bundle
   curl -X POST "https://<connect-server>/__api__/v1/content/<guid>/bundles" \
     -H "Authorization: Key <api-key>" \
     -F "archive=@cdda-bundle.tar.gz"

   # Deploy the uploaded bundle
   curl -X POST "https://<connect-server>/__api__/v1/content/<guid>/deploy" \
     -H "Authorization: Key <api-key>" \
     -H "Content-Type: application/json" \
     -d '{"bundle_id": "<bundle-id-from-upload>"}'
   ```

4. Set the environment variables in Posit Connect and verify the app loads.

---

## Debugging

App errors surface in the **Logs** tab within Posit Connect:

1. Open the content's Logs tab.
2. Reload the app to trigger the error.
3. Read the traceback for the file, line, and exception.

Common issues:
- Missing env var -- `os.getenv` returns `None`, token call fails
- Wrong secret -- pasting the secret **ID** instead of the **VALUE** gives `AADSTS7000215`
- Stale bundle -- regenerate the manifest and redeploy after any file change
