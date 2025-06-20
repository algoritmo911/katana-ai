# E2E Test Scenarios for Logging Feature (Cypress)

This document outlines End-to-End (E2E) test scenarios for the logging feature, intended for implementation with a framework like Cypress.

**Conceptual Test File:** `cypress/e2e/logging_feature.cy.ts` (or `.js`)

**General Setup (Conceptual `beforeEach` for most scenarios):**
1.  `cy.visit('/logs')`: Navigate to the Logs page.
2.  `cy.intercept('GET', '/api/logs/status').as('getLogStatus')`: Intercept status API call.
3.  `cy.intercept('GET', '/api/logs*').as('getLogs')`: Intercept logs API call (wildcard for query params).
4.  `cy.intercept('POST', '/api/logs/level').as('postLogLevel')`: Intercept level change API call.
5.  Wait for initial API calls (e.g., status and initial log fetch) to complete using `cy.wait('@aliasName')`.
6.  Perform basic visibility checks for main page headings (e.g., "Application Logs & Configuration", "Log Configuration", "Log Viewer") using `cy.contains('hX', 'Heading Text').should('be.visible')`.

---

## Scenario 1: View Logs and Initial Status

*   **Objective:** Verify that the Logs page loads, displays initial log status, and shows some log entries.
*   **Steps & Assertions:**
    1.  Execute General Setup.
    2.  **Log Configuration Display:**
        *   Assert that "Current Log Level:" text is visible and a log level (e.g., "INFO") is displayed next to it.
        *   Assert that "Log File:" text is visible and a file path is displayed next to it.
    3.  **Log Viewer Display:**
        *   Assert that a container for log entries is present.
        *   If logs are expected: `cy.get('.log-entry-class-or-testid').should('have.length.greaterThan', 0)`.
        *   If no logs are expected (e.g., fresh log file): `cy.contains('No log entries found.').should('be.visible')`.
        *   Assert that the "Load More" button is visible (if applicable, i.e., if total logs potentially exceed one page).

---

## Scenario 2: Filter Logs by Level (LogViewer)

*   **Objective:** Verify that selecting a log level filters the displayed logs in the LogViewer.
*   **Prerequisites:** Test environment should allow mocking API responses or pre-populating the log file with logs of various levels.
*   **Steps & Assertions:**
    1.  Execute General Setup.
    2.  Identify the level filter dropdown (e.g., `cy.get('select[aria-label="Filter by level"]')` or `cy.get('[data-testid="log-level-filter"]')`).
    3.  Select "ERROR" from the dropdown: `levelFilter.select('ERROR')`.
    4.  `cy.wait('@getLogs')`.
    5.  Assert the API request URL included `level=ERROR`: `cy.get('@getLogs').its('request.url').should('include', 'level=ERROR')`.
    6.  Verify that only "ERROR" level logs are displayed. This might involve checking the text/class of each visible log entry.
    7.  Select "All Levels" (or the empty value option) from the dropdown.
    8.  `cy.wait('@getLogs')`.
    9.  Assert the API request URL no longer includes `level=ERROR` (or is appropriate for "all").
    10. Verify that logs of multiple levels (if available in the source) are visible again.

---

## Scenario 3: Search Logs by Term (LogViewer)

*   **Objective:** Verify that searching by a term filters the displayed logs in the LogViewer.
*   **Prerequisites:** Logs with distinct, searchable keywords.
*   **Steps & Assertions:**
    1.  Execute General Setup.
    2.  Identify the search input field (e.g., `cy.get('input[placeholder="Enter search term..."]')`) and the "Search" button.
    3.  Type a specific keyword (e.g., "PaymentFailed") into the search input: `searchInput.type('PaymentFailed')`.
    4.  Click the "Search" button: `searchButton.click()`.
    5.  `cy.wait('@getLogs')`.
    6.  Assert the API request URL included `search=PaymentFailed`: `cy.get('@getLogs').its('request.url').should('include', 'search=PaymentFailed')`.
    7.  Verify that all displayed log entries contain the keyword "PaymentFailed" (case-insensitive check recommended for messages).
    8.  Clear the search input.
    9.  Click the "Search" button again (or interact with a "Clear Search" button if one exists).
    10. `cy.wait('@getLogs')`.
    11. Assert the API request URL no longer includes the `search=PaymentFailed` parameter.
    12. Verify that logs not containing "PaymentFailed" are visible again.

---

## Scenario 4: Change Application Log Level (LogConfiguration)

*   **Objective:** Verify that the application's overall log level can be changed using the LogConfiguration UI.
*   **Steps & Assertions:**
    1.  Execute General Setup.
    2.  Note the initial log level displayed in the "Log Configuration" section.
    3.  Identify the log level select dropdown and the "Set Level" button in the "Log Configuration" section.
    4.  Select a new log level (e.g., "DEBUG") from this dropdown.
    5.  Click the "Set Level" button.
    6.  `cy.wait('@postLogLevel')`.
    7.  Assert the POST request body was correct: `cy.get('@postLogLevel').its('request.body').should('deep.equal', { level: 'DEBUG' })`.
    8.  A success message (e.g., "Log level set to DEBUG") should appear.
    9.  `cy.wait('@getLogStatus')` (as the status should refresh after setting).
    10. Assert the "Current Log Level" display in the "Log Configuration" section now shows "DEBUG".
    11. **(Optional Advanced Verification):** If possible, trigger an application action known to produce a DEBUG-level log. Then, check the LogViewer (possibly after a refresh/filter action) to see if this DEBUG log appears, confirming the backend logging behavior has changed.

---

## Scenario 5: Pagination - "Load More" (LogViewer)

*   **Objective:** Verify the "Load More" functionality for paginating through logs in the LogViewer.
*   **Prerequisites:** The log source must contain more log entries than the per-page limit (e.g., >50 if limit is 50).
*   **Steps & Assertions:**
    1.  Execute General Setup.
    2.  Count the initial number of visible log entries (`cy.get('.log-entry-class-or-testid').its('length').as('initialLogCount')`).
    3.  Identify and click the "Load More" button.
    4.  `cy.wait('@getLogs')`.
    5.  Assert the API request URL for this fetch included `page=2`: `cy.get('@getLogs').its('request.url').should('include', 'page=2')`.
    6.  The number of visible log entries should now be greater than the initial count (`cy.get('.log-entry-class-or-testid').its('length').should('be.gt', '@initialLogCount')`).
    7.  If there are still more logs, the "Load More" button should remain visible and enabled.
    8.  If all logs have been loaded, the "Load More" button should become disabled or hidden, and/or a "No more logs to load" message should appear.

---

**Notes for Actual Implementation:**
*   Use `data-testid` attributes on key interactive elements (buttons, inputs, selects, log entry containers) for more robust Cypress selectors.
*   For reliable E2E tests, either ensure a consistent state of `katana_events.log` before each test run or, more commonly, use `cy.intercept()` to provide mock API responses. The latter gives more control and avoids test data management issues.
*   Leverage Cypress's retry-ability and assertions for asynchronous operations.
*   Consider creating custom Cypress commands for repeated sequences of actions (e.g., logging in, navigating to the logs page).
```
