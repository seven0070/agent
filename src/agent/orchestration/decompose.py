"""Compose a capability DAG from a user goal.

Clause structure and available tools drive the graph. This is not a catalog of
prompt IDs: each clause is classified, then operations are wired by dependency
(read/inspect/compute produce values that later writes consume).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.orchestration.intent import (
    BUILD_PROGRAM,
    CAPABILITY_UNAVAILABLE,
    CHANGE_PROGRAM,
    COMPUTE,
    CONVERSE,
    QUERY_DATA,
    READ_TEXT,
    READ_THEN_WRITE,
    UNSUPPORTED,
    WRITE_TEXT,
    _FILENAME,
    classify_intent,
)


_CLAUSE_SPLIT = re.compile(
    r"\s*(?:;|\band then\b|\bthen\b|\bafter that\b|\bfinally\b)\s+",
    flags=re.IGNORECASE,
)
_UNSAFE_PATH = re.compile(r"((?:\.\./)+[\w./\\-]+|/(?:etc|Windows)[\w./\\-]*)")
_PLACEHOLDER = re.compile(r"\$([A-Za-z0-9_]+)\.output")


@dataclass
class Op:
    kind: str
    tool_id: Optional[str]
    inputs: Dict[str, Any]
    description: str
    bind: Dict[str, str] = field(default_factory=dict)
    id: str = ""


def split_clauses(goal: str) -> List[str]:
    parts = [part.strip(" \t,") for part in _CLAUSE_SPLIT.split(goal) if part.strip(" \t,")]
    return parts or [goal.strip()]


def mentioned_files(goal: str) -> List[str]:
    found: List[str] = []
    for name in re.findall(_FILENAME, goal):
        if name not in found:
            found.append(name)
    return found


def unsafe_paths(goal: str) -> List[str]:
    found: List[str] = []
    for match in _UNSAFE_PATH.finditer(goal):
        path = match.group(1).replace("\\", "/")
        if path not in found:
            found.append(path)
    return found


def numeric_reduce(goal: str) -> Optional[str]:
    lower = goal.lower()
    if re.search(r"\b(average|mean)\b", lower):
        return "avg"
    if re.search(r"\b(add|sum|total)\b", lower):
        return "add"
    if re.search(r"\b(multiply|product)\b", lower):
        return "mul"
    return None


def aggregating(goal: str) -> bool:
    return bool(
        re.search(
            r"\b(highest|lowest|which|who has|max|min|largest|smallest|average|mean|"
            r"how many|count|total|sum|summarize|summary)\b",
            goal,
            flags=re.IGNORECASE,
        )
    )


def persist_destinations(goal: str) -> List[str]:
    from agent.orchestration.planner import extract_file_write_ops, extract_filename

    dests: List[str] = []
    for name, _content in extract_file_write_ops(goal):
        if name not in dests:
            dests.append(name)
    for match in re.finditer(rf"(?:into|to|in)\s+[\"']?({_FILENAME})[\"']?", goal, flags=re.IGNORECASE):
        name = match.group(1)
        if name not in dests:
            dests.append(name)
    named = extract_filename(goal)
    if named and named not in dests and re.search(
        r"\b(write|save|put|into|to)\b", goal, flags=re.IGNORECASE
    ):
        dests.append(named)
    return dests


def _data_name(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(".json") or lower.endswith(".csv")


def ops_from_intent(intent, clause: str, workspace_dir: Optional[str]) -> List[Op]:
    from agent.orchestration.planner import extract_file_write_ops

    kind = intent.kind
    slots = intent.slots
    ops: List[Op] = []
    if kind in (BUILD_PROGRAM, CHANGE_PROGRAM):
        ops.append(
            Op("code", "coding-engine-v1", {"goal": clause}, "Execute coding task with Jcode engine")
        )
    elif kind == READ_THEN_WRITE:
        source = str(slots.get("source") or "")
        dest = str(slots.get("dest") or "summary.txt")
        ops.append(Op("read", "read_file-v1", {"relative_path": source}, f"Read {source}"))
        explicit = ""
        for name, content in extract_file_write_ops(clause):
            if name == dest and str(content).strip():
                explicit = str(content)
                break
        write = Op(
            "write",
            "write_file-v1",
            {"relative_path": dest, "content": explicit},
            f"Write {dest}",
        )
        if not explicit:
            write.bind["content"] = "prev"
        ops.append(write)
    elif kind == READ_TEXT:
        rel = str(slots.get("filename") or clause.strip())
        ops.append(Op("read", "read_file-v1", {"relative_path": rel}, f"Read {rel}"))
    elif kind == QUERY_DATA:
        rel = slots.get("filename")
        if not rel:
            ops.append(
                Op(
                    "unavailable",
                    CAPABILITY_UNAVAILABLE,
                    {"goal": clause},
                    "Structured data file is required but was not found",
                )
            )
        else:
            ops.append(
                Op(
                    "inspect",
                    "inspect_data-v1",
                    {"relative_path": rel, "query": slots.get("query") or clause},
                    f"Inspect {rel}",
                )
            )
    elif kind == COMPUTE:
        expr = str(slots.get("expression") or "")
        ops.append(Op("compute", "calculator-v1", {"expression": expr}, "Evaluate mathematical calculation"))
        save_as = slots.get("save_as")
        if save_as:
            write = Op(
                "write",
                "write_file-v1",
                {"relative_path": str(save_as), "content": ""},
                "Write calculation result to workspace file",
            )
            write.bind["content"] = "prev"
            ops.append(write)
    elif kind == WRITE_TEXT:
        pairs = extract_file_write_ops(clause)
        if not pairs:
            pairs = [(str(slots.get("filename") or "note.txt"), str(slots.get("content") or ""))]
        for name, content in pairs:
            ops.append(
                Op(
                    "write",
                    "write_file-v1",
                    {"relative_path": name, "content": content},
                    "Write requested content to a workspace file",
                )
            )
    elif kind == CONVERSE:
        ops.append(Op("converse", None, {"prompt": clause}, f"Process goal: {clause}"))
    else:
        ops.append(
            Op(
                "unavailable",
                CAPABILITY_UNAVAILABLE,
                {"goal": clause},
                "Requested capability is not available",
            )
        )
    return ops


def _first_data_file(workspace_dir: Optional[str]) -> Optional[str]:
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return None
    for root, _, files in os.walk(workspace_dir):
        for name in files:
            if _data_name(name):
                return name
    return None


def compose_operations(goal: str, workspace_dir: Optional[str] = None) -> List[Op]:
    """Turn a goal into ordered, dependency-wired operations."""
    unsafe = unsafe_paths(goal)
    if unsafe and re.search(r"\b(read|open|cat |look)\b", goal, flags=re.IGNORECASE):
        return [Op("read", "read_file-v1", {"relative_path": path}, f"Read {path}") for path in unsafe]

    clauses = split_clauses(goal)
    ops: List[Op] = []
    for clause in clauses:
        intent = classify_intent(clause, workspace_dir=workspace_dir)
        ops.extend(ops_from_intent(intent, clause, workspace_dir))

    files = mentioned_files(goal)
    dests = persist_destinations(goal)
    reduce = numeric_reduce(goal)
    wants_query = aggregating(goal)
    data_files = [name for name in files if _data_name(name)]
    if not data_files:
        inferred = _first_data_file(workspace_dir)
        if inferred and wants_query:
            data_files = [inferred]

    reads = [op for op in ops if op.kind == "read"]
    writes = [op for op in ops if op.kind == "write"]
    inspects = [op for op in ops if op.kind == "inspect"]
    computes = [op for op in ops if op.kind == "compute"]

    source_files = [name for name in files if name not in dests]

    if wants_query and data_files:
        query_source = data_files[0]
        if not inspects:
            ops = [op for op in ops if not (op.kind == "read" and op.inputs.get("relative_path") == query_source)]
            inspects = [
                Op(
                    "inspect",
                    "inspect_data-v1",
                    {"relative_path": query_source, "query": goal},
                    f"Inspect {query_source}",
                )
            ]
            insert_at = 0
            ops = inspects + [op for op in ops if op.kind != "inspect"]
        query_dests = [name for name in dests if not _data_name(name)]
        existing_write_names = {op.inputs.get("relative_path") for op in ops if op.kind == "write"}
        for dest in query_dests:
            if dest in existing_write_names:
                continue
            write = Op(
                "write",
                "write_file-v1",
                {"relative_path": dest, "content": ""},
                f"Write {dest} from inspection",
            )
            write.bind["content"] = "inspect"
            ops.append(write)
        for op in ops:
            if op.kind == "write" and not op.inputs.get("content") and not op.bind:
                op.bind["content"] = "inspect"
        reads = [op for op in ops if op.kind == "read"]
        writes = [op for op in ops if op.kind == "write"]
        inspects = [op for op in ops if op.kind == "inspect"]

    explicit = _explicit_write_contents(goal)
    if reduce and len(source_files) >= 2 and dests and not computes:
        reduce_dests = [name for name in dests if name not in explicit]
        kept_writes = [
            op
            for op in ops
            if op.kind == "write" and str(op.inputs.get("relative_path") or "") in explicit
        ]
        ops = [op for op in ops if op.kind not in {"read", "compute", "write", "converse"}]
        read_ops = [
            Op("read", "read_file-v1", {"relative_path": name}, f"Read {name}") for name in source_files
        ]
        refs = [f"$read{i}.output" for i in range(len(read_ops))]
        if reduce == "avg":
            expr_body = "+".join(refs)
            expression = f"({expr_body})/{len(read_ops)}"
        elif reduce == "mul":
            expression = "*".join(refs)
        else:
            expression = "+".join(refs)
        compute = Op("compute", "calculator-v1", {"expression": expression}, "Reduce numeric file values")
        compute.bind["expression"] = "reads"
        write_ops = list(kept_writes)
        existing_explicit = {op.inputs.get("relative_path") for op in write_ops}
        for dest in reduce_dests:
            write = Op(
                "write",
                "write_file-v1",
                {"relative_path": dest, "content": ""},
                f"Write reduced value to {dest}",
            )
            write.bind["content"] = "compute"
            write_ops.append(write)
        for name, content in explicit.items():
            if name in existing_explicit:
                continue
            write_ops.append(
                Op(
                    "write",
                    "write_file-v1",
                    {"relative_path": name, "content": content},
                    f"Write {name}",
                )
            )
        ops = ops + read_ops + [compute] + write_ops

    ops = _drop_noop_converse(ops)
    ops = _dedupe_identical_ops(ops)
    _wire_binds(ops)
    return ops


def _explicit_write_contents(goal: str) -> Dict[str, str]:
    from agent.orchestration.planner import extract_file_write_ops

    found: Dict[str, str] = {}
    for name, content in extract_file_write_ops(goal):
        if str(content).strip():
            found[name] = str(content)
    return found


def _drop_noop_converse(ops: List[Op]) -> List[Op]:
    if any(op.kind not in {"converse"} for op in ops):
        return [op for op in ops if op.kind != "converse"]
    return ops


def _dedupe_identical_ops(ops: List[Op]) -> List[Op]:
    out: List[Op] = []
    for op in ops:
        if out and _ops_equivalent(out[-1], op):
            continue
        out.append(op)
    return out


def _ops_equivalent(left: Op, right: Op) -> bool:
    if left.kind != right.kind or left.tool_id != right.tool_id:
        return False
    if left.kind == "compute":
        return str(left.inputs.get("expression") or "") == str(right.inputs.get("expression") or "")
    if left.kind == "write":
        return str(left.inputs.get("relative_path") or "") == str(right.inputs.get("relative_path") or "") and str(
            left.inputs.get("content") or ""
        ) == str(right.inputs.get("content") or "")
    if left.kind == "read":
        return str(left.inputs.get("relative_path") or "") == str(right.inputs.get("relative_path") or "")
    return left.inputs == right.inputs


def _wire_binds(ops: List[Op]) -> None:
    has_producer = False
    for op in ops:
        if op.kind in {"read", "inspect", "compute", "code"}:
            has_producer = True
        if op.kind == "write" and not (op.inputs.get("content") or "").strip() and "content" not in op.bind:
            if has_producer:
                op.bind["content"] = "prev"


def assign_ids_and_placeholders(ops: List[Op]) -> List[Op]:
    counters = {"read": 0, "write": 0, "compute": 0, "inspect": 0, "code": 0, "converse": 0, "unavailable": 0}
    producers: List[Op] = []
    last_by_kind: Dict[str, Op] = {}
    has_compute = any(op.kind == "compute" for op in ops)
    has_read = any(op.kind == "read" for op in ops)
    for op in ops:
        counters[op.kind] = counters.get(op.kind, 0) + 1
        n = counters[op.kind]
        if op.kind == "read":
            op.id = f"task_read_{n}"
        elif op.kind == "compute":
            op.id = "task_calc_1" if n == 1 else f"task_calc_{n}"
        elif op.kind == "inspect":
            op.id = f"task_inspect_{n}"
        elif op.kind == "code":
            op.id = "task_code_1" if n == 1 else f"task_code_{n}"
        elif op.kind == "converse":
            op.id = "task_gen_1" if n == 1 else f"task_gen_{n}"
        elif op.kind == "unavailable":
            op.id = "task_unavailable_1" if n == 1 else f"task_unavailable_{n}"
        elif op.kind == "write":
            if has_compute or has_read or any(item.kind == "inspect" for item in ops):
                op.id = f"task_write_{n + 1}"
            else:
                op.id = f"task_write_{n}"
        else:
            op.id = f"task_{op.kind}_{n}"

        if op.kind == "compute" and op.bind.get("expression") == "reads":
            read_ids = [item.id for item in producers if item.kind == "read"]
            if read_ids:
                refs = [f"${rid}.output" for rid in read_ids]
                raw = str(op.inputs.get("expression") or "")
                if "avg" in (op.description or "").lower() or "/{0}".format(len(read_ids)) in raw or raw.startswith("("):
                    op.inputs["expression"] = f"({'+'.join(refs)})/{len(read_ids)}"
                elif "*" in raw and "+" not in raw:
                    op.inputs["expression"] = "*".join(refs)
                else:
                    op.inputs["expression"] = "+".join(refs)

        for key, source in op.bind.items():
            if source == "reads":
                continue
            target = None
            if source == "prev":
                target = producers[-1] if producers else None
            else:
                target = last_by_kind.get(source)
            if target is not None:
                op.inputs[key] = f"${target.id}.output"

        if op.kind in {"read", "inspect", "compute", "code"}:
            producers.append(op)
            last_by_kind[op.kind] = op
    return ops


def resolve_placeholders(value: Any, outputs: Dict[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if re.fullmatch(r"\$[A-Za-z0-9_]+\.output", value):
        tid = value[1:].split(".output")[0]
        if tid in outputs and outputs[tid] is not None:
            return str(outputs[tid]).strip()
        return value

    def _replace(match: re.Match[str]) -> str:
        tid = match.group(1)
        if tid in outputs and outputs[tid] is not None:
            return str(outputs[tid]).strip()
        return match.group(0)

    return _PLACEHOLDER.sub(_replace, value)
