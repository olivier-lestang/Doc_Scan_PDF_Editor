# ADR 0002: Accounts, subscriptions and eIDAS signing are designed but not implemented

- **Status:** accepted (interfaces only; no implementation yet)
- **Date:** 2026-11-22

## Context

The app is fully functional offline without an account. In the future,
some features (e.g. eIDAS qualified electronic signature via a qualified
trust service provider) will be sold as subscriptions, either through a
future website (username/password sign-in) or through app-store billing
(StoreKit / Google Play Billing, mandatory for digital goods on mobile).

## Decision

- Define domain **ports** now: `AuthRepository`, `LicenseManager`,
  `SubscriptionProvider` (sources: `"website"` and `"store"`),
  `Entitlement` (e.g. `EIDAS_QUALIFIED_SIGNATURE`), and a
  `SignatureProviderRegistry` that only exposes providers whose required
  entitlement is present.
- Ship **offline stubs** only: `OfflineLicenseManager` (base entitlements,
  no-op refresh), `UnauthenticatedAuthRepository` (always signed out),
  feature flag `account_enabled = false` hiding the account UI.
- **No network code exists in the app today.** Secrets/tokens, when they
  exist, will be stored only in the OS secure storage (Keychain, Keystore,
  libsecret, DPAPI); passwords are never stored.
- Future website auth: HTTPS/TLS 1.3, username/password exchanged once to
  obtain short-lived tokens (OAuth2/OIDC-compatible design), certificate
  pinning planned.

## Consequences

- Adding accounts/subscriptions/eIDAS later means implementing the ports
  (`WebsiteAuthRepository`, `WebsiteSubscriptionProvider`,
  `StoreSubscriptionProvider`, `EidasQualifiedSignatureProvider`) and
  flipping `account_enabled` — without touching existing features.
- eIDAS qualified signatures necessarily involve a remote qualified trust
  service provider (QSCD), so they belong to the future opt-in "cloud"
  gate; the app stays 100% on-device by default.
