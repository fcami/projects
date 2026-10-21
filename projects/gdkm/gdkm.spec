Name:           gdkm
Version:        0.1.0
Release:        1%{?dist}
Summary:        Move GitHub deploy keys between repositories

License:        MIT
URL:            https://github.com/fcami/projects
# Not released upstream yet. The tarball is built from the committed content of
# projects/gdkm in the monorepo, with gdkm-%%{version}/ as its top directory:
#   make release        (in projects/gdkm; writes gdkm-%%{version}.tar.gz)
# which runs this (in a subdirectory, git archive only takes that subtree):
#   git archive --prefix=gdkm-%%{version}/ -o gdkm-%%{version}.tar.gz HEAD
Source0:        gdkm-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
# For %%check
BuildRequires:  python3dist(tomlkit)
# A bare script: dependencies are not generated automatically
Requires:       python3dist(tomlkit)
# Used at runtime only, to run "gh auth token"
Requires:       gh

%description
gdkm moves GitHub deploy keys between repositories with one command. GitHub
allows a public key to be a deploy key on only one repository, so reusing a key
means removing it from the old repository first. gdkm does that, rolls back if
the add fails, and records where each key is in a TOML configuration file.

%prep
%autosetup

%build
# Nothing to build: gdkm is a single Python script.

%install
install -D -p -m 0755 src/gdkm.py %{buildroot}%{_bindir}/gdkm
%py3_shebang_fix %{buildroot}%{_bindir}/gdkm

%check
PYTHONPATH=src %{python3} -m unittest discover -s tests -t .

%files
%license LICENSE
%doc README.md example-config.toml
%{_bindir}/gdkm

%changelog
* Wed Oct 21 2026 François Cami <contribs@fcami.net> - 0.1.0-1
- Initial package
