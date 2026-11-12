"""MCP server: draft -> approve -> publish LinkedIn posts, plus a profile-optimizer prompt."""
import json
import time
import uuid

from mcp.server.fastmcp import FastMCP

from .auth import HOME, load_token
from .client import LinkedInClient, LinkedInError

mcp = FastMCP("linkedin")
DRAFTS = HOME / "drafts.json"


def _drafts() -> dict:
    return json.loads(DRAFTS.read_text()) if DRAFTS.exists() else {}


def _save(d: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    DRAFTS.write_text(json.dumps(d, indent=2))


def _client() -> tuple[LinkedInClient, dict]:
    tok = load_token()
    if not tok:
        raise LinkedInError("Not logged in. Run `linkedin-connector-login` first.")
    if tok["expires_at"] < time.time():
        raise LinkedInError("LinkedIn token expired. Run `linkedin-connector-login` again.")
    return LinkedInClient(tok["access_token"]), tok


@mcp.tool()
def auth_status() -> str:
    """Check whether LinkedIn is connected and when the token expires."""
    tok = load_token()
    if not tok:
        return "Not connected. Run `linkedin-connector-login`."
    days = (tok["expires_at"] - time.time()) / 86400
    return f"Connected as member {tok['member_id']}; token valid for {days:.0f} more days."


@mcp.tool()
def draft_post(text: str, image_path: str = "", alt_text: str = "") -> str:
    """Save a post draft for review. Nothing is published until publish_post is called with confirm=true."""
    d = _drafts()
    did = uuid.uuid4().hex[:8]
    d[did] = {"text": text, "image_path": image_path, "alt_text": alt_text}
    _save(d)
    return f"Draft {did} saved ({len(text)}/3000 chars). Show it to the user and ask for approval."


@mcp.tool()
def list_drafts() -> str:
    """List saved drafts."""
    return json.dumps(_drafts(), indent=2) or "{}"


@mcp.tool()
def discard_draft(draft_id: str) -> str:
    """Delete a draft."""
    d = _drafts()
    d.pop(draft_id, None)
    _save(d)
    return f"Draft {draft_id} discarded."


@mcp.tool()
def publish_post(draft_id: str, confirm: bool = False) -> str:
    """Publish a draft to the user's LinkedIn feed. Only call with confirm=true after the user has explicitly approved this exact draft."""
    if not confirm:
        return "Not published: confirm=false. Get explicit user approval first."
    d = _drafts()
    if draft_id not in d:
        return f"No draft {draft_id}."
    item = d[draft_id]
    client, _ = _client()
    me = client.whoami()
    image_urn = client.upload_image(me["urn"], item["image_path"]) if item["image_path"] else None
    post_id = client.create_post(me["urn"], item["text"], image_urn, item["alt_text"])
    d.pop(draft_id)
    _save(d)
    return f"Published. Post id: {post_id}"


@mcp.prompt()
def profile_optimizer(target_role: str, profile_text: str) -> str:
    """Rewrite LinkedIn profile sections for a target role."""
    return (
        f"Optimize this LinkedIn profile for: {target_role}.\n\n"
        "Return: (1) headline (max 220 chars), (2) About section, (3) top 10 skills, "
        "(4) rewritten bullets for the two most recent roles using measurable outcomes, "
        "(5) Featured section ideas, (6) keyword gaps versus the target role. "
        "Do not invent achievements; mark anything needing user confirmation with [CONFIRM].\n\n"
        f"CURRENT PROFILE:\n{profile_text}"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
