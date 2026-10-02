# Live description validation fixtures

`live_description_validation.jsonl` contains the exact `description` values from the
14 board rows in the supplied capture
`/home/priyesh/.cache/hermes-remote-codex/jr-live-descriptions.jsonl` (October 2,
2026). The capture is a local record of live detail extraction; these tests make
no network requests. BrowserStack contains only company narrative and benefits,
so its expected result is false. The other 13 rows contain role duties and are
expected true. The source capture's status fields were omitted from this fixture
because the test asserts independently reviewed role evidence.

Marketing and navigation negatives in the Python tests are synthetic and labelled
there. They are separate from the captured descriptions.
