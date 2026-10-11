# Unreleased

- The local curation app server reads and discards the body of a write that it refuses before reading it, such as a write without a session (401) or without the action token (403), before it closes the connection. Closing with the body unread reset the connection, so on Windows the browser could lose the answer and see a network error instead; a client test failed at random on Windows this way and stopped the first release run of 0.12.3.
