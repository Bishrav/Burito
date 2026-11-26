# BURITO_BRAIN storage and recovery

The migration guide records an ext4 filesystem labeled `BURITO_BRAIN` with
UUID `ce024ab9-6884-4482-afdd-edbe189ebcf2` and expected mount
`/mnt/burito-brain`. Its existing `data` directory is the private brain.
The expected identity is recorded configuration. Confirm it against hardware
before use. See the [migration guide](NEW_LINUX_MIGRATION.md).

## Read-only inspection and integration

On 2026-11-26 the checkout was on internal Btrfs with about 73 GiB available.
`lsblk` showed internal NVMe and zram only, and there was no dedicated mount at
`/mnt/burito-brain`. The Windows NTFS partitions were unmounted. The Transcend
model, filesystem, contents, capacity and health could not be verified live.
Use only isolated temporary conversations until the volume is attached.

1. Inspect `lsblk`, filesystem UUIDs and exact mount sources with `findmnt`.
   Match the physical device, capacity, filesystem and expected UUID; reject a
   fallback directory on internal storage or an unexpected device. Read the
   filesystem metadata, top-level layout, available capacity and existing Burito
   config before opening a database. Do not change mounts, boot settings,
   partitions, formatting or ownership during inspection.
2. If the drive needs mounting, get approval for the verified device and
   use a read-only inspection procedure appropriate for the filesystem first.
   Collect read-only health data with SMART tooling where the USB bridge supports
   it. Do not install tooling or start a long drive self-test without approval.
3. Inventory existing database and model locations without reading private
   content into logs. Establish an independent backup and test restore into
   scratch. Benchmark bounded sequential reads and SQLite read latency on existing
   approved test data; benchmark writes only in an explicitly approved scratch
   area on the verified drive. Record capacity, workload and caching conditions.
4. Add a portable manifest and schema checks before publishing any migration.
   Leave existing data in place. Validate each transactional copy and its
   checksums, switch configuration only after verification, and keep rollback.
   If the device is missing or disappears, block durable operations and offer
   clearly labeled temporary mode. Revalidate identity on reconnect.

## Durable library and fast runtime

Use the HDD for durable conversation archives, memory and preferences, research
and education, model weights, datasets, embeddings as artifacts, adapters and
checkpoints, evaluated skills and experiences, audit metadata, evaluations and
snapshots. Keep volatile Eve state and latency-sensitive caches/indexes on NVMe
only where measurements justify it. Make cache invalidation and durable writes
explicit. Avoid duplicating model weights. Phase 2 keeps private transcripts
outside Git and separate from the existing brain; migration belongs to Phase 3.
Keep conversation, artifact and user-memory access independently scoped.

A versioned manifest should record a unique brain ID, disk identity, storage
and database schema versions, compatible runtimes, model references, artifact
checksums, migration steps and recovery procedures. Database operations use
transactions, owner-only permissions, an integrity check and a consistent backup
mechanism. Plan encryption at rest and key recovery separately before migrating
private data. Test clean shutdown, sudden disconnection, interrupted migration,
corruption detection, export/import, rollback and independent restore.
A snapshot on the same disk has value for rollback and cannot survive disk loss.
