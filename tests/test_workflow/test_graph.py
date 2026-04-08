"""Tests for workflow graph renderer."""

from agenttree.workflow.graph import render_workflow_graph, render_workflow_list
from agenttree.workflow.types import (
    ConditionSpec,
    EdgeSpec,
    NodeSpec,
    WorkflowDefinition,
)


# ── Fixture helpers ──────────────────────────────────────────────────────────


def _make_workflow():
    """Simple branching workflow: start → yes / no."""
    return WorkflowDefinition(
        name="test_wf",
        description="A test workflow",
        start_node="start",
        nodes={
            "start": NodeSpec(
                prompt="Begin",
                tools=["bash"],
                edges=[
                    EdgeSpec(target="yes", when=ConditionSpec(signal="approve")),
                    EdgeSpec(target="no", when=ConditionSpec(signal="reject")),
                ],
            ),
            "yes": NodeSpec(prompt="Approved path"),
            "no": NodeSpec(prompt="Rejected path"),
        },
    )


def _make_linear_workflow():
    """Linear chain: a → b → c."""
    return WorkflowDefinition(
        name="linear",
        description="Linear workflow",
        start_node="a",
        nodes={
            "a": NodeSpec(prompt="Step A", edges=[EdgeSpec(target="b")]),
            "b": NodeSpec(prompt="Step B", edges=[EdgeSpec(target="c")]),
            "c": NodeSpec(prompt="Step C"),
        },
    )


def _make_self_loop_workflow():
    """Node with a self-loop: start → loop (loop→loop via dig, loop→done via finish)."""
    return WorkflowDefinition(
        name="self_loop",
        description="Self-loop test",
        start_node="start",
        nodes={
            "start": NodeSpec(
                prompt="Init",
                edges=[EdgeSpec(target="loop")],
            ),
            "loop": NodeSpec(
                prompt="Processing",
                edges=[
                    EdgeSpec(target="loop", when=ConditionSpec(signal="dig")),
                    EdgeSpec(target="done", when=ConditionSpec(signal="finish")),
                ],
            ),
            "done": NodeSpec(prompt="Finished"),
        },
    )


def _make_diamond_workflow():
    """Diamond pattern: a → b / c → d (merge)."""
    return WorkflowDefinition(
        name="diamond",
        description="Diamond merge pattern",
        start_node="a",
        nodes={
            "a": NodeSpec(
                prompt="Start",
                edges=[
                    EdgeSpec(target="b", when=ConditionSpec(signal="left")),
                    EdgeSpec(target="c", when=ConditionSpec(signal="right")),
                ],
            ),
            "b": NodeSpec(prompt="Left path", edges=[EdgeSpec(target="d")]),
            "c": NodeSpec(prompt="Right path", edges=[EdgeSpec(target="d")]),
            "d": NodeSpec(prompt="Merged"),
        },
    )


def _make_skip_layer_workflow():
    """Skip-layer pattern (the explore_codebase pattern):
    a → b → c → d, and a → d (bypass through b and c).
    """
    return WorkflowDefinition(
        name="skip_layer",
        description="Skip-layer bypass test",
        start_node="a",
        nodes={
            "a": NodeSpec(
                prompt="Start",
                edges=[
                    EdgeSpec(target="b", when=ConditionSpec(signal="deep")),
                    EdgeSpec(target="d", when=ConditionSpec(signal="skip")),
                ],
            ),
            "b": NodeSpec(
                prompt="Middle 1",
                edges=[EdgeSpec(target="c")],
            ),
            "c": NodeSpec(
                prompt="Middle 2",
                edges=[EdgeSpec(target="d")],
            ),
            "d": NodeSpec(prompt="End"),
        },
    )


def _make_back_edge_workflow():
    """Back-edge (non-self-loop): a → b → c, c → a."""
    return WorkflowDefinition(
        name="back_edge",
        description="Back-edge loop test",
        start_node="a",
        nodes={
            "a": NodeSpec(
                prompt="Entry",
                edges=[EdgeSpec(target="b")],
            ),
            "b": NodeSpec(
                prompt="Process",
                edges=[EdgeSpec(target="c")],
            ),
            "c": NodeSpec(
                prompt="Check",
                edges=[
                    EdgeSpec(target="a", when=ConditionSpec(signal="retry")),
                    EdgeSpec(target="done", when=ConditionSpec(signal="ok")),
                ],
            ),
            "done": NodeSpec(prompt="Done"),
        },
    )


def _make_multi_merge_workflow():
    """Three-way branch merging to one terminal: hub → x / y / z → end."""
    return WorkflowDefinition(
        name="multi_merge",
        description="Three-way merge",
        start_node="hub",
        nodes={
            "hub": NodeSpec(
                prompt="Decide",
                edges=[
                    EdgeSpec(target="x", when=ConditionSpec(signal="opt_x")),
                    EdgeSpec(target="y", when=ConditionSpec(signal="opt_y")),
                    EdgeSpec(target="z", when=ConditionSpec(signal="opt_z")),
                ],
            ),
            "x": NodeSpec(prompt="Path X", edges=[EdgeSpec(target="end")]),
            "y": NodeSpec(prompt="Path Y", edges=[EdgeSpec(target="end")]),
            "z": NodeSpec(prompt="Path Z", edges=[EdgeSpec(target="end")]),
            "end": NodeSpec(prompt="Terminal"),
        },
    )


def _make_explore_codebase_workflow():
    """The exact explore_codebase pattern that originally rendered badly:
    scan → assess → deep_dive (self-loop) → summarize, assess → summarize.
    """
    return WorkflowDefinition(
        name="explore_codebase",
        description="Explore a codebase: scan structure, find key files, summarize architecture",
        start_node="scan",
        nodes={
            "scan": NodeSpec(
                prompt="Scan project",
                tools=["glob", "bash"],
                edges=[EdgeSpec(target="assess")],
            ),
            "assess": NodeSpec(
                prompt="Assess project",
                edges=[
                    EdgeSpec(target="deep_dive", when=ConditionSpec(signal="needs_investigation")),
                    EdgeSpec(target="summarize", when=ConditionSpec(signal="well_documented")),
                    EdgeSpec(target="summarize", when=ConditionSpec(signal="trivial")),
                ],
            ),
            "deep_dive": NodeSpec(
                prompt="Investigate",
                tools=["glob", "bash"],
                edges=[
                    EdgeSpec(target="deep_dive", when=ConditionSpec(signal="dig_deeper")),
                    EdgeSpec(target="summarize", when=ConditionSpec(signal="enough")),
                ],
            ),
            "summarize": NodeSpec(prompt="Write summary"),
        },
    )


# ── Basic rendering tests ────────────────────────────────────────────────────


def test_render_graph_contains_nodes():
    graph = render_workflow_graph(_make_workflow())
    assert "start start" in graph
    assert "yes end" in graph
    assert "no end" in graph


def test_render_graph_contains_edges():
    graph = render_workflow_graph(_make_workflow())
    assert "approve" in graph
    assert "reject" in graph


def test_render_graph_contains_title():
    graph = render_workflow_graph(_make_workflow())
    assert "Workflow: test_wf" in graph
    assert "A test workflow" in graph


def test_render_list_empty():
    text = render_workflow_list([])
    assert "No workflows" in text


def test_render_list_with_workflows():
    text = render_workflow_list([_make_workflow()])
    assert "1. test_wf" in text
    assert "3 nodes" in text
    assert "2 terminal" in text


# ── Linear workflow ──────────────────────────────────────────────────────────


def test_linear_nodes_appear_in_order():
    graph = render_workflow_graph(_make_linear_workflow())
    a_pos = graph.index("a start")
    b_pos = graph.index("│" + " b ".center(12) + "│")  # middle of box
    c_pos = graph.index("c end")
    assert a_pos < b_pos < c_pos


def test_linear_no_horizontal_bar():
    """Linear graphs should have no branching bar (├ or ┤)."""
    graph = render_workflow_graph(_make_linear_workflow())
    assert "├" not in graph
    assert "┤" not in graph


def test_linear_has_arrows():
    graph = render_workflow_graph(_make_linear_workflow())
    assert "▼" in graph


# ── Self-loop ────────────────────────────────────────────────────────────────


def test_self_loop_back_edge_drawn():
    """Self-loop should produce a back-edge indicator (◄ arrow into the loop node)."""
    graph = render_workflow_graph(_make_self_loop_workflow())
    assert "◄" in graph


def test_self_loop_labels():
    graph = render_workflow_graph(_make_self_loop_workflow())
    assert "dig" in graph
    assert "finish" in graph


def test_self_loop_nodes():
    graph = render_workflow_graph(_make_self_loop_workflow())
    assert "start start" in graph
    assert "loop" in graph
    assert "done end" in graph


# ── Diamond (branch + merge) ────────────────────────────────────────────────


def test_diamond_all_nodes():
    graph = render_workflow_graph(_make_diamond_workflow())
    assert "a start" in graph
    assert "d end" in graph
    # b and c should both appear
    assert " b " in graph
    assert " c " in graph


def test_diamond_branch_labels():
    graph = render_workflow_graph(_make_diamond_workflow())
    assert "left" in graph
    assert "right" in graph


def test_diamond_branching_bar():
    """Diamond should have a branching bar with ├ and ┤."""
    graph = render_workflow_graph(_make_diamond_workflow())
    assert "├" in graph or "┬" in graph


def test_diamond_merge_arrow():
    """Both b and c should have arrows (▼) pointing to d."""
    graph = render_workflow_graph(_make_diamond_workflow())
    # d should appear below the branch
    assert "▼" in graph


# ── Skip-layer (bypass) ─────────────────────────────────────────────────────


def test_skip_layer_no_box_corruption():
    """Bypass edge from a→d must not draw through intermediate boxes b or c."""
    graph = render_workflow_graph(_make_skip_layer_workflow())
    lines = graph.split("\n")
    for line in lines:
        # Box content should never have ┼ artifacts
        if " b " in line or " c " in line:
            # The box line should only contain box-drawing chars and the label
            assert "┼" not in line, f"Box corruption in: {line!r}"


def test_skip_layer_bypass_indicator():
    """Bypass edge should use ► (exit) and ◄ (entry) arrows."""
    graph = render_workflow_graph(_make_skip_layer_workflow())
    assert "►" in graph  # bypass exit from source
    assert "◄" in graph  # bypass entry into target


def test_skip_layer_all_nodes():
    graph = render_workflow_graph(_make_skip_layer_workflow())
    assert "a start" in graph
    assert "d end" in graph
    assert " b " in graph
    assert " c " in graph


def test_skip_layer_labels():
    graph = render_workflow_graph(_make_skip_layer_workflow())
    assert "deep" in graph
    assert "skip" in graph


# ── Back-edge (non-self-loop) ────────────────────────────────────────────────


def test_back_edge_loop_indicator():
    """Non-self back-edge (c → a) should use ◄ arrow into target."""
    graph = render_workflow_graph(_make_back_edge_workflow())
    assert "◄" in graph


def test_back_edge_label():
    graph = render_workflow_graph(_make_back_edge_workflow())
    assert "retry" in graph
    assert "ok" in graph


def test_back_edge_all_nodes():
    graph = render_workflow_graph(_make_back_edge_workflow())
    assert "a start" in graph
    assert "done end" in graph


# ── Multi-merge ──────────────────────────────────────────────────────────────


def test_multi_merge_all_nodes():
    graph = render_workflow_graph(_make_multi_merge_workflow())
    assert "hub start" in graph
    assert "end end" in graph
    assert " x " in graph
    assert " y " in graph
    assert " z " in graph


def test_multi_merge_labels():
    graph = render_workflow_graph(_make_multi_merge_workflow())
    assert "opt_x" in graph
    assert "opt_y" in graph
    assert "opt_z" in graph


def test_multi_merge_branching():
    """Three-way branch should produce a branching bar."""
    graph = render_workflow_graph(_make_multi_merge_workflow())
    assert "├" in graph or "┬" in graph


# ── explore_codebase (regression) ────────────────────────────────────────────


def test_explore_codebase_no_box_corruption():
    """The original bug: deep_dive and summarize at same layer caused ┼ in boxes."""
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    lines = graph.split("\n")
    for line in lines:
        if "deep_dive" in line and "│" in line and "┼" in line:
            # ┼ inside a box line is corruption
            box_start = line.find("┌")
            box_end = line.find("┐")
            if box_start != -1 and box_end != -1:
                box_content = line[box_start : box_end + 1]
                assert "┼" not in box_content, f"Box corruption: {box_content!r}"


def test_explore_codebase_bypass_routing():
    """assess→summarize should bypass deep_dive using ► and ◄ indicators."""
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    assert "►" in graph  # bypass exit from assess
    assert "◄" in graph  # bypass entry into summarize (or self-loop entry)


def test_explore_codebase_all_nodes():
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    assert "scan start" in graph
    assert "assess" in graph
    assert "deep_dive" in graph
    assert "summarize end" in graph


def test_explore_codebase_all_labels():
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    assert "needs_investigation" in graph
    assert "well_documented" in graph  # might be combined with "trivial"
    assert "dig_deeper" in graph
    assert "enough" in graph


def test_explore_codebase_self_loop():
    """deep_dive should have a self-loop back-edge."""
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    # The self-loop should show ◄ on the deep_dive line
    lines = graph.split("\n")
    deep_dive_lines = [l for l in lines if "deep_dive" in l]
    assert any("◄" in l for l in deep_dive_lines), "Self-loop arrow missing on deep_dive"


def test_explore_codebase_summarize_not_at_same_layer_as_deep_dive():
    """summarize should be below deep_dive (different vertical position)."""
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    lines = graph.split("\n")
    deep_dive_row = None
    summarize_row = None
    for i, line in enumerate(lines):
        if "deep_dive" in line and "│" in line:
            deep_dive_row = i
        if "summarize" in line and "│" in line:
            summarize_row = i
    assert deep_dive_row is not None
    assert summarize_row is not None
    assert summarize_row > deep_dive_row, "summarize should be below deep_dive"


def test_explore_codebase_junction_preserves_downward_edge():
    """The back-edge junction at deep_dive's bottom should use ├ (not └)
    to preserve the downward connection to summarize."""
    graph = render_workflow_graph(_make_explore_codebase_workflow())
    assert "├" in graph  # junction connecting down + right


# ── Layer assignment ─────────────────────────────────────────────────────────


def test_layer_assignment_longest_path():
    """Nodes reachable via longer paths should be at deeper layers."""
    from agenttree.workflow.graph import _assign_layers

    wf = _make_explore_codebase_workflow()
    layers = _assign_layers(wf)
    assert layers["scan"] == 0
    assert layers["assess"] == 1
    assert layers["deep_dive"] == 2
    assert layers["summarize"] == 3  # NOT 2 (the old BFS bug)


def test_layer_assignment_diamond():
    from agenttree.workflow.graph import _assign_layers

    wf = _make_diamond_workflow()
    layers = _assign_layers(wf)
    assert layers["a"] == 0
    assert layers["b"] == 1
    assert layers["c"] == 1
    assert layers["d"] == 2  # merge point


def test_layer_assignment_back_edge():
    """Back-edges should not affect layer assignment of forward-reachable nodes."""
    from agenttree.workflow.graph import _assign_layers

    wf = _make_back_edge_workflow()
    layers = _assign_layers(wf)
    assert layers["a"] == 0
    assert layers["b"] == 1
    assert layers["c"] == 2
    assert layers["done"] == 3


# ── Edge classification ──────────────────────────────────────────────────────


def test_edge_classification_self_loop():
    from agenttree.workflow.graph import _assign_layers, _classify_edges

    wf = _make_self_loop_workflow()
    layers = _assign_layers(wf)
    fwd, back = _classify_edges(wf, layers)
    back_pairs = [(s, t) for s, t, _ in back]
    assert ("loop", "loop") in back_pairs


def test_edge_classification_back_edge():
    from agenttree.workflow.graph import _assign_layers, _classify_edges

    wf = _make_back_edge_workflow()
    layers = _assign_layers(wf)
    fwd, back = _classify_edges(wf, layers)
    back_pairs = [(s, t) for s, t, _ in back]
    assert ("c", "a") in back_pairs
    fwd_pairs = [(s, t) for s, t, _ in fwd]
    assert ("c", "done") in fwd_pairs


# ── Empty / minimal ──────────────────────────────────────────────────────────


def test_single_node_workflow():
    """A workflow with one node (no edges) should render without error."""
    wf = WorkflowDefinition(
        name="minimal",
        start_node="only",
        nodes={"only": NodeSpec(prompt="Just me")},
    )
    graph = render_workflow_graph(wf)
    assert "only start,end" in graph
    assert "Workflow: minimal" in graph
