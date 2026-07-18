**Unreleased**

* Encoded Microsoft Graph path identifiers before constructing request URLs.
* Escaped values embedded in Microsoft Teams widget JavaScript.
* Bound OAuth and admin-consent callbacks to their initiating flows with single-use nonces.
* Validated webhook reply identifiers before using them in SOAR REST requests.
* Bounded Microsoft Graph pagination and rejected repeated continuation links.
* Bound prompt answers to their conversation and offered choices, required bot authentication, and recorded stable responder IDs.
* Removed HTTP response bodies and headers from action debug data to prevent OAuth token logging.
