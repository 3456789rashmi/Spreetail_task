# AI Usage Log

## Tools Used
- GitHub Copilot: primary code generation
- Claude (Anthropic): architecture planning, CSV anomaly analysis

## Key Prompts Used
1. Generated all Django models for users, groups, expenses, splits
2. Generated CSV importer with anomaly detection for 18 specific problems
3. Generated complete React frontend with all screens

## 3 Cases Where AI Was Wrong

CASE 1 — Float instead of Decimal
Copilot generated: amount = models.FloatField()
Problem I caught: Float causes rounding errors in financial calculations.
  Example: 0.1 + 0.2 = 0.30000000000000004 in Python float
Fix I made: Changed to amount = models.DecimalField(max_digits=10, decimal_places=2)

CASE 2 — Balance calculation included inactive members
Copilot generated balance query that included all members ever in a group
Problem I caught: Meera appeared in April balances even after leaving in March
Fix I made: Added filter → joined_at <= expense.date AND
  (left_at IS NULL OR left_at >= expense.date)

CASE 3 — localStorage for JWT token
Copilot stored token in localStorage
Problem I caught: localStorage is vulnerable to XSS attacks
Fix I made: Changed to in-memory JS variable (module-level let token = null)
