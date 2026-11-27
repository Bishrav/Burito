# Private owner glossary

The glossary stores owner-defined meanings separately from general reference
material. It lives in the same private SQLite database as Burito memory and is
not committed to the repository.

When a term is unclear, Burito should ask what it means instead of guessing.
After the owner explains, it should restate the meaning and ask whether to save
it. The `remember_definition` tool always requests Eve approval before writing
to the glossary. Approving a tool call is the final confirmation to store the
shown term and definition. Definitions are attributed to the owner and are not
treated as universal facts.

Private glossary retrieval is included when chat opts in to personal memory
with `--include-personal`. Manage records from the project root:

```sh
BURITO_DATA_DIR=/mnt/burito-brain/memory python3 -m burito glossary list
BURITO_DATA_DIR=/mnt/burito-brain/memory python3 -m burito glossary search "term in a question"
BURITO_DATA_DIR=/mnt/burito-brain/memory python3 -m burito glossary define "term" "owner-approved meaning" --source owner
BURITO_DATA_DIR=/mnt/burito-brain/memory python3 -m burito glossary forget RECORD_ID
```

The `define` command is an explicit owner action. Do not use it to store a
definition supplied by the model or inferred from context.
