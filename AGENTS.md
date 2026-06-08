# Agent Guidelines

## This is a Learning Project

This repository is a learning exercise: two people are implementing the DEFLATE
compression algorithm (RFC 1951) by hand, from scratch.

## Off-limits: `/src`

**Agents must not create, edit, or delete any files inside the `/src` directory.**

The `/src` directory is reserved entirely for the human authors. The whole
point of the project is for us to write that code ourselves. Automatically
generating or modifying implementation code would defeat the purpose.

This applies even if:
- The code is broken or obviously wrong.
- You are asked to "just fix one small thing."
- The change would be trivial.

If you notice a bug or have a suggestion for `/src`, describe it in plain
English rather than editing the file.

## Commit Authorship

To keep the git history clear about who wrote what, agents should commit their
own changes promptly and separately from any human-authored changes.

Specifically:
- **Do commit** your own additions or modifications as a standalone commit.
- **Do not stage or commit** files that were modified by a human — even if they
  are sitting unstaged alongside your changes. Leave human changes for the
  humans to commit themselves.

## Everything Else

Outside of `/src`, normal assistance is welcome:
- `/examples` — adding, updating, or explaining test files is fine.
- `/rfc1951.txt` — the spec is read-only reference material; leave it as-is.
- Root-level config files, documentation, tooling — fair game.
