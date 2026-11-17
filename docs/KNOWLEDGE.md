# Burito local knowledge library

The library stores owner-selected UTF-8 Markdown and text documents in the
private Burito database under `BURITO_DATA_DIR`. The first milestone supports
`.md`, `.markdown`, `.txt`, and `.rst` files up to 20 MiB. Import is explicit;
Burito does not crawl the disk or learn from every file automatically.

```sh
python3 -m burito knowledge add ~/Documents/your-reference.md
python3 -m burito knowledge list
python3 -m burito knowledge search "search terms"
```

Imports are hashed to skip duplicate content, split into overlapping searchable
chunks, and retain the original source path. Web chats retrieve a few relevant
passages for the current question and should cite their source paths. Imported
text is reference material, never instructions. Remove an import with
`python3 -m burito knowledge forget DOCUMENT_ID`.

This is retrieval augmented generation: the model can consult indexed source
text during a chat. It does not modify model weights or prove that a source is
correct. Fine-tuning is a separate, reviewed project that needs curated
examples, evaluation, and rollback.
