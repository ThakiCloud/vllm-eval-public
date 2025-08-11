# VLLM‑Eval Docs (MkDocs)

Simple guide to view, edit, and publish the documentation in this repo using MkDocs.

## Preview locally

```bash
mkdocs serve
```

Open `http://127.0.0.1:8000` in your browser. Auto‑reload is enabled.

Tip: to expose on all interfaces (e.g., containers):

```bash
mkdocs serve -a 0.0.0.0:8000
```

## Edit docs

- All pages live under the `docs/` folder.
- To add a page, create a new `.md` file in `docs/` and (optionally) list it under `nav` in `mkdocs.yml` so it appears in the sidebar.
- Keep `mkdocs serve` running to preview changes instantly.

## Build (optional)

```bash
mkdocs build
```

Generates the static site in the `site/` directory.

## Publish to GitHub Pages

```bash
mkdocs gh-deploy
```

This builds the site and updates the `gh-pages` branch. Your Pages site will refresh shortly.
