#!/usr/bin/env bash
# Exploratory retrospective on Sim A/B event data (2026-11-09). Not pre-registered: hypothesis generation only.
cd "$(dirname "$0")/../.." || exit 1
{
  echo "# Retrospective diagnostics 2026-11-09 (exploratory — hypothesis generation only, not a test)"
  echo
  for i in 1 2 3 4; do echo "## retro$i.py"; echo '```'; python3 simulation/retro/retro$i.py; echo '```'; echo; done
} > outputs/retro_2026-11-09.md
