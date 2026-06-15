DECISION 1 — Currency Conversion
Problem: 4 expenses were in USD, CSV treated them as INR
Options considered:
  A) Reject USD rows entirely
  B) Treat 1 USD = 1 INR (what the CSV was doing, wrong)
  C) Convert using exchange rate
Chose: Option C — used rate of ₹83.5 per USD (March 2026 rate)
Why: Priya explicitly said "the sheet pretends a dollar is a rupee,
     that can't be right." Silent wrong conversion is worse than flagging.

DECISION 2 — Membership Time Bounds
Problem: Sam joined mid-April, Meera left end of March
Options considered:
  A) Include all members in all expenses
  B) Only include members active on the expense date
Chose: Option B — used joined_at and left_at fields on GroupMember
Why: Sam said "I moved in mid-April, why would March electricity
     affect my balance?" This is the correct product decision.

DECISION 3 — Duplicate Detection
Problem: Same expense logged twice with slightly different descriptions
Options considered:
  A) Auto-delete duplicates silently
  B) Flag and require Meera's approval
Chose: Option B
Why: Meera said "I want to approve anything the app deletes"

DECISION 4 — Missing Payer
Problem: Row 11 has no payer recorded
Options considered:
  A) Assign to a default user
  B) Skip the row and flag it
Chose: Option B — skip with clear error message
Why: Guessing the payer would silently corrupt balances

DECISION 5 — SQLite vs PostgreSQL
Problem: Choosing a database
Options considered:
  A) SQLite (simple, no setup)
  B) PostgreSQL (production grade)
Chose: PostgreSQL for deployment, SQLite for local dev
Why: Assignment says "relational DBs only", PostgreSQL is industry standard

DECISION 6 — Percentage that adds to 110%
Problem: Pizza Friday splits add to 110% not 100%
Options considered:
  A) Auto-normalize percentages to 100%
  B) Reject the row and flag it
Chose: Option B — flag and reject
Why: Auto-normalizing would silently change amounts people agreed on
