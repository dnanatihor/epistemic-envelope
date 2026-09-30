# TODO: record docs/demo.gif with vhs. The committed gif is a 1x1 placeholder.
# Re-record when the rendered envelope text changes.
# Demo: an MCP client calls get_asset_profile, then the same call with EPIENV_INFERENCE=off.

Output docs/demo.gif

Require echo
Set Shell bash
Type "uv run python -m examples.catalog_server"
Enter
Sleep 2s
