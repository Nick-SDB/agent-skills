---
name: update-skill
description: Update a skill in both the cc-switch config directory and the agent-skills repository, then commit and push changes.
argument-hint: "<skill-name>"
allowed-tools: Bash Glob Grep Read Write Edit
---

# Update Skill

Update a skill in both the cc-switch config directory and the agent-skills repository, then commit and push to git.

## Skill Paths

- **cc-switch dir**: `/nfs/AE/shidebo/app/cc-switch/config/skills/<skill-name>/`
- **repo dir**: `/nfs/AE/shidebo/code/agent-skills/skills/<category>/<skill-name>/`

The skill must exist under the repo in one of the categories under `/nfs/AE/shidebo/code/agent-skills/skills/`.

## Steps

### Step 1: Identify the Skill Location

Run this to find the skill in the repo:

```bash
# Find the skill in the repo
skill_name="$ARGUMENTS"
find /nfs/AE/shidebo/code/agent-skills/skills -type d -name "$skill_name"
```

Also check if it exists in cc-switch:

```bash
ls -la /nfs/AE/shidebo/app/cc-switch/config/skills/"$skill_name"/
```

### Step 2: Read Current Content

1. Read the current SKILL.md from the repo (this is the source of truth)
2. Read any existing files in cc-switch if they exist

### Step 3: Make Updates

Edit the skill files as needed. You can update:
- The SKILL.md in the repo (primary)
- Copy to cc-switch if needed (for immediate testing/deployment)

### Step 4: Commit and Push

After making changes, commit and push the repo changes:

```bash
cd /nfs/AE/shidebo/code/agent-skills

# Check status
git status

# Add the changed files
git add skills/<category>/<skill-name>/

# Commit with a message
git commit -m "Update skill: $ARGUMENTS

Updated skill content.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# Push to remote
git push
```

## Output

Report to the user:
1. What files were changed
2. The git commit URL (if available)
3. Any notes about the cc-switch symlink if it exists