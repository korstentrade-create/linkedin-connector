# linkedin-connector

An MCP server that lets Claude draft and publish LinkedIn posts to **your own profile**, with an
explicit approval step, plus a prompt that rewrites your profile for a target role.

## What it can and can't do
- Can: publish text and image posts to your own profile (`w_member_social`, self-serve).
- Can't: edit profile fields or read your posts back. LinkedIn does not offer these to
  self-serve apps, so profile changes are suggested by Claude and pasted in by you.
- Company Page posting needs LinkedIn partner approval and is out of scope for v0.1.

## Setup
1. Create an app at https://developer.linkedin.com (it needs a Company Page to associate with).
2. Products tab: add **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect**.
3. Auth tab: add redirect URL `http://localhost:8765/callback`.
4. `pip install -e .`
5. `export LINKEDIN_CLIENT_ID=... LINKEDIN_CLIENT_SECRET=...` (see `.env.example`)
6. `linkedin-connector-login` (tokens last about 60 days; re-run when expired)
7. Add the server to your MCP client (see `claude_desktop_config.example.json`) and pass the
   two env vars in its `env` block.

## Safety
- `publish_post` refuses unless `confirm=true`, and the tool description tells Claude to get
  your explicit approval first.
- Never commit `.env` or the token directory. Everyone running this uses their own LinkedIn app.

## Status
v0.1, not yet tested against the live API. Please follow LinkedIn's API Terms of Use.
