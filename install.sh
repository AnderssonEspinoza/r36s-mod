#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
base=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
    python=python3
elif [ -x /opt/r36s-toolkit/bin/python3 ]; then
    python=/opt/r36s-toolkit/bin/python3
else
    echo 'Falta Python 3. Lee docs/INSTALACION.md y docs/TOOLKIT.md.' >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then set -- doctor; fi
exec "$python" "$base/scripts/r36s_mod.py" "$@"
