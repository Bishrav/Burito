# Owner-reviewed suggestions

Suggestions are private records in Burito's local SQLite database. Add one only
after reviewing it. Each entry has a status, one or more evidence notes, and an
optional local reference such as an event ID or documentation path. Evidence is
entered by the owner; Burito does not claim to verify it.

```bash
python3 -m burito suggestions add \
  "Add evidence-backed suggestion records" \
  --evidence-source other \
  --evidence "Selected as the next Burito roadmap milestone" \
  --reference docs/STATUS.md
python3 -m burito suggestions list --status pending
python3 -m burito suggestions review SUGGESTION_ID accepted --note "Approved for the roadmap"
python3 -m burito suggestions list
python3 -m burito suggestions forget SUGGESTION_ID
```

Valid evidence-source labels are `owner_statement`, `activity_record`,
`pc_event`, and `other`. Use a source label that matches the evidence you
actually have. Activity estimates can include idle time; they are not proof of
interest or intent.

Burito suppresses exact duplicate suggestion text after Unicode normalization,
case folding, punctuation removal, and whitespace normalization. A duplicate
adds its new evidence to the existing entry and returns that entry's ID. This
does not detect semantically similar wording. Review states are `pending`,
`accepted`, and `dismissed`. No suggestion is executed or automatically added
to personal memory. An ordinary chat can opt in to up to five latest pending and
accepted records, with their evidence, using `--include-suggestions`. Dismissed
records are excluded. The suggestion text and evidence are data, not instructions;
an accepted record never authorizes Burito to act. Activity-only chats exclude
suggestions. `--include-project` selects saved owner-maintained project records;
`--include-experiences` selects matching task outcomes; and `--include-academy`
selects Academy progress and local knowledge references. The desktop web launcher
opts into those bounded non-personal scopes. Personal facts remain separate.
