import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def build_dependency_graph(steps: list) -> dict:
    graph = {step["step_id"]: [] for step in steps}
    for step in steps:
        for dep in step.get("depends_on", []):
            if dep in graph:
                graph[dep].append(step["step_id"])
    logger.info("Dependency graph built with %d nodes", len(graph))
    return graph


def topological_sort(graph: dict) -> list:
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

    queue = [node for node, deg in in_degree.items() if deg == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(graph):
        raise ValueError("Circular dependency detected in pipeline graph")

    logger.info("Execution order: %s", order)
    return order


def find_circular_dependencies(steps: list) -> list:
    graph = {step["step_id"]: step.get("depends_on", []) for step in steps}
    cycles = []

    def dfs(node, visited, stack, path):
        visited.add(node)
        stack.add(node)
        path.append(node)
        for dep in graph.get(node, []):
            if dep not in visited:
                dfs(dep, visited, stack, path)
            elif dep in stack:
                cycle_start = path.index(dep)
                cycles.append(path[cycle_start:] + [dep])
        path.pop()
        stack.discard(node)

    visited = set()
    for step_id in graph:
        if step_id not in visited:
            dfs(step_id, visited, set(), [])

    return cycles


def get_critical_path(steps: list, durations: dict) -> list:
    graph = {step["step_id"]: step.get("depends_on", []) for step in steps}

    earliest_finish = {}
    try:
        fwd_graph = build_dependency_graph(steps)
        order = topological_sort(fwd_graph)
    except ValueError:
        return []

    for node in order:
        deps = graph.get(node, [])
        if not deps:
            earliest_finish[node] = durations.get(node, 0)
        else:
            earliest_finish[node] = max(earliest_finish.get(d, 0) for d in deps) + durations.get(
                node, 0
            )

    makespan = max(earliest_finish.values()) if earliest_finish else 0

    critical = []
    end_node = max(earliest_finish, key=earliest_finish.get) if earliest_finish else None
    node = end_node
    while node:
        critical.insert(0, node)
        deps = graph.get(node, [])
        if not deps:
            break
        node = max(deps, key=lambda d: earliest_finish.get(d, 0))

    logger.info("Critical path: %s, estimated duration: %ds", critical, makespan)
    return critical


def validate_pipeline_config(steps: list) -> dict:
    errors = []
    step_ids = {step["step_id"] for step in steps}
    required_fields = {"step_id", "name", "depends_on"}

    for step in steps:
        missing = required_fields - step.keys()
        if missing:
            errors.append(f"Step {step.get('step_id', '?')} missing fields: {missing}")
            continue
        for dep in step["depends_on"]:
            if dep not in step_ids:
                errors.append(f"Step {step['step_id']} depends on unknown step: {dep}")

    cycles = find_circular_dependencies(steps)
    if cycles:
        for cycle in cycles:
            errors.append(f"Circular dependency: {' -> '.join(cycle)}")

    return {"valid": len(errors) == 0, "errors": errors}


if __name__ == "__main__":
    pass
