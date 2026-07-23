# Third-party notices

This repository does not redistribute model weights or container-image layers. Their immutable
identifiers, sizes, upstream locations, and upstream license identifiers are recorded in
`configs/models.lock.json` and `configs/runtime.lock.json`.

The benchmark corpus contains public vulnerability records and a frozen public Known Exploited
Vulnerabilities snapshot alongside study-authored synthetic assets and policies. Source identity,
retrieval time, and SHA-256 provenance are retained in the reference source manifest. Upstream
notices continue to apply to public source material; see `data/sources/NOTICE.md`.

The bundled third-party source classes are:

- CVE Program JSON records obtained from the official CVE Services API; individual source URLs and
  hashes are listed in `data/sources/cve_program_source_manifest.json`. CVE reuse is governed by the
  [official CVE Terms of Use](https://www.cve.org/legal/termsofuse), which permits reproduction,
  derivative works, display, sublicensing, and distribution subject to retaining the MITRE
  copyright designation and CVE Usage license. Copyright © 1999–2026, The MITRE Corporation.
  CVE is a trademark and the CVE logo is a registered trademark of The MITRE Corporation.
- The CISA Known Exploited Vulnerabilities catalog snapshot identified and hashed in the reference
  source manifest is distributed under
  [CC0 1.0](https://www.cisa.gov/sites/default/files/licenses/kev/license.txt). That dedication does
  not license linked third-party material, CISA names, seals, logos, or other marks and does not
  imply CISA endorsement. The canonical catalog page is
  <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>.

The repository `LICENSE-DATA` applies CC BY 4.0 only to study-authored synthetic and derived
material; it does not purport to relicense CVE or CISA KEV records. The official source-specific
terms, URLs, and attribution above remain controlling. Repository source code is licensed under
Apache-2.0 through `LICENSE`.
