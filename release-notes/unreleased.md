# Unreleased

- Simplify browser login to username and password. Remove GitHub/ORCID authentication and administrator MFA, retaining editable optional GitHub/ORCID profile fields. Add `pkdb create-user` for active local accounts without SMTP or email setup. Apply the authentication cleanup migration when upgrading; provider-only accounts need a password reset.
