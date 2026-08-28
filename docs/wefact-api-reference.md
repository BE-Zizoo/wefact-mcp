# WeFact API v2 Reference

Compiled from the official docs (developer.wefact.com / www.wefact.nl/api, API version 2.6.x, changelog through 2.6.6). Field names are case-sensitive and reproduced exactly.

## 1. Transport

| Item | Value |
|---|---|
| Endpoint | `https://api.mijnwefact.nl/v2/` (single URL, all actions) |
| Method | `POST` only |
| Request body | `application/x-www-form-urlencoded` (PHP `http_build_query`). Nested arrays use bracket notation: `InvoiceLines[0][ProductCode]=P0001`, `modified[from]=...`, `Groups[0]=1`, `CustomFields[fieldcode]=value`. |
| Auth | POST field `api_key=<key>` (Settings > API in WeFact; per-administration; IP whitelist configurable there). No headers needed. |
| Routing | POST fields `controller` and `action` (both lowercase strings). |
| Response | JSON object. |
| Rate limits | 200 calls/minute, 3,600 calls/hour per IP. Also a daily cap on failed auth attempts per IP. Exceeding => IP blocked, HTTP 403. Failed calls count too. |
| Rate-limit headers | `API-RateLimit-Remaining-Minute`, `API-RateLimit-Remaining-Hour`, `API-RateLimit-Reset-Minute`, `API-RateLimit-Reset-Hour` (unix seconds UTC). |
| List defaults | `offset` default 0, `limit` default 1000. |

Minimal request:

```
POST https://api.mijnwefact.nl/v2/
Content-Type: application/x-www-form-urlencoded

api_key=XXXX&controller=invoice&action=show&InvoiceCode=F2024-0001
```

### Response envelope

Every response:

```json
{ "controller": "invoice", "action": "show", "status": "success", "date": "2024-01-21T12:00:00+02:00", ... }
```

- `status` is `"success"` or `"error"`. Branch on this, not on HTTP code.
- On error: `"errors": ["message", ...]` (array of strings). Example (blocked IP):
  `{"controller":"invalid","action":"invalid","status":"error","date":"...","errors":["IP 123.456.78.9 currently in firewall"]}`
- On success, payload key depends on action: singular object key (`invoice`, `debtor`, `product`, `subscription`, `creditinvoice`, `creditor`, `pricequote`, `group`, `task`, `interaction`, `transaction`, `extraclientcontact`, `settings`) or, for `list`, a plural array key (`invoices`, `debtors`, `products`, `creditinvoices`, `creditors`, `pricequotes`, `groups`, `tasks`, `interactions`, `transactions`; `subscription list` returns `subscriptions`).
- Many mutating actions also return `"success": ["human readable message", ...]`; email actions add `"warning": []`.
- `list` responses contain `totalresults` (int, all matching), `currentresults` (int, in this page), `offset` (int), and often `filters` (echo of the filter params given).
- Empty values are returned as `""`; numbers are often returned as strings/floats (e.g. `"AmountExcl": "229.64"`, `"Identifier": 1`). Booleans are `"yes"`/`"no"`; some flags `0`/`1`.
- Objects include `Translations` (human-readable NL labels for `Status`, `Country`, `InvoiceMethod`, `PaymentMethod`, `LanguageLabel`, ...).

### Common list parameters

| Param | Type | Notes |
|---|---|---|
| `offset` | int | default 0 |
| `limit` | int | default 1000 |
| `sort` | string | field name; default per controller (below) |
| `order` | `ASC` / `DESC` | default per controller |
| `searchat` | string | pipe-separated field list to search, e.g. `EmailAddress` or `InvoiceCode\|CompanyName` |
| `searchfor` | string | search term |
| `created` | filter_datetime | `created[from]=YYYY-MM-DD HH:MM:SS&created[to]=...` |
| `modified` | filter_datetime | same shape |
| `date` / `paybefore` / `paydate` / `expirationdate` | filter_date | `date[from]=YYYY-MM-DD&date[to]=YYYY-MM-DD` |

Filter shape as PHP: `$params['modified'] = ['from' => '2020-01-01 00:00:00', 'to' => '2020-12-31 23:59:59'];`

### Identification convention

Most actions accept either `Identifier` (internal int id) OR the human code: `DebtorCode` (DB10000), `CreditorCode` (CD50000), `InvoiceCode` (F2024-0001, concept: `[concept]0001`), `ProductCode` (P0001), `CreditInvoiceCode` (CF0002), `PriceQuoteCode` (OF2024-0001). `edit` actions change only the parameters supplied.

## 2. Enumerations (variable list)

| Enum | Values |
|---|---|
| Invoice `Status` | `0` concept, `2` sent, `3` partly paid, `4` paid, `8` credit invoice, `9` expired |
| Invoice `SubStatus` | `""`, `BLOCKED` (blocked concept), `PAUSED` (payment process paused) |
| Purchase invoice (`creditinvoice`) `Status` | `1` not yet paid, `2` partly paid, `3` paid, `8` credit invoice |
| Price quote `Status` | `0` concept, `2` sent, `3` accepted, `4` invoice created, `8` declined |
| Subscription `status` (list filter) | `active` (default), `terminated` |
| Task `Status` | `open`, `in_progress`, `completed` |
| Bank transaction `Status` | `unmatched`, `ignored`, `matched`, `pending`, `proposed_match`, `skipped` |
| Bank transaction `Type` | `batch`, `deposit`, `withdrawal`, `reversal` |
| Cost category `Status` | `active`, `removed` |
| `Periodic` / `PricePeriod` | `""` none, `d` day, `w` week, `m` month, `k` quarter, `h` half year, `j` year, `t` two years |
| `PeriodicType` (line) | `once` (default), `period` |
| `InvoiceMethod` / `PriceQuoteMethod` (send method) | `0` email, `1` post, `3` email+post, `5` Peppol, `""` debtor preference |
| `PaymentMethod` | `wire` bank transfer, `cash`, `card` (pin), `auth` direct debit, `accounting` via bookkeeping package, `various`, `paypal`, `ideal`, `qrcode`, `other` online |
| `Sex` / `Salutation` | `m`, `f`, `d`, `fam`, `u` (unknown). Default `m` |
| `Mailing` | `yes`, `no`, `unsubscribed` |
| `DirectDebitApplyTo` (debtor) | `none`, `invoices`, `subscriptions`, `all` |
| `DirectDebit` (subscription) | `client` (default), `yes`, `no` |
| `MandateCreationType` | `manual`, `automatic` (required when Mollie direct debit active) |
| `VatCalcMethod` | `excl`, `incl` |
| `DiscountPercentageType` | `line`, `subscription` |
| `InvoiceTemplateType` (download) | `invoice` (default), `workorder`, `confirmation`, `deliveryorder`, `packageorder` |
| `FileType` (download) | `pdf` (default), `ubl`, `ublwithpdf` |
| Attachment `Type` | `invoice`, `creditinvoice`, `pricequote`, `debtor`, `creditor`, `crm_task`, `crm_interaction` |
| Group `Type` / `type` | `debtor`, `product` |
| Interaction `CommunicationMethod` | `phone`, `whatsapp`, `email`, `post`, `in_person` |
| `referenceType` (interaction list) | `debtor`, `creditor`, `invoice`, `pricequote`, `creditinvoice`, `unprocessed_creditinvoice`, `subscription` |
| `referenceType` (task list) | `unlinked` + the same list |
| Transaction match `ReferenceType` | `invoice`, `creditinvoice`, `directdebit` |
| Transaction match `PaymentType` | `received`, `paid`, `directdebit` |
| Transaction `transactionDirection` | `incoming`, `outgoing` |
| `Country` | ISO 3166-1 alpha-2 (`NL`, `BE`, ...) |
| `Currency` | ISO codes (`EUR` default; others only if enabled in administration) |
| `LanguageCode` (corporate identity) | e.g. `nl_nl`; empty = default identity |
| `TaxCode` | from `settings list`: sale `V0`, `V9`, `V21`, `VEU`, `VNONEU`; purchase `I0`, `I9`, `I21`, `IEU`, `INONEU`, `INONE` (administration-specific). Passing `TaxPercentage` instead still works (legacy). |

## 3. Controller map

| Controller | Actions |
|---|---|
| `debtor` | list, show, add, edit |
| `extraclientcontact` | add, edit, delete |
| `creditor` | list, show, add, edit, delete |
| `product` | list, show, add, edit, delete |
| `invoice` | list, show, add, edit, delete, credit, download, sendbyemail, sendreminderbyemail, sendsummationbyemail, markaspaid, markasunpaid, partpayment, block, unblock, schedule, cancelschedule, paymentprocesspause, paymentprocessreactivate |
| `invoiceline` | add, delete, sortlines |
| `creditinvoice` (purchase invoices) | list, show, add, edit, delete, markaspaid, partpayment |
| `creditinvoiceline` | add, delete |
| `pricequote` | list, show, add, edit, delete, accept, decline, archive, download, sendbyemail, schedule, cancelschedule |
| `pricequoteline` | add, delete, sortlines |
| `subscription` | list, show, add, edit, terminate |
| `group` | list, show, add, edit, delete |
| `attachment` | add, download, delete |
| `transaction` (bank) | list, show, add, delete, ignore, match |
| `task` | list, show, add, edit, changestatus |
| `interaction` | list, show, add, edit |
| `settings` | list, costcategory_list, costcategory_show, costcategory_add, costcategory_edit, costcategory_delete |

Note: there is no separate "creditinvoice = sales credit note" controller. Sales credit notes are invoices with `Status` 8 created via `invoice credit`. `creditinvoice` = purchase invoices from suppliers.

## 4. Invoices (`controller=invoice`)

### Invoice object (returned by show/add/edit/sendbyemail/partpayment/credit/invoiceline *)

`Identifier`, `InvoiceCode`, `Debtor` (int), `DebtorCode`, `Status`, `SubStatus`, `PaymentPausedEndDate`, `PaymentPausedReason`, `Date`, `Term`, `PayBefore`, `PaymentURL`, `AmountExcl`, `AmountTax`, `AmountIncl`, `AmountPaid`, `AmountOutstanding`, `Discount`, `VatCalcMethod`, `IgnoreDiscount` (`yes`/`no`), `ReferenceNumber`, `CompanyName`, `Initials`, `SurName`, `Sex`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `ExtraClientContactId`, `InvoiceMethod`, `ScheduledAt` (concept only), `SentDate`, `Sent`, `Reminders`, `ReminderDate`, `Summations`, `SummationDate`, `Authorisation`, `PaymentMethod`, `PayDate`, `TransactionID`, `LanguageCode`, `Currency`, `Description`, `Comment`, `InvoiceLines[]`, `Created`, `Modified`, `VatShift`, `Attachments[]`, `Translations{Status,Country,InvoiceMethod,PaymentMethod,LanguageLabel}`, `PeppolAddress`.

InvoiceLines item: `Identifier`, `Ordering` (sortlines only), `Date`, `Number`, `NumberSuffix`, `ProductCode`, `Description`, `PriceExcl`, `DiscountPercentage`, `DiscountPercentageType`, `TaxCode`, `TaxPercentage`, `PeriodicID`, `Periods`, `Periodic`, `StartDate`, `EndDate`, `StartPeriod`, `EndPeriod`.

### invoice list

Params: `status` (string, invoice status code), `offset`, `limit`, `sort` (default `InvoiceCode`), `order` (default `DESC`), `searchat` (default `InvoiceCode|CompanyName|SurName`), `searchfor`, `created`, `modified` (filter_datetime), `date`, `paybefore`, `paydate` (filter_date). None required.

```
controller=invoice&action=list&status=2&limit=50&modified[from]=2024-01-01 00:00:00&modified[to]=2024-12-31 23:59:59
```
```json
{"controller":"invoice","action":"list","status":"success","date":"2024-01-21T12:00:00+02:00",
 "totalresults":1,"currentresults":1,"offset":0,
 "invoices":[{"Identifier":1,"InvoiceCode":"F2024-0001","Debtor":1,"DebtorCode":"DB10000","CompanyName":"Jan Janssen B.V.","Initials":"Jan","SurName":"Janssen","AmountExcl":"229.64","AmountIncl":"277.86","AmountPaid":"277.86","AmountOutstanding":"0.00","Currency":"EUR","Date":"2023-11-22","Term":14,"Status":4,"SubStatus":"","Sent":1,"SentDate":"2024-01-01 00:00:00","Reminders":0,"ReminderDate":"","Summations":0,"SummationDate":"","Modified":"2024-01-21 11:00:00","PayBefore":"2023-12-06"}]}
```

### invoice show

Params: `Identifier` | `InvoiceCode` (one required).

```
controller=invoice&action=show&InvoiceCode=F2024-0001
```
```json
{"controller":"invoice","action":"show","status":"success","date":"...",
 "invoice":{"Identifier":1,"InvoiceCode":"F2024-0001","Debtor":1,"DebtorCode":"DB10000","Status":4,"SubStatus":"","PaymentPausedEndDate":"","PaymentPausedReason":"","Date":"2023-11-22","Term":14,"PayBefore":"2023-12-06","PaymentURL":"","AmountExcl":"229.64","AmountTax":"48.22","AmountIncl":"277.86","AmountPaid":"277.86","AmountOutstanding":"0.00","Discount":0,"VatCalcMethod":"excl","IgnoreDiscount":"no","ReferenceNumber":"","CompanyName":"Jan Janssen B.V.","Initials":"Jan","SurName":"Janssen","Sex":"m","Address":"Keizersgracht 100","ZipCode":"1015 AA","City":"Amsterdam","Country":"NL","EmailAddress":"info@example.com","ExtraClientContactId":0,"InvoiceMethod":5,"SentDate":"2024-01-01 00:00:00","Sent":1,"Reminders":0,"ReminderDate":"","Summations":0,"SummationDate":"","Authorisation":"no","PaymentMethod":"wire","PayDate":"","TransactionID":"","LanguageCode":"nl_nl","Currency":"EUR","Description":"","Comment":"",
  "InvoiceLines":[{"Identifier":1,"Date":"2023-11-22","Number":2,"NumberSuffix":"","ProductCode":"P0001","Description":"Werkzaamheden gebaseerd op uurtarief","PriceExcl":100,"DiscountPercentage":0,"DiscountPercentageType":"line","TaxCode":"V21","TaxPercentage":21,"PeriodicID":0,"Periods":1,"Periodic":"","StartDate":"","EndDate":"","StartPeriod":"","EndPeriod":""}],
  "Created":"2024-01-21 11:00:00","Modified":"2024-01-21 11:00:00","VatShift":"no","Attachments":[],
  "Translations":{"Status":"Betaald","Country":"Nederland","InvoiceMethod":"Via Peppol","PaymentMethod":"Bankoverschrijving","LanguageLabel":"Nederlands"},"PeppolAddress":"0106:17237249"}}
```

### invoice add

Required: `Debtor` or `DebtorCode`, and `InvoiceLines` (min 1). Debtor data (name/address/email) is auto-filled from the debtor; if a line has `ProductCode`, `Description`, `PriceExcl`, `TaxCode`, `PeriodicType`, `Periods`, `Periodic`, `StartDate` are auto-filled from the product.

Params: `InvoiceCode` (omit for auto-number), `Debtor` (int), `DebtorCode`, `ExtraClientContactId` (int), `Date` (date), `Term` (int days), `AmountPaid` (float), `Discount` (float 0-100, whole invoice), `IgnoreDiscount` (`0`/`1`, default 0), `UseProductInventory` (`yes`/`no`, default yes), `VatCalcMethod` (`excl`/`incl`), `ReferenceNumber`, `CompanyName`, `Initials`, `SurName`, `Sex`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `InvoiceMethod` (int), `SentDate` (datetime), `Sent` (int, default 0), `LanguageCode`, `Authorisation` (`yes`/`no`), `PaymentMethod`, `PayDate` (date), `TransactionID`, `Description`, `Comment` (internal note), `Status` (int, default 0 concept), `SubStatus` (`BLOCKED` for concept / `PAUSED` for sent), `CustomFields` (assoc array fieldcode=>value), `AccountingCostCentre`, `AccountingProject`, `InvoiceLines` (array).

InvoiceLines item params: `Identifier` (int, existing line), `Date` (date, default today), `Number` (float, default 1), `NumberSuffix`, `ProductCode`, `Description`, `PriceExcl` (float, per unit excl VAT), `DiscountPercentage` (float 0-100), `DiscountPercentageType` (`line`/`subscription`), `TaxCode`, `StartDate` (date), `EndDate` (date, only when PeriodicType once), `PeriodicType` (`once`/`period`), `Periods` (int), `Periodic` (string), `AccountingCostCentre`, `AccountingProject`.

```
controller=invoice&action=add&DebtorCode=DB10000
&InvoiceLines[0][Number]=2&InvoiceLines[0][ProductCode]=P0001
&InvoiceLines[1][Description]=Reiskosten&InvoiceLines[1][PriceExcl]=0.19
```
Response: `{"controller":"invoice","action":"add","status":"success","date":"...","invoice":{ ...full invoice object, "InvoiceCode":"[concept]0001","Status":0, "ScheduledAt":"" ... }}`

### invoice edit

Same params as add plus `Identifier`. Required: `Identifier` or `InvoiceCode`. Only supplied params change. Response: `"invoice": {...}`.

```
controller=invoice&action=edit&Identifier=1&Discount=10&Term=30
```

### invoice delete

Concept invoices only (otherwise use `credit`). Params: `Identifier` | `InvoiceCode`.
Response: `{"status":"success","success":["Conceptfactuur [concept]0001 is verwijderd."]}`

### invoice credit

Creates a credit invoice (Status 8, negated amounts, extra line "Corresponderende factuur: F2024-0001") and marks the original as credited. Params: `Identifier` | `InvoiceCode`.
Response: `{"success":["Creditfactuur F2024-0002 is aangemaakt","Factuur F2024-0001 is gecrediteerd."],"invoice":{ ...the new credit invoice, "Status":8, "AmountIncl":"-277.86" ...}}`

### invoice download

Params: `Identifier` | `InvoiceCode`, `InvoiceTemplateType` (`invoice` default | `workorder` | `confirmation` | `deliveryorder` | `packageorder`), `FileType` (`pdf` default | `ubl` | `ublwithpdf`).
Response: `{"invoice":{"Filename":"Factuur-F2024-0001.pdf","Base64":"JVBERi0x...","MimeType":"application/pdf"}}`

### invoice sendbyemail

Sends by email (or Peppol if configured). Concept becomes Status 2 and gets a real `InvoiceCode`. Params: `Identifier` | `InvoiceCode`.
Response: `{"warning":[],"success":["Factuur F2024-0001 is per e-mail verzonden naar BCC."],"invoice":{...,"Status":2,"PaymentURL":"https://www.mijnwefact.nl/betalen/?payment=F2024-0001&key=...","SentDate":"2024-09-25 09:23:31","Sent":1}}`

### invoice sendreminderbyemail / sendsummationbyemail

Reminder (herinnering) / summation (aanmaning). Params: `Identifier` | `InvoiceCode`.
Response: `{"warning":[],"success":["Herinnering voor factuur F2024-0001 is per e-mail verzonden naar BCC."]}` (no invoice object).

### invoice markaspaid

Not for concepts. Sets Status 4. Params: `Identifier` | `InvoiceCode`, `PayDate` (date, default today), `PaymentMethod` (default `wire`).
Response: `{"success":["Factuur F2024-0001 is betaald"]}`

### invoice markasunpaid

Status 4 -> 2. Params: `Identifier` | `InvoiceCode`. Response: `{"success":["Betaling van factuur F2024-0001 is ongedaan gemaakt"]}`

### invoice partpayment

Not for concepts. Sets Status 3 (or 4 if fully paid). Required: `Identifier` | `InvoiceCode`, `AmountPaid` (float). Optional `PayDate` (date), `PaymentMethod`.
Response: `{"success":["Deelbetaling factuur F2024-0001 is verwerkt"],"invoice":{...,"Status":3,"AmountPaid":"25.00","AmountOutstanding":"252.86"}}`

### invoice block / unblock

Concept only; sets/clears `SubStatus=BLOCKED` (no subscriptions added, cannot be sent). Params: `Identifier` | `InvoiceCode`.
Response: `{"success":["Factuur [concept]0001 is geblokkeerd."]}` / `["De blokkade van conceptfactuur [concept]0001 is opgeheven."]`

### invoice schedule / cancelschedule

Concept only. `schedule` requires `ScheduledAt` (datetime `YYYY-MM-DD HH:MM:SS`) plus `Identifier` | `InvoiceCode`.
Response: `{"success":["Factuur [concept]0001 is ingepland op 25-09-2024 om 20:00."]}` / `["Factuur [concept]0001 is niet langer ingepland."]`

### invoice paymentprocesspause / paymentprocessreactivate

Only for Status 2 or 3. `pause` params: `Identifier` | `InvoiceCode`, `PaymentPausedEndDate` (date), `PaymentPausedReason` (string; docs table misspells as `PaymentPausedreason`, example uses `PaymentPausedReason`), `DisableOnlinePayment` (`yes`/`no`, default no). Sets `SubStatus=PAUSED`.
Response: `{"success":["Betalingstraject voor factuur F2024-0001 is gepauzeerd."]}` / `["Betalingstraject voor factuur F2024-0001 is geactiveerd."]`

### invoiceline add (`controller=invoiceline&action=add`)

Works on invoices in any status. Required: `Identifier` | `InvoiceCode` (of the invoice), `InvoiceLines` (array). Line params: `Date`, `Number`, `ProductCode`, `Description`, `PriceExcl`, `DiscountPercentage`, `DiscountPercentageType`, `TaxCode`, `StartDate`, `EndDate`, `PeriodicType`, `Periods`, `Periodic`.
```
controller=invoiceline&action=add&InvoiceCode=[concept]0001&InvoiceLines[0][ProductCode]=P0001&InvoiceLines[0][PriceExcl]=100
```
Response: `{"controller":"invoiceline","action":"add","success":["Er zijn 1 factuurregels toegevoegd"],"invoice":{...}}`

### invoiceline delete

Required: `Identifier` | `InvoiceCode`, `InvoiceLines[][Identifier]`.
```
controller=invoiceline&action=delete&InvoiceCode=[concept]0001&InvoiceLines[0][Identifier]=1
```
Response: `{"success":["Er zijn 1 factuurregels verwijderd"],"invoice":{...}}`

### invoiceline sortlines

Required: `Identifier` | `InvoiceCode`, `InvoiceLines[][Identifier]` in desired order.
```
controller=invoiceline&action=sortlines&InvoiceCode=[concept]0001&InvoiceLines[0][Identifier]=2&InvoiceLines[1][Identifier]=1
```
Response: `{"success":["Er zijn 2 factuurregels gesorteerd"],"invoice":{... lines include "Ordering"}}`

## 5. Debtors (`controller=debtor`)

### Debtor object (show/add/edit)

`Identifier`, `DebtorCode`, `CompanyName`, `CompanyNumber` (KvK), `TaxNumber` (VAT), `Sex`, `Initials`, `SurName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`, `FaxNumber`, `Comment`, `InvoiceMethod`, `DirectDebitApplyTo`, `InvoiceAuthorisation` (deprecated), `MandateDate`, `MandateID`, `AccountNumber`, `AccountIban`, `AccountBIC`, `AccountName`, `AccountBank`, `AccountCity`, `Mailing`, `InvoiceTerm` (-1 = default), `PeriodicInvoiceDays` (-1 = default), `PaymentMail` (-1 = default), `LanguageCode`, `Currency`, `CustomTaxCode`, `ReminderEmailAddress`, `Groups` (object keyed by id: `{id, GroupName}`), `Created`, `Modified`, `DefaultBillingContactId`, `DefaultQuoteContactId`, `ExtraClientContacts[]`, `InvoiceDataForPriceQuote`, `InvoiceCompanyName`, `InvoiceSex`, `InvoiceInitials`, `InvoiceSurName`, `InvoiceAddress`, `InvoiceZipCode`, `InvoiceCity`, `InvoiceCountry`, `InvoiceEmailAddress`, `ExternalMandateId`, `ExternalCustomerId`, `Translations{Country,InvoiceMethod,InvoiceCountry,LanguageLabel}`, `PeppolAddress`.

ExtraClientContacts item: `Identifier`, `ClientId`, `CompanyName`, `Salutation`, `FirstName`, `LastName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`, `Created`, `Modified`.

### debtor list

Params: `offset`, `limit`, `sort` (default `DebtorCode`), `order` (default `ASC`), `searchat` (default `DebtorCode|CompanyName|SurName`), `searchfor`, `group` (int, debtor group id), `created`, `modified`.
```
controller=debtor&action=list&searchat=EmailAddress&searchfor=info@example.com
```
```json
{"controller":"debtor","action":"list","status":"success","date":"...","totalresults":1,"currentresults":1,"offset":0,
 "filters":{"searchat":"EmailAddress","searchfor":"info@example.com"},
 "debtors":[{"Identifier":1,"DebtorCode":"DB10000","CompanyName":"Jan Janssen B.V.","Sex":"m","Initials":"Jan","SurName":"Janssen","EmailAddress":"info@example.com","Modified":"2024-01-21 11:00:00"}]}
```

### debtor show

Params: `Identifier` | `DebtorCode`. Response: `{"debtor":{...full object}}`.

### debtor add

Required: `CompanyName` or `SurName`. Params: `DebtorCode` (omit for auto), `CompanyName`, `CompanyNumber`, `TaxNumber`, `Sex`, `Initials`, `SurName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`, `FaxNumber`, `Comment`, `InvoiceMethod` (default 0), `DirectDebitApplyTo` (default `none`), `MandateID`, `MandateDate` (default today), `AccountNumber` (IBAN), `MandateCreationType`, `AccountName`, `AccountBank`, `AccountCity`, `AccountBIC`, `Mailing`, `InvoiceTerm` (int), `PeriodicInvoiceDays` (-1 or int), `PaymentMail` (-1 or int), `LanguageCode`, `Currency`, `CustomTaxCode`, `ReminderEmailAddress`, `Groups` (array of group ids, or empty string for none), `CustomFields` (assoc), `PeppolAddress`. Mandate/Account fields are ignored when Mollie direct debit is active.
```
controller=debtor&action=add&CompanyName=Jan Janssen B.V.&SurName=Janssen&EmailAddress=info@example.com&Country=NL&Groups[0]=1
```
Response: `{"controller":"debtor","action":"add","status":"success","debtor":{"Identifier":1,"DebtorCode":"DB10000",...,"Groups":{"1":{"id":1,"GroupName":"Laadpaal"}},...}}`

### debtor edit

Same params + `Identifier`. Required: `Identifier` | `DebtorCode` (docs also say CompanyName or SurName). Response `{"debtor":{...}}`.

### extraclientcontact (`controller=extraclientcontact`)

- `add`: required `ClientId` | `DebtorCode`, and one of `CompanyName`, `LastName`, `EmailAddress`. Params: `ClientId`, `DebtorCode`, `CompanyName`, `Salutation`, `FirstName`, `LastName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`. Response `{"extraclientcontact":{...}}`.
- `edit`: required `Identifier`; same fields minus ClientId/DebtorCode. Response `{"extraclientcontact":{...}}`.
- `delete`: required `Identifier`. Response `{"success":["Extra contactpersoon \"Bedrijfsnaam (Jan Janssen)\" succesvol verwijderd"]}`.

## 6. Products (`controller=product`)

Object: `Identifier`, `ProductCode`, `ProductName`, `ProductKeyPhrase` (description on invoice), `ProductDescription` (internal), `NumberSuffix`, `Barcode`, `PriceExcl`, `PricePeriod`, `TaxCode`, `TaxPercentage`, `Groups` (show/add/edit), `Created`, `Modified` (list has only `Modified`), `Translations{PricePeriod}`.

- `list`: `offset`, `limit`, `sort` (default `ProductCode`), `order` (default `ASC`), `searchat` (default `ProductCode|ProductName|ProductKeyPhrase`), `searchfor`, `group` (int), `created`, `modified`. Response key `products` + `totalresults`/`currentresults`/`offset`.
  ```json
  {"products":[{"Identifier":1,"ProductCode":"P0001","ProductName":"Uurtarief","ProductKeyPhrase":"Werkzaamheden gebaseerd op uurtarief","ProductDescription":"","NumberSuffix":"","Barcode":"","PriceExcl":100,"TaxCode":"V21","TaxPercentage":21,"PricePeriod":"","Modified":"2024-01-21 11:00:00"}]}
  ```
- `show`: `Identifier` | `ProductCode`. Response `{"product":{...}}`.
- `add`: required `ProductName`, `ProductKeyPhrase`, `PriceExcl`. Params: `ProductCode` (omit for auto), `ProductName`, `ProductKeyPhrase`, `ProductDescription`, `NumberSuffix`, `Barcode`, `PriceExcl`, `PricePeriod` (default `""`), `TaxCode`, `AccountingCostCentre`, `AccountingProject`, `Groups` (array of ids or `""`), `ProductInventory` (array: `IsProductInventoryEnabled` yes/no, `TotalStock` float, `StockWarningThreshold`, `SupplierIds` array, `WarehouseID` int).
  `controller=product&action=add&ProductName=Service contract&ProductKeyPhrase=Service contract&PriceExcl=150&PricePeriod=m` -> `{"product":{"Identifier":1,"ProductCode":"P0001",...,"PricePeriod":"m","Translations":{"PricePeriod":"maand"}}}`
- `edit`: required `Identifier` | `ProductCode`; same params. Response `{"product":{...}}`.
- `delete`: `Identifier` | `ProductCode`. Response `{"success":["Product P0001 is verwijderd"]}`.

## 7. Subscriptions (`controller=subscription`)

Object: `Identifier`, `Debtor`, `DebtorCode`, `Number`, `NumberSuffix`, `ProductCode`, `Description`, `Group` (show only), `PriceExcl`, `PriceIncl`, `Currency`, `TaxCode`, `TaxPercentage`, `DiscountPercentage`, `Periods`, `Periodic`, `StartDate`, `EndDate`, `StartPeriod`, `EndPeriod`, `NextDate`, `Comment`, `TerminateAfter`, `TerminationDate`, `AmountExcl`, `AmountIncl`, `DirectDebit`, `DiscountAmountExcl`, `DiscountAmountIncl`, `Created`, `Modified`.

- `list`: `status` (`active` default | `terminated`), `offset`, `limit`, `sort` (default `NextDate`), `order` (default `ASC`), `searchat` (default `DebtorCode|ProductCode|Description`), `searchfor`, `created`, `modified`. Response: `totalresults`, `currentresults`, `offset`, `filters`, `subscriptions[]` (key absent when 0 results in docs example).
- `show`: required `Identifier`. Response `{"subscription":{...}}`.
- `add`: required `Debtor` | `DebtorCode` and `Subscription[ProductCode]` (without ProductCode: `Description`, `PriceExcl`, `Periodic` required). Note the nested key is a single assoc array `Subscription` (not a list). Sub-params: `Number` (default 1), `NumberSuffix`, `ProductCode`, `Description`, `PriceExcl`, `TaxCode`, `DiscountPercentage`, `Periods`, `Periodic`, `StartDate`, `NextDate` (only if "invoice in advance" setting is 0), `TerminationDate`, `TerminateAfter` (int, 0 = indefinite; not together with TerminationDate), `Comment`, `AccountingCostCentre`, `AccountingProject`, `DirectDebit` (`client`/`yes`/`no`).
  `controller=subscription&action=add&DebtorCode=DB10000&Subscription[ProductCode]=P0001` -> `{"success":["Abonnement Service contract is aangemaakt.","Abonnement Service contract van klant DB10000 is gefactureerd."],"subscription":{...}}`
- `edit`: required `Identifier`; optional `Debtor`, `DebtorCode`, `Subscription[...]` same sub-params. `controller=subscription&action=edit&Identifier=1&Subscription[PriceExcl]=125`
- `terminate`: required `Identifier`; `Subscription[TerminationDate]` (date) or `Subscription[TerminateAfter]` (int). Empty `TerminationDate` undoes termination. Response `{"success":["Abonnement 'Service contract' is opgezegd per 01-01-2025"],"subscription":{...}}`.

## 8. Purchase invoices (`controller=creditinvoice`)

Object: `Identifier`, `CreditInvoiceCode` (own internal number), `InvoiceCode` (supplier's number), `Creditor`, `CreditorCode`, `Status`, `SubStatus`, `AuthorisationStatus`, `Date`, `Term`, `AmountExcl`, `AmountIncl`, `AmountPaid`, `AmountOutstanding`, `Authorisation`, `PayDate`, `PaymentMethod`, `Currency`, `Comment`, `InvoiceLines[]` (`Identifier`, `Number`, `Description`, `PriceExcl`, `TaxCode`, `TaxPercentage`, `StartDate`, `EndDate`, `CostCategory`), `Created`, `Modified`, `Attachments[]`, `Translations{Status,PaymentMethod}`. List items additionally: `CompanyName`, `Initials`, `SurName`, `PayBefore`.

- `list`: `status` (docs label it `Identifier` string = status code; use status), `offset`, `limit`, `sort` (default `CreditInvoiceCode`), `order` (default `DESC`), `searchat` (default `CreditInvoiceCode|InvoiceCode|CompanyName|SurName|Description`), `searchfor`, `created`, `modified`. Response key `creditinvoices`.
- `show`: `Identifier` | `CreditInvoiceCode`. Response `{"creditinvoice":{...}}`.
- `add`: required `InvoiceCode`, `Creditor` | `CreditorCode`, `InvoiceLines` (min 1). Params: `CreditInvoiceCode` (omit for auto), `InvoiceCode`, `Creditor`, `CreditorCode`, `Date` (default today), `Term`, `AmountIncl` (VAT rounding correction), `AmountPaid`, `Authorisation` yes/no, `PayDate`, `PaymentMethod`, `Currency`, `Comment`, `Status` (default 1), `AccountingCostCentre`, `AccountingProject`, `InvoiceLines[]` (`Description`, `PriceExcl`, `TaxCode`, `CostCategory` int, `StartDate`, `EndDate`, `AccountingCostCentre`, `AccountingProject`), `ProductInventory[]` (`ProductId`, `Number`).
  `controller=creditinvoice&action=add&CreditorCode=CD50000&InvoiceCode=INV123456&Date=2024-01-01&InvoiceLines[0][Description]=Test line&InvoiceLines[0][PriceExcl]=100`
- `edit`: required `Identifier` | `CreditInvoiceCode`; same params.
- `delete`: `Identifier` | `CreditInvoiceCode`. Response `{"success":["Inkoopfactuur INV123456 is verwijderd."]}`.
- `markaspaid`: `Identifier` | `CreditInvoiceCode`, `PayDate`, `PaymentMethod`. Response `{"success":["Inkomende factuur INV123456 is gekenmerkt als betaald"]}`.
- `partpayment`: `Identifier` | `CreditInvoiceCode`, `AmountPaid` (required), `PayDate`, `PaymentMethod`. Response `{"success":[...],"creditinvoice":{...,"Status":2}}`.
- `creditinvoiceline add` (`controller=creditinvoiceline`): `Identifier` | `CreditInvoiceCode`, `RecalculateInclTotalAmount` (yes/no, default no), `InvoiceLines[]` (same line fields). Response `{"success":["Er zijn 1 factuurregels toegevoegd"],"creditinvoice":{...}}`.
- `creditinvoiceline delete`: `Identifier` | `CreditInvoiceCode`, `RecalculateInclTotalAmount`, `InvoiceLines[][Identifier]`.

## 9. Creditors / suppliers (`controller=creditor`)

Object: `Identifier`, `CreditorCode`, `MyCustomerCode`, `CompanyName`, `CompanyNumber`, `TaxNumber`, `Sex`, `Initials`, `SurName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`, `FaxNumber`, `Comment`, `Authorisation`, `AccountNumber`, `AccountIban`, `AccountName`, `AccountBank`, `AccountCity`, `AccountBIC`, `InvoiceTerm`, `BookingRules[]`, `Created`, `Modified`, `Translations{Country}`.

- `list`: `offset`, `limit`, `sort` (default `CreditorCode`), `order` (default `ASC`), `searchat` (default `CreditorCode|CompanyName|SurName`), `searchfor`, `created`, `modified`. Response key `creditors` (items: `Identifier`, `CreditorCode`, `CompanyName`, `Sex`, `Initials`, `SurName`, `EmailAddress`, `Modified`).
- `show`: `Identifier` | `CreditorCode`. Response `{"creditor":{...}}`.
- `add`: required `CompanyName` or `SurName`. Params: `CreditorCode` (omit for auto), `MyCustomerCode`, `CompanyName`, `CompanyNumber`, `TaxNumber`, `Sex`, `Initials`, `SurName`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `PhoneNumber`, `MobileNumber`, `FaxNumber`, `Comment`, `Authorisation` (yes/no, default no), `AccountNumber`, `AccountName`, `AccountBank`, `AccountCity`, `AccountBIC`, `InvoiceTerm`, `ProductInventory[ProductIds]` (array).
- `edit`: required `Identifier` | `CreditorCode`; same params.
- `delete`: `Identifier` | `CreditorCode`, `withcreditinvoice` (`yes`/`no`, also delete its purchase invoices). Response `{"success":["Leverancier CD50000 is verwijderd."]}`.

## 10. Price quotes (`controller=pricequote`)

Object: `Identifier`, `PriceQuoteCode`, `Debtor`, `DebtorCode`, `Status`, `Archived` (0/1), `Date`, `Term` (validity days), `AmountExcl`, `AmountTax`, `AmountIncl`, `Discount`, `VatCalcMethod`, `IgnoreDiscount`, `ReferenceNumber`, `CompanyName`, `Initials`, `SurName`, `Sex`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `ExtraClientContactId`, `PriceQuoteMethod`, `ScheduledAt`, `SentDate`, `Sent`, `LanguageCode`, `Currency`, `Description`, `Comment`, `PriceQuoteLines[]` (`Identifier`, `Date`, `Number`, `NumberSuffix`, `ProductCode`, `Description`, `PriceExcl`, `DiscountPercentage`, `DiscountPercentageType`, `TaxCode`, `TaxPercentage`, `Periods`, `Periodic`, `StartDate`, `EndDate`, `StartPeriod`, `EndPeriod`), `Created`, `Modified`, `AcceptURL`, `VatShift`, `Attachments[]`, `Translations{Status,Country,PriceQuoteMethod,LanguageLabel}`.

- `list`: `status`, `offset`, `limit`, `sort` (default `PriceQuoteCode`), `order` (default `DESC`), `searchat` (default `PriceQuoteCode|CompanyName|SurName`), `searchfor`, `created`, `modified`, `date`, `expirationdate` (filter_date), `archived` (0/1). Response key `pricequotes` (items: `Identifier`, `PriceQuoteCode`, `Debtor`, `DebtorCode`, `CompanyName`, `Initials`, `SurName`, `AmountExcl`, `AmountIncl`, `Currency`, `Date`, `Status`, `Archived`, `Modified`).
- `show`: `Identifier` | `PriceQuoteCode`. Response `{"pricequote":{...}}`.
- `add`: required `Debtor` | `DebtorCode`, `PriceQuoteLines` (min 1). Params: `PriceQuoteCode` (omit for auto), `Debtor`, `DebtorCode`, `ExtraClientContactId`, `Date`, `Term`, `Discount`, `IgnoreDiscount`, `UseProductInventory`, `VatCalcMethod`, `ReferenceNumber`, `CompanyName`, `Initials`, `SurName`, `Sex`, `Address`, `ZipCode`, `City`, `Country`, `EmailAddress`, `SentDate`, `Sent`, `LanguageCode`, `Description`, `Comment`, `Status` (default 0), `Archived` (0/1), `CustomFields`, `PriceQuoteLines[]` (same line params as InvoiceLines: `Identifier`, `Date`, `Number`, `NumberSuffix`, `ProductCode`, `Description`, `PriceExcl`, `DiscountPercentage`, `DiscountPercentageType`, `TaxCode`, `StartDate`, `EndDate`, `PeriodicType`, `Periods`, `Periodic`).
- `edit`: required `Identifier` | `PriceQuoteCode`; same params.
- `delete`: `Identifier` | `PriceQuoteCode`. Response `{"success":["Offerte OF2024-0001 is verwijderd."]}`.
- `sendbyemail`: `Identifier` | `PriceQuoteCode`. Response `{"warning":[],"success":["Offerte OF2024-0001 is per e-mail verzonden naar BCC."],"pricequote":{...,"Status":2,"AcceptURL":"https://www.mijnwefact.nl/accepteren/?pricequote=...&key=...&wa=..."}}`.
- `accept`: `Identifier` | `PriceQuoteCode`, `CreateInvoice` (yes/no, default no), `UsePriceQuoteCodeASInvoiceReference` (yes/no, default no), `UseTodayAsInvoiceLinesDate` (yes/no, default yes). Sets Status 3 (or 4 when invoice created). Response `{"invoice":{"Identifier":1,"InvoiceCode":"[concept]0001"},"success":["Offerte OF2024-0001 is geaccepteerd","Offerte OF2024-0001 is gefactureerd, factuur [concept]0001 is aangemaakt."],"pricequote":{...,"Status":4}}`.
- `decline`: `Identifier` | `PriceQuoteCode`. Status 8, `Archived` 1. Response `{"success":["Offerte OF2024-0001 is geweigerd"],"pricequote":{...}}`.
- `archive`: only Status 3/4/8. Response `{"success":["Offerte OF2024-0001 is gearchiveerd"],"pricequote":{...,"Archived":1}}`.
- `download`: `Identifier` | `PriceQuoteCode`. Response `{"pricequote":{"Filename":"Offerte-OF2024-0001.pdf","Base64":"...","MimeType":"application/pdf"}}`.
- `schedule`: `Identifier` | `PriceQuoteCode`, `ScheduledAt` (datetime). Response `{"pricequote":{...,"ScheduledAt":"2024-09-25 20:00:00"}}`. `cancelschedule`: `Identifier` | `PriceQuoteCode`.
- `pricequoteline add` (`controller=pricequoteline`): `Identifier` | `PriceQuoteCode`, `PriceQuoteLines[]`. `pricequoteline delete` / `sortlines`: `PriceQuoteLines[][Identifier]`. Responses: `{"success":["Er zijn 1 offerteregels toegevoegd"],"pricequote":{...}}`.

## 11. Groups (`controller=group`)

Object: `Identifier`, `GroupName`, `Type` (`debtor`/`product`), `Items` (object keyed by id; product items `{Identifier, ProductCode, ProductName}`).

- `list`: `offset`, `limit`, `type` (`debtor`/`product`). Response `{"totalresults":1,"currentresults":1,"offset":0,"filters":{"type":"product"},"groups":[{"Identifier":1,"GroupName":"Consultancy","Type":"product","Items":[]}]}`.
- `show`: `Identifier`. Response `{"group":{...}}`.
- `add`: required `GroupName`, `Type`; optional `Items` (array of ids). Response `{"success":["Groep New productgroup is aangemaakt."],"group":{...}}`.
- `edit`: required `Identifier`; `GroupName`, `Items` (must pass ALL item ids; omitted ones are unlinked).
- `delete`: `Identifier`. Response `{"success":["Groep Consultancy is verwijderd."]}`.

## 12. Attachments (`controller=attachment`)

Shared by invoice, creditinvoice, pricequote, debtor, creditor, task (`crm_task`), interaction (`crm_interaction`).

- `add`: required `ReferenceIdentifier` (int id of parent) or the parent's code (`InvoiceCode` / `CreditInvoiceCode` / `DebtorCode` / `CreditorCode` / `PriceQuoteCode` — docs tables inconsistently label the column `CreditorCode`), `Type`, `Filename`, `Base64`.
  ```
  controller=attachment&action=add&ReferenceIdentifier=1&Type=invoice&Filename=sample.pdf&Base64=JVBERi0x...
  ```
  Response `{"success":["Het bestand 'sample.pdf' is toegevoegd als bijlage bij de factuur"]}`.
- `download`: `Identifier` (attachment id) or `Filename`, plus `ReferenceIdentifier` or code, plus `Type`. Response: `{"success":[123, "sample.pdf", "JVBERi0x...", "application/pdf"]}` (positional: id, filename, base64, mimetype).
- `delete`: same addressing as download. Response `{"success":["De bijlage 'sample.pdf' is verwijderd"]}`.
- Object `Attachments[]` on invoices etc. lists attachment info; first item of each entry is the attachment id (v2.6.2).

## 13. Bank transactions (`controller=transaction`)

Object: `Identifier`, `BankAccount`, `Date`, `Type`, `Amount`, `Currency`, `ShortDescription`, `ExtendedDescription`, `AccountName`, `AccountNumber`, `AccountBIC`, `BankReference`, `Status`, `Matches[]` (`ReferenceType`, `ReferenceId`, `MatchedAmount`, `Currency`, `MatchType` e.g. `full_payment`), `Origin` (e.g. `api`), `Created`, `Modified`.

- `list`: `transactionDirection` (`incoming`/`outgoing`), `status`, `offset`, `limit`, `sort` (default `date`), `order` (default `DESC`), `searchfor`. Response key `transactions`.
- `show`: `Identifier`.
- `add`: required `BankAccount`, `Date`, `Type`, `Amount`, `Currency`; optional `ShortDescription`, `ExtendedDescription`, `AccountName`, `AccountNumber`, `AccountBIC`, `BankReference` (auto-generated if empty). Response `{"transaction":{...,"Status":"unmatched"}}`.
- `delete`: `Identifier`. Response has no payload (just envelope).
- `ignore`: `Identifier`. Response `{"transaction":{...,"Status":"ignored"}}`.
- `match`: `Identifier`, `Matches[]` each with required `ReferenceId`, `ReferenceType`, `MatchedAmount`, `Currency`, `PaymentType`; optional `MarkAsPaid` yes/no, `DoublePayment` yes/no, `Reversal{Reason, InvoiceAction (move_to_next_batch|remove_direct_debit_from_invoice|remove_direct_debit_from_debtor), BatchDate, NotifyClient yes/no}`.
  ```
  controller=transaction&action=match&Identifier=1&Matches[0][ReferenceId]=1&Matches[0][ReferenceType]=invoice&Matches[0][MatchedAmount]=100&Matches[0][Currency]=EUR&Matches[0][PaymentType]=received&Matches[0][MarkAsPaid]=yes
  ```

## 14. Tasks (`controller=task`) and interactions (`controller=interaction`)

Task object: `Identifier`, `DueAt`, `DueAtTime`, `CompletedAt`, `AssigneeId`, `DebtorId`, `DebtorContactId`, `CreditorId`, `InvoiceId`, `PriceQuoteId`, `CreditInvoiceId`, `UnprocessedCreditInvoiceId`, `SubscriptionId`, `Title`, `Description`, `CreatedByEmployeeId`, `Status`, `Created`, `Modified`, `Comments[]`, `Attachments[]`.

- `task list`: `referenceId`, `referenceType`, `status`, `offset`, `limit`, `sort` (default `DueAtDate`), `order` (default `DESC`), `searchat` (default `Title|Description`), `searchfor`. Response key `tasks`.
- `task show`: `Identifier`.
- `task add`: required `Title`. Params: `DueAt` (date), `Hours`, `Minutes`, `AssigneeId`, `DebtorId`, `DebtorContactId`, `CreditorId`, `InvoiceId`, `PriceQuoteId`, `CreditInvoiceId`, `UnprocessedCreditInvoiceId`, `SubscriptionId`, `Title`, `Description`, `Status` (default `open`). Response `{"task":{...}}`.
- `task edit`: required `Identifier`; same params.
- `task changestatus`: `Identifier`, `Status`. Response `{"task":{...,"Status":"completed","CompletedAt":"..."}}`.

Interaction object: `Identifier`, `Date`, `Time`, `AssigneeId`, `DebtorId`, `DebtorContactId`, `CreditorId`, `InvoiceId`, `PriceQuoteId`, `CreditInvoiceId`, `UnprocessedCreditInvoiceId`, `SubscriptionId`, `Description`, `CreatedByEmployeeId`, `CommunicationMethod`, `Created`, `Modified`, `Comments[]`, `Attachments[]`.

- `interaction list`: required `referenceId`, `referenceType`; `offset`, `limit`, `sort` (default `Date`), `order` (default `DESC`), `searchat` (default `Description`), `searchfor`. Response key `interactions`.
- `interaction show`: `Identifier`.
- `interaction add`: required `AssigneeId`, `Description`, `CommunicationMethod`, and one of `DebtorId`/`CreditorId`/`InvoiceId`/`PriceQuoteId`/`CreditInvoiceId`/`UnprocessedCreditInvoiceId`/`SubscriptionId`. Params also `Date`, `Hours`, `Minutes`, `DebtorContactId`.
- `interaction edit`: `Identifier` + same params.

## 15. Settings (`controller=settings`)

- `list` (no params): returns `settings` with `CorporateIdentity[]` (`LanguageCode`, `Name`, `Default`) and `Tax` = `{Codes: {Sale: {V21: {TaxCode, Name, Direction, Type (rate|shifted|none), ReportCode, ReportCodeCredit, IsDefault, Visibility (always|rule), Status, Rate (0.210000), PerformanceType}}, Purchase: {...}}, Rules: {Sale: [{Direction, CountryRestrictionType (otherEU|nonEU), CountryCode, RelationRestriction (company_vat|all), AllowedTaxCodes[]}], Purchase: [...]}}`.
- `costcategory_list`: `status` (default `active`; `active|removed` allowed). Response `{"settings":{"costcategories":[{"Identifier":1,"Title":"Cost category","Status":"active","PerformanceType":"services"}]}}`.
- `costcategory_show`: `Identifier`. Response `{"settings":{"costcategory":{Identifier,Title,Status,PerformanceType,Created,Modified}}}`.
- `costcategory_add`: required `Title`.
- `costcategory_edit`: `Identifier`, `Title`, `Status` (`active`/`removed`).
- `costcategory_delete`: `Identifier` (sets Status `removed`).

## 16. Notable changelog items

- 2.6.5 (2026-01): `PeppolAddress` on debtor/invoice; send method `5` Peppol.
- 2.6.4: `MandateCreationType` on debtor.
- 2.6.3 / 2.6.6: rate-limit response headers.
- 2.6.0/2.6.1: `transaction` controller; `Name` renamed to `AccountName`.
- 2.5.9/2.5.6: `ProductInventory` on product/creditor/creditinvoice; `UseProductInventory` on invoice/pricequote.
- 2.5.7/2.5.8: `task` and `interaction` controllers and their attachments.
- 2.5.4: `Mailing` gained `unsubscribed`.
- 2.5.3: `RecalculateInclTotalAmount` on creditinvoiceline.
- 2.5.2: debtor `SynchronizeAddress`/`SynchronizeEmail` replaced by `SynchronizeAddressToInvoices`, `SynchronizeAddressToQuotes`, `SynchronizeEmailToInvoices`, `SynchronizeEmailToQuotes`; added `SynchronizeSendMethodToInvoices`, `SynchronizeSendMethodToQuotes`, `SynchronizeCorporateIdentity` (accepted on debtor edit; not in current field tables).
- 2.5.1: `MimeType` in download responses.
- 2.5.0: `InvoiceAuthorisation` replaced by `DirectDebitApplyTo`; subscription `DirectDebit`; `settings` controller.
- 2.4.9: `DisableOnlinePayment` on paymentprocesspause.
- 2.4.7: `sortlines`; sex `u`.
- 2.4.6: `extraclientcontact` controller, `ExtraClientContactId`.
- 2.4.5: `AmountPaid`/`AmountOutstanding` in list+show.
- 2.4.4: `LegalForm` removed; pause end date/reason.
- 2.4.0: `Sent`, `SentDate`, `Reminders`, `ReminderDate`, `Summations`, `SummationDate` in invoice list; `ReminderEmailAddress`.
- 2.3.9: `TaxCode` replaces `TaxPercentage` (percentage still accepted).
- 2.3.6: endpoint moved to `https://api.mijnwefact.nl/v2/`; debtor `Taxable` removed.
- 2.3.4: `StartDate`/`EndDate` replace `StartPeriod`/`EndPeriod` (both still returned).
