# Teaching Burito together

The owner supplies personal context and corrects preferences; development adds
curated general lessons, references, examples, and evaluation tasks. Installing
lessons stores knowledge locally. It does not change model weights, prove
understanding, or make an assistant an expert in every field.

## Begin at home

```bash
python3 -m burito school list
python3 -m burito school install
python3 -m burito school lesson home.honesty
python3 -m burito school status
```

The default installation loads three home lessons: honest reasoning,
communication, and gradual learning. These live in a separate knowledge table,
not in personal facts. Existing database backups include both tables.

## Progress to school

The initial catalog contains eleven small lessons covering home foundations,
IT, health literacy, mathematics, scientific reasoning, budgeting, and civics.
Each has notes, prerequisite lessons, provenance, and open-ended review prompts.
Sources distinguish externally checked documentation from original project
policies and elementary exercises. Links are references; installation does not
download entire websites, textbooks, or updates.

```bash
python3 -m burito school lesson health.sources
python3 -m burito school install --stage school
```

School installation includes prerequisite home lessons. Repeating installation
does not duplicate references. Changed content requires a newer lesson revision;
upgrades are explicit, not automatic. Review prompts are currently for manual
use. No model has answered or passed them yet.

## College and specialization (planned)

Expand one topic at a time: Linux, networking, programming, databases,
cybersecurity in authorized labs, engineering, biological sciences, economics,
agriculture, education, and creative work. Add domain-specific sources before
claiming coverage. A source list alone is not a completed course.

The prepared chat bridge reads one installed lesson at a time. After AI chat
works and the bridge is verified, evaluate explanations
and novel practice tasks, record mistakes separately, and revisit weak areas.
Do not automatically count a lesson as understood because the model says so.
Use held-out tasks and owner/domain-expert review when the stakes justify it.

For health, start with terminology and judging information using
[MedlinePlus](https://medlineplus.gov/evaluatinghealthinformation.html).
Medical learning here is educational; patient-specific diagnosis, prescribing,
and treatment changes are not taught as autonomous tasks. Legal and financial
decisions similarly require current, relevant evidence and appropriate expertise.

There is no background teaching service or autonomous self-training in this
milestone. We add lessons during development; the owner can teach personal
facts with `teach` or `remember`. Neither silently expands action permissions.

After reviewing a suggestion, owner feedback can be saved separately from
personal facts:

```bash
python3 -m burito feedback add useful "The next step matched my current task."
python3 -m burito feedback add correction "Ask about project goals before inferring them."
python3 -m burito feedback list
python3 -m burito feedback forget FEEDBACK_ID
```

An ordinary chat can receive these notes only with `--include-feedback`.
Activity-only chats do not receive them. Burito never writes feedback from its
own suggestions, and storing a note does not update model weights.
