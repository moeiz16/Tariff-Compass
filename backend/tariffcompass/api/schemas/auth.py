"""Auth, session, organisations, members, invitations, roles (API_CONTRACT §1.2–1.3)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from tariffcompass.api.schemas.common import ClockOut
from tariffcompass.core.wire import Wire

RoleKey = Literal["importer", "broker", "compliance", "admin"]
EMAIL = r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$"


class UserOut(Wire):
    id: str
    email: str
    full_name: str
    licence: str = ""
    avatar_color: str


class OrgOut(Wire):
    id: str
    name: str
    slug: str
    kind: Literal["importer", "broker"]
    kind_label: str  # "Importer" | "Customs broker firm"
    locations: list[str]
    timezone: str
    is_sample: bool


class OrgSummary(Wire):
    id: str
    name: str
    kind: Literal["importer", "broker"]
    role: RoleKey
    role_label: str
    via_broker: str | None = None  # "Driftwood Customs Brokers" when acting for a client
    is_sample: bool


class MembershipOut(Wire):
    role: RoleKey
    role_label: str
    title: str
    permissions: list[str]


class SessionTimes(Wire):
    expires_at: datetime
    absolute_expires_at: datetime


class Me(Wire):
    user: UserOut
    active_org: OrgOut | None
    membership: MembershipOut | None
    orgs: list[OrgSummary]
    session: SessionTimes


class DemoPerson(Wire):
    role: RoleKey
    role_label: str
    full_name: str
    title: str
    org_name: str


class SessionOut(Wire):
    """GET /auth/session: always 200, so public pages never see a 401."""

    me: Me | None
    clock: ClockOut
    demo_sign_in: bool
    demo_people: list[DemoPerson] = []


class LoginIn(Wire):
    email: str = Field(pattern=EMAIL, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class DemoSignInIn(Wire):
    role: RoleKey


class SignupIn(Wire):
    email: str = Field(pattern=EMAIL, max_length=254)
    password: str = Field(min_length=12, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    org_name: str = Field(min_length=2, max_length=200)
    kind: Literal["importer", "broker"] = "importer"


class SwitchOrgIn(Wire):
    org_id: str


class PasswordIn(Wire):
    current_password: str
    new_password: str = Field(min_length=12, max_length=200)


class MemberOut(Wire):
    id: str
    user: UserOut
    role: RoleKey
    role_label: str
    title: str
    via_broker: str | None = None
    joined_at: datetime


class MemberPatch(Wire):
    role: RoleKey | None = None
    title: str | None = None


class InvitationIn(Wire):
    email: str = Field(pattern=EMAIL, max_length=254)
    role: RoleKey


class InvitationOut(Wire):
    id: str
    email: str
    role: RoleKey
    role_label: str
    expires_at: datetime
    invited_by: str
    link: str | None = None  # only in the create response (the token is shown once)


class AcceptInvitationIn(Wire):
    full_name: str | None = None
    password: str | None = None


class RoleOut(Wire):
    role: RoleKey
    role_label: str
    description: str
    permissions: list[str]


class EngagementOut(Wire):
    id: str
    broker_org: str
    importer_org: str
    countries: list[Literal["US", "CA"]]
    countries_label: str  # "US and Canadian entries"
    started_on: date
    people: list[MemberOut]
