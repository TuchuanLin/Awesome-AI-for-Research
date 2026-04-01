#!/usr/bin/env python3

from __future__ import annotations

from datetime import date
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote


TOOLING = Path(__file__).resolve().parent
ROOT = TOOLING.parent
TEMPLATES = TOOLING / "templates"


class MiniJinja:
    include_pattern = re.compile(r'{%\s*include\s+"([^"]+)"\s*%}')
    variable_pattern = re.compile(r'{{\s*([a-zA-Z0-9_.-]+)\s*}}')

    def __init__(self, root: Path) -> None:
        self.root = root

    def render_path(self, template_path: str, context: dict[str, Any]) -> str:
        return self._render_text((self.root / template_path).read_text(encoding="utf-8"), context)

    def _render_text(self, text: str, context: dict[str, Any]) -> str:
        def include_replacer(match: re.Match[str]) -> str:
            include_path = self.root / match.group(1)
            return self._render_text(include_path.read_text(encoding="utf-8"), context)

        with_includes = self.include_pattern.sub(include_replacer, text)

        def variable_replacer(match: re.Match[str]) -> str:
            value = resolve_context(context, match.group(1))
            return "" if value is None else str(value)

        return self.variable_pattern.sub(variable_replacer, with_includes)


def resolve_context(context: dict[str, Any], key: str) -> Any:
    current: Any = context
    for part in key.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def load_jsonish(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    value = text.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_date_value(item: dict[str, Any]) -> int:
        iso_date = item.get("sort_date") or f"{item['year']:04d}-01-01"
        return int(iso_date.replace("-", ""))

    return sorted(entries, key=lambda item: (-sort_date_value(item), item["title"].lower()))


def shields_badge(label: str, value: str, color: str, link: str | None = None) -> str:
    def escape_badge_text(text: str) -> str:
        return text.replace("-", "--").replace("_", "__").replace(" ", "_")

    badge = (
        "https://img.shields.io/badge/"
        f"{quote(escape_badge_text(label))}-{quote(escape_badge_text(value))}-{color}?style=flat-square"
    )
    image = f"![{label}: {value}]({badge})"
    if link:
        return f"[{image}]({link})"
    return image


def shields_badge_html(
    label: str,
    value: str,
    color: str,
    link: str | None = None,
    logo: str | None = None,
) -> str:
    def escape_badge_text(text: str) -> str:
        return text.replace("-", "--").replace("_", "__").replace(" ", "_")

    badge = (
        "https://img.shields.io/badge/"
        f"{quote(escape_badge_text(label))}-{quote(escape_badge_text(value))}-{color}?style=flat-square"
    )
    if logo:
        badge += f"&logo={quote(logo)}"
    image = f'<img alt="{label}: {value}" src="{badge}" />'
    if link:
        return f'<a href="{link}">{image}</a>'
    return image


def markdown_link(label: str, target: str) -> str:
    return f"[{label}]({target})"


def html_link(label: str, target: str) -> str:
    return f'<a href="{target}">{label}</a>'


def render_links(links: dict[str, str]) -> str:
    order = [
        ("paper", "Paper"),
        ("repo", "Repo"),
        ("project", "Project"),
        ("benchmark", "Benchmark"),
        ("blog", "Blog"),
    ]
    parts = [markdown_link(label, links[key]) for key, label in order if key in links]
    return " · ".join(parts)


def render_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_tag_chips(tags: list[str]) -> str:
    return " ".join(f"`{tag}`" for tag in tags)


def rel_path(from_file: Path, to_file: Path) -> str:
    return os.path.relpath(to_file, start=from_file.parent).replace(os.sep, "/")


def catalog_permalink(output_file: Path, anchor: str) -> str:
    return f"{rel_path(output_file, ROOT / 'docs/catalog.md')}#{anchor}"


def entry_permalink(output_file: Path, entry: dict[str, Any]) -> str:
    return catalog_permalink(output_file, entry["anchor"])


def benchmark_permalink(output_file: Path, benchmark: dict[str, Any]) -> str:
    return catalog_permalink(output_file, benchmark["anchor"])


def group_link(output_file: Path, target_path: str, anchor: str) -> str:
    return f"{rel_path(output_file, ROOT / target_path)}#{anchor}"


def enrich_entries(
    entries: list[dict[str, Any]],
    section_index: dict[str, dict[str, Any]],
    level_index: dict[str, dict[str, Any]],
    research_stage_index: dict[str, dict[str, Any]],
    domain_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in entries:
        section_meta = section_index[item["section"]]
        level_meta = level_index[item["level"]]
        stage_focus_meta = research_stage_index[item["stage_focus"]] if item["stage_focus"] else None
        stage_secondary_meta = research_stage_index[item["stage_secondary"]] if item["stage_secondary"] else None
        domains = [domain_index[slug] for slug in item["domains"]]
        enriched_item = dict(item)
        enriched_item["anchor"] = item["id"]
        enriched_item["section_meta"] = section_meta
        enriched_item["section_label"] = section_meta["label"]
        enriched_item["kind"] = "entry"
        enriched_item["level_meta"] = level_meta
        enriched_item["level_label"] = level_meta["label"]
        enriched_item["level_short"] = level_meta["label"].split()[0]
        enriched_item["stage_focus_meta"] = stage_focus_meta
        enriched_item["stage_secondary_meta"] = stage_secondary_meta
        enriched_item["stage_focus_label"] = stage_focus_meta["label"] if stage_focus_meta else None
        enriched_item["stage_secondary_label"] = stage_secondary_meta["label"] if stage_secondary_meta else None
        enriched_item["domain_meta"] = domains
        enriched_item["domain_label"] = " · ".join(domain["label"] for domain in domains)
        enriched_item["links_md"] = render_links(item["links"])
        enriched_item["tags_md"] = render_tag_chips(item["tags"])
        enriched_item["page"] = section_meta["page"]
        enriched.append(enriched_item)
    return enriched


def enrich_benchmarks(benchmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        item = dict(benchmark)
        item["anchor"] = benchmark["id"]
        item["kind"] = "benchmark"
        item["links_md"] = render_links(benchmark["links"])
        item["tags_md"] = render_tag_chips(benchmark["tags"])
        item["types_md"] = " · ".join(f"`{item}`" for item in benchmark["types"])
        enriched.append(item)
    return sort_entries(enriched)


def item_matches_group(item: dict[str, Any], key: str, slug: str) -> bool:
    if key == "research_stage":
        return item.get("stage_focus") == slug or item.get("stage_secondary") == slug
    value = item.get(key)
    return slug in value if isinstance(value, list) else value == slug


def build_entry_anchor(entry: dict[str, Any], anchor_prefix: str | None = None) -> str:
    if anchor_prefix:
        return f"{anchor_prefix}--{entry['anchor']}"
    return entry["anchor"]


def render_entry_meta_line(entry: dict[str, Any]) -> str:
    parts = [entry["section_label"], entry["level_short"]]
    if entry["stage_focus_label"]:
        parts.append(entry["stage_focus_label"])
    parts.append(entry["evidence"])
    return " · ".join(parts)


def render_benchmark_meta_line(benchmark: dict[str, Any]) -> str:
    return " · ".join([*benchmark["types"], benchmark["evidence"]])


def render_entry_card(
    renderer: MiniJinja,
    entry: dict[str, Any],
    include_anchor: bool,
    anchor_prefix: str | None = None,
) -> str:
    anchor_name = build_entry_anchor(entry, anchor_prefix) if include_anchor else None
    return renderer.render_path(
        "partials/entry_card.md.j2",
        {
            "anchor_md": f"<a id=\"{anchor_name}\"></a>\n" if anchor_name else "",
            "title": entry["title"],
            "year": entry["year"],
            "meta_line": render_entry_meta_line(entry),
            "links_md": entry["links_md"],
            "summary": entry["summary"],
            "tags_md": entry["tags_md"],
        },
    ).strip()


def render_benchmark_detail_block(benchmark: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"<a id=\"{benchmark['anchor']}\"></a>",
            f"### {benchmark['title']} ({benchmark['year']})",
            "",
            render_benchmark_meta_line(benchmark),
            "",
            f"**Links:** {benchmark['links_md']}",
            "",
            f"**Summary:** {benchmark['summary']}",
            "",
            benchmark["tags_md"],
        ]
    )


def render_catalog_items(
    renderer: MiniJinja,
    entries: list[dict[str, Any]],
    benchmarks: list[dict[str, Any]],
) -> str:
    mixed_items = sort_entries([*entries, *benchmarks])
    blocks = []
    for item in mixed_items:
        if item["kind"] == "entry":
            blocks.append(render_entry_card(renderer, item, include_anchor=True))
        else:
            blocks.append(render_benchmark_detail_block(item))
    return "\n\n---\n\n".join(blocks)


def render_featured_items(entries: list[dict[str, Any]], output_file: Path) -> str:
    lines: list[str] = []
    for entry in sort_entries(entries):
        links = [
            markdown_link(entry["title"], entry_permalink(output_file, entry)),
            f"({entry['year']})",
            f"`{entry['section_label']}`",
            f"`{entry['level_short']}`",
        ]
        line = f"- **{' '.join(links)}**\n  {entry['summary']} {render_links(entry['links'])}"
        lines.append(line)
    return "\n".join(lines)


def build_stats(
    entries: list[dict[str, Any]],
    benchmarks: list[dict[str, Any]],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    research_stage_counts = {
        stage["slug"]: sum(item_matches_group(entry, "research_stage", stage["slug"]) for entry in entries)
        for stage in taxonomy["research_stages"]
    }
    level_counts = {
        level["slug"]: sum(entry["level"] == level["slug"] for entry in entries)
        for level in taxonomy["levels"]
    }
    section_counts = {
        section["slug"]: (
            len(benchmarks)
            if section["slug"] == "benchmarks-evaluation"
            else sum(entry["section"] == section["slug"] for entry in entries)
        )
        for section in taxonomy["sections"]
    }
    domain_counts = {
        domain["slug"]: sum(domain["slug"] in entry["domains"] for entry in entries)
        for domain in taxonomy["domains"]
    }
    return {
        "entries": len(entries),
        "benchmarks": len(benchmarks),
        "research_stages": research_stage_counts,
        "levels": level_counts,
        "sections": section_counts,
        "domains": domain_counts,
    }


def write_generated(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.strip() + "\n"
    path.write_text(normalized, encoding="utf-8")


def render_research_stage_nav(
    research_stages: list[dict[str, Any]],
    stats: dict[str, Any],
    output_file: Path,
) -> str:
    chips = []
    for stage in research_stages:
        target = group_link(output_file, "docs/views/by-research-stage.md", stage["slug"])
        chips.append(markdown_link(f"`{stage['label']} · {stats['research_stages'][stage['slug']]}`", target))
    midpoint = (len(chips) + 1) // 2
    return "  \n".join([" · ".join(chips[:midpoint]), " · ".join(chips[midpoint:])])


def render_intelligence_nav(
    levels: list[dict[str, Any]],
    stats: dict[str, Any],
    output_file: Path,
) -> str:
    lines = []
    for index, level in enumerate(levels, start=1):
        target = group_link(output_file, "docs/views/by-intelligence-level.md", level["slug"])
        label = f"`{level['label']} · {stats['levels'][level['slug']]}`"
        lines.append(
            f"{index}. {markdown_link(label, target)} - {level['description']}"
        )
    return "\n".join(lines)


def render_section_nav(
    sections: list[dict[str, Any]],
    stats: dict[str, Any],
    output_file: Path,
) -> str:
    header = "| Section | Focus | Count |\n| --- | --- | --- |"
    rows = []
    for section in sections:
        target = group_link(output_file, section["page"], slugify(section["label"]))
        section_label = f"{section['emoji']} {section['label']}"
        rows.append(
            f"| {markdown_link(section_label, target)} | {section['short']} | {stats['sections'][section['slug']]} |"
        )
    return "\n".join([header, *rows])


def render_start_here(output_file: Path) -> str:
    end_to_end = rel_path(output_file, ROOT / "docs/sections/end-to-end-research-systems.md")
    experimentation_agent_methods = rel_path(output_file, ROOT / "docs/sections/experimentation-agent-methods.md")
    self_evolving = rel_path(output_file, ROOT / "docs/views/self-evolving.md")
    by_domain = rel_path(output_file, ROOT / "docs/views/by-domain.md")
    benchmarks_index = rel_path(output_file, ROOT / "docs/benchmarks/index.md")

    blocks = [
        "1. **If you care about AI for Research systems**  \n"
        f"   Start with {markdown_link('End-to-End Research Systems', end_to_end)} and {markdown_link('Benchmarks & Evaluation', benchmarks_index)} to compare what representative AI-for-research systems actually cover and how they are evaluated.",
        "2. **If you care about AI for Research in a vertical domain**  \n"
        f"   Start with {markdown_link('By Domain', by_domain)}, then move to the relevant section pages and {markdown_link('Benchmarks & Evaluation', benchmarks_index)} for the systems and evaluation anchors that matter in that discipline.",
        "3. **If you care about self-evolving systems**  \n"
        f"   Start with {markdown_link('Self-Evolving Systems', self_evolving)}, then use {markdown_link('Experimentation & Agent Methods', experimentation_agent_methods)} to compare explicit self-improvement loops, experiment-improve systems, and reusable agent methods.",
    ]
    return "\n\n".join(blocks)


def render_benchmark_highlights(benchmarks: list[dict[str, Any]], output_file: Path) -> str:
    lines = []
    for benchmark in sort_entries(benchmarks):
        lines.append(
            f"- **{markdown_link(benchmark['title'], benchmark_permalink(output_file, benchmark))}** ({benchmark['year']}) · {benchmark['types_md']}\n"
            f"  {benchmark['summary']}"
        )
    return "\n".join(lines)


def render_benchmark_types(types: list[dict[str, Any]]) -> str:
    return "\n".join(f"- `{item['label']}` - {item['description']}" for item in types)


def render_taxonomy_links(output_file: Path) -> str:
    taxonomy_path = rel_path(output_file, ROOT / "docs/taxonomy.md")
    return "\n".join(
        [
            f"- {markdown_link('Research stage taxonomy', taxonomy_path + '#research-stage-taxonomy')} for the macro stage map and fine-grained stage legend.",
            f"- {markdown_link('Role taxonomy', taxonomy_path + '#role-taxonomy')} for the L1 to L3 human-tool-system ladder, with `self-evolving` tracked as a tag.",
            f"- {markdown_link('Application domain taxonomy', taxonomy_path + '#application-domain-taxonomy')} for discipline-oriented navigation across artificial intelligence, biomedical, chemistry, computer science, general, materials science, math, physics, and social science.",
            f"- {markdown_link('Benchmark taxonomy', taxonomy_path + '#benchmark-taxonomy')} for the compressed evaluation vocabulary used across benchmark pages.",
            f"- {markdown_link('Evidence taxonomy', taxonomy_path + '#evidence-level-taxonomy')} for how we interpret evidence strength across papers, reports, benchmarks, and repositories.",
        ]
    )


def render_contributing_md() -> str:
    return "\n".join(
        [
            "This repository is curated, and contributions are welcome when they improve the source data.",
            "",
            "The most helpful contributions are:",
            "- adding a new entry",
            "- correcting links or metadata for an existing entry",
            "",
            "Please keep the scope narrow: recent, high-signal AI4Research systems over historical completeness.",
            "",
            "When contributing:",
            "- prefer primary sources for papers, repositories, benchmark pages, and project sites",
            "- edit the source data rather than generated Markdown pages",
            "- leave featured selections, taxonomy files, and templates unchanged unless a broader change is clearly necessary",
            "- regenerate the repository with `python3 tooling/build.py` before submitting a pull request",
        ]
    )


def render_contributor_badges(contributors: list[dict[str, str]]) -> str:
    colors = ["1f6feb", "0f766e", "7c3aed", "b45309"]
    badges = [shields_badge_html("contributors", str(len(contributors)), "475569")]
    for index, contributor in enumerate(contributors):
        badges.append(
            shields_badge_html(
                contributor["name"],
                "GitHub",
                colors[index % len(colors)],
                contributor["url"],
                logo="github",
            )
        )
    return " ".join(badges)


def filter_entries_by_exact_tag(entries: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    return [entry for entry in entries if tag in entry.get("tags", [])]


def render_entry_nav_list(entries: list[dict[str, Any]], output_file: Path) -> str:
    return "\n".join(
        f"- {markdown_link(entry['title'], entry_permalink(output_file, entry))} ({entry['year']})"
        for entry in sort_entries(entries)
    )


def render_navigation_table(items: list[dict[str, Any]], output_file: Path) -> str:
    if not items:
        return "_No entries yet._"
    header = "| Work | Details | External |\n| --- | --- | --- |"
    rows = []
    for item in sort_entries(items):
        rows.append(
            f"| {item['title']} ({item['year']}) | {markdown_link('Details', catalog_permalink(output_file, item['anchor']))} | {item['links_md'] or '-'} |"
        )
    return "\n".join([header, *rows])


def render_benchmark_types_table(types: list[dict[str, Any]]) -> str:
    header = "| Type | Description |\n| --- | --- |"
    rows = [f"| `{item['label']}` | {item['description']} |" for item in types]
    return "\n".join([header, *rows])


def render_domain_nav(
    domains: list[dict[str, Any]],
    stats: dict[str, Any],
    output_file: Path,
) -> str:
    header = "| Domain | Focus | Count |\n| --- | --- | --- |"
    rows = []
    for domain in domains:
        target = group_link(output_file, "docs/views/by-domain.md", domain["slug"])
        rows.append(
            f"| {markdown_link(domain['label'], target)} | {domain['description']} | {stats['domains'][domain['slug']]} |"
        )
    return "\n".join([header, *rows])


def render_research_stage_table(research_stages: list[dict[str, Any]]) -> str:
    header = "| Stage | What it captures |\n| --- | --- |"
    rows = [f"| `{stage['label']}` | {stage['description']} |" for stage in research_stages]
    return "\n".join([header, *rows])


def render_research_stage_legend(research_stages: list[dict[str, Any]]) -> str:
    blocks = []
    for stage in research_stages:
        fine = ", ".join(f"`{item}`" for item in stage["fine_stages"])
        blocks.append(f"- **{stage['label']}**: {fine}")
    return "\n".join(blocks)


def render_simple_table(items: list[dict[str, str]], key_label: str) -> str:
    header = f"| {key_label} | Definition |\n| --- | --- |"
    rows = [f"| `{item['label']}` | {item['description']} |" for item in items]
    return "\n".join([header, *rows])


def render_group_page(
    items: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    key: str,
    output_file: Path,
    anchor_aliases: dict[str, list[str]] | None = None,
) -> str:
    sections = []
    for group in groups:
        anchor = group["slug"]
        group_items = [item for item in items if item_matches_group(item, key, group["slug"])]
        alias_lines = []
        for alias in (anchor_aliases or {}).get(anchor, []):
            alias_lines.append(f"<a id=\"{alias}\"></a>")
        sections.append(
            "\n".join(
                [
                    f"<a id=\"{anchor}\"></a>",
                    *alias_lines,
                    f"## {group['label']}",
                    "",
                    group["description"],
                    "",
                    render_navigation_table(group_items, output_file),
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def render_group_nav_list(
    groups: list[dict[str, Any]],
    items: list[dict[str, Any]],
    key: str,
) -> str:
    lines = []
    for group in groups:
        count = sum(item_matches_group(item, key, group["slug"]) for item in items)
        lines.append(f"- {markdown_link(group['label'], '#' + group['slug'])} ({count})")
    return "\n".join(lines)


def render_benchmark_nav_list(benchmarks: list[dict[str, Any]], output_file: Path) -> str:
    return "\n".join(
        f"- {markdown_link(benchmark['title'], benchmark_permalink(output_file, benchmark))} ({benchmark['year']})"
        for benchmark in sort_entries(benchmarks)
    )


def main() -> None:
    renderer = MiniJinja(TEMPLATES)
    build_date = date.today().isoformat()

    site = load_jsonish(TOOLING / "data/site.yaml")
    taxonomy = load_jsonish(TOOLING / "data/taxonomy.yaml")
    raw_entries = load_jsonish(TOOLING / "collections/entries.yaml")
    raw_benchmarks = load_jsonish(TOOLING / "collections/benchmarks.yaml")
    must_read_ids = load_jsonish(TOOLING / "collections/must_read.yaml")

    section_index = {item["slug"]: item for item in taxonomy["sections"]}
    level_index = {item["slug"]: item for item in taxonomy["levels"]}
    research_stage_index = {item["slug"]: item for item in taxonomy["research_stages"]}
    domain_index = {item["slug"]: item for item in taxonomy["domains"]}

    entries = enrich_entries(raw_entries, section_index, level_index, research_stage_index, domain_index)
    benchmarks = enrich_benchmarks(raw_benchmarks)
    entry_by_id = {entry["id"]: entry for entry in entries}
    benchmark_by_id = {benchmark["id"]: benchmark for benchmark in benchmarks}
    stats = build_stats(entries, benchmarks, taxonomy)

    readme_path = ROOT / "README.md"
    badge_line = " ".join(
        [
            '<a href="https://awesome.re"><img alt="Awesome" src="https://awesome.re/badge.svg" /></a>',
            shields_badge_html("license", "MIT", "2563eb", rel_path(readme_path, ROOT / "LICENSE")),
            shields_badge_html("entries", str(stats["entries"]), "0f766e"),
            shields_badge_html("benchmarks", str(stats["benchmarks"]), "b45309"),
            shields_badge_html("updated", build_date, "475569"),
            shields_badge_html("curation", "curated", "334155"),
            shields_badge_html("coverage", "benchmark-aware", "7c3aed"),
        ]
    )
    quick_nav_line = " · ".join(
        html_link(item["label"], item["anchor"]) for item in site["quick_nav"]
    )
    featured_entries = [entry_by_id[item_id] for item_id in must_read_ids]

    readme = renderer.render_path(
        "pages/readme.md.j2",
        {
            "badge_line": badge_line,
            "hero_quote": site["hero_quote"],
            "hero_quote_author_line": f"&mdash; {site['hero_quote_author']}",
            "subtitle_line_1": site["subtitle_line_1"],
            "subtitle_line_2": site["subtitle_line_2"],
            "mission": site["mission"],
            "quick_nav_line": quick_nav_line,
            "start_here_md": render_start_here(readme_path),
            "featured_items_md": render_featured_items(featured_entries, readme_path),
            "research_stage_nav_md": render_research_stage_nav(taxonomy["research_stages"], stats, readme_path),
            "intelligence_nav_md": render_intelligence_nav(taxonomy["levels"], stats, readme_path),
            "section_nav_md": render_section_nav(taxonomy["sections"], stats, readme_path),
            "domain_nav_md": render_domain_nav(taxonomy["domains"], stats, readme_path),
            "benchmark_highlights_md": render_benchmark_highlights(
                [benchmark_by_id[item_id] for item_id in ["scienceagentbench", "frontierscience", "mle-bench", "scientist-bench"]],
                readme_path,
            ),
            "benchmark_types_md": render_benchmark_types(taxonomy["benchmark_types"]),
            "taxonomy_links_md": render_taxonomy_links(readme_path),
            "contributing_md": render_contributing_md(),
            "contributor_badges_html": render_contributor_badges(site["contributors"]),
        },
    )
    write_generated(readme_path, readme)

    catalog_path = ROOT / "docs/catalog.md"
    catalog_page = renderer.render_path(
        "pages/catalog.md.j2",
        {
            "catalog_items_md": render_catalog_items(renderer, entries, benchmarks),
        },
    )
    write_generated(catalog_path, catalog_page)

    for section in taxonomy["sections"]:
        if section["slug"] == "benchmarks-evaluation":
            continue
        section_entries = [entry for entry in entries if entry["section"] == section["slug"]]
        target = ROOT / section["page"]
        page = renderer.render_path(
            "pages/section.md.j2",
            {
                "section_anchor": slugify(section["label"]),
                "section_header": f"{section['emoji']} {section['label']}",
                "section_intro": section["intro"],
                "section_includes_md": render_bullets(section["includes"]),
                "section_excludes_md": render_bullets(section["excludes"]),
                "section_table_md": render_navigation_table(section_entries, target),
            },
        )
        write_generated(target, page)

    benchmarks_path = ROOT / "docs/benchmarks/index.md"
    benchmarks_page = renderer.render_path(
        "pages/benchmarks.md.j2",
        {
            "benchmark_nav_list_md": render_benchmark_nav_list(benchmarks, benchmarks_path),
            "benchmark_types_table_md": render_benchmark_types_table(taxonomy["benchmark_types"]),
            "benchmark_table_md": render_navigation_table(benchmarks, benchmarks_path),
        },
    )
    write_generated(benchmarks_path, benchmarks_page)

    taxonomy_page = renderer.render_path(
        "pages/taxonomy.md.j2",
        {
            "research_stage_table_md": render_research_stage_table(taxonomy["research_stages"]),
            "research_stage_legend_md": render_research_stage_legend(taxonomy["research_stages"]),
            "levels_table_md": render_simple_table(taxonomy["levels"], "Level"),
            "self_evolving_note_md": f"`self-evolving` is tracked as a tag; see {markdown_link('Self-Evolving Systems', 'views/self-evolving.md')}.",
            "domains_table_md": render_simple_table(taxonomy["domains"], "Domain"),
            "benchmark_types_table_md": render_benchmark_types_table(taxonomy["benchmark_types"]),
            "human_role_table_md": render_simple_table(taxonomy["human_roles"], "Human role"),
            "evidence_table_md": render_simple_table(taxonomy["evidence_levels"], "Evidence"),
        },
    )
    write_generated(ROOT / "docs/taxonomy.md", taxonomy_page)

    research_stage_view_path = ROOT / "docs/views/by-research-stage.md"
    research_stage_view = renderer.render_path(
        "pages/by-research-stage.md.j2",
        {
            "research_stage_nav_list_md": render_group_nav_list(taxonomy["research_stages"], entries, "research_stage"),
            "research_stage_groups_md": render_group_page(entries, taxonomy["research_stages"], "research_stage", research_stage_view_path),
        },
    )
    write_generated(research_stage_view_path, research_stage_view)

    intelligence_view_path = ROOT / "docs/views/by-intelligence-level.md"
    intelligence_view = renderer.render_path(
        "pages/by-intelligence-level.md.j2",
        {
            "self_evolving_note_md": f"`self-evolving` is tracked as a tag; see {markdown_link('Self-Evolving Systems', 'self-evolving.md')}.",
            "level_nav_list_md": render_group_nav_list(taxonomy["levels"], entries, "level"),
            "level_groups_md": render_group_page(
                entries,
                taxonomy["levels"],
                "level",
                intelligence_view_path,
            ),
        },
    )
    write_generated(intelligence_view_path, intelligence_view)

    self_evolving_view_path = ROOT / "docs/views/self-evolving.md"
    self_evolving_entries = filter_entries_by_exact_tag(entries, "self-evolving")
    self_evolving_view = renderer.render_path(
        "pages/self-evolving.md.j2",
        {
            "self_evolving_nav_list_md": render_entry_nav_list(self_evolving_entries, self_evolving_view_path),
            "self_evolving_table_md": render_navigation_table(self_evolving_entries, self_evolving_view_path),
        },
    )
    write_generated(self_evolving_view_path, self_evolving_view)

    domain_view_path = ROOT / "docs/views/by-domain.md"
    domain_view = renderer.render_path(
        "pages/by-domain.md.j2",
        {
            "domain_nav_list_md": render_group_nav_list(taxonomy["domains"], entries, "domains"),
            "domain_groups_md": render_group_page(entries, taxonomy["domains"], "domains", domain_view_path),
        },
    )
    write_generated(domain_view_path, domain_view)


if __name__ == "__main__":
    main()
