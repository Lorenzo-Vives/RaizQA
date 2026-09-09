import json


def fragment_identity(fragment):
    """Return a stable, hashable identity for text, image, and legacy fragments."""
    if not isinstance(fragment, dict):
        return ("raw", _canonical_value(fragment))

    fragment_type = fragment.get("type")
    is_image = (
        fragment_type == "image"
        or "rect" in fragment
        or "image_size" in fragment
    )
    if is_image:
        return (
            "image",
            _canonical_value(fragment.get("rect")),
            _canonical_value(fragment.get("image_size")),
            _canonical_value(fragment.get("note")),
        )

    start = fragment.get("start")
    end = fragment.get("end")
    if start is not None and end is not None:
        return ("text", _canonical_value(start), _canonical_value(end))

    return ("legacy", _canonical_value(fragment))


def merge_unique_fragments(existing_fragments, new_fragments):
    """Append only fragments whose type-aware identity is not already present."""
    seen = {fragment_identity(fragment) for fragment in existing_fragments}
    for fragment in new_fragments:
        identity = fragment_identity(fragment)
        if identity not in seen:
            existing_fragments.append(fragment)
            seen.add(identity)
    return existing_fragments


def _canonical_value(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    except (TypeError, ValueError):
        return repr(value)
