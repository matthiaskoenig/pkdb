# Unreleased

- `pkdb curate` answers the curation app at once while it queues the initial validations of a large workspace. It saved its state after each queued job, so the app and every action waited for seconds after a start on 1,000 studies, about 3 seconds on a fast machine and 11 seconds in continuous integration; it now saves once after queueing them, and so does **Validate** for many selected studies (#976).
