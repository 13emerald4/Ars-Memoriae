"""Automated remediation script for CPSC 210 flashcard defects in dev.db.

Patches:
1. diffHoursWorked in LA10 Task 3 (5c9645f8b8e94d5a8e5a039489aef10a):
   - Loops over this.tasks instead of snapshot.tasks, accounting for tasks added after the snapshot.
   - Inlines Status, TaskSnapshot, ProjectSnapshot, Task class, and test driver.
   - Populates test cases.
2. extremeTides in Lab 02 Task 2 (9d0e71876020432c930b82897de2f885):
   - Fixes comparator byTime so byTime(a, a) === 0.
   - Retitles card to "Lab 2, T2: extremeTides(readings, fromDay, toDay, k)".
3. Retitles mislabeled Lab 02 cards:
   - 1c6ed8bc4ad74be09c116d509f06700b -> "Lab 2, T1: highestReading(readings)"
   - b55fe8dc0d1040e19cc7a97c4a09bbc0 -> "Lab 2, T4: passageWindows(readings, minHeight, minHours)"
4. stationOptions in Lab 05 Task 1 (97c82dc4419a4869beae4f3fbc9d3126):
   - Sorts by station.title before mapping to { value, label } rather than sorting by label.
5. LA04 · drop (502444bcecb64287860ca1ac557535a9):
   - Inlines List<T> type definition with inductive empty and cons.
   - Removes external import and fixes non-standard kind: "items" to kind: "cons".
   - Places drop() first so the test harness calls it as the primary entry point.
6. LA08 cards:
   - Inlines isLevel, Level, EventRecord, parseEventLine, parseLog, and simulated/valid fs helpers.
   - Places the primary card function first in each card so candidate detection selects it.
   - Populates test cases for previously empty suites.
7. LA09 cards:
   - Places runReactorTaskNTests() first in each card with local expect matcher.
   - Bundles ReactorCoolingSystem domain implementation and populates test cases.
8. LA10 Task 2, LA11 Task 2 & 3, LA12:
   - Inlines missing type definitions (Status, TaskSnapshot, Zone, etc.).
   - Adds test drivers and populates comprehensive test cases.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "dev.db"

true = True
false = False
null = None


def load_card_fields(c: sqlite3.Cursor, card_id: str) -> tuple[str, dict]:
    c.execute(
        """
        SELECT n.id, n.field_values
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        WHERE c.id = ?
        """,
        (card_id,),
    )
    row = c.fetchone()
    if not row:
        raise ValueError(f"Card {card_id} not found")
    return row[0], json.loads(row[1])


def save_card_fields(c: sqlite3.Cursor, note_id: str, fields: dict) -> None:
    c.execute(
        """
        UPDATE notes
        SET field_values = ?
        WHERE id = ?
        """,
        (json.dumps(fields, ensure_ascii=False), note_id),
    )


def patch_all():
    backup_path = DB_PATH.with_suffix(".db.bak-pre-audit-remediation")
    if not backup_path.exists():
        shutil.copy2(DB_PATH, backup_path)
        print(f"Created database backup at {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # =========================================================================
        # 1. LA10 Task 3 (5c9645f8b8e94d5a8e5a039489aef10a)
        # =========================================================================
        card_id = "5c9645f8b8e94d5a8e5a039489aef10a"
        note_id, fv = load_card_fields(c, card_id)

        fv["Back"] = """export type Status = "backlog" | "todo" | "doing" | "done";

export type TaskSnapshot = {
  title: string;
  assignee: string;
  estimatedHours: number;
  workedHours: number;
  status: Status;
};

export type ProjectSnapshot = {
  tasks: TaskSnapshot[];
};

type BoardOp =
  | { op: "addTask"; title: string; assignee: string; estimatedHours: number; worked?: number }
  | { op: "setTaskStatus"; title: string; to: Status }
  | { op: "getTasksForAssignee"; dev: string }
  | { op: "snapshotProject" }
  | { op: "logWork"; title: string; hours: number }
  | { op: "diffHoursWorked"; snapshotIndex: number };

export function runProjectBoard(ops: BoardOp[]): any[] {
  const board = new ProjectBoard();
  const snapshots: ProjectSnapshot[] = [];
  const results: any[] = [];

  for (const o of ops) {
    try {
      if (o.op === "addTask") {
        const t = new Task(o.title, o.assignee, o.estimatedHours);
        if (o.worked) t.increaseWorkedHours(o.worked);
        board.addTask(t);
        results.push({ ok: true });
      } else if (o.op === "setTaskStatus") {
        results.push(board.setTaskStatus(o.title, o.to));
      } else if (o.op === "getTasksForAssignee") {
        results.push(board.getTasksForAssignee(o.dev).map((t) => t.title));
      } else if (o.op === "snapshotProject") {
        const snap = board.snapshotProject();
        snapshots.push(snap);
        results.push(snap);
      } else if (o.op === "logWork") {
        const t = board.tasks.find((task) => task.title === o.title);
        if (!t) throw new Error("Task not found");
        results.push(t.increaseWorkedHours(o.hours));
      } else if (o.op === "diffHoursWorked") {
        const snap = snapshots[o.snapshotIndex];
        results.push(board.diffHoursWorked(snap));
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Task {
  public title: string;
  public assignee: string;
  public estimatedHours: number;
  public workedHours: number;
  public status: Status;

  public constructor(title: string, assignee: string, estimatedHours: number) {
    if (estimatedHours <= 0) {
      throw new Error("Estimated hours must be greater than 0");
    }
    this.title = title;
    this.assignee = assignee;
    this.estimatedHours = estimatedHours;
    this.workedHours = 0;
    this.status = "backlog";
  }

  public increaseWorkedHours(hours: number): number {
    if (hours <= 0) {
      throw new Error("Worked hours to add must be greater than 0");
    }
    this.workedHours += hours;
    return this.workedHours;
  }

  public setStatus(to: Status): Status {
    const prev = this.status;
    this.status = to;
    return prev;
  }

  public snapshot(): TaskSnapshot {
    return {
      title: this.title,
      assignee: this.assignee,
      estimatedHours: this.estimatedHours,
      workedHours: this.workedHours,
      status: this.status,
    };
  }
}

export class ProjectBoard {
  public tasks: Task[];

  public constructor() {
    this.tasks = [];
  }

  public addTask(task: Task): void {
    this.tasks.push(task);
  }

  public setTaskStatus(title: string, to: Status): Status {
    const task = this.tasks.find((t) => t.title === title);
    if (!task) {
      throw new Error("Task not found");
    }
    return task.setStatus(to);
  }

  public getTasksForAssignee(dev: string): Task[] {
    return this.tasks.filter((t) => t.assignee === dev);
  }

  public snapshotProject(): ProjectSnapshot {
    return {
      tasks: this.tasks.map((t) => t.snapshot()),
    };
  }

  public diffHoursWorked(snapshot: ProjectSnapshot): number {
    let diff = 0;
    for (const current of this.tasks) {
      const snapTask = snapshot.tasks.find((t) => t.title === current.title);
      if (snapTask) {
        diff += current.workedHours - snapTask.workedHours;
      } else {
        diff += current.workedHours;
      }
    }
    return diff;
  }
}"""

        fv["starter_code"] = """export type Status = "backlog" | "todo" | "doing" | "done";

export type TaskSnapshot = {
  title: string;
  assignee: string;
  estimatedHours: number;
  workedHours: number;
  status: Status;
};

export type ProjectSnapshot = {
  tasks: TaskSnapshot[];
};

type BoardOp =
  | { op: "addTask"; title: string; assignee: string; estimatedHours: number; worked?: number }
  | { op: "setTaskStatus"; title: string; to: Status }
  | { op: "getTasksForAssignee"; dev: string }
  | { op: "snapshotProject" }
  | { op: "logWork"; title: string; hours: number }
  | { op: "diffHoursWorked"; snapshotIndex: number };

export function runProjectBoard(ops: BoardOp[]): any[] {
  const board = new ProjectBoard();
  const snapshots: ProjectSnapshot[] = [];
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "addTask") {
        const t = new Task(o.title, o.assignee, o.estimatedHours);
        if (o.worked) t.increaseWorkedHours(o.worked);
        board.addTask(t);
        results.push({ ok: true });
      } else if (o.op === "setTaskStatus") {
        results.push(board.setTaskStatus(o.title, o.to));
      } else if (o.op === "getTasksForAssignee") {
        results.push(board.getTasksForAssignee(o.dev).map((t) => t.title));
      } else if (o.op === "snapshotProject") {
        const snap = board.snapshotProject();
        snapshots.push(snap);
        results.push(snap);
      } else if (o.op === "logWork") {
        const t = board.tasks.find((task) => task.title === o.title);
        if (!t) throw new Error("Task not found");
        results.push(t.increaseWorkedHours(o.hours));
      } else if (o.op === "diffHoursWorked") {
        const snap = snapshots[o.snapshotIndex];
        results.push(board.diffHoursWorked(snap));
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Task {
  public title: string;
  public assignee: string;
  public estimatedHours: number;
  public workedHours: number;
  public status: Status;

  public constructor(title: string, assignee: string, estimatedHours: number) {
    if (estimatedHours <= 0) {
      throw new Error("Estimated hours must be greater than 0");
    }
    this.title = title;
    this.assignee = assignee;
    this.estimatedHours = estimatedHours;
    this.workedHours = 0;
    this.status = "backlog";
  }

  public increaseWorkedHours(hours: number): number {
    if (hours <= 0) {
      throw new Error("Worked hours to add must be greater than 0");
    }
    this.workedHours += hours;
    return this.workedHours;
  }

  public setStatus(to: Status): Status {
    const prev = this.status;
    this.status = to;
    return prev;
  }

  public snapshot(): TaskSnapshot {
    return {
      title: this.title,
      assignee: this.assignee,
      estimatedHours: this.estimatedHours,
      workedHours: this.workedHours,
      status: this.status,
    };
  }
}

export class ProjectBoard {
  // TODO: tasks field and methods
}"""

        fv["test_cases"] = [
            {
                "input": [
                    [
                        {
                            "op": "addTask",
                            "title": "A",
                            "assignee": "alice",
                            "estimatedHours": 10,
                            "worked": 2,
                        },
                        {"op": "snapshotProject"},
                        {"op": "logWork", "title": "A", "hours": 3},
                        {
                            "op": "addTask",
                            "title": "B",
                            "assignee": "bob",
                            "estimatedHours": 5,
                            "worked": 4,
                        },
                        {"op": "diffHoursWorked", "snapshotIndex": 0},
                        {"op": "setTaskStatus", "title": "A", "to": "doing"},
                        {"op": "getTasksForAssignee", "dev": "alice"},
                    ]
                ],
                "expected": [
                    {"ok": true},
                    {
                        "tasks": [
                            {
                                "title": "A",
                                "assignee": "alice",
                                "estimatedHours": 10,
                                "workedHours": 2,
                                "status": "backlog",
                            }
                        ]
                    },
                    5,
                    {"ok": true},
                    7,
                    "backlog",
                    ["A"],
                ],
            },
            {
                "input": [
                    [
                        {"op": "setTaskStatus", "title": "NonExistent", "to": "done"},
                        {"op": "getTasksForAssignee", "dev": "nobody"},
                    ]
                ],
                "expected": [
                    {"ok": false, "error": "Task not found"},
                    [],
                ],
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA10 Task 3 (diffHoursWorked + types + test_cases)")

        # =========================================================================
        # 2. Lab 02 Task 2 extremeTides (9d0e71876020432c930b82897de2f885)
        # =========================================================================
        card_id = "9d0e71876020432c930b82897de2f885"
        note_id, fv = load_card_fields(c, card_id)
        fv["title"] = "Lab 2, T2: extremeTides(readings, fromDay, toDay, k)"
        fv["Back"] = fv["Back"].replace(
            "const byTime = (a: TideReading, b: TideReading) => (isLaterThan(a, b) ? 1 : -1);",
            "const byTime = (a: TideReading, b: TideReading) => (isLaterThan(a, b) ? 1 : isLaterThan(b, a) ? -1 : 0);",
        )
        save_card_fields(c, note_id, fv)
        print("✓ Patched Lab 02 Task 2 extremeTides (byTime comparator + retitle)")

        # =========================================================================
        # 3. Retitle mislabeled Lab 02 cards
        # =========================================================================
        # 1c6ed8bc4ad74be09c116d509f06700b -> highestReading
        note_id, fv = load_card_fields(c, "1c6ed8bc4ad74be09c116d509f06700b")
        fv["title"] = "Lab 2, T1: highestReading(readings)"
        save_card_fields(c, note_id, fv)

        # b55fe8dc0d1040e19cc7a97c4a09bbc0 -> passageWindows
        note_id, fv = load_card_fields(c, "b55fe8dc0d1040e19cc7a97c4a09bbc0")
        fv["title"] = "Lab 2, T4: passageWindows(readings, minHeight, minHours)"
        save_card_fields(c, note_id, fv)
        print("✓ Retitled Lab 02 cards (highestReading, passageWindows)")

        # =========================================================================
        # 4. stationOptions in Lab 05 Task 1 (97c82dc4419a4869beae4f3fbc9d3126)
        # =========================================================================
        note_id, fv = load_card_fields(c, "97c82dc4419a4869beae4f3fbc9d3126")
        fv["Back"] = """type StationSummary = { id: string; title: string; region: string };
type StationOption = { value: string; label: string };

function stationOptions(stations: StationSummary[]): StationOption[] {
  return [...stations]
    .sort((a, b) => a.title.localeCompare(b.title))
    .map((s) => ({
      value: s.id,
      label: `${s.title} (${s.region})`,
    }));
}"""
        save_card_fields(c, note_id, fv)
        print("✓ Patched stationOptions in Lab 05 Task 1 (sorted by title before mapping)")

        # =========================================================================
        # 5. LA04 · drop (502444bcecb64287860ca1ac557535a9)
        # =========================================================================
        note_id, fv = load_card_fields(c, "502444bcecb64287860ca1ac557535a9")
        fv[
            "Front"
        ] = """Implement `drop(section: Section, student: string): Section` using inductive `List<string>`.
Precondition: `section` satisfies Section invariants (`capacity > 0`, `length(enrolled) <= capacity`).
Postcondition: returns a new `Section` with student's first occurrence removed; unchanged if student was not enrolled.

Type definition:
```ts
type List<T> = { kind: "empty" } | { kind: "cons"; first: T; rest: List<T> };
type Section = { capacity: number; enrolled: List<string> };
```"""
        # Place drop() FIRST so candidateFunctionNames matches drop as __fn
        fv[
            "Back"
        ] = """export type List<T> = { kind: "empty" } | { kind: "cons"; first: T; rest: List<T> };
export type Section = { capacity: number; enrolled: List<string> };

export function drop(section: Section, student: string): Section {
  return {
    capacity: section.capacity,
    enrolled: removeFirst(section.enrolled, student),
  };
}

function removeFirst(lst: List<string>, item: string): List<string> {
  if (lst.kind === "empty") {
    return lst;
  }
  if (lst.first === item) {
    return lst.rest;
  }
  return { kind: "cons", first: lst.first, rest: removeFirst(lst.rest, item) };
}
// Preserves invariants: dropping a student never increases length(enrolled) or changes capacity."""

        fv[
            "starter_code"
        ] = """export type List<T> = { kind: "empty" } | { kind: "cons"; first: T; rest: List<T> };
export type Section = { capacity: number; enrolled: List<string> };

export function drop(section: Section, student: string): Section {
  // TODO: implement and test drop
  return section;
}"""

        fv["test_cases"] = [
            {
                "input": {
                    "section": {
                        "capacity": 2,
                        "enrolled": {
                            "kind": "cons",
                            "first": "alice",
                            "rest": {"kind": "empty"},
                        },
                    },
                    "student": "alice",
                },
                "expected": {
                    "capacity": 2,
                    "enrolled": {"kind": "empty"},
                },
            },
            {
                "input": {
                    "section": {
                        "capacity": 2,
                        "enrolled": {
                            "kind": "cons",
                            "first": "bob",
                            "rest": {
                                "kind": "cons",
                                "first": "alice",
                                "rest": {"kind": "empty"},
                            },
                        },
                    },
                    "student": "alice",
                },
                "expected": {
                    "capacity": 2,
                    "enrolled": {
                        "kind": "cons",
                        "first": "bob",
                        "rest": {"kind": "empty"},
                    },
                },
            },
            {
                "input": {
                    "section": {
                        "capacity": 2,
                        "enrolled": {
                            "kind": "cons",
                            "first": "bob",
                            "rest": {"kind": "empty"},
                        },
                    },
                    "student": "alice",
                },
                "expected": {
                    "capacity": 2,
                    "enrolled": {
                        "kind": "cons",
                        "first": "bob",
                        "rest": {"kind": "empty"},
                    },
                },
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA04 drop (inlined List types + kind: cons + drop first)")

        # =========================================================================
        # 6. LA08 cards
        # =========================================================================
        # f5a7dd745ab94e8380ea2b46e7d5511c: parseEventLine (parseEventLine first)
        note_id, fv = load_card_fields(c, "f5a7dd745ab94e8380ea2b46e7d5511c")
        fv["Back"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export function parseEventLine(line: string): EventRecord {
  const parts = line.split("|");
  if (parts.length !== 3) {
    throw new Error(`malformed event line: ${line}`);
  }
  const [timestamp, levelStr, message] = parts;
  if (!isLevel(levelStr)) {
    throw new Error(`malformed event line: ${line}`);
  }
  return { timestamp, level: levelStr, message };
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["starter_code"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export function parseEventLine(line: string): EventRecord {
  // TODO
  throw new Error("TODO");
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["test_cases"] = [
            {
                "input": ["2026-01-01T10:00:00Z|INFO|boot"],
                "expected": {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "level": "INFO",
                    "message": "boot",
                },
            },
            {
                "input": ["2026-01-01T10:05:00Z|WARN|low battery"],
                "expected": {
                    "timestamp": "2026-01-01T10:05:00Z",
                    "level": "WARN",
                    "message": "low battery",
                },
            },
            {
                "input": ["2026-01-01T10:10:00Z|ERROR|disk full"],
                "expected": {
                    "timestamp": "2026-01-01T10:10:00Z",
                    "level": "ERROR",
                    "message": "disk full",
                },
            },
        ]
        save_card_fields(c, note_id, fv)

        # 0b8066adb2d24524b0f21d2b34d47358: parseLog (parseLog first)
        note_id, fv = load_card_fields(c, "0b8066adb2d24524b0f21d2b34d47358")
        fv["Back"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export function parseLog(content: string): EventRecord[] {
  const lines = content.split("\\n");
  const records: EventRecord[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.length === 0) {
      continue;
    }
    try {
      records.push(parseEventLine(line));
    } catch {
      throw new Error(`line ${i + 1}: malformed`);
    }
  }
  return records;
}

function parseEventLine(line: string): EventRecord {
  const parts = line.split("|");
  if (parts.length !== 3) {
    throw new Error(`malformed event line: ${line}`);
  }
  const [timestamp, levelStr, message] = parts;
  if (!isLevel(levelStr)) {
    throw new Error(`malformed event line: ${line}`);
  }
  return { timestamp, level: levelStr, message };
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["starter_code"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export function parseLog(content: string): EventRecord[] {
  // TODO
  throw new Error("TODO");
}

function parseEventLine(line: string): EventRecord {
  const parts = line.split("|");
  if (parts.length !== 3) {
    throw new Error(`malformed event line: ${line}`);
  }
  const [timestamp, levelStr, message] = parts;
  if (!isLevel(levelStr)) {
    throw new Error(`malformed event line: ${line}`);
  }
  return { timestamp, level: levelStr, message };
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["test_cases"] = [
            {
                "input": ["t1|INFO|boot\n\nt2|WARN|low battery"],
                "expected": [
                    {"timestamp": "t1", "level": "INFO", "message": "boot"},
                    {"timestamp": "t2", "level": "WARN", "message": "low battery"},
                ],
            }
        ]
        save_card_fields(c, note_id, fv)

        # 1e4736086f2c4568a9372709997a246d: loadEventsFromFile (loadEventsFromFile first)
        note_id, fv = load_card_fields(c, "1e4736086f2c4568a9372709997a246d")
        fv["Back"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export async function loadEventsFromFile(path: string): Promise<EventRecord[]> {
  const content = await readLogFile(path);
  return parseLog(content);
}

const VIRTUAL_LOGS: Record<string, string> = {
  "/data/sample.log": "t1|INFO|boot\\nt2|WARN|low battery",
  "/data/empty.log": ""
};

export async function readLogFile(path: string): Promise<string> {
  if (path in VIRTUAL_LOGS) {
    return VIRTUAL_LOGS[path];
  }
  const fs = await import("node:fs/promises");
  return await fs.readFile(path, "utf8");
}

function parseLog(content: string): EventRecord[] {
  const lines = content.split("\\n");
  const records: EventRecord[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.length === 0) continue;
    try {
      records.push(parseEventLine(line));
    } catch {
      throw new Error(`line ${i + 1}: malformed`);
    }
  }
  return records;
}

function parseEventLine(line: string): EventRecord {
  const parts = line.split("|");
  if (parts.length !== 3) {
    throw new Error(`malformed event line: ${line}`);
  }
  const [timestamp, levelStr, message] = parts;
  if (!isLevel(levelStr)) {
    throw new Error(`malformed event line: ${line}`);
  }
  return { timestamp, level: levelStr, message };
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["starter_code"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export async function loadEventsFromFile(path: string): Promise<EventRecord[]> {
  throw new Error("TODO");
}

export async function readLogFile(path: string): Promise<string> {
  throw new Error("TODO");
}"""
        fv["test_cases"] = [
            {
                "input": ["/data/sample.log"],
                "expected": [
                    {"timestamp": "t1", "level": "INFO", "message": "boot"},
                    {"timestamp": "t2", "level": "WARN", "message": "low battery"},
                ],
            },
            {
                "input": ["/data/empty.log"],
                "expected": [],
            },
        ]
        save_card_fields(c, note_id, fv)

        # 781564f436f149b78803446a37ec82d1: loadEventsLenient (loadEventsLenient first)
        note_id, fv = load_card_fields(c, "781564f436f149b78803446a37ec82d1")
        fv["Back"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export async function loadEventsLenient(path: string): Promise<EventRecord[]> {
  return await loadEventsFromFile(path);
}

const VIRTUAL_LOGS: Record<string, string> = {
  "/data/sample.log": "t1|INFO|boot\\nt2|WARN|low battery",
  "/data/empty.log": ""
};

async function readLogFile(path: string): Promise<string> {
  if (path in VIRTUAL_LOGS) {
    return VIRTUAL_LOGS[path];
  }
  const fs = await import("node:fs/promises");
  return await fs.readFile(path, "utf8");
}

async function loadEventsFromFile(path: string): Promise<EventRecord[]> {
  const content = await readLogFile(path);
  return parseLog(content);
}

function parseLog(content: string): EventRecord[] {
  const lines = content.split("\\n");
  const records: EventRecord[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.length === 0) continue;
    try {
      records.push(parseEventLine(line));
    } catch {
      throw new Error(`line ${i + 1}: malformed`);
    }
  }
  return records;
}

function parseEventLine(line: string): EventRecord {
  const parts = line.split("|");
  if (parts.length !== 3) {
    throw new Error(`malformed event line: ${line}`);
  }
  const [timestamp, levelStr, message] = parts;
  if (!isLevel(levelStr)) {
    throw new Error(`malformed event line: ${line}`);
  }
  return { timestamp, level: levelStr, message };
}

function isLevel(str: string): str is Level {
  return str === "INFO" || str === "WARN" || str === "ERROR";
}"""
        fv["starter_code"] = """export type Level = "INFO" | "WARN" | "ERROR";
export type EventRecord = { timestamp: string; level: Level; message: string };

export async function loadEventsLenient(path: string): Promise<EventRecord[]> {
  // Refactor to propagate error rather than swallowing
  return await loadEventsFromFile(path);
}"""
        fv["test_cases"] = [
            {
                "input": ["/data/sample.log"],
                "expected": [
                    {"timestamp": "t1", "level": "INFO", "message": "boot"},
                    {"timestamp": "t2", "level": "WARN", "message": "low battery"},
                ],
            },
            {
                "input": ["/data/empty.log"],
                "expected": [],
            },
        ]
        save_card_fields(c, note_id, fv)

        # d631572f3fca44bfbc0a686720f87eed: writeSummaryFile (writeSummaryFile first)
        note_id, fv = load_card_fields(c, "d631572f3fca44bfbc0a686720f87eed")
        fv["Back"] = """import { dirname } from "node:path";

export type ImportSummary = {
  totalFiles: number;
  totalEvents: number;
  warnings: number;
  errors: number;
};

export async function runWriteSummaryFile(reportPath: string, summary: ImportSummary): Promise<{ ok: boolean; written: string }> {
  await writeSummaryFile(reportPath, summary);
  return { ok: true, written: VIRTUAL_FILES[reportPath] };
}

export async function writeSummaryFile(reportPath: string, summary: ImportSummary): Promise<void> {
  const text = formatSummary(summary);
  try {
    await writeFile(reportPath, text, "utf8");
  } catch (err) {
    if (isENOENTErr(err as Error)) {
      await mkdir(dirname(reportPath), { recursive: true });
      await writeFile(reportPath, text, "utf8");
    } else {
      throw err;
    }
  }
}

function formatSummary(summary: ImportSummary): string {
  return [
    `files=${summary.totalFiles}`,
    `events=${summary.totalEvents}`,
    `warnings=${summary.warnings}`,
    `errors=${summary.errors}`,
  ].join("\\n");
}

function isENOENTErr(error: Error): boolean {
  return (error as any).code === "ENOENT";
}

const VIRTUAL_DIRS = new Set<string>(["/reports", "."]);
const VIRTUAL_FILES: Record<string, string> = {};

async function writeFile(path: string, content: string, encoding: string): Promise<void> {
  const dir = dirname(path);
  if (!VIRTUAL_DIRS.has(dir) && !path.startsWith(".")) {
    const err: any = new Error(`ENOENT: no such file or directory, open '${path}'`);
    err.code = "ENOENT";
    throw err;
  }
  VIRTUAL_FILES[path] = content;
}

async function mkdir(path: string, options?: { recursive?: boolean }): Promise<void> {
  VIRTUAL_DIRS.add(path);
}"""
        fv["starter_code"] = """import { dirname } from "node:path";

export type ImportSummary = {
  totalFiles: number;
  totalEvents: number;
  warnings: number;
  errors: number;
};

export async function runWriteSummaryFile(reportPath: string, summary: ImportSummary): Promise<{ ok: boolean; written: string }> {
  await writeSummaryFile(reportPath, summary);
  return { ok: true, written: VIRTUAL_FILES[reportPath] };
}

export function formatSummary(summary: ImportSummary): string {
  return [
    `files=${summary.totalFiles}`,
    `events=${summary.totalEvents}`,
    `warnings=${summary.warnings}`,
    `errors=${summary.errors}`,
  ].join("\\n");
}

function isENOENTErr(error: Error): boolean {
  return (error as any).code === "ENOENT";
}

const VIRTUAL_DIRS = new Set<string>(["/reports", "."]);
const VIRTUAL_FILES: Record<string, string> = {};

async function writeFile(path: string, content: string, encoding: string): Promise<void> {
  const dir = dirname(path);
  if (!VIRTUAL_DIRS.has(dir) && !path.startsWith(".")) {
    const err: any = new Error(`ENOENT: no such file or directory, open '${path}'`);
    err.code = "ENOENT";
    throw err;
  }
  VIRTUAL_FILES[path] = content;
}

async function mkdir(path: string, options?: { recursive?: boolean }): Promise<void> {
  VIRTUAL_DIRS.add(path);
}

export async function writeSummaryFile(reportPath: string, summary: ImportSummary): Promise<void> {
  // TODO
  throw new Error("TODO");
}"""
        fv["test_cases"] = [
            {
                "input": [
                    "/reports/summary.txt",
                    {"totalFiles": 2, "totalEvents": 10, "warnings": 1, "errors": 0},
                ],
                "expected": {"ok": True, "written": "files=2\nevents=10\nwarnings=1\nerrors=0"},
            },
            {
                "input": [
                    "/newdir/summary.txt",
                    {"totalFiles": 1, "totalEvents": 5, "warnings": 0, "errors": 1},
                ],
                "expected": {"ok": True, "written": "files=1\nevents=5\nwarnings=0\nerrors=1"},
            },
        ]
        save_card_fields(c, note_id, fv)
        print(
            "✓ Patched LA08 cards (inlined helpers, types, simulated fs, test_cases, primary function first)"
        )

        # =========================================================================
        # 7. LA09 cards (runReactorTaskNTests first, local expect inside test function)
        # =========================================================================
        reactor_models_code = """
export type CoolingStatus = "stable" | "warning" | "emergency";

export type CoolingAssessment = {
  status: CoolingStatus;
  activePumps: number;
  netCoolingPerMinute: number;
  minutesToCritical: number | null;
  shouldScram: boolean;
};

export type ReactorSnapshot = {
  powerMw: number;
  coolantTempC: number;
  pumpOnline: boolean[];
};

export type ReactorCoolingSystem = {
  setPowerMw(powerMw: number): void;
  setPumpOnline(index: number, online: boolean): void;
  activePumpCount(): number;
  tick(minutes: number): void;
  evaluateSafety(): CoolingAssessment;
  startEmergencyCooldown(): void;
  snapshot(): ReactorSnapshot;
};

export function makeReactorCoolingSystem(
  pumpCount: number,
  initialTempC = 300,
  criticalTempC = 650,
): ReactorCoolingSystem {
  if (pumpCount <= 0) throw new Error("pumpCount must be positive");
  if (initialTempC < 250) throw new Error("initialTempC must be >= 250");
  if (criticalTempC <= initialTempC) throw new Error("criticalTempC must be greater than initialTempC");

  let powerMw = 0;
  let coolantTempC = initialTempC;
  const pumpOnline = Array.from({ length: pumpCount }, () => true);

  return {
    setPowerMw(mw: number): void {
      if (mw < 0 || mw > 1000) throw new Error("powerMw must be in [0, 1000]");
      powerMw = mw;
    },
    setPumpOnline(index: number, online: boolean): void {
      if (index < 0 || index >= pumpCount) throw new Error("pump index out of range");
      pumpOnline[index] = online;
    },
    activePumpCount(): number {
      return pumpOnline.filter(Boolean).length;
    },
    tick(minutes: number): void {
      if (minutes <= 0) throw new Error("minutes must be > 0");
      const active = pumpOnline.filter(Boolean).length;
      const netHeat = powerMw * 0.12 - active * 18;
      coolantTempC = Math.max(250, coolantTempC + netHeat * minutes);
    },
    evaluateSafety(): CoolingAssessment {
      const active = pumpOnline.filter(Boolean).length;
      const netHeat = powerMw * 0.12 - active * 18;
      let status: CoolingStatus;
      let shouldScram = false;
      if (coolantTempC >= criticalTempC - 20) {
        status = "emergency";
        shouldScram = true;
      } else if (active === 0 && powerMw > 0) {
        status = "emergency";
        shouldScram = true;
      } else if (netHeat > 0) {
        status = "warning";
      } else {
        status = "stable";
      }
      let minutesToCritical: number | null = null;
      if (netHeat > 0) {
        const gap = criticalTempC - coolantTempC;
        minutesToCritical = gap <= 0 ? 0 : Math.ceil(gap / netHeat);
      }
      return {
        status,
        activePumps: active,
        netCoolingPerMinute: -netHeat,
        minutesToCritical,
        shouldScram,
      };
    },
    startEmergencyCooldown(): void {
      powerMw = 0;
      for (let i = 0; i < pumpCount; i++) pumpOnline[i] = true;
    },
    snapshot(): ReactorSnapshot {
      return {
        powerMw,
        coolantTempC,
        pumpOnline: [...pumpOnline],
      };
    },
  };
}"""

        # LA09 Task 1: 2af62478e1804530b410f0afa9518301
        note_id, fv = load_card_fields(c, "2af62478e1804530b410f0afa9518301")
        fv["Back"] = (
            """export function runReactorTask1Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get true() { if (actual !== true) throw new Error("Expected true"); return true; },
        get false() { if (actual !== false) throw new Error("Expected false"); return true; },
        get null() { if (actual !== null) throw new Error("Expected null"); return true; }
      }
    }
  });

  // 1. emergency by temp boundary
  const r1 = makeReactorCoolingSystem(1, 300, 650);
  r1.setPowerMw(400);
  r1.tick(11);
  const rep1 = r1.evaluateSafety();
  expect(rep1.status).to.equal("emergency");
  expect(rep1.shouldScram).to.be.true;

  // 2. emergency when all pumps offline under power
  const r2 = makeReactorCoolingSystem(1, 300, 650);
  r2.setPowerMw(100);
  r2.setPumpOnline(0, false);
  expect(r2.evaluateSafety().status).to.equal("emergency");

  // 3. warning when net heat is positive
  const r3 = makeReactorCoolingSystem(1, 300, 650);
  r3.setPowerMw(200);
  expect(r3.evaluateSafety().status).to.equal("warning");

  // 4. stable when net heat is zero or negative
  const r4 = makeReactorCoolingSystem(1, 300, 650);
  r4.setPowerMw(150);
  expect(r4.evaluateSafety().status).to.equal("stable");

  return { passed: true, count: 4 };
}
"""
            + reactor_models_code
        )
        fv["starter_code"] = (
            """export function runReactorTask1Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get true() { if (actual !== true) throw new Error("Expected true"); return true; },
        get false() { if (actual !== false) throw new Error("Expected false"); return true; },
        get null() { if (actual !== null) throw new Error("Expected null"); return true; }
      }
    }
  });

  // TODO: Implement tests reaching all 4 branches
  throw new Error("TODO: Implement tests reaching all 4 branches");
}
"""
            + reactor_models_code
        )
        fv["test_cases"] = [{"input": [], "expected": {"passed": True, "count": 4}}]
        save_card_fields(c, note_id, fv)

        # LA09 Task 2 & 3: 4809561d7c864516a5f291da4f99fc0e
        note_id, fv = load_card_fields(c, "4809561d7c864516a5f291da4f99fc0e")
        fv["Back"] = (
            """export function runReactorTask2Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get true() { if (actual !== true) throw new Error("Expected true"); return true; },
        get false() { if (actual !== false) throw new Error("Expected false"); return true; },
        get null() { if (actual !== null) throw new Error("Expected null"); return true; }
      }
    }
  });

  const r1 = makeReactorCoolingSystem(1, 300, 650);
  r1.setPowerMw(100);
  const rep1 = r1.evaluateSafety();
  expect(rep1.status).to.equal("stable");
  expect(rep1.minutesToCritical).to.be.null;
  expect(rep1.shouldScram).to.be.false;

  const r2 = makeReactorCoolingSystem(1, 300, 650);
  r2.setPowerMw(200);
  const rep2 = r2.evaluateSafety();
  expect(rep2.status).to.equal("warning");
  expect(rep2.minutesToCritical).to.equal(59);
  expect(rep2.shouldScram).to.be.false;
  expect(rep2.activePumps).to.equal(1);
  expect(rep2.netCoolingPerMinute).to.equal(-6);

  return { passed: true, count: 2 };
}
"""
            + reactor_models_code
        )
        fv["starter_code"] = (
            """export function runReactorTask2Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get true() { if (actual !== true) throw new Error("Expected true"); return true; },
        get false() { if (actual !== false) throw new Error("Expected false"); return true; },
        get null() { if (actual !== null) throw new Error("Expected null"); return true; }
      }
    }
  });

  // TODO: Implement tests for evaluateSafety outputs and layered assertions
  throw new Error("TODO: Implement tests for evaluateSafety outputs and layered assertions");
}
"""
            + reactor_models_code
        )
        fv["test_cases"] = [{"input": [], "expected": {"passed": True, "count": 2}}]
        save_card_fields(c, note_id, fv)

        # LA09 Task 4: a11328f6669349e0a14ffff70ec8041b
        note_id, fv = load_card_fields(c, "a11328f6669349e0a14ffff70ec8041b")
        fv["Back"] = (
            """export function runReactorTask4Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      closeTo(exp: number, delta: number) {
        if (Math.abs(actual - exp) > delta) throw new Error(`Expected close to ${exp}`);
      },
      throw() {
        let threw = false;
        try { actual(); } catch { threw = true; }
        if (!threw) throw new Error("Expected function to throw");
      },
      not: {
        throw() {
          try { actual(); } catch (e) { throw new Error(`Unexpected throw: ${e}`); }
        }
      }
    }
  });

  const r1 = makeReactorCoolingSystem(1, 300, 650);
  expect(() => r1.setPowerMw(1000)).to.not.throw();
  expect(() => r1.setPowerMw(-1)).to.throw();
  expect(() => r1.setPowerMw(1001)).to.throw();

  const r2 = makeReactorCoolingSystem(2, 300, 650);
  expect(() => r2.setPumpOnline(2, false)).to.throw();
  expect(() => r2.setPumpOnline(-1, false)).to.throw();

  const r3 = makeReactorCoolingSystem(1, 300, 650);
  expect(() => r3.tick(0)).to.throw();
  expect(() => r3.tick(-5)).to.throw();

  const r4 = makeReactorCoolingSystem(2, 300, 650);
  r4.setPowerMw(0);
  r4.tick(100);
  expect(r4.snapshot().coolantTempC).to.closeTo(250, 0.001);

  return { passed: true, count: 4 };
}
"""
            + reactor_models_code
        )
        fv["starter_code"] = (
            """export function runReactorTask4Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      closeTo(exp: number, delta: number) {
        if (Math.abs(actual - exp) > delta) throw new Error(`Expected close to ${exp}`);
      },
      throw() {
        let threw = false;
        try { actual(); } catch { threw = true; }
        if (!threw) throw new Error("Expected function to throw");
      },
      not: {
        throw() {
          try { actual(); } catch (e) { throw new Error(`Unexpected throw: ${e}`); }
        }
      }
    }
  });

  // TODO: Implement boundaries and thrown errors tests
  throw new Error("TODO: Implement boundaries and thrown errors tests");
}
"""
            + reactor_models_code
        )
        fv["test_cases"] = [{"input": [], "expected": {"passed": True, "count": 4}}]
        save_card_fields(c, note_id, fv)

        # LA09 Task 5: b3b6880834c249bbaaee1aade51820f8
        note_id, fv = load_card_fields(c, "b3b6880834c249bbaaee1aade51820f8")
        fv["Back"] = (
            """export function runReactorTask5Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get false() { if (actual !== false) throw new Error("Expected false"); return true; }
      }
    }
  });

  const r = makeReactorCoolingSystem(2, 300, 650);
  r.setPowerMw(500);
  r.setPumpOnline(0, false);
  r.tick(5);

  r.startEmergencyCooldown();
  const afterCooldown = r.snapshot();
  expect(afterCooldown.powerMw).to.equal(0);
  expect(afterCooldown.pumpOnline).to.deep.equal([true, true]);

  r.tick(2);
  const finalReport = r.evaluateSafety();
  expect(finalReport.status).to.equal("stable");
  expect(finalReport.shouldScram).to.be.false;
  expect(finalReport.activePumps).to.equal(2);

  return { passed: true, count: 1 };
}
"""
            + reactor_models_code
        )
        fv["starter_code"] = (
            """export function runReactorTask5Tests(): { passed: boolean; count: number } {
  const expect = (actual: any) => ({
    to: {
      equal(exp: any) { if (actual !== exp) throw new Error(`Expected ${exp} but got ${actual}`); },
      deep: { equal(exp: any) { if (JSON.stringify(actual) !== JSON.stringify(exp)) throw new Error(`Mismatch`); } },
      be: {
        get false() { if (actual !== false) throw new Error("Expected false"); return true; }
      }
    }
  });

  // TODO: Implement stateful sequence test
  throw new Error("TODO: Implement stateful sequence test");
}
"""
            + reactor_models_code
        )
        fv["test_cases"] = [{"input": [], "expected": {"passed": True, "count": 1}}]
        save_card_fields(c, note_id, fv)
        print(
            "✓ Patched LA09 cards (inlined Reactor domain + test harnesses + test_cases, run function first)"
        )

        # =========================================================================
        # 8. LA10 Task 2: Task to a class (7a4259b89f054e24a4a7cc4dee058073)
        # =========================================================================
        note_id, fv = load_card_fields(c, "7a4259b89f054e24a4a7cc4dee058073")
        fv["Back"] = """export type Status = "backlog" | "todo" | "doing" | "done";

export type TaskSnapshot = {
  title: string;
  assignee: string;
  estimatedHours: number;
  workedHours: number;
  status: Status;
};

type TaskOp =
  | { op: "construct"; title: string; assignee: string; estimatedHours: number }
  | { op: "increaseWorkedHours"; hours: number }
  | { op: "setStatus"; to: Status }
  | { op: "snapshot" };

export function runTask(ops: TaskOp[]): any[] {
  let task: Task | null = null;
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "construct") {
        task = new Task(o.title, o.assignee, o.estimatedHours);
        results.push({ ok: true });
      } else if (!task) {
        results.push({ ok: false, error: "task not constructed" });
      } else if (o.op === "increaseWorkedHours") {
        results.push(task.increaseWorkedHours(o.hours));
      } else if (o.op === "setStatus") {
        results.push(task.setStatus(o.to));
      } else if (o.op === "snapshot") {
        results.push(task.snapshot());
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Task {
  public title: string;
  public assignee: string;
  public estimatedHours: number;
  public workedHours: number;
  public status: Status;

  public constructor(title: string, assignee: string, estimatedHours: number) {
    if (estimatedHours <= 0) {
      throw new Error("Estimated hours must be greater than 0");
    }
    this.title = title;
    this.assignee = assignee;
    this.estimatedHours = estimatedHours;
    this.workedHours = 0;
    this.status = "backlog";
  }

  public increaseWorkedHours(hours: number): number {
    if (hours <= 0) {
      throw new Error("Worked hours to add must be greater than 0");
    }
    this.workedHours += hours;
    return this.workedHours;
  }

  public setStatus(to: Status): Status {
    const prev = this.status;
    this.status = to;
    return prev;
  }

  public snapshot(): TaskSnapshot {
    return {
      title: this.title,
      assignee: this.assignee,
      estimatedHours: this.estimatedHours,
      workedHours: this.workedHours,
      status: this.status,
    };
  }
}"""
        fv["starter_code"] = """export type Status = "backlog" | "todo" | "doing" | "done";

export type TaskSnapshot = {
  title: string;
  assignee: string;
  estimatedHours: number;
  workedHours: number;
  status: Status;
};

type TaskOp =
  | { op: "construct"; title: string; assignee: string; estimatedHours: number }
  | { op: "increaseWorkedHours"; hours: number }
  | { op: "setStatus"; to: Status }
  | { op: "snapshot" };

export function runTask(ops: TaskOp[]): any[] {
  let task: Task | null = null;
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "construct") {
        task = new Task(o.title, o.assignee, o.estimatedHours);
        results.push({ ok: true });
      } else if (!task) {
        results.push({ ok: false, error: "task not constructed" });
      } else if (o.op === "increaseWorkedHours") {
        results.push(task.increaseWorkedHours(o.hours));
      } else if (o.op === "setStatus") {
        results.push(task.setStatus(o.to));
      } else if (o.op === "snapshot") {
        results.push(task.snapshot());
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Task {
  // TODO: constructor and methods
}"""
        fv["test_cases"] = [
            {
                "input": [
                    [
                        {
                            "op": "construct",
                            "title": "Feature",
                            "assignee": "alice",
                            "estimatedHours": 8,
                        },
                        {"op": "increaseWorkedHours", "hours": 3},
                        {"op": "setStatus", "to": "doing"},
                        {"op": "snapshot"},
                    ]
                ],
                "expected": [
                    {"ok": true},
                    3,
                    "backlog",
                    {
                        "title": "Feature",
                        "assignee": "alice",
                        "estimatedHours": 8,
                        "workedHours": 3,
                        "status": "doing",
                    },
                ],
            },
            {
                "input": [
                    [
                        {"op": "construct", "title": "Bad", "assignee": "bob", "estimatedHours": 0},
                        {
                            "op": "construct",
                            "title": "Good",
                            "assignee": "bob",
                            "estimatedHours": 5,
                        },
                        {"op": "increaseWorkedHours", "hours": -1},
                    ]
                ],
                "expected": [
                    {"ok": false, "error": "Estimated hours must be greater than 0"},
                    {"ok": true},
                    {"ok": false, "error": "Worked hours to add must be greater than 0"},
                ],
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA10 Task 2 (inlined Status/TaskSnapshot + runTask + test_cases)")

        # =========================================================================
        # 9. LA11 Task 2: Zone class (13df0b7b9619459cafbf5bc00c75c72a)
        # =========================================================================
        note_id, fv = load_card_fields(c, "13df0b7b9619459cafbf5bc00c75c72a")
        fv["Back"] = """type ZoneOp =
  | { op: "construct"; name: string; moisture: number; threshold: number; absorptionPerMinute: number }
  | { op: "needsWater" }
  | { op: "minutesToReachThreshold" }
  | { op: "applyWater"; minutes: number };

export function runZone(ops: ZoneOp[]): any[] {
  let zone: Zone | null = null;
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "construct") {
        zone = new Zone(o.name, o.moisture, o.threshold, o.absorptionPerMinute);
        results.push({ ok: true });
      } else if (!zone) {
        results.push({ ok: false, error: "zone not constructed" });
      } else if (o.op === "needsWater") {
        results.push(zone.needsWater());
      } else if (o.op === "minutesToReachThreshold") {
        results.push(zone.minutesToReachThreshold());
      } else if (o.op === "applyWater") {
        results.push(zone.applyWater(o.minutes));
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Zone {
  public name: string;
  public moisture: number;
  public threshold: number;
  public absorptionPerMinute: number;

  public constructor(name: string, moisture: number, threshold: number, absorptionPerMinute: number) {
    if (!name || name.length === 0) throw new Error("zone name must be non-empty");
    if (moisture < 0 || moisture > 100) throw new Error("moisture in [0,100]");
    if (threshold < 0 || threshold > 100) throw new Error("threshold in [0,100]");
    if (absorptionPerMinute <= 0) throw new Error("absorptionPerMinute must be > 0");

    this.name = name;
    this.moisture = moisture;
    this.threshold = threshold;
    this.absorptionPerMinute = absorptionPerMinute;
  }

  public needsWater(): boolean {
    return this.moisture < this.threshold;
  }

  public minutesToReachThreshold(): number {
    if (!this.needsWater()) return 0;
    return Math.ceil((this.threshold - this.moisture) / this.absorptionPerMinute);
  }

  public applyWater(minutes: number): { before: number; after: number } {
    if (minutes < 0) throw new Error("minutes cannot be negative");
    const before = this.moisture;
    this.moisture = Math.min(100, this.moisture + minutes * this.absorptionPerMinute);
    return { before, after: this.moisture };
  }
}"""
        fv["starter_code"] = """type ZoneOp =
  | { op: "construct"; name: string; moisture: number; threshold: number; absorptionPerMinute: number }
  | { op: "needsWater" }
  | { op: "minutesToReachThreshold" }
  | { op: "applyWater"; minutes: number };

export function runZone(ops: ZoneOp[]): any[] {
  let zone: Zone | null = null;
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "construct") {
        zone = new Zone(o.name, o.moisture, o.threshold, o.absorptionPerMinute);
        results.push({ ok: true });
      } else if (!zone) {
        results.push({ ok: false, error: "zone not constructed" });
      } else if (o.op === "needsWater") {
        results.push(zone.needsWater());
      } else if (o.op === "minutesToReachThreshold") {
        results.push(zone.minutesToReachThreshold());
      } else if (o.op === "applyWater") {
        results.push(zone.applyWater(o.minutes));
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

export class Zone {
  // TODO: constructor and methods
}"""
        fv["test_cases"] = [
            {
                "input": [
                    [
                        {
                            "op": "construct",
                            "name": "Lawn",
                            "moisture": 40,
                            "threshold": 70,
                            "absorptionPerMinute": 6,
                        },
                        {"op": "needsWater"},
                        {"op": "minutesToReachThreshold"},
                        {"op": "applyWater", "minutes": 5},
                        {"op": "needsWater"},
                        {"op": "minutesToReachThreshold"},
                        {"op": "applyWater", "minutes": 10},
                    ]
                ],
                "expected": [
                    {"ok": true},
                    True,
                    5,
                    {"before": 40, "after": 70},
                    False,
                    0,
                    {"before": 70, "after": 100},
                ],
            },
            {
                "input": [
                    [
                        {
                            "op": "construct",
                            "name": "",
                            "moisture": 50,
                            "threshold": 70,
                            "absorptionPerMinute": 5,
                        },
                        {
                            "op": "construct",
                            "name": "Lawn",
                            "moisture": -5,
                            "threshold": 70,
                            "absorptionPerMinute": 5,
                        },
                        {
                            "op": "construct",
                            "name": "Lawn",
                            "moisture": 50,
                            "threshold": 70,
                            "absorptionPerMinute": 0,
                        },
                    ]
                ],
                "expected": [
                    {"ok": false, "error": "zone name must be non-empty"},
                    {"ok": false, "error": "moisture in [0,100]"},
                    {"ok": false, "error": "absorptionPerMinute must be > 0"},
                ],
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA11 Task 2 (Zone + runZone + test_cases)")

        # =========================================================================
        # 10. LA11 Task 3: WaterBudgetPolicy (2a624a1083fa438ebd25fe4a3ce5a32c)
        # =========================================================================
        note_id, fv = load_card_fields(c, "2a624a1083fa438ebd25fe4a3ce5a32c")
        fv["Back"] = """export type Allocation = { zoneName: string; minutes: number };

export function runWaterBudget(
  totalBudgetMinutes: number,
  maxMinutesPerZone: number,
  zoneConfigs: Array<[string, number, number, number]>
): Allocation[] {
  const policy = new WaterBudgetPolicy(totalBudgetMinutes, maxMinutesPerZone);
  const zones = zoneConfigs.map((cfg) => new Zone(cfg[0], cfg[1], cfg[2], cfg[3]));
  return policy.allocate(zones);
}

export class Zone {
  public name: string;
  public moisture: number;
  public threshold: number;
  public absorptionPerMinute: number;

  public constructor(name: string, moisture: number, threshold: number, absorptionPerMinute: number) {
    if (!name || name.length === 0) throw new Error("zone name must be non-empty");
    if (moisture < 0 || moisture > 100) throw new Error("moisture in [0,100]");
    if (threshold < 0 || threshold > 100) throw new Error("threshold in [0,100]");
    if (absorptionPerMinute <= 0) throw new Error("absorptionPerMinute must be > 0");

    this.name = name;
    this.moisture = moisture;
    this.threshold = threshold;
    this.absorptionPerMinute = absorptionPerMinute;
  }

  public needsWater(): boolean {
    return this.moisture < this.threshold;
  }

  public minutesToReachThreshold(): number {
    if (!this.needsWater()) return 0;
    return Math.ceil((this.threshold - this.moisture) / this.absorptionPerMinute);
  }

  public applyWater(minutes: number): { before: number; after: number } {
    if (minutes < 0) throw new Error("minutes cannot be negative");
    const before = this.moisture;
    this.moisture = Math.min(100, this.moisture + minutes * this.absorptionPerMinute);
    return { before, after: this.moisture };
  }
}

export class WaterBudgetPolicy {
  public totalBudgetMinutes: number;
  public maxMinutesPerZone: number;

  public constructor(totalBudgetMinutes: number, maxMinutesPerZone: number) {
    if (totalBudgetMinutes < 0) throw new Error("totalBudgetMinutes must be >= 0");
    if (maxMinutesPerZone < 0) throw new Error("maxMinutesPerZone must be >= 0");
    if (maxMinutesPerZone > totalBudgetMinutes) throw new Error("maxMinutesPerZone must be <= totalBudgetMinutes");
    this.totalBudgetMinutes = totalBudgetMinutes;
    this.maxMinutesPerZone = maxMinutesPerZone;
  }

  public allocate(zones: Zone[]): Allocation[] {
    let remaining = this.totalBudgetMinutes;
    const allocations: Allocation[] = [];

    for (const zone of zones) {
      const needed = zone.minutesToReachThreshold();
      const granted = Math.min(needed, this.maxMinutesPerZone, remaining);
      allocations.push({ zoneName: zone.name, minutes: granted });
      remaining -= granted;
    }

    return allocations;
  }
}"""
        fv["starter_code"] = """export type Allocation = { zoneName: string; minutes: number };

export function runWaterBudget(
  totalBudgetMinutes: number,
  maxMinutesPerZone: number,
  zoneConfigs: Array<[string, number, number, number]>
): Allocation[] {
  const policy = new WaterBudgetPolicy(totalBudgetMinutes, maxMinutesPerZone);
  const zones = zoneConfigs.map((cfg) => new Zone(cfg[0], cfg[1], cfg[2], cfg[3]));
  return policy.allocate(zones);
}

export class Zone {
  public name: string;
  public moisture: number;
  public threshold: number;
  public absorptionPerMinute: number;

  public constructor(name: string, moisture: number, threshold: number, absorptionPerMinute: number) {
    this.name = name;
    this.moisture = moisture;
    this.threshold = threshold;
    this.absorptionPerMinute = absorptionPerMinute;
  }

  public minutesToReachThreshold(): number {
    return Math.max(0, Math.ceil((this.threshold - this.moisture) / this.absorptionPerMinute));
  }
}

export class WaterBudgetPolicy {
  // TODO: constructor and allocate method
}"""
        fv["test_cases"] = [
            {
                "input": [
                    30,
                    15,
                    [
                        ["Roses", 20, 80, 5],
                        ["Vegetables", 10, 90, 4],
                        ["Lawn", 30, 70, 4],
                    ],
                ],
                "expected": [
                    {"zoneName": "Roses", "minutes": 12},
                    {"zoneName": "Vegetables", "minutes": 15},
                    {"zoneName": "Lawn", "minutes": 3},
                ],
            },
            {
                "input": [
                    20,
                    10,
                    [
                        ["Cactus", 80, 50, 5],
                    ],
                ],
                "expected": [
                    {"zoneName": "Cactus", "minutes": 0},
                ],
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA11 Task 3 (inlined Zone + runWaterBudget + test_cases)")

        # =========================================================================
        # 11. LA12: HeartRateMonitor (22229a8be72347c1ba7acfa42de2a5d9)
        # =========================================================================
        note_id, fv = load_card_fields(c, "22229a8be72347c1ba7acfa42de2a5d9")
        fv["Back"] = """export type Reading = { atMs: number; bpm: number };

type MonitorOp =
  | { op: "record"; atMs: number; bpm: number }
  | { op: "currentBpm" }
  | { op: "averageBpm" }
  | { op: "maxBpm" }
  | { op: "needsAttention" }
  | { op: "mutateDefensiveCopy" };

export function runHeartRateMonitor(windowMinutes: number, ops: MonitorOp[]): any[] {
  const monitor = new HeartRateMonitor(windowMinutes);
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "record") {
        monitor.record(o.atMs, o.bpm);
        results.push({ ok: true });
      } else if (o.op === "currentBpm") {
        results.push(monitor.currentBpm());
      } else if (o.op === "averageBpm") {
        results.push(monitor.averageBpm());
      } else if (o.op === "maxBpm") {
        results.push(monitor.maxBpm());
      } else if (o.op === "needsAttention") {
        results.push(monitor.needsAttention());
      } else if (o.op === "mutateDefensiveCopy") {
        const copy = monitor.recentReadings();
        copy.push({ atMs: 999999, bpm: 99 });
        results.push(monitor.recentReadings().length);
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

const MIN_BPM = 20;
const MAX_BPM = 250;
const HIGH_BPM = 190;
const SUSTAINED_COUNT = 3;

export class HeartRateMonitor {
  private readonly windowMs: number;
  private readings: Reading[];

  public constructor(windowMinutes: number) {
    if (windowMinutes <= 0) {
      throw new Error("windowMinutes must be positive");
    }
    this.windowMs = windowMinutes * 60_000;
    this.readings = [];
  }

  public record(atMs: number, bpm: number): void {
    if (bpm < MIN_BPM || bpm > MAX_BPM) {
      throw new Error(`bpm must be in [${MIN_BPM}, ${MAX_BPM}]`);
    }
    if (this.readings.length > 0 && atMs < this.readings[this.readings.length - 1].atMs) {
      throw new Error("atMs must be non-decreasing");
    }
    this.readings.push({ atMs, bpm });
    const cutoff = atMs - this.windowMs;
    this.readings = this.readings.filter((r) => r.atMs >= cutoff);
  }

  public currentBpm(): number | null {
    if (this.readings.length === 0) return null;
    return this.readings[this.readings.length - 1].bpm;
  }

  public averageBpm(): number | null {
    if (this.readings.length === 0) return null;
    const sum = this.readings.reduce((acc, r) => acc + r.bpm, 0);
    return sum / this.readings.length;
  }

  public maxBpm(): number | null {
    if (this.readings.length === 0) return null;
    return Math.max(...this.readings.map((r) => r.bpm));
  }

  public needsAttention(): boolean {
    if (this.readings.length < SUSTAINED_COUNT) return false;
    return this.readings.every((r) => r.bpm >= HIGH_BPM);
  }

  public recentReadings(): Reading[] {
    return this.readings.map((r) => ({ ...r }));
  }
}"""
        fv["starter_code"] = """export type Reading = { atMs: number; bpm: number };

type MonitorOp =
  | { op: "record"; atMs: number; bpm: number }
  | { op: "currentBpm" }
  | { op: "averageBpm" }
  | { op: "maxBpm" }
  | { op: "needsAttention" }
  | { op: "mutateDefensiveCopy" };

export function runHeartRateMonitor(windowMinutes: number, ops: MonitorOp[]): any[] {
  const monitor = new HeartRateMonitor(windowMinutes);
  const results: any[] = [];
  for (const o of ops) {
    try {
      if (o.op === "record") {
        monitor.record(o.atMs, o.bpm);
        results.push({ ok: true });
      } else if (o.op === "currentBpm") {
        results.push(monitor.currentBpm());
      } else if (o.op === "averageBpm") {
        results.push(monitor.averageBpm());
      } else if (o.op === "maxBpm") {
        results.push(monitor.maxBpm());
      } else if (o.op === "needsAttention") {
        results.push(monitor.needsAttention());
      } else if (o.op === "mutateDefensiveCopy") {
        const copy = monitor.recentReadings();
        copy.push({ atMs: 999999, bpm: 99 });
        results.push(monitor.recentReadings().length);
      }
    } catch (e: any) {
      results.push({ ok: false, error: e.message });
    }
  }
  return results;
}

const MIN_BPM = 20;
const MAX_BPM = 250;
const HIGH_BPM = 190;
const SUSTAINED_COUNT = 3;

export class HeartRateMonitor {
  // TODO: constructor and methods
}"""
        fv["test_cases"] = [
            {
                "input": [
                    1,
                    [
                        {"op": "currentBpm"},
                        {"op": "averageBpm"},
                        {"op": "maxBpm"},
                        {"op": "needsAttention"},
                        {"op": "record", "atMs": 1000, "bpm": 70},
                        {"op": "record", "atMs": 2000, "bpm": 80},
                        {"op": "currentBpm"},
                        {"op": "averageBpm"},
                        {"op": "maxBpm"},
                        {"op": "mutateDefensiveCopy"},
                        {"op": "record", "atMs": 65000, "bpm": 90},
                        {"op": "averageBpm"},
                    ],
                ],
                "expected": [
                    None,
                    None,
                    None,
                    False,
                    {"ok": True},
                    {"ok": True},
                    80,
                    75,
                    80,
                    2,
                    {"ok": True},
                    90,
                ],
            },
            {
                "input": [
                    5,
                    [
                        {"op": "record", "atMs": 1000, "bpm": 195},
                        {"op": "record", "atMs": 2000, "bpm": 200},
                        {"op": "needsAttention"},
                        {"op": "record", "atMs": 3000, "bpm": 190},
                        {"op": "needsAttention"},
                        {"op": "record", "atMs": 2500, "bpm": 100},
                        {"op": "record", "atMs": 4000, "bpm": 300},
                    ],
                ],
                "expected": [
                    {"ok": True},
                    {"ok": True},
                    False,
                    {"ok": True},
                    True,
                    {"ok": False, "error": "atMs must be non-decreasing"},
                    {"ok": False, "error": "bpm must be in [20, 250]"},
                ],
            },
        ]
        save_card_fields(c, note_id, fv)
        print("✓ Patched LA12 (HeartRateMonitor + runHeartRateMonitor + test_cases)")

        conn.commit()
        print("\nAll patches committed successfully to backend/dev.db!")
    except Exception as e:
        conn.rollback()
        print(f"\nError applying patches: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    patch_all()
