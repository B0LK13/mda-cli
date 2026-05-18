"""Batch pre-flight summaries for TUI confirmation (issue #31 / WP-B5)."""

from __future__ import annotations

from dataclasses import dataclass

from mda_cli.core import LARGE_BATCH_TOTAL_BYTES, LARGE_FILE_BYTES, Job


@dataclass(frozen=True)
class BatchPreflightSummary:
    """Heuristic summary shown before a TUI batch run."""

    file_count: int
    output_mode: str
    total_bytes: int
    warnings: tuple[str, ...]
    est_input_tokens: int
    est_output_tokens: int
    est_total_tokens: int


def build_batch_preflight(
    jobs: list[Job],
    *,
    max_tokens: int,
    output_mode: str,
) -> BatchPreflightSummary:
    """Compute file count, size totals, and token budget warnings for a batch."""
    total = 0
    warnings: list[str] = []
    for job in jobs:
        try:
            st = job.src.stat()
        except OSError:
            continue
        total += st.st_size
        if st.st_size >= LARGE_FILE_BYTES:
            warnings.append(
                f"Large source {job.src.name} ({st.st_size // 1024} KiB); "
                "consider splitting before MDA."
            )
    if total >= LARGE_BATCH_TOTAL_BYTES:
        warnings.append(
            f"Batch input is large (~{total // 1024} KiB total); "
            "watch for context or rate limits."
        )

    est_input_tokens = max(1, total // 4) if jobs else 0
    per_file_budget = max(1, max_tokens)
    est_output_tokens = per_file_budget * len(jobs) if jobs else 0
    est_total = est_input_tokens + est_output_tokens

    if jobs and max_tokens > 0 and est_input_tokens > per_file_budget * len(jobs):
        warnings.append(
            f"Estimated input tokens (~{est_input_tokens:,}) may exceed "
            f"--max-tokens ({per_file_budget:,}) per file for {len(jobs)} job(s)."
        )
    if est_total > 200_000:
        warnings.append(
            f"Rough token budget ~{est_total:,} "
            f"(input ~{est_input_tokens:,} + output up to {est_output_tokens:,}); "
            "API cost may be significant."
        )

    return BatchPreflightSummary(
        file_count=len(jobs),
        output_mode=output_mode,
        total_bytes=total,
        warnings=tuple(warnings),
        est_input_tokens=est_input_tokens,
        est_output_tokens=est_output_tokens,
        est_total_tokens=est_total,
    )


def format_preflight_message(summary: BatchPreflightSummary) -> str:
    """Multi-line body for the pre-flight modal."""
    lines = [
        f"Files selected: {summary.file_count}",
        f"Output mode: {summary.output_mode}",
        f"Input size: ~{summary.total_bytes // 1024} KiB total",
        (
            f"Token estimate (rough): input ~{summary.est_input_tokens:,}, "
            f"output up to {summary.est_output_tokens:,}, "
            f"total ~{summary.est_total_tokens:,}"
        ),
    ]
    if summary.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  • {w}" for w in summary.warnings)
    else:
        lines.append("")
        lines.append("No size or token warnings for this batch.")
    lines.append("")
    lines.append("Continue with MDA batch? (y / Enter = continue, n / Esc = cancel)")
    return "\n".join(lines)
