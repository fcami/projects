#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
"""Create a new subproject from the template.

Usage:
    ./new-project.py <project-name> --license <license> [--language <lang>]

Examples:
    ./new-project.py my-tool --language rust --license MIT
    ./new-project.py my-lib --language python --license "Apache-2.0"
    ./new-project.py my-app --language cpp --license GPL-3.0-only

This script:
1. Copies infrastructure/templates/new-project/ into projects/<name>/
2. Replaces {{PROJECT_NAME}} with the project name in all files
3. Sets the language in ci.yaml
4. Creates a LICENSE file (--license is required)
5. Sets up REUSE compliance (REUSE.toml + LICENSES/ for the subproject)
6. Creates src/ and tests/ directories
7. Prints next steps
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates", "new-project")
PROJECTS_DIR = os.path.join(REPO_ROOT, "projects")
# CI scripts resolve this project name to infrastructure/, not projects/
RESERVED_NAMES = {"infrastructure"}

LICENSE_HEADERS = {
    "MIT": "MIT License\n\nCopyright (c) {year} {author}\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n",
    "Apache-2.0": "Licensed under the Apache License, Version 2.0.\nSee https://www.apache.org/licenses/LICENSE-2.0 for the full text.\n\nCopyright (c) {year} {author}\n",
    "GPL-3.0-only": "This program is free software: you can redistribute it and/or modify\nit under the terms of the GNU General Public License as published by\nthe Free Software Foundation, version 3.\n\nSee https://www.gnu.org/licenses/gpl-3.0.html for the full text.\n\nCopyright (c) {year} {author}\n",
    "LGPL-3.0-only": "This library is free software: you can redistribute it and/or modify\nit under the terms of the GNU Lesser General Public License as published by\nthe Free Software Foundation, version 3.\n\nSee https://www.gnu.org/licenses/lgpl-3.0.html for the full text.\n\nCopyright (c) {year} {author}\n",
    "BSD-2-Clause": "BSD 2-Clause License\n\nCopyright (c) {year} {author}\n\nSee https://opensource.org/licenses/BSD-2-Clause for the full text.\n",
    "BSD-3-Clause": "BSD 3-Clause License\n\nCopyright (c) {year} {author}\n\nSee https://opensource.org/licenses/BSD-3-Clause for the full text.\n",
}

LANGUAGE_DEFAULTS = {
    "rust": {"src_files": ["src/lib.rs"], "test_files": []},
    "python": {"src_files": ["src/__init__.py"], "test_files": ["tests/__init__.py", "tests/test_placeholder.py"]},
    "c": {"src_files": [], "test_files": []},
    "cpp": {"src_files": [], "test_files": []},
    "go": {"src_files": [], "test_files": []},
    "node": {"src_files": ["src/index.js"], "test_files": []},
}


def replace_placeholder(filepath, project_name):
    """Replace {{PROJECT_NAME}} in a file."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except UnicodeDecodeError:
        return
    if "{{PROJECT_NAME}}" in content:
        content = content.replace("{{PROJECT_NAME}}", project_name)
        with open(filepath, "w") as f:
            f.write(content)


def get_author(args_author):
    """Resolve author name from args, git config, or fallback."""
    if args_author:
        return args_author
    try:
        return subprocess.check_output(
            ["git", "config", "user.name"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "AUTHOR"


def ensure_license_text(license_id):
    """Ensure LICENSES/<id>.txt exists at monorepo root. Returns the path."""
    monorepo_licenses = os.path.join(REPO_ROOT, "LICENSES")
    os.makedirs(monorepo_licenses, exist_ok=True)
    target = os.path.join(monorepo_licenses, f"{license_id}.txt")

    if os.path.exists(target):
        return target

    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "LICENSES"))
            subprocess.run(
                ["reuse", "download", license_id],
                cwd=tmpdir, capture_output=True, check=True,
            )
            downloaded = os.path.join(tmpdir, "LICENSES", f"{license_id}.txt")
            if os.path.exists(downloaded):
                shutil.copy2(downloaded, target)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if not os.path.exists(target):
        with open(target, "w") as f:
            f.write(f"See https://spdx.org/licenses/{license_id}.html\n")

    return target


def setup_reuse(project_dir, license_id, year, author):
    """Create REUSE.toml and LICENSES/ for the subproject."""
    # Ensure license text exists at monorepo root (reuse lint checks there)
    monorepo_license = ensure_license_text(license_id)

    # Copy into subproject LICENSES/ (for standalone extraction)
    subproject_licenses = os.path.join(project_dir, "LICENSES")
    os.makedirs(subproject_licenses, exist_ok=True)
    shutil.copy2(monorepo_license, os.path.join(subproject_licenses, f"{license_id}.txt"))

    reuse_toml = os.path.join(project_dir, "REUSE.toml")
    with open(reuse_toml, "w") as f:
        f.write(f'''version = 1

[[annotations]]
path = "**"
precedence = "aggregate"
SPDX-FileCopyrightText = "{year} {author}"
SPDX-License-Identifier = "{license_id}"
''')


def main():
    parser = argparse.ArgumentParser(description="Create a new subproject from the template.")
    parser.add_argument("name", help="Project name (used as directory name under projects/)")
    parser.add_argument("--language", "-l", default="other",
                        choices=["rust", "python", "c", "cpp", "go", "node", "other"],
                        help="Programming language (sets ci.yaml and Makefile hints)")
    parser.add_argument("--license", required=True,
                        help="SPDX license identifier (required: MIT, Apache-2.0, GPL-3.0-only, LGPL-3.0-only, BSD-2-Clause, BSD-3-Clause)")
    parser.add_argument("--author", default=None,
                        help="Author name for LICENSE file (default: git user.name)")
    args = parser.parse_args()

    if args.name in RESERVED_NAMES:
        print(f"Error: {args.name!r} is reserved (CI uses it for the monorepo "
              "tooling)", file=sys.stderr)
        sys.exit(1)

    project_dir = os.path.join(PROJECTS_DIR, args.name)

    if os.path.exists(project_dir):
        print(f"Error: {project_dir} already exists", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(TEMPLATE_DIR):
        print(f"Error: template directory not found: {TEMPLATE_DIR}", file=sys.stderr)
        sys.exit(1)

    # Copy template
    shutil.copytree(TEMPLATE_DIR, project_dir)
    print(f"Created {project_dir}/ from template")

    # Replace placeholders in all files
    for root, _dirs, files in os.walk(project_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            replace_placeholder(filepath, args.name)

    # Set language in ci.yaml
    ci_yaml = os.path.join(project_dir, "ci.yaml")
    if os.path.exists(ci_yaml):
        with open(ci_yaml, "r") as f:
            content = f.read()
        content = content.replace("language: rust", f"language: {args.language}")
        with open(ci_yaml, "w") as f:
            f.write(content)

    # Create source directories
    os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "tests"), exist_ok=True)

    # Create language-specific starter files
    defaults = LANGUAGE_DEFAULTS.get(args.language, {})
    for src_file in defaults.get("src_files", []):
        path = os.path.join(project_dir, src_file)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write("")

    for test_file in defaults.get("test_files", []):
        path = os.path.join(project_dir, test_file)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write("")

    # Create LICENSE file
    year = datetime.now().year
    author = get_author(args.author)
    license_id = args.license

    if license_id in LICENSE_HEADERS:
        text = LICENSE_HEADERS[license_id].format(year=year, author=author)
    else:
        text = f"{license_id}\n\nCopyright (c) {year} {author}\n\nSee https://spdx.org/licenses/{license_id}.html for the full text.\n"

    with open(os.path.join(project_dir, "LICENSE"), "w") as f:
        f.write(text)
    print(f"Created LICENSE ({license_id})")

    # Set up REUSE compliance (REUSE.toml + LICENSES/ for the subproject)
    setup_reuse(project_dir, license_id, year, author)
    print(f"Created REUSE.toml + LICENSES/{license_id}.txt")

    # Print next steps
    print()
    print("Next steps:")
    print(f"  1. Edit projects/{args.name}/Makefile — uncomment the {args.language} block")
    print("     and wire up your build/test/lint commands")
    print(f"  2. Edit projects/{args.name}/README.md — describe the project")
    print(f"  3. Write code in projects/{args.name}/src/")
    print(f"  4. Write tests in projects/{args.name}/tests/")
    print(f"  5. Verify: make -C projects/{args.name} lint build test")
    print("  6. Verify: reuse lint")
    print("  7. Commit and push — CI picks it up automatically")


if __name__ == "__main__":
    main()
