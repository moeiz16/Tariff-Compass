/** Role checks shared by every screen. `membership.permissions` from the API is the only source of truth. */

export function allows(permissions: readonly string[] | undefined | null, permission: string): boolean {
  return !!permissions?.includes(permission);
}

/** The permission each scope in the query strip needs. */
export const SCOPE_PERMISSION: Record<string, string> = {
  answer: "classify:read",
  rulings: "rulings:read",
  tariff: "tariff:read",
  products: "products:read",
  review: "review:read",
  watch: "watch:read",
  lab: "lab:read",
};
