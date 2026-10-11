import { describe, expect, it } from "vitest";

import { resolvePostLoginRedirect } from "./useLoginForm";

describe("resolvePostLoginRedirect", () => {
  it("keeps the original path when it is a normal page", () => {
    expect(resolvePostLoginRedirect("/profile")).toBe("/profile");
  });

  it("never returns to an auth page after login", () => {
    expect(resolvePostLoginRedirect("/login")).toBe("/");
  });

  it("ignores admin paths — the admin area is a separate app", () => {
    expect(resolvePostLoginRedirect("/admin/dashboard")).toBe("/");
  });

  it("defaults to home when there is no origin", () => {
    expect(resolvePostLoginRedirect(undefined)).toBe("/");
  });
});
