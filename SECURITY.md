# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's private
vulnerability reporting ("Security" tab -> "Report a vulnerability")
or by opening a security advisory on this repository.
Do not open a public issue for security reports.

## Scope

The application processes documents 100% on-device. No document content
is sent anywhere by default. The only network uses planned are the
future opt-in account/subscription backend (HTTPS, TLS 1.3) and optional
cloud OCR behind an explicit user consent.

## Secrets

No secrets, tokens or credentials are ever committed to this repository.
Secret scanning and Dependabot are enabled. If you believe a secret was
committed, rotate it immediately and report it as above.
