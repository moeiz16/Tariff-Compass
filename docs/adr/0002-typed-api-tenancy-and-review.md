# ADR 0002: A typed Django Ninja API, broker tenancy through engagements, and people in the loop

**Status:** accepted

## Context

Tariff Compass serves two kinds of organisation: importers, who own products and binders, and customs broker firms,
who review and approve their clients' codes. The web app needs one predictable API with plain-words labels, and
the record has to stand up years later as evidence of reasonable care.

## Decision

1. **Django 5.2 + Django Ninja.** Pydantic schemas are the contract in code (`api/schemas`), OpenAPI comes for
   free, and Django gives migrations, sessions, CSRF and Argon2 out of the box. JSON is camelCase on the wire via
   one base schema and one router class; every code travels with its label; every error is an RFC 7807 problem
   document with a stable `code`.
2. **Tenancy by organisation, brokers through engagements.** Every domain row belongs to an importer
   organisation. A broker firm is an organisation too; an `Engagement` links it to each importer it serves, and its
   brokers get a broker membership inside that importer (`Membership.engagement`). Switching organisation is how a
   broker moves between clients. Cross-tenant ids return 404.
3. **Permissions, not roles, in views.** Four roles (importer, broker, compliance, admin) map to permissions in
   `platform/roles.py`. Only brokers decide review items. Promoting a training round needs two `lab:sign`
   signatures from two different people (in practice one compliance lead and one licensed broker).
4. **Nothing is filed.** The product proposes, explains and records; a licensed broker approves every code before
   it is used on an entry. Unsure answers, answers that differ from the last code, products whose ruling changed and
   always-review rules route items to the broker's docket.
5. **An append-only record.** Binder versions are never edited; each links to an audit event in a per-organisation
   SHA-256 chain. The fingerprint is shown on screen and printed on every exported page.

## Consequences

- One API for both importers and brokers; the UI hides what the viewer's permissions don't allow, the API enforces
  it.
- A broker's corrections carry their name and licence into the binder, and become labelled examples for the next
  training round (ADR 0003).
- Verifying the chain is linear in the number of events per organisation, which stays small (thousands).
