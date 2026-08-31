# GitHub publication checklist

Complete these repository-owner-specific steps before making the project public:

1. Confirm the GitHub account and repository name.
2. Confirm the software copyright holder and preferred licence. The prepared
   default is `Copyright (c) 2026 University of Warwick` under MIT.
3. Add a permanent maintainer contact to the Code of Conduct and security
   policy, or enable GitHub private vulnerability reporting.
4. Review the software citation shown by GitHub's “Cite this repository”
   interface.
5. Run `pytest`, `ruff check .`, and `python -m build` on the release commit.
6. Create the first signed or annotated tag (`v0.1.0`) and attach an archived
   release. Link a Zenodo record if a software DOI is required.
7. Enable Issues and Discussions, branch protection, required CI checks,
   Dependabot alerts, and private vulnerability reporting as appropriate.
8. Add repository topics such as `peridynamics`, `taichi`,
   `computational-mechanics`, `geomaterials`, and `research-software`.
9. If benchmark result files are published, deposit them separately with the
    exact configuration, Git commit, environment metadata, and licence.

Do not upload private source documents or unrelated research records to the
public repository.
