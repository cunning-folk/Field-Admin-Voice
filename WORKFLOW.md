# Development Workflow Guide

A simple guide for working on this project across multiple environments
(Replit, Claude Code, Windsurf, Cursor, etc.) without creating conflicts.

## The Golden Rule

**Only work in ONE environment at a time, and always sync before switching.**

## Before You Start Working

Always pull the latest changes first:

```bash
git pull
```

In Replit: Click the Git icon (Version Control) → Pull

## When You're Done Working

Save your work before stepping away or switching environments:

```bash
git add .
git commit -m "Brief description of what you changed"
git push
```

In Replit: Git icon → Stage All → Write commit message → Commit → Push

## Switching Environments Checklist

- [ ] Commit and push all changes in the current environment
- [ ] Open the new environment
- [ ] Pull latest changes before editing anything

## If Something Goes Wrong

### "Your local changes would be overwritten"

You have uncommitted changes. Either:

1. Commit them first: `git add . && git commit -m "save work"`
2. Or discard them: `git checkout .` (warning: loses uncommitted work)

### Merge Conflict

This means the same file was edited in two places. Options:

1. Ask Claude Code to help resolve it
2. In Replit, the Version Control panel will show conflicts to resolve

### Not Sure What's Happening

Run this to see the current state:

```bash
git status
```

## Tips for Non-Engineers

- Commit often, even small changes
- Write commit messages that remind you what you did
- When in doubt, commit and push before switching tools
- It's okay to ask Claude Code to handle git commands for you

## Quick Reference

| Action | Command |
|--------|---------|
| Get latest changes | `git pull` |
| See what's changed | `git status` |
| Save everything | `git add . && git commit -m "message" && git push` |
| Undo uncommitted changes | `git checkout .` |
