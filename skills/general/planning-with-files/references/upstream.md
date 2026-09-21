# Upstream attribution

- Project: [https://github.com/OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files).
- Skill path: `.agents/skills/planning-with-files`.
- Requested ref: `2fbbd77ba9a74cddb9504285935ef9ae0837cdec`.
- Fixed commit: [2fbbd77ba9a74cddb9504285935ef9ae0837cdec](https://github.com/OthmanAdi/planning-with-files/tree/2fbbd77ba9a74cddb9504285935ef9ae0837cdec).
- Upstream version: 3.20.0.
- Local version: 1.1.0.
- License: [MIT](LICENSE).

## Local adaptations

- Adapted the three-file workflow into concise portable instructions with only name and description in frontmatter.
- Copied three upstream templates unchanged into assets/templates and retained the MIT license unchanged.
- Replaced upstream shell scripts with a locally maintained Python helper for init, list, resolve, and check; this is not an upstream CLI replacement.
- Excluded lifecycle hooks, plugin commands, transcript recovery, attestation, autonomous continuation, and host settings changes.
- Kept task-specific plans separate from project milestones; required explicit selection for multiple plans without a shared active pointer.
- Migrated the initial hand-maintained provenance to the unified external-source metadata and generated citations.

## Provenance

[upstream.json](upstream.json) records original upstream SHA-256 hashes and the separately tracked local file hashes. Local versions are independent of upstream versions. Offline validation checks local integrity and generated citations; it does not re-fetch upstream files.
