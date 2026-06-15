Part A — Database Schema (copy your models)
Users, Groups, GroupMembers,
Expenses, ExpenseSplits,
Settlements, ImportBatch, ImportAnomaly

Part B — All 18 Anomalies (you already have these from my analysis)

ANOMALY 1 — EXACT DUPLICATE
Rows affected: 3 and 4
What it is: "Dinner at Marina Bites" logged twice, same date/payer/amount
How detected: Case-insensitive match on date + paid_by + amount
Policy chosen: Keep row 3, flag row 4 for approval before deletion
Why: Meera explicitly requested approval before any deletion
