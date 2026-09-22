"""
CDDA Meeting Manager — Manual UI Test Checklist
=================================================

BEFORE YOU START:
  1. Add these to your .env file:
       DEV_USER_EMAIL=sarthak.khattar@lilly.com
       RLS_ADMINS=sarthak.khattar@lilly.com
       APPROVER_EMAILS=sarthak.khattar@lilly.com
       DEMO_MODE=1

  2. Restart the app:  python app.py

  3. Open http://localhost:8050

=================================================
TEST 1: USER IDENTITY
=================================================
[ ] Status bar shows: "Connected — 2 forum(s) loaded (Demo Mode) | sarthak.khattar@lilly.com (Admin)"
[ ] Your email and "(Admin)" role appear in the status bar

=================================================
TEST 2: ADMIN FEATURES ON HOME SCREEN
=================================================
[ ] Each forum card has a "⚙ Manage Dates" button below it
[ ] The button is styled as an outline (border, not filled)

=================================================
TEST 3: STATUS BADGES
=================================================
[ ] Click "CDDA Open Office Hours" → select "07 Jan 2026"
[ ] Each agenda item shows a colored "Pending" badge (amber/yellow)
[ ] Badges appear next to the title

=================================================
TEST 4: CONDITIONAL BUTTONS
=================================================
[ ] Each item shows "✓ Approve" (green) — you're an approver
[ ] Each item shows "📦 Archive" (amber) — you're an admin
[ ] The old "✕ Delete" (red) button is GONE

=================================================
TEST 5: APPROVE AN ITEM
=================================================
[ ] Click "✓ Approve" on "Request Intake Walkthrough"
[ ] The item's badge changes from "Pending" to "Approved" (green)
[ ] The "✓ Approve" button disappears (item is already approved)
[ ] The "📦 Archive" button remains

=================================================
TEST 6: ARCHIVE (SOFT DELETE)
=================================================
[ ] Click "📦 Archive" on an item
[ ] The item disappears from the main list
[ ] The sidebar count decreases by 1
[ ] The time used decreases

=================================================
TEST 7: ARCHIVE SECTION
=================================================
[ ] Below the agenda items, you see "📦 Show Archive (N)"
[ ] N should be >= 1 (the demo has 1 archived item for 07 Jan)
[ ] Click "📦 Show Archive" — archived items appear in a muted style
[ ] Each archived item has a "↩ Restore" button (purple)
[ ] The button text changes to "📦 Hide Archive"

=================================================
TEST 8: RESTORE FROM ARCHIVE
=================================================
[ ] Click "↩ Restore" on an archived item
[ ] The item disappears from the archive section
[ ] It reappears in the main agenda list with "Pending" status
[ ] Archive count decreases

=================================================
TEST 9: DATE MANAGEMENT — OPEN/CLOSE
=================================================
[ ] Go back to Forums (← Back to Forums)
[ ] Click "⚙ Manage Dates" on any forum
[ ] The date management view opens showing:
      - "Manage Meeting Dates" heading
      - "← Back to Forums" button
      - "Current Meeting Dates" with existing dates listed
      - "Add Recurring Schedule" form
      - "Add Single Date" form
[ ] Click "← Back to Forums" — returns to forum list

=================================================
TEST 10: DATE MANAGEMENT — ADD SINGLE DATE
=================================================
[ ] Open Manage Dates for "CDDA Open Office Hours"
[ ] In "Add Single Date", pick a date (e.g., Feb 15 2026)
[ ] Click "Add Date"
[ ] Success message: "✓ Date 15 Feb 2026 added!"
    (Note: in Demo Mode, the list won't update since demo data is hardcoded.
     This will work in Live mode with actual Fabric tables.)

=================================================
TEST 11: DATE MANAGEMENT — RECURRING SCHEDULE
=================================================
[ ] In "Add Recurring Schedule":
      - Day of Week: select "Wednesday"
      - Start Date: pick Jan 1, 2026
      - End Date: pick Mar 31, 2026
[ ] Click "Generate Dates"
[ ] Success message: "✓ N date(s) added!" (should be ~13 Wednesdays)

=================================================
TEST 12: DATE MANAGEMENT — DELETE DATE
=================================================
[ ] Each date in "Current Meeting Dates" has a "🗑 Remove" button
[ ] Click "🗑 Remove" on a date
    (In Demo Mode, the deletion succeeds but the list is hardcoded
     so it won't visually remove. Works in Live mode.)

=================================================
TEST 13: NON-ADMIN VIEW (remove yourself from RLS_ADMINS)
=================================================
To test what non-admins see:
  1. Change .env:  RLS_ADMINS=someone.else@lilly.com
  2. Keep:         APPROVER_EMAILS=sarthak.khattar@lilly.com
  3. Restart app

[ ] "⚙ Manage Dates" buttons are GONE from forum cards
[ ] "📦 Archive" buttons are GONE from agenda items
[ ] "📦 Show Archive" section is GONE
[ ] "✓ Approve" buttons still appear (you're still an approver)

=================================================
TEST 14: NON-APPROVER VIEW (remove yourself from APPROVER_EMAILS)
=================================================
  1. Change .env:  APPROVER_EMAILS=someone.else@lilly.com
  2. Keep:         RLS_ADMINS=sarthak.khattar@lilly.com
  3. Restart app

[ ] "✓ Approve" buttons are GONE
[ ] "📦 Archive" buttons still appear (you're still admin)
[ ] "⚙ Manage Dates" still appears

=================================================
TEST 15: ANONYMOUS VIEW (clear DEV_USER_EMAIL)
=================================================
  1. Change .env:  DEV_USER_EMAIL=
  2. Restart app

[ ] Status bar shows no email/role
[ ] No Approve, Archive, or Manage Dates buttons
[ ] You can still VIEW agenda items
[ ] Adding items shows "Authentication required" error
"""
