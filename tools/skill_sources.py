"""Pinned GitHub skill imports and offline provenance validation (stdlib only)."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request


START = "<!-- skillctl:external-sources:start -->"
END = "<!-- skillctl:external-sources:end -->"
GENERATED = {"references/upstream.json", "references/upstream.md"}
SHA = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
REPO = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\Z")


class SourceError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise SourceError("source paths must be non-empty relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
        raise SourceError("unsafe source path: " + value)
    return value


def clean_text(value, label):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n|"):
        raise SourceError(label + " must be non-empty single-line text without table delimiters")
    return value


def local_files(source):
    files = {}
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise SourceError("external skill must not contain symlinks")
        if path.is_file():
            name = path.relative_to(source).as_posix()
            if name not in GENERATED:
                files[name] = digest(path.read_bytes())
    return files


def metadata(source):
    try:
        data = json.loads((source / "references/upstream.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SourceError("missing or invalid references/upstream.json: " + str(exc)) from exc
    fields = {"format_version", "repository", "requested_ref", "commit", "skill_path",
              "upstream_version", "license", "files", "local_files", "adaptations"}
    if not isinstance(data, dict) or set(data) != fields or data["format_version"] != 1:
        raise SourceError("invalid upstream metadata fields or format_version")
    if not isinstance(data["repository"], str) or not REPO.fullmatch(data["repository"]):
        raise SourceError("repository must be a canonical GitHub HTTPS URL")
    if not isinstance(data["commit"], str) or not SHA.fullmatch(data["commit"]):
        raise SourceError("upstream commit must be a full 40-character SHA")
    clean_text(data["requested_ref"], "requested_ref")
    safe_path(data["skill_path"])
    if data["upstream_version"] is not None:
        clean_text(data["upstream_version"], "upstream_version")
    license_info = data["license"]
    if not isinstance(license_info, dict) or set(license_info) != {"id", "local_path"}:
        raise SourceError("license must identify its id and retained local_path")
    clean_text(license_info["id"], "license id")
    safe_path(license_info["local_path"])
    if not isinstance(data["adaptations"], list) or not data["adaptations"]:
        raise SourceError("adaptations must record the local changes")
    for note in data["adaptations"]:
        clean_text(note, "adaptation")
    if not isinstance(data["files"], list) or not data["files"]:
        raise SourceError("upstream file records are required")
    seen = set()
    for item in data["files"]:
        if not isinstance(item, dict) or set(item) != {"upstream_path", "local_path", "sha256"}:
            raise SourceError("invalid upstream file record")
        safe_path(item["upstream_path"])
        safe_path(item["local_path"])
        if item["local_path"] in seen:
            raise SourceError("duplicate upstream file destination")
        seen.add(item["local_path"])
        if not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"]):
            raise SourceError("invalid upstream file checksum")
    if license_info["local_path"] not in seen:
        raise SourceError("retained license must have an upstream file record")
    if not isinstance(data["local_files"], dict) or "SKILL.md" not in data["local_files"]:
        raise SourceError("local file checksums must include SKILL.md")
    for name, value in data["local_files"].items():
        safe_path(name)
        if name in GENERATED or not isinstance(value, str) or not HASH.fullmatch(value):
            raise SourceError("invalid local file checksum")
    return data


def citation(entry, data):
    version = data["upstream_version"] or "Not declared"
    repo, commit = data["repository"], data["commit"]
    lines = ["# Upstream attribution", "", f"- Project: [{repo}]({repo}).",
             f"- Skill path: `{data['skill_path']}`.",
             f"- Requested ref: `{data['requested_ref']}`.",
             f"- Fixed commit: [{commit}]({repo}/tree/{commit}).",
             f"- Upstream version: {version}.", f"- Local version: {entry['version']}.",
             f"- License: [{data['license']['id']}]({Path(data['license']['local_path']).name}).",
             "", "## Local adaptations", ""]
    lines.extend("- " + note for note in data["adaptations"])
    lines.extend(["", "## Provenance", "",
                  "[upstream.json](upstream.json) records original upstream SHA-256 hashes and the separately tracked local file hashes. Local versions are independent of upstream versions. Offline validation checks local integrity and generated citations; it does not re-fetch upstream files.", ""])
    return "\n".join(lines)


def table(root, registry):
    lines = [START, "| Skill | Upstream | Upstream version | Commit | Local version | License |",
             "|---|---|---|---|---|---|"]
    for entry in registry["skills"]:
        if entry.get("origin") != "external":
            continue
        data = metadata(root / entry["source"])
        repo, commit = data["repository"], data["commit"]
        label = repo[len("https://github.com/"):]
        lines.append(f"| [{entry['name']}]({entry['source']}/SKILL.md) | [{label}]({repo}) | "
                     f"{data['upstream_version'] or 'Not declared'} | [{commit[:12]}]({repo}/tree/{commit}) | "
                     f"{entry['version']} | {data['license']['id']} |")
    return "\n".join(lines + [END])


def readme_text(root, registry):
    text = (root / "README.md").read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise SourceError("README must contain one ordered external-sources marker pair")
    start, end = text.index(START), text.index(END) + len(END)
    return text[:start] + table(root, registry) + text[end:]


def generate(root, registry):
    for entry in registry["skills"]:
        if entry.get("origin") == "external":
            source = root / entry["source"]
            (source / "references/upstream.md").write_text(citation(entry, metadata(source)), encoding="utf-8")
    (root / "README.md").write_text(readme_text(root, registry), encoding="utf-8")


def validate(root, registry):
    errors = []
    for entry in registry["skills"]:
        source = root / entry["source"]
        if entry.get("origin") != "external":
            if (source / "references/upstream.json").exists():
                errors.append(entry["name"] + ": provenance requires origin: external in registry")
            continue
        try:
            data = metadata(source)
            if local_files(source) != data["local_files"]:
                raise SourceError("local checksums differ; review changes, bump version, then run provenance --refresh")
            lic = data["license"]["local_path"]
            original = next(item["sha256"] for item in data["files"] if item["local_path"] == lic)
            if data["local_files"].get(lic) != original:
                raise SourceError("retained license differs from its upstream checksum")
            if (source / "references/upstream.md").read_text(encoding="utf-8") != citation(entry, data):
                raise SourceError("generated upstream.md is stale; run provenance")
        except (SourceError, OSError) as exc:
            errors.append(entry["name"] + ": " + str(exc))
    try:
        if (root / "README.md").read_text(encoding="utf-8") != readme_text(root, registry):
            errors.append("README external-sources table is stale; run provenance")
    except (SourceError, OSError) as exc:
        errors.append(str(exc))
    return errors


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "agent-skills-import"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(8 * 1024 * 1024 + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise SourceError("cannot fetch " + url + ": " + str(exc)) from exc
    if len(data) > 8 * 1024 * 1024:
        raise SourceError("upstream response exceeds 8 MiB limit")
    return data


def scalar(frontmatter, key):
    match = re.search(r"^" + re.escape(key) + r":\s*(.*?)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return None
    value = match.group(1)
    if value in {"|", ">", "|-", ">-", "", "null", "~"}:
        raise SourceError(key + " must be a single-line scalar; adapt this skill manually")
    if value.startswith('"'):
        try:
            return json.loads(value)
        except ValueError as exc:
            raise SourceError("unsupported quoted " + key) from exc
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def prepare_import(args):
    repo = args.repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not REPO.fullmatch(repo):
        raise SourceError("import currently supports GitHub HTTPS repositories only")
    path = safe_path(args.path)
    license_path = safe_path(args.license_path)
    clean_text(args.ref, "ref")
    api = "https://api.github.com/repos/" + repo[len("https://github.com/"):]
    commit = json.loads(fetch(api + "/commits/" + urllib.parse.quote(args.ref, safe="")))["sha"]
    if not SHA.fullmatch(commit):
        raise SourceError("upstream did not return a full commit SHA")
    tree = json.loads(fetch(api + "/git/trees/" + commit + "?recursive=1"))
    if tree.get("truncated"):
        raise SourceError("upstream tree is truncated; cannot safely import a partial skill")
    selected = {}
    prefix = path + "/"
    for item in tree["tree"]:
        name = item["path"]
        if not name.startswith(prefix) and name != license_path:
            continue
        if item["type"] == "tree":
            continue
        if item["type"] != "blob" or item.get("mode") not in {"100644", "100755"}:
            raise SourceError("symlinks and submodules cannot be imported: " + name)
        local = "references/LICENSE" if name == license_path else name[len(prefix):]
        safe_path(local)
        if local in selected or local in GENERATED:
            raise SourceError("upstream path collides with generated provenance: " + local)
        selected[local] = item
    if "SKILL.md" not in selected or "references/LICENSE" not in selected:
        raise SourceError("skill or selected license file is missing at the pinned commit")
    files, records = {}, []
    raw = repo.replace("https://github.com/", "https://raw.githubusercontent.com/") + "/" + commit + "/"
    for local, item in sorted(selected.items()):
        data = fetch(raw + urllib.parse.quote(item["path"], safe="/"))
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != item["sha"]:
            raise SourceError("download differs from pinned Git blob: " + item["path"])
        files[local] = (data, int(item["mode"], 8) & 0o777)
        records.append({"upstream_path": item["path"], "local_path": local, "sha256": digest(data)})
    text = files["SKILL.md"][0].decode("utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SourceError("upstream SKILL.md lacks frontmatter")
    frontmatter = match.group(1)
    name, description = scalar(frontmatter, "name"), scalar(frontmatter, "description")
    if not name or not re.fullmatch(r"[a-z0-9-]{1,64}", name) or not description:
        raise SourceError("invalid upstream skill name or description")
    license_id = args.license_id or scalar(frontmatter, "license")
    if not license_id:
        raise SourceError("license is not declared; review the license and pass --license-id")
    clean_text(license_id, "license id")
    attribution = ("\n\n## Attribution\n\nSee [upstream source and adaptations](references/upstream.md), "
                   "[pinned provenance](references/upstream.json), and the [license](references/LICENSE).\n")
    adapted = "---\nname: " + name + "\ndescription: " + description + "\n---\n" + text[match.end():].rstrip() + attribution
    files["SKILL.md"] = (adapted.encode("utf-8"), files["SKILL.md"][1])
    data = {"format_version": 1, "repository": repo, "requested_ref": args.ref, "commit": commit,
            "skill_path": path, "upstream_version": scalar(frontmatter, "version"),
            "license": {"id": license_id, "local_path": "references/LICENSE"}, "files": records,
            "local_files": {name: digest(value[0]) for name, value in sorted(files.items())},
            "adaptations": ["Retained only name and description in portable frontmatter; preserved the upstream body and added attribution links.",
                            "Copied the selected upstream license unchanged. No hooks or upstream code were executed during import."]}
    return name, files, data


def import_skill(root, registry, args, validate_repository):
    name, files, data = prepare_import(args)
    source_text = "skills/" + args.category + "/" + name
    destination = root / source_text
    if destination.exists() or destination.is_symlink() or any(e["name"] == name for e in registry["skills"]):
        raise SourceError("skill already exists; import never overwrites existing work")
    entry = {"category": args.category, "name": name, "source": source_text,
             "targets": sorted(set(args.targets)), "version": "1.0.0", "origin": "external"}
    backups = {p: p.read_bytes() for p in [root / "registry.json", root / "README.md"]}
    try:
        destination.mkdir(parents=True)
        for local, (content, mode) in files.items():
            target = destination / local
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(mode)
        write_json(destination / "references/upstream.json", data)
        registry["skills"].append(entry)
        registry["skills"].sort(key=lambda e: e["name"])
        write_json(root / "registry.json", registry)
        (destination / "references/upstream.md").write_text(citation(entry, data), encoding="utf-8")
        (root / "README.md").write_text(readme_text(root, registry), encoding="utf-8")
        validate_repository()
    except Exception:
        for path, content in backups.items():
            path.write_bytes(content)
        if destination.exists():
            shutil.rmtree(destination)
        raise
    print("imported " + name + " at " + data["commit"] + " (local 1.0.0)")


def provenance(root, registry, args):
    if args.check:
        if args.refresh or args.note:
            raise SourceError("--check cannot be combined with --refresh or --note")
        errors = validate(root, registry)
        if errors:
            raise SourceError("\n".join(errors))
        print("checked external provenance and README citations")
        return
    if bool(args.refresh) != bool(args.note):
        raise SourceError("--refresh NAME requires --note describing reviewed local changes")
    if args.refresh:
        matches = [e for e in registry["skills"] if e["name"] == args.refresh and e.get("origin") == "external"]
        if not matches:
            raise SourceError("--refresh requires a registered external skill")
        source = root / matches[0]["source"]
        data = metadata(source)
        clean_text(args.note, "adaptation note")
        new_files = local_files(source)
        lic = data["license"]["local_path"]
        original = next(item["sha256"] for item in data["files"] if item["local_path"] == lic)
        if new_files.get(lic) != original:
            raise SourceError("refusing to refresh a changed or missing upstream license")
        data["local_files"] = new_files
        data["adaptations"].append(args.note)
        write_json(source / "references/upstream.json", data)
    generate(root, registry)
    errors = validate(root, registry)
    if errors:
        raise SourceError("\n".join(errors))
    print("generated external provenance citations")
