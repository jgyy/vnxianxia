# AGENTS.md: .github/

This directory holds GitHub configuration only. Right now that is the CI workflow in
[workflows/](workflows/AGENTS.md), with no issue templates, PR templates or other actions.

- CI runs on pushes to `main`, on pull requests and on `workflow_dispatch`. A newer run on the same ref cancels the
  older one (`concurrency: ci-${{ github.ref }}`).
- The tool versions are pinned in the workflow's `env`: `BPY_VERSION: "5.2.2"` (Blender as a Python module, on
  Python 3.13) and `GODOT_VERSION: "4.7.2"`. When you bump either one, also update README.md, the root
  [AGENTS.md](../AGENTS.md) and the `config/features` in `godot/project.godot` (for Godot).
- Every check in the workflow can be reproduced locally with the commands in the root AGENTS.md. Run them before
  proposing a change to a workflow step, so the step is known to pass.
