#!/bin/zsh
# usage: _run-hud.sh '<json jobs array>'
cd /Users/vincent/Desktop/work/playdate-test/safu
JOBS="$1" ; export JOBS
python3 - "$JOBS" <<'PY' > /tmp/safu-hud-driver.mjs
import sys
print("""const { renderHud } = await import('/Users/vincent/Desktop/work/playdate-test/safu/images/svg/_render-hud.mjs')
const jobs = %s
await useOrCreateTaskSpace('render safu hud')
await renderHud(jobs, { js, openOrReuseTab, wait, cliLog })""" % sys.argv[1])
PY
ego-browser nodejs < /tmp/safu-hud-driver.mjs
