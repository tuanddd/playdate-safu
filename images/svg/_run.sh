#!/bin/zsh
# usage: _run.sh '<json jobs array>'
cd /Users/vincent/Desktop/work/playdate-test/safu
JF=$(mktemp /tmp/neko-jobs.XXXXXX.json)
printf '%s' "$1" > "$JF"
JF="$JF" ego-browser nodejs <<'EOF'
const fs = await import('node:fs')
const { renderJobs } = await import('/Users/vincent/Desktop/work/playdate-test/safu/images/svg/_render.mjs')
const jobs = JSON.parse(fs.readFileSync(process.env.JF,'utf8'))
await useOrCreateTaskSpace('render neko art')
await renderJobs(jobs, { js, openOrReuseTab, wait, cliLog })
EOF
