# Unreleased

- Run the client tests on Windows again: the migration tests skip there, since `pkdb migrate` needs Linux or macOS and says so, and manual runs of the `CI-CD` workflow test every platform before a release is tagged.
