# BURITO_BRAIN storage and recovery

The verified ext4 filesystem is labeled `BURITO_BRAIN`, UUID
`9428a980-24a6-45b2-a0a6-5e057c819406`, mounted at `/mnt/burito-brain`.
The existing `/memory` directory is the SQLite data location; `/manifest` is
available for the portable identity record. See the [migration guide](NEW_LINUX_MIGRATION.md).

## Read-only inspection and integration

The earlier USB 2.0 inspection on 2026-11-26 found a transient 0-byte device,
CRC/read errors and disconnects. That observation was superseded after moving
the drive to a USB 3.0 connection.

The latest host check identifies WDC WD40NPJZ-00CCDT0, serial
`WD-WX12D25FPSS5`, on `/dev/sda1` with 4.00 TB nominal capacity (3.64 TiB).
`findmnt` verifies UUID `9428a980-24a6-45b2-a0a6-5e057c819406`, ext4, and
`rw,noatime` at `/mnt/burito-brain`; `findmnt --verify --verbose` reports zero
errors and warnings. The mount root is burito-owned mode 700. `df` reports
3.6 TiB available. The host kernel reports a SuperSpeed 5 Gbps connection and
successful ext4 read/write mounts. Earlier USB 2.0 CRC errors remain in the
boot log; after the SuperSpeed reconnect, no further read/CRC errors were
observed, though an unsupported discard command was logged during setup.

On 2026-11-27, the owner reported SMART overall health `PASSED`, short and
extended self-tests completed without error, zero reallocated/pending/
uncorrectable sectors and UDMA CRC errors, no logged SMART errors, 33 °C, and
48 power-on hours. These are owner-executed results; this session did not
independently inspect the SMART log or start another test. An earlier Codex
sandbox observation reported the expected brain UUID as read-only. A later
host-scoped check on 2026-11-27 confirmed that this was a sandbox restriction:
both `/home` and `/mnt/burito-brain` are read/write on the physical host. No
mount settings were changed. An authorized scratch test wrote 163,840
synthetic bytes to a unique file, fsynced it, read it back with a matching
SHA-256, removed only that file, and fsynced the mount directory. No existing
file was overwritten. The owner reports a 4 GiB sustained read test passed
and sequential reads measured about 117 MB/s; this session did not repeat that
large read benchmark.

The existing root has `memory/`, `identity/`, `academy/`, `audit/`,
`snapshots/`, `datasets/`, `models/`, `skills/`, `experiments/`, `experience/`,
`workspace/`, `learning/` and `research/`. At initial inspection, `memory/`
and `manifest/` contained no entries; the drive also contains a 1 GiB
`.integrity-test` and checksum file, which were not modified. A version-1 brain
manifest and schema-version-1 SQLite database were created in those existing
directories. After synthetic migration tests passed, the empty live database
was upgraded transactionally to schema 2; the manifest records migration 1 to
2. A read-only check confirmed zero memory rows, schema version 2 and
`integrity_check=ok`. On synthetic data, correction history, conflict review,
deletion, fresh-process retrieval and temporary backup/restore passed. No
private memory content was migrated or inspected. After the continuity check,
six non-personal Academy progress records were deliberately persisted with
test evidence and verified from a fresh process. They do not represent private
conversation memory or neural model training. The configured path reuses
`/memory`; it does not create the previously assumed `/data` directory.

Previously, on 2026-11-26, `lsusb` identified Transcend StoreJet 25H3 (USB ID
`8564:7000`); `lsusb -t` showed it connected through a USB 2.0 path at
480 Mbps. `lsblk` exposed a device-reported serial that SMART did not confirm;
it is omitted because it identifies the physical drive. Capacity remained 0
bytes and no partition, filesystem, UUID or mount appeared.
The kernel log records USB disconnect, failed capacity reads, and a not-ready
device. The device disappeared before `blkid` could inspect it. SMART identity
and health could not be queried because device access requires a sudo password;
no self-test was run. The expected mount path is absent. The conventional local
fallback directory was also absent; only directory metadata was checked. No
private database or disk content was read or changed. The cause of the device
failure is undetermined. Do not use or initialize the transient device; continue
with synthetic storage until the drive has stable capacity and readable metadata.

The default application data path is the existing brain `memory` directory.
Opening it requires the configured filesystem UUID/type and an already-existing,
owned directory; the application does not create a mountpoint or data
directory. SQLite uses a pinned directory descriptor, so a later USB detach
cannot redirect writes into an unmounted placeholder. A changed identity before
open is rejected. `burito doctor` reports brain storage unavailable and does not
report free space from the internal disk as brain capacity. An explicit
`BURITO_DATA_DIR` override is still supported for isolated tests.

`Memory.backup(path)` writes a SQLite online-backup snapshot and an adjacent
owner-only `path.manifest.json` with the database schema, source brain identity
when applicable, creation time, SHA-256 and supported restore schema versions.
`Memory.verify_backup(path)` checks the manifest, private regular-file
permissions, checksum, schema and SQLite integrity through no-follow file
descriptors. A synthetic test restored a snapshot into a separate scratch
database and detected a changed artifact. The checksum detects accidental
corruption; it is not a signature against an attacker able to replace both
files.

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
4. The version-1 manifest and transactional schema migration are implemented.
   Existing rows are preserved; unsupported schema versions fail closed. The
   physical empty database is now version 2. Before importing private records,
   establish an independent backup and tested restore. Missing or changed brain
   identity blocks durable operations; revalidate identity on each open.

## 2026-11-27 release-candidate recheck

Read-only inspection again confirmed `/dev/sda1`, ext4 UUID
`9428a980-24a6-45b2-a0a6-5e057c819406`, and about 3.6 TiB free. The mount was
`ro`; `burito doctor` reported `read_only` and did not open a durable database
for writing. SQLite read-only checks returned schema 2, `integrity_check=ok`,
and six rows, all Academy progress records. No memory text was read. The live
database is 98,304 bytes.

The initial sandbox-only check saw `/home` and `/mnt/burito-brain` as
read-only. See the host-scoped verification below for the actual host state and
backup result. The proposed destination's parent was on the separate NVMe with
about 67 GiB free and had no symlink components.

### 2026-11-27 host-access and independent backup verification

Host-scoped inspection showed `/home` read/write Btrfs on Kingston `nvme0n1p8`
(filesystem UUID `5c077186-8501-4863-9055-2ff6f68980a5`) and BURITO_BRAIN
read/write ext4 on the physically separate WDC `WD40NPJZ-00CCDT0` (`/dev/sda1`,
expected UUID). The backup target's parent resolved without symlinks, was
burito-owned, and had about 67 GiB free. With owner approval,
`/home/burito/.local/share/burito-backups` was created mode 700. It is on the
separate NVMe, not the brain HDD.

`Memory.backup` produced
`/home/burito/.local/share/burito-backups/brain-20261127T160923.sqlite3`
(98,304 bytes, mode 600) and its owner-only manifest. The manifest checksum,
schema v2, brain UUID and SQLite integrity all verified. The live database
contains six Academy progress records and no other memory categories; no
record content was read or printed. An isolated scratch restore on the NVMe
passed SQLite integrity/schema checks, preserved all six Academy rows, and
passed synthetic fresh-process retrieval, project continuity, correction and
deletion checks. The live database was not overwritten. This verifies a backup
and restore path but is not a substitute for a second off-machine copy; the
backup remains exposed to host-level failure.

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
