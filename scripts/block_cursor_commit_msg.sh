#!/bin/bash
# Block commits that list Cursor (or cootor) as co-author.

MSG_FILE="${1:?Usage: $0 <commit-msg-file>}"
if grep -iE "Co-Authored-By:.*(cursor|cootor)" "$MSG_FILE" 1>/dev/null 2>&1; then
    echo "❌ Commit blocked: Co-Authored-By must not contain Cursor."
    exit 1
fi
exit 0
