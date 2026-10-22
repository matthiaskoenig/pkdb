# Unreleased

- Security: the backend image and its lock no longer trust the emSign root CA whose intermediate keys were compromised. The backend requires certifi 2026.10.19 or newer and locks it (GHSA-6q48-6c7w-9gw2), the image builds with uv 0.13.4, whose bundled CA store had the same defect (GHSA-hq85-5cpj-mr62), and upgrades the pip 26.2.1 of the python base images, whose vendored certifi is 2026.06.17, to pip 26.2.2. The workflows install uv with setup-uv 10.3.1.
