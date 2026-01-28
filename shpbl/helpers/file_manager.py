import base64
from typing_extensions import get_args
from container import exec_in_container
from helpers.helpers import (
    DIRECTORIES_TO_EXCLUDE,
    FILE_TYPES_TO_INCLUDE,
    FILES_TO_EXCLUDE,
)
from interface import ContainerName
import shlex


def read_file(
    container_name: ContainerName,
    file_path: str,
    start_line: int,
    end_line: int,
    include_line_numbers: bool = True,
) -> str:
    """
    # NOTE:
    returns raw file content (a string with actual \t tabs and \n newlines)
    - if end_line < start_line, returns only end line
    - if end_line > max lines, returns up to max lines
    - if end_line < 1, returns from start line to end of file
    """
    start_line = max(1, start_line)
    if end_line < 1:
        end_line = "$"  # sed syntax for end of file
    if include_line_numbers:
        _cmd = f"nl -ba {file_path} | sed -n '{start_line},{end_line}p'"
    else:
        _cmd = f"sed -n '{start_line},{end_line}p' {file_path}"

    result = exec_in_container(container_name, _cmd)
    if not result.success:
        raise Exception(
            f"Failed to read file {file_path} in {container_name}: {result.stderr}"
        )
    if result.stdout is None:
        raise Exception(
            f"Failed to read file {file_path} in {container_name}: No output received"
        )
    return result.stdout


def overwrite_file(
    container_name: ContainerName,
    file_path: str,
    content: str,
) -> bool:
    """
    Overwrite the content of a file in the specified container.

    Args:
        container_name: Name of the container
        file_path: Path to the file within the container
        content: New content to write to the file
    """
    # Use base64 encoding to safely pass content through shell
    # This avoids all shell escaping issues and handles special characters reliably
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    cmd = f"echo {encoded} | base64 -d > {shlex.quote(file_path)}"
    result = exec_in_container(container_name, cmd)
    if not result.success:
        raise Exception(
            f"Failed to overwrite file {file_path} in {container_name}: {result.stderr}"
        )

    return True


def delete_file(
    container_name: ContainerName,
    file_path: str,
) -> bool:
    """
    Delete a file in the specified container.

    Args:
        container_name: Name of the container
        file_path: Path to the file within the container
    """
    cmd = f"rm -f {shlex.quote(file_path)}"
    result = exec_in_container(container_name, cmd)
    if not result.success:
        raise Exception(
            f"Failed to delete file {file_path} in {container_name}: {result.stderr}"
        )

    return True


def create_directory(
    container_name: ContainerName,
    dir_path: str,
) -> bool:
    """
    Create a directory in the specified container.

    Args:
        container_name: Name of the container
        dir_path: Path to the directory within the container
    """
    cmd = f"mkdir -p {shlex.quote(dir_path)}"
    result = exec_in_container(container_name, cmd)
    if not result.success:
        raise Exception(
            f"Failed to create directory {dir_path} in {container_name}: {result.stderr}"
        )

    return True


def directory_exists(
    container_name: ContainerName,
    dir_path: str,
) -> bool:
    """
    Check if a directory exists in the specified container.

    Args:
        container_name: Name of the container
        dir_path: Path to the directory within the container
    """
    cmd = f"test -d {shlex.quote(dir_path)}"
    result = exec_in_container(container_name, cmd)
    return result.success


def build_find_grep_cmd(extended_regex_query: str) -> str:
    quoted_pattern = shlex.quote(extended_regex_query)

    # --- directories prune ---
    dirs = set(DIRECTORIES_TO_EXCLUDE)
    dir_terms: list[str] = []

    if ".*" in dirs:
        dir_terms.append("-name '.*'")  # any dot-directory
        dirs.remove(".*")

    for d in sorted(dirs):
        dir_terms.append(f"-name {shlex.quote(d)}")

    dir_prune_clause = (
        "-mindepth 1 -type d \\( " + " -o ".join(dir_terms) + " \\) -prune -o"
        if dir_terms
        else "-mindepth 1"
    )

    # --- files exclude (by basename) ---
    files = sorted(FILES_TO_EXCLUDE)
    file_prune_clause = ""
    if files:
        file_terms = [f"-name {shlex.quote(f)}" for f in files]
        # If file matches any excluded name, drop it; otherwise continue
        file_prune_clause = "-type f \\( " + " -o ".join(file_terms) + " \\) -prune -o "

    # --- include extensions ---
    ext_patterns = [f"-name '*{ext}'" for ext in sorted(FILE_TYPES_TO_INCLUDE)]
    include_clause = "-type f \\( " + " -o ".join(ext_patterns) + " \\)"

    cmd = (
        f"find . {dir_prune_clause} "
        f"{file_prune_clause}"
        f"{include_clause} "
        f"-exec grep -nH -i -E -e {quoted_pattern} {{}} + 2>/dev/null"
    )
    return cmd


def build_find_grep_fileline_cmd(extended_regex_query: str) -> str:
    """
    Build a find + grep command that returns file:line for each match.
    """
    return build_find_grep_cmd(extended_regex_query) + " | cut -d: -f1-2"


def create_line_ranges_with_context(
    line_numbers: list[int], context_lines: int
) -> list[tuple[int, int]]:
    """
    Create optimized line ranges with context, merging overlapping ranges.

    Args:
        line_numbers: List of line numbers to create ranges for
        context_lines: Number of context lines to include before and after each line

    Returns:
        List of (start_line, end_line) tuples representing merged ranges

    Example:
        >>> create_line_ranges_with_context([5, 7, 15], context_lines=2)
        [(3, 9), (13, 17)]  # Lines 5 and 7 overlap, so they're merged

    Limits:
        - if after the first pass there are secondary overlaps, they are not merged again
    """
    if not line_numbers:
        return []

    # Create initial ranges with context
    ranges = []
    for line in line_numbers:
        start = max(1, line - context_lines)
        end = line + context_lines
        ranges.append((start, end))

    # Sort ranges by start position
    ranges.sort()

    # Merge overlapping ranges
    merged = [ranges[0]]
    for current_start, current_end in ranges[1:]:
        last_start, last_end = merged[-1]

        # If ranges overlap or touch, merge them
        if current_start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # No overlap, add as new range
            merged.append((current_start, current_end))

    return merged


def dry_search(extended_regex_query: str, context_lines: int) -> dict:
    """
    Before searching and reciving actual content, do a dry run to get file:line matches.
    This helps caller narrow their search results without consuming too many tokens.
    After this the caller can request search with file paths and line ranges.
    """
    valid_containers = list(get_args(ContainerName))
    search_res: dict = {}
    errors: list[str] = []

    # first find files and line numbers matching the query
    cmd = build_find_grep_fileline_cmd(extended_regex_query)
    for container in valid_containers:
        file_path_lines = {}
        result = exec_in_container(container, cmd)

        if result.success:
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                # Each line is file:line_number:match
                parts = line.split(":")
                file_path = parts[0].strip()
                line_number = int(parts[1].strip())
                file_path_lines.setdefault(file_path, set()).add(line_number)
            search_res[container] = file_path_lines
        else:
            errors.append(f"{container}: {result.stderr or 'Command failed'}")

    # create line_ranges within context lines
    combined_line_ranges: dict = {}
    for container, file_dict in search_res.items():
        combined_line_ranges[container] = {}
        for file_path, line_numbers in file_dict.items():
            line_ranges = create_line_ranges_with_context(
                sorted(line_numbers), context_lines
            )
            combined_line_ranges[container][file_path] = line_ranges

    # add container names to file paths becuase model expects that
    _merged_result = {}
    for container, file_dict in combined_line_ranges.items():
        for file_path, line_ranges in file_dict.items():
            full_path = f"{container}/{file_path.lstrip('./')}"
            _merged_result[full_path] = line_ranges
    return _merged_result


def search(
    extended_regex_query: str,
    context_lines: int,
    file_path: str,
    include_line_numbers: bool,
) -> list[str]:
    """
    Perform a search for the given query within a specific file path, returning matched lines with context.
    """
    valid_containers = list(get_args(ContainerName))
    container = file_path.split("/")[0]  # get container name only
    assert (
        container in valid_containers
    ), "Container could not be determined from file_path"

    # first dry_search to find files and line numbers matching the query
    _dry_search_res = dry_search(extended_regex_query, context_lines)

    # filter to only requested file_path
    filtered_result: list[str] = []
    _search_res_at_file: dict = _dry_search_res.get(file_path, {})
    if _search_res_at_file:
        filtered_result.append(
            read_file(
                container_name=container,
                file_path=file_path[len(container) + 1 :],  # remove container prefix
                start_line=_search_res_at_file[0][0],
                end_line=_search_res_at_file[-1][1],
                include_line_numbers=include_line_numbers,
            )
        )
    return filtered_result
