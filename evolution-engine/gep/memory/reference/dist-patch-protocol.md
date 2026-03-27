# Dist Patch Protocol v1.1

## Purpose
Standardize dist patching process to prevent wasted time on unfixable issues.

## Core Principle
**One-round rule for dependency bugs**: If first dist patch attempt fails for a dependency issue (discord.js, express, etc.), stop and document. Do not attempt multiple rounds.

## Decision Tree

### Step 1: Issue Classification
```
Is this an OpenClaw-specific issue? (e.g., nested lane #14214, health-monitor #54782)
  YES → Proceed with patch
  NO → Is it a third-party library bug?
    YES → Apply one round of patch only, then stop
    NO → Proceed with patch
```

### Step 2: Patch Strategy
- **OpenClaw-specific**: Create idempotent script, include in upgrade checklist
- **Third-party bug**: Document only, mark as upstream-tracked
- **Node.js stream internals**: Never patch, document as known limitation

### Step 3: Verification
After patch:
- Does it work on first attempt? → Mark as fixed
- Does it fail? → For dependency bugs, stop immediately

## Anti-Patterns (Forbidden)

### ❌ Multiple Rounds on Same Bug
- **Example**: DAVE encryption debugging (4 rounds, 1h 20m)
- **Rule**: If first patch fails for dependency bug, stop after 30min
- **Exception**: If human explicitly requests more attempts

### ❌ Chasing Symptoms
- **Example**: Patching decrypt() → parsePacket() → wrapper on same AbortError
- **Rule**: Fix root cause, not symptoms
- **Exception**: When root cause is confirmed to be patchable

### ❌ Ignoring Community Reports
- **Example**: discord.js#11419 has 50+ reports, still attempt patches
- **Rule**: Check GitHub issues before starting patch work
- **Exception**: When workaround is critical and no alternatives exist

## Patch Templates

### OpenClaw-Specific Patch
```bash
#!/bin/bash
# Apply patch for OpenClaw-specific issue

set -e

# Find dist file by content pattern
DIST_FILE=$(find /usr/lib/node_modules/openclaw/dist -name "*.js" -exec grep -l "pattern-to-find" {} \; | head -1)

if [ -z "$DIST_FILE" ]; then
    echo "Error: Dist file not found"
    exit 1
fi

# Backup and patch
cp "$DIST_FILE" "$DIST_FILE.bak"
sed -i 's/old-pattern/new-pattern/g' "$DIST_FILE"

echo "Applied patch to: $DIST_FILE"
```

### Dependency Bug Documentation
```markdown
## [Bug Name]
- **Library**: @discordjs/voice
- **Issue**: discord.js#11419
- **Symptom**: DAVE decryption failures
- **Status**: Upstream bug, no patch possible
- **Workaround**: Disable voice channels
- **Next check**: When library version updates
```

## Success Metrics
- Time spent on dist patches < 30min per issue (dependency bugs)
- 100% idempotent patch application
- Zero regression after upgrades
- Clear documentation for maintenance

## Maintenance
- Review after each OpenClaw upgrade
- Update scripts if dist file patterns change
- Archive old protocols in archive/ directory

## v1.1 Changes (2026-03-27)
- Added one-round rule for dependency bugs
- Added anti-patterns section
- Added decision tree
- Added community reports check requirement