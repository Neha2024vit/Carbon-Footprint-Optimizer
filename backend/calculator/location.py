def optimize_regions(regions):
    """Rank by lowest estimated emissions, then higher project sustainability score on ties."""
    return sorted(
        regions,
        key=lambda item: (
            item["carbon"]["carbon_kg"],
            -(item.get("sustainability_score") if item.get("sustainability_score") is not None else -1),
        ),
    )
