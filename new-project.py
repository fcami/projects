#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
"""Create a new subproject. Delegates to infrastructure/new-project.py."""
import os, subprocess, sys; sys.exit(subprocess.call([sys.executable, os.path.join(os.path.dirname(__file__), "infrastructure", "new-project.py")] + sys.argv[1:]))
