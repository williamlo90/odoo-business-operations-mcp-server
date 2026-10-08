# Recorded product walkthrough

A quotation for company A: two units of P1 and one unit of P2, totaling
**IDR 250,000**. This walkthrough follows an actual reference CLI session against
the local synthetic Odoo sandbox.

The figures below are rendered summaries of recorded receipts, not screenshots
of a browser application. Full identifiers, command outputs, exit codes and
durations are preserved in [recording.json](recording.json). The local
[index.html](index.html) file contains the full static transcript; GitHub shows
its source, so download/open it locally for that view.

## 1. Prepare the correct record

![Recorded preview](../assets/proposal.png)

Two customers share a name. The recorded name-only selection is rejected. Using
`OPS-A-001` resolves the intended customer and produces a versioned proposal.
Preparation alone does not create an Odoo draft.

## 2. Enforce the approval boundary

![Recorded approval boundary](../assets/approval.png)

`operator.a` receives `403 role_not_permitted` when attempting approval.
`approver.a` approves the matching proposal hash. The test automates those two
identities; an operator still needs a separate human reviewer in real use.

## 3. Verify the Odoo result

![Recorded Odoo result](../assets/receipt.png)

Execution returns draft `S00132`, status `verified`, with the expected total.
The status is based on actual Odoo read-back. It does not mean the quotation
was emailed, confirmed as an order or invoiced.

## 4. Resume without a second write

![Recorded resume and replay](../assets/replay.png)

A new CLI process retrieves the saved operation. Replaying the original
execution key returns the same result. Direct Odoo queries count one ledger
entry and one draft. A company B account cannot read the company A operation.
This scene demonstrates caller restart/resume; the separately recorded
[connected fault test](../PHASE-8.md) covers a lost response after an Odoo write.

## Reproduce

Follow the [operator guide](../USER-GUIDE.md), then run from the project root:

```powershell
$env:ODOO_LIVE_TESTS='synthetic-sandbox'
.venv/Scripts/python.exe -m deploy.record_demo
```

Each run intentionally creates one sandbox draft and makes no model request.
The recording was produced against application revision
`e42441aee2b06483e7158f8ccc4ecc0e632a6041`; runtime code is unchanged by this
portfolio update. [Acceptance checklist](../DELIVERY-ACCEPTANCE.md).
