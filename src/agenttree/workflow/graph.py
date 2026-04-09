"""ASCII graph renderer for workflow definitions."""

from __future__ import annotations

from agenttree.workflow.types import ConditionType, WorkflowDefinition

# Layout constants
_STD_BOX_H = 3   # standard box height (top border, content, bottom border)
_PAR_BOX_H = 5   # parallel box height (border, name, separator, branches, border)
_V_GAP = 5       # rows between layer boxes for edge routing
_H_GAP = 6       # horizontal gap between boxes in same layer
_BACK_MARGIN = 4  # right margin for back-edge loops
_MAX_LABEL = 26  # max chars for an edge label in the graph


def _condition_label(cond, *, verbose: bool = False) -> str:
    """Format a ConditionSpec into a label.

    ``verbose=False`` (default): compact for edge labels (e.g. ``approve``).
    ``verbose=True``: readable for branch descriptions (e.g. ``if output matches "pattern"``).
    """
    if cond.type == ConditionType.SIGNAL:
        lbl = f'if signal "{cond.value}"' if verbose else cond.value
    elif cond.type == ConditionType.OUTPUT_MATCHES:
        lbl = f'if output matches "{cond.value}"' if verbose else f'match:"{cond.value}"'
    elif cond.type == ConditionType.TOOL_WAS_CALLED:
        lbl = f"if tool {cond.value} called" if verbose else f"tool:{cond.value}"
    else:
        lbl = "always" if verbose else ""
    if cond.negate:
        lbl = f"NOT {lbl}" if verbose else f"!{lbl}"
    return lbl


def _edge_label(edge) -> str:
    return _condition_label(edge.condition, verbose=False)


def _fmt_label(lbl: str) -> str:
    """Wrap a label in brackets so it's visually distinct from node names."""
    if not lbl:
        return ""
    truncated = lbl[:_MAX_LABEL] if len(lbl) > _MAX_LABEL else lbl
    return f"[{truncated}]"


def _is_parallel(name: str, wf: WorkflowDefinition) -> bool:
    return wf.nodes[name].parallel is not None


def _node_height(name: str, wf: WorkflowDefinition) -> int:
    if not _is_parallel(name, wf):
        return _STD_BOX_H
    # 3 fixed rows (top border, name, separator) + branch lines + bottom border
    n_lines = len(_branch_lines(name, wf))
    return 3 + max(n_lines, 1) + 1


def _node_tag(name: str, wf: WorkflowDefinition) -> str:
    parts = []
    if name == wf.start_node:
        parts.append("start")
    if wf.is_terminal(name):
        parts.append("end")
    node = wf.nodes[name]
    if node.parallel is not None:
        parts.append("parallel")
    if node.skills:
        parts.append(f"s:{len(node.skills)}")
    if node.mcp_servers:
        parts.append(f"mcp:{','.join(node.mcp_servers)}")
    if parts:
        return " " + ",".join(parts)
    return ""


def _branch_lines(name: str, wf: WorkflowDefinition) -> list[str]:
    """Build readable branch listing lines for a parallel node.

    Returns a list of lines. If everything fits on one line (under 60 chars),
    returns one line.  Otherwise one branch per line.
    """
    node = wf.nodes[name]
    if node.parallel is None:
        return []
    try:
        spec = node.get_parallel_spec()
    except Exception:
        return ["(invalid parallel spec)"]

    entries: list[str] = []
    for bname, branch in spec.branches.items():
        label = bname
        if branch.condition.type != ConditionType.ALWAYS:
            label += f" ({_condition_label(branch.condition, verbose=True)})"
        if branch.requires_approval:
            label += " [requires user approval]"
        entries.append(label)

    one_line = " | ".join(entries)
    if len(one_line) <= 60:
        return [one_line]
    # One branch per line
    return entries


# ── Character grid ──────────────────────────────────────────────────────────


class _Grid:
    """Mutable 2-D character buffer."""

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]

    def _ok(self, r: int, c: int) -> bool:
        return 0 <= r < self.h and 0 <= c < self.w

    def put(self, r: int, c: int, ch: str) -> None:
        if self._ok(r, c):
            self.g[r][c] = ch

    def puts(self, r: int, c: int, s: str) -> None:
        for i, ch in enumerate(s):
            self.put(r, c + i, ch)

    def box(self, r: int, c: int, w: int, label: str) -> None:
        self.puts(r, c, "┌" + "─" * (w - 2) + "┐")
        self.puts(r + 1, c, "│" + label.center(w - 2) + "│")
        self.puts(r + 2, c, "└" + "─" * (w - 2) + "┘")

    def parallel_box(self, r: int, c: int, w: int, label: str, branch_lines: list[str]) -> None:
        """Draw a double-border box for parallel nodes."""
        self.puts(r, c, "╔" + "═" * (w - 2) + "╗")
        self.puts(r + 1, c, "║" + label.center(w - 2) + "║")
        self.puts(r + 2, c, "╠" + "─" * (w - 2) + "╣")
        for i, line in enumerate(branch_lines):
            text = line[:w - 4]  # leave room for "║ " prefix and " ║" suffix
            self.puts(r + 3 + i, c, "║ " + text.ljust(w - 4) + " ║")
        bottom = r + 3 + len(branch_lines)
        self.puts(bottom, c, "╚" + "═" * (w - 2) + "╝")

    def vline(self, col: int, r0: int, r1: int) -> None:
        for r in range(r0, r1 + 1):
            cur = self.g[r][col] if self._ok(r, col) else " "
            if cur == "─":
                self.put(r, col, "┼")
            elif cur in (" ", "│"):
                self.put(r, col, "│")

    def hline(self, row: int, c0: int, c1: int) -> None:
        lo, hi = min(c0, c1), max(c0, c1)
        for c in range(lo, hi + 1):
            cur = self.g[row][c] if self._ok(row, c) else " "
            if cur == "│":
                self.put(row, c, "┼")
            elif cur in (" ", "─"):
                self.put(row, c, "─")

    def to_str(self) -> str:
        out: list[str] = []
        for row in self.g:
            out.append("".join(row).rstrip())
        while out and not out[-1]:
            out.pop()
        return "\n".join(out)


# ── Layout helpers ──────────────────────────────────────────────────────────


def _assign_layers(wf: WorkflowDefinition) -> dict[str, int]:
    """Longest-path layer assignment (pushes nodes as deep as possible).

    Uses DFS to detect back-edges (cycles), then computes the longest
    forward-path distance from the start node so that nodes connected
    by forward edges never share a layer.
    """
    # Step 1: DFS to discover reachable nodes and identify back-edges
    back_edges: set[tuple[str, str]] = set()
    visited: set[str] = set()
    on_stack: set[str] = set()

    def _dfs(name: str) -> None:
        visited.add(name)
        on_stack.add(name)
        for edge in wf.nodes[name].edges:
            if edge.target in on_stack:
                back_edges.add((name, edge.target))
            elif edge.target not in visited:
                _dfs(edge.target)
        on_stack.discard(name)

    _dfs(wf.start_node)

    # Step 2: Build forward-edge adjacency and compute in-degrees
    fwd: dict[str, list[str]] = {n: [] for n in visited}
    in_deg: dict[str, int] = {n: 0 for n in visited}
    for name in visited:
        for edge in wf.nodes[name].edges:
            if edge.target in visited and (name, edge.target) not in back_edges:
                fwd[name].append(edge.target)
                in_deg[edge.target] += 1

    # Step 3: Topological sort (Kahn's algorithm)
    topo: list[str] = []
    queue = [n for n in visited if in_deg[n] == 0]
    while queue:
        name = queue.pop(0)
        topo.append(name)
        for tgt in fwd[name]:
            in_deg[tgt] -= 1
            if in_deg[tgt] == 0:
                queue.append(tgt)

    # Step 4: Longest path on the forward-edge DAG
    layers: dict[str, int] = {n: 0 for n in visited}
    for name in topo:
        for tgt in fwd[name]:
            layers[tgt] = max(layers[tgt], layers[name] + 1)

    return layers


def _classify_edges(wf: WorkflowDefinition, layers: dict[str, int]):
    """Split edges into forward (down or same layer) and back (loops to earlier layer)."""
    fwd: list[tuple[str, str, str]] = []
    back: list[tuple[str, str, str]] = []
    for name, node in wf.nodes.items():
        for edge in node.edges:
            lbl = _edge_label(edge)
            src_layer = layers.get(name, 0)
            tgt_layer = layers.get(edge.target, 0)
            if tgt_layer < src_layer or edge.target == name:
                # Strictly earlier layer, or self-loop
                back.append((name, edge.target, lbl))
            else:
                fwd.append((name, edge.target, lbl))
    return fwd, back


# ── Main renderer ───────────────────────────────────────────────────────────


def render_workflow_graph(wf: WorkflowDefinition) -> str:
    """Render a workflow as a layered ASCII graph.

    Handles branching, merging, and loops (back-edges shown on the right).
    """
    layers = _assign_layers(wf)
    if not layers:
        return f"  Workflow: {wf.name}\n  (empty)"

    fwd_edges, back_edges = _classify_edges(wf, layers)

    max_layer = max(layers.values())

    # Group nodes by layer
    groups: dict[int, list[str]] = {i: [] for i in range(max_layer + 1)}
    for name, layer in sorted(layers.items(), key=lambda x: x[1]):
        groups[layer].append(name)

    # Compute box widths and heights
    box_w: dict[str, int] = {}
    box_h: dict[str, int] = {}
    _branch_cache: dict[str, list[str]] = {}  # cache branch lines per node
    for name in wf.nodes:
        tag = _node_tag(name, wf)
        min_w = len(name + tag) + 4
        if _is_parallel(name, wf):
            lines = _branch_lines(name, wf)
            _branch_cache[name] = lines
            max_line = max((len(l) for l in lines), default=0)
            min_w = max(min_w, max_line + 6)  # 6 = "║ " + " ║" + padding
        box_w[name] = max(14, min_w)
        box_h[name] = _node_height(name, wf)

    # Layer total widths (for centering)
    layer_total_w: dict[int, int] = {}
    for li, names in groups.items():
        layer_total_w[li] = sum(box_w[n] for n in names) + _H_GAP * max(len(names) - 1, 0)

    content_w = max(layer_total_w.values()) if layer_total_w else 40
    has_back = len(back_edges) > 0
    back_space = (_BACK_MARGIN + 3 * len(back_edges) + _MAX_LABEL + 2) if has_back else 0
    # Extra width for forward edges that bypass intermediate layers
    _n_skip = sum(
        1 for _s, _t, _ in fwd_edges
        if layers.get(_t, 0) > layers.get(_s, 0) + 1
        and any(groups.get(_ml, []) for _ml in range(layers.get(_s, 0) + 1, layers.get(_t, 0)))
    )
    bypass_extra = (_n_skip * 3 + _MAX_LABEL + 4) if _n_skip > 0 else 0
    grid_w = content_w + back_space + bypass_extra + 6

    # Header
    header_rows = 3 if wf.description else 2

    # Per-layer max height (tallest box in each layer)
    layer_max_h: dict[int, int] = {}
    for li, names in groups.items():
        layer_max_h[li] = max(box_h[n] for n in names) if names else _STD_BOX_H

    # Grid height: header + sum(layer heights) + gaps * v_gap + bottom padding
    total_box_h = sum(layer_max_h.get(i, _STD_BOX_H) for i in range(max_layer + 1))
    grid_h = header_rows + total_box_h + max_layer * _V_GAP + 1

    # Compute positions: top-left (row, col) for each node box
    pos: dict[str, tuple[int, int]] = {}
    for li, names in groups.items():
        total_w = layer_total_w[li]
        start_x = (content_w - total_w) // 2 + 2
        # Cumulative y offset
        y = header_rows
        for prev_li in range(li):
            y += layer_max_h.get(prev_li, _STD_BOX_H) + _V_GAP
        x = start_x
        for name in names:
            pos[name] = (y, x)
            x += box_w[name] + _H_GAP

    # Node center-x helper
    def cx(name: str) -> int:
        return pos[name][1] + box_w[name] // 2

    def bot(name: str) -> int:
        return pos[name][0] + box_h[name]  # row just below the box bottom border

    def top(name: str) -> int:
        return pos[name][0]  # row of box top border

    # ── Build grid ──

    grid = _Grid(grid_w, grid_h)

    # Header (truncate to grid width)
    title = f"Workflow: {wf.name}"
    grid.puts(0, 2, title[:grid_w - 4])
    if wf.description:
        grid.puts(1, 2, wf.description[:grid_w - 4])

    # Draw boxes
    for name in wf.nodes:
        if name not in pos:
            continue
        r, c = pos[name]
        tag = _node_tag(name, wf)
        if _is_parallel(name, wf):
            grid.parallel_box(r, c, box_w[name], name + tag, _branch_cache.get(name, []))
        else:
            grid.box(r, c, box_w[name], name + tag)

    # Max right edge of any box (for bypass/back-edge routing)
    max_right = max((pos[n][1] + box_w[n] for n in pos), default=0)

    # Collect bypass forward edges (drawn after back-edges)
    bypass_fwd: list[tuple[str, str, str]] = []

    # ── Draw forward edges ──
    # Group forward edges by source to handle branching
    from collections import defaultdict

    # Consolidate edges: if multiple edges go from same source to same target,
    # merge their labels (e.g. classify -> report_fix via "critical"/"major"/"minor")
    _raw_src: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for src, tgt, lbl in fwd_edges:
        _raw_src[src].append((tgt, lbl))

    src_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for src, pairs in _raw_src.items():
        # Group by target
        by_target: dict[str, list[str]] = defaultdict(list)
        for tgt, lbl in pairs:
            by_target[tgt].append(lbl)
        for tgt, labels in by_target.items():
            combined = "/".join(l for l in labels if l) or ""
            src_edges[src].append((tgt, combined))

    for src, targets in src_edges.items():
        src_col = cx(src)
        src_bottom = bot(src)

        # Separate same-layer targets from below-layer targets
        same_layer = [(t, l) for t, l in targets if layers.get(t, -1) == layers.get(src, -1)]
        below_layer = [(t, l) for t, l in targets if layers.get(t, -1) != layers.get(src, -1)]

        # Draw same-layer edges as horizontal arrows
        for tgt, lbl in same_layer:
            src_r = pos[src][0] + 1  # middle of source box
            src_right = pos[src][1] + box_w[src]  # col after source box right border
            tgt_left = pos[tgt][1] - 1  # col before target box left border
            if tgt_left > src_right:
                grid.hline(src_r, src_right, tgt_left - 1)
                grid.put(src_r, tgt_left, "►")
            elif tgt_left < src_right:
                # Target is to the left
                tgt_right = pos[tgt][1] + box_w[tgt]
                src_left = pos[src][1] - 1
                grid.hline(src_r, tgt_right, src_left + 1)
                grid.put(src_r, src_left, "◄")
            if lbl:
                flbl = _fmt_label(lbl)
                mid_c = (src_right + tgt_left) // 2 - len(flbl) // 2
                grid.puts(src_r - 1, max(0, mid_c), flbl)

        targets = below_layer
        if not targets:
            continue

        # Separate bypass targets: edges that skip layers with intermediate boxes
        if len(targets) > 1:
            near_targets = []
            for tgt, lbl in targets:
                src_l = layers.get(src, 0)
                tgt_l = layers.get(tgt, 0)
                needs_bypass = False
                if tgt_l > src_l + 1:
                    for mid_l in range(src_l + 1, tgt_l):
                        for mid_name in groups.get(mid_l, []):
                            mid_left = pos[mid_name][1]
                            mid_right = mid_left + box_w[mid_name] - 1
                            if mid_left <= cx(tgt) <= mid_right:
                                needs_bypass = True
                                break
                        if needs_bypass:
                            break
                if needs_bypass:
                    bypass_fwd.append((src, tgt, lbl))
                else:
                    near_targets.append((tgt, lbl))
            targets = near_targets
            if not targets:
                continue

        if len(targets) == 1:
            # Single edge — straight down
            tgt, lbl = targets[0]
            tgt_col = cx(tgt)
            tgt_top = top(tgt)

            if abs(src_col - tgt_col) <= 2:
                # Close enough — draw straight down to target center
                grid.vline(tgt_col, src_bottom, tgt_top - 2)
                grid.put(tgt_top - 1, tgt_col, "▼")
            else:
                # Route: down, horizontal, down
                route_r = src_bottom + 1
                grid.vline(src_col, src_bottom, route_r)
                grid.hline(route_r, src_col, tgt_col)
                # Junctions
                if tgt_col > src_col:
                    grid.put(route_r, src_col, "└")
                    grid.put(route_r, tgt_col, "┐")
                else:
                    grid.put(route_r, src_col, "┘")
                    grid.put(route_r, tgt_col, "┌")
                grid.vline(tgt_col, route_r + 1, tgt_top - 2)
                grid.put(tgt_top - 1, tgt_col, "▼")

            # Label (1 row below box to avoid collision with back-edge routing)
            if lbl:
                label_r = src_bottom + 1
                label_c = min(src_col, tgt_col) + 2
                grid.puts(label_r, label_c, _fmt_label(lbl))
        else:
            # Multiple edges — branching
            tgt_cols = [(cx(t), t, l) for t, l in targets]
            tgt_cols.sort(key=lambda x: x[0])

            # Vertical down from source
            route_r = src_bottom + 1
            grid.vline(src_col, src_bottom, route_r)

            # Horizontal bar spanning all targets
            leftmost = tgt_cols[0][0]
            rightmost = tgt_cols[-1][0]
            grid.hline(route_r, leftmost, rightmost)

            # Junction at source column
            if leftmost <= src_col <= rightmost:
                grid.put(route_r, src_col, "┬")
            elif src_col < leftmost:
                grid.put(route_r, src_col, "└")
            else:
                grid.put(route_r, src_col, "┘")

            # Endpoints
            grid.put(route_r, leftmost, "├" if leftmost < rightmost else "│")
            grid.put(route_r, rightmost, "┤" if rightmost > leftmost else "│")

            # Vertical down to each target + labels
            for i, (tc, tgt, lbl) in enumerate(tgt_cols):
                tgt_top = top(tgt)
                # Junction on the horizontal bar
                if tc != leftmost and tc != rightmost:
                    grid.put(route_r, tc, "┬")

                grid.vline(tc, route_r + 1, tgt_top - 2)
                grid.put(tgt_top - 1, tc, "▼")

                # Label: place just above the target box
                if lbl:
                    flbl = _fmt_label(lbl)
                    lbl_c = max(0, tc - len(flbl) // 2)
                    grid.puts(tgt_top - 2, lbl_c, flbl)

    # ── Draw back-edges (loops) on the right side ──
    for i, (src, tgt, lbl) in enumerate(back_edges):
        loop_col = max_right + 3 + i * 3

        src_bot = pos[src][0] + box_h[src]  # row just below source box
        tgt_r = pos[tgt][0] + 1         # middle row of target box
        tgt_right = pos[tgt][1] + box_w[tgt]  # right edge of target box

        # Vertical down from source bottom to one row below
        src_hook_r = src_bot
        grid.vline(loop_col, tgt_r + 1, src_hook_r)

        # Horizontal from below source box to loop column
        src_cx = cx(src)
        # Check for downward edge BEFORE hline overwrites │ with ┼
        has_down = grid.g[src_hook_r][src_cx] in ("│", "├") if grid._ok(src_hook_r, src_cx) else False
        grid.hline(src_hook_r, src_cx, loop_col - 1)
        grid.put(src_hook_r, src_cx, "├" if has_down else "└")
        grid.put(src_hook_r, loop_col, "┘")

        # Corner at target and horizontal to target box right edge
        grid.put(tgt_r, loop_col, "┐")
        grid.hline(tgt_r, tgt_right + 1, loop_col - 1)
        grid.put(tgt_r, tgt_right, "◄")

        # Label on the vertical segment
        if lbl:
            mid_r = (tgt_r + src_hook_r) // 2
            grid.puts(mid_r, loop_col + 2, _fmt_label(lbl))

    # ── Draw bypass (skip-layer) forward edges on the right side ──
    # These exit from the source box's right side to avoid conflicting
    # with forward-edge labels below the box.
    if bypass_fwd:
        bypass_start = max_right + 3 + len(back_edges) * 3 + 3
        for i, (src, tgt, lbl) in enumerate(bypass_fwd):
            bp_col = bypass_start + i * 3

            src_r = pos[src][0] + 1   # middle row of source box
            src_right = pos[src][1] + box_w[src]  # one past right border
            tgt_r = pos[tgt][0] + 1   # middle row of target box
            tgt_right = pos[tgt][1] + box_w[tgt]  # one past right border

            # Exit from source right side → horizontal to bypass column
            grid.put(src_r, src_right, "►")
            if src_right + 1 <= bp_col - 1:
                grid.hline(src_r, src_right + 1, bp_col - 1)
            grid.put(src_r, bp_col, "┐")

            # Vertical down to target level
            if src_r + 1 <= tgt_r - 1:
                grid.vline(bp_col, src_r + 1, tgt_r - 1)

            # Corner and horizontal to target right edge
            grid.put(tgt_r, bp_col, "┘")
            if tgt_right + 1 <= bp_col - 1:
                grid.hline(tgt_r, tgt_right + 1, bp_col - 1)
            grid.put(tgt_r, tgt_right, "◄")

            # Label on the vertical segment
            if lbl:
                mid_r = (src_r + tgt_r) // 2
                grid.puts(mid_r, bp_col + 2, _fmt_label(lbl))

    return grid.to_str()


def render_workflow_list(workflows: list[WorkflowDefinition]) -> str:
    """Render a numbered list of available workflows."""
    if not workflows:
        return (
            "No workflows discovered.\n\n"
            "Place .yaml files in ~/.agenttree/workflows/ or <project>/.agenttree/workflows/"
        )

    lines = ["Available workflows:", ""]
    for i, w in enumerate(workflows, 1):
        node_count = len(w.nodes)
        terminal_count = sum(1 for n in w.nodes if w.is_terminal(n))
        parallel_count = sum(1 for n in w.nodes if w.nodes[n].parallel is not None)
        desc = w.description or "(no description)"
        lines.append(f"  {i}. {w.name}")
        lines.append(f"     {desc}")
        info = f"     {node_count} nodes, {terminal_count} terminal"
        if parallel_count:
            lines.append(f"{info}, {parallel_count} parallel")
        else:
            lines.append(info)
        lines.append("")

    lines.append("Use /workflows to browse interactively.")
    lines.append("Use /workflow <name> <context> to run a workflow.")
    return "\n".join(lines)
