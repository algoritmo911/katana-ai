graph [
  directed 1
  node [
    id 0
    label "0d79a8e3f2f2bcc74fbc3cf7ac9d1b8174f5af2040d3ba22e266372e4fb8cfdb"
    type "MemoryEvent"
    chronos_id "0d79a8e3f2f2bcc74fbc3cf7ac9d1b8174f5af2040d3ba22e266372e4fb8cfdb"
    event_id "DIR-001"
    source "architect_directive"
    timestamp_utc "2025-08-21T21:58:39.694952"
    payload "{&#34;title&#34;: &#34;\u041c\u0438\u0441\u0441\u0438\u044f '\u041a\u0440\u043e\u043d\u043e\u0441'&#34;, &#34;goal&#34;: &#34;\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0433\u0435\u043d\u0435\u0440\u0430\u0442\u043e\u0440 n8n-\u0432\u043e\u0440\u043a\u0444\u043b\u043e\u0443&#34;}"
    gravity_score 0.13472563637590337
  ]
  node [
    id 1
    label "2916971a3eaf316c22978d857745698745dd89e5b30e11b95cf06ed340ffa689"
    type "MemoryEvent"
    chronos_id "2916971a3eaf316c22978d857745698745dd89e5b30e11b95cf06ed340ffa689"
    event_id "commit-a1b2c3"
    source "github_commit"
    timestamp_utc "2025-08-21T23:58:39.694994"
    payload "{&#34;author&#34;: &#34;Jules&#34;, &#34;message&#34;: &#34;feat: Implemented N8nBlueprintGenerator class&#34;}"
    gravity_score 0.13472563637590337
  ]
  node [
    id 2
    label "fbfc441ff65fea9eecbc711c2f98f3aee1adcab373c94db2104932052c07b7b5"
    type "MemoryEvent"
    chronos_id "fbfc441ff65fea9eecbc711c2f98f3aee1adcab373c94db2104932052c07b7b5"
    event_id "PROJ-123"
    source "jira_ticket"
    timestamp_utc "2025-08-22T01:58:39.695021"
    payload "{&#34;type&#34;: &#34;bug&#34;, &#34;summary&#34;: &#34;Generator fails on missing template&#34;, &#34;status&#34;: &#34;OPEN&#34;}"
    gravity_score 0.13472563637590337
  ]
  node [
    id 3
    label "b1df010dcd938db6d25dd627386da7f26cf8242a39e05e0ddb4f86554e5bcb47"
    type "MemoryEvent"
    chronos_id "b1df010dcd938db6d25dd627386da7f26cf8242a39e05e0ddb4f86554e5bcb47"
    event_id "commit-d4e5f6"
    source "github_commit"
    timestamp_utc "2025-08-22T03:58:39.695038"
    payload "{&#34;author&#34;: &#34;Jules&#34;, &#34;message&#34;: &#34;fix: Added error handling for missing templates&#34;, &#34;reference&#34;: &#34;PROJ-123&#34;}"
    gravity_score 0.249242563041625
  ]
  node [
    id 4
    label "43012711505425e6578727f758f0da2cdefe9c0d44b29af141b6d8f0b9f55098"
    type "MemoryEvent"
    chronos_id "43012711505425e6578727f758f0da2cdefe9c0d44b29af141b6d8f0b9f55098"
    event_id "QA-005"
    source "qa_report"
    timestamp_utc "2025-08-22T05:58:39.695055"
    payload "{&#34;test_case&#34;: &#34;test_missing_template&#34;, &#34;result&#34;: &#34;PASS&#34;, &#34;notes&#34;: &#34;Fix confirmed&#34;}"
    gravity_score 0.34658052783066506
  ]
  edge [
    source 2
    target 3
    type "caused"
    justification "Bug likely prompted the fix implementation by Jules."
    confidence 0.9
  ]
  edge [
    source 3
    target 4
    type "caused"
    justification "Error handling fix likely caused test case to pass."
    confidence 0.9
  ]
]
