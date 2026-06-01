"""HCP hardware CLI — HOS version control (Phase 0.5 beta)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from hcp import Client
from hcp.exceptions import HCPError


def _env_client() -> Client:
    api_url = os.environ.get("HCP_API_URL", "https://api.hcp.io")
    token = os.environ.get("HCP_ACCESS_TOKEN") or os.environ.get("HCP_API_KEY")
    if not token:
        raise SystemExit(
            "Set HCP_API_KEY or HCP_ACCESS_TOKEN (or run `hw auth login`)."
        )
    return Client(api_url=api_url, access_token=token, api_key=token)


def _emit(data: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(json.dumps(data, indent=2))


def _cmd_auth_login(args: argparse.Namespace) -> int:
    import httpx

    api_url = args.api_url.rstrip("/")
    resp = httpx.post(
        f"{api_url}/v1/auth/login",
        json={"email": args.email, "password": args.password},
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise SystemExit(f"login failed: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    if args.json:
        _emit({"api_url": api_url, "access_token": token}, as_json=True)
    else:
        print(f"export HCP_API_URL={api_url}")
        print(f"export HCP_ACCESS_TOKEN={token}")
    return 0


def _with_client(args: argparse.Namespace, fn: Callable[[Client], Any]) -> int:
    try:
        client = _env_client()
        try:
            result = fn(client)
        finally:
            client.close()
    except HCPError as exc:
        raise SystemExit(str(exc)) from exc
    _emit(result, as_json=args.json)
    return 0


def _cmd_branch_create(args: argparse.Namespace) -> int:
    return _with_client(
        args,
        lambda c: c.hos.create_branch(
            project_id=args.project_id,
            name=args.name,
            from_commit_id=args.from_commit,
        ),
    )


def _cmd_branch_list(args: argparse.Namespace) -> int:
    return _with_client(
        args,
        lambda c: c.hos.list_branches(project_id=args.project_id),
    )


def _cmd_commit_create(args: argparse.Namespace) -> int:
    tree: dict[str, Any] = {}
    if args.tree:
        tree = json.loads(Path(args.tree).read_text())
    elif args.tree_json:
        tree = json.loads(args.tree_json)
    return _with_client(
        args,
        lambda c: c.hos.commit(
            project_id=args.project_id,
            branch_id=args.branch_id,
            message=args.message,
            tree=tree,
            parent_commit_ids=args.parent or None,
        ),
    )


def _cmd_diff(args: argparse.Namespace) -> int:
    return _with_client(
        args,
        lambda c: c.hos.diff(
            project_id=args.project_id,
            from_commit_id=args.from_commit,
            to_commit_id=args.to_commit,
        ),
    )


def _cmd_merge(args: argparse.Namespace) -> int:
    return _with_client(
        args,
        lambda c: c.hos.merge(
            project_id=args.project_id,
            target_branch_id=args.target,
            source_branch_id=args.source,
        ),
    )


def _cmd_conflicts_list(args: argparse.Namespace) -> int:
    return _with_client(
        args,
        lambda c: c.hos.list_conflicts(
            project_id=args.project_id,
            merge_id=args.merge_id,
        ),
    )


def _cmd_conflicts_resolve(args: argparse.Namespace) -> int:
    resolution = json.loads(args.resolution)
    return _with_client(
        args,
        lambda c: c.hos.resolve_conflict(
            project_id=args.project_id,
            conflict_id=args.conflict_id,
            resolution=resolution,
        ),
    )


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hw", description="HCP hardware CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="Authentication")
    auth_sub = auth.add_subparsers(dest="auth_cmd", required=True)
    login = auth_sub.add_parser("login", help="Obtain access token via /v1/auth/login")
    login.add_argument("--email", required=True)
    login.add_argument("--password", required=True)
    login.add_argument("--api-url", default=os.environ.get("HCP_API_URL", "https://api.hcp.io"))
    _add_json_flag(login)
    login.set_defaults(_fn=_cmd_auth_login)

    branch = sub.add_parser("branch", help="Branch operations")
    branch_sub = branch.add_subparsers(dest="branch_cmd", required=True)
    b_create = branch_sub.add_parser("create", help="Create branch")
    b_create.add_argument("--project-id", required=True)
    b_create.add_argument("--name", required=True)
    b_create.add_argument("--from-commit", default=None)
    _add_json_flag(b_create)
    b_create.set_defaults(_fn=_cmd_branch_create)

    b_list = branch_sub.add_parser("list", help="List branches")
    b_list.add_argument("--project-id", required=True)
    _add_json_flag(b_list)
    b_list.set_defaults(_fn=_cmd_branch_list)

    commit = sub.add_parser("commit", help="Commit operations")
    commit_sub = commit.add_subparsers(dest="commit_cmd", required=True)
    c_create = commit_sub.add_parser("create", help="Create commit")
    c_create.add_argument("--project-id", required=True)
    c_create.add_argument("--branch-id", required=True)
    c_create.add_argument("--message", required=True)
    c_create.add_argument("--tree", help="Path to JSON tree file")
    c_create.add_argument("--tree-json", help="Inline JSON tree")
    c_create.add_argument("--parent", action="append", default=None)
    _add_json_flag(c_create)
    c_create.set_defaults(_fn=_cmd_commit_create)

    diff = sub.add_parser("diff", help="Diff two commits")
    diff.add_argument("--project-id", required=True)
    diff.add_argument("--from", dest="from_commit", required=True)
    diff.add_argument("--to", dest="to_commit", required=True)
    _add_json_flag(diff)
    diff.set_defaults(_fn=_cmd_diff)

    merge = sub.add_parser("merge", help="Merge branches")
    merge.add_argument("--project-id", required=True)
    merge.add_argument("--target", required=True, help="Target branch id")
    merge.add_argument("--source", required=True, help="Source branch id")
    _add_json_flag(merge)
    merge.set_defaults(_fn=_cmd_merge)

    conflicts = sub.add_parser("conflicts", help="Merge conflict operations")
    conflicts_sub = conflicts.add_subparsers(dest="conflicts_cmd", required=True)
    cl = conflicts_sub.add_parser("list", help="List merge conflicts")
    cl.add_argument("--merge-id", required=True)
    cl.add_argument("--project-id", required=True)
    _add_json_flag(cl)
    cl.set_defaults(_fn=_cmd_conflicts_list)

    cr = conflicts_sub.add_parser("resolve", help="Resolve a conflict")
    cr.add_argument("--conflict-id", required=True)
    cr.add_argument("--project-id", required=True)
    cr.add_argument("--resolution", required=True, help="JSON resolution object")
    _add_json_flag(cr)
    cr.set_defaults(_fn=_cmd_conflicts_resolve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args._fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
