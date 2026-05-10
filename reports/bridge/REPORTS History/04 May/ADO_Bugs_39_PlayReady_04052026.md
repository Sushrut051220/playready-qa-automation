## BUG 1: Response correctness failure - What are the mandatory compliance requirements related to Copy Count and License Securi...
**Test Case ID:** `pdf001_q08_comp_rule`

**Query**

```
What are the mandatory compliance requirements related to Copy Count and License Security Level in PlayReady?
```

**Response (Agent Output)**

```
Mandatory compliance requirements in PlayReady related to Copy Count and License Security Level include:

- Copy Count:
  - If a Copy Count Restriction Object is specified in the PlayReady License, a Domain Restriction Object must not be specified.
  - Allowed values for the Copy Enabler Type field in the Copy Enabler Type Object must be limited to values described in PlayReady's Content Provider Authorized Exports section.
  - Allowed Copy Enabler Type values include "Copy to PC" and "Copy to device," with an exception for a specific Copy Enabler Type allowed only for PlayReady content from ISDB.

- License Security Level:
  - The Security Level Object must be specified in the PlayReady License.
  - Allowed Minimum Security Level values are:
    - 150: Indicates non-commercial quality content, accessible only by players/devices with Certificate Security Level 150 or higher.
    - 2000: Indicates commercial quality content, accessible only by players/devices with Certificate Security Level 2000 or higher.
    - 3000: Indicates commercial quality content, accessible only by players/devices with Certificate Security Level 3000 or higher, and such devices must implement a PlayReady Trusted Execution Environment.

These rules ensure the correct restrictions on copying and the minimum security assurance for content playback within PlayReady licenses【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
The document outlines Copy Count and License Security Level as specific sections in the compliance rules, indicating that managing the number of allowable copies and maintaining a defined License Security Level are mandatory obligations. These requirements ensure controlled copying and secure license handling as part of the PlayReady compliance framework.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.4137884705752912). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 2: Response correctness failure - What must a PlayReady Product do when passing multiple instances of decrypted audio/vid...
**Test Case ID:** `pdf002_q08_comp_rule`

**Query**

```
What must a PlayReady Product do when passing multiple instances of decrypted audio/video content simultaneously to the same output?
```

**Response (Agent Output)**

```
When a PlayReady Product passes multiple instances of decrypted audio/video content simultaneously to the same output, it must select the most restrictive Output Control associated with all the instances of content for that output. This is specified in Section 3.6.1 (Multiple Simultaneous Streams) of the Compliance Rules for PlayReady Products.

In summary:
- The PlayReady Product must apply the most restrictive output control among all the simultaneous instances of A/V content passed to the same output. 

This ensures compliance with the licensing and output protection requirements set by PlayReady for secure content handling.
```

**Expected / Ground Truth**

```
A PlayReady Product that passes multiple instances of decrypted A/V Content simultaneously to the same output must select the most restrictive Output Control associated with all the instances of A/V Content for that output.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.6122408302589288). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 3: Response correctness failure - What are the mandatory requirements for a PlayReady product when the first byte of the...
**Test Case ID:** `pdf003_q08_comp_rule`

**Query**

```
What are the mandatory requirements for a PlayReady product when the first byte of the Binary Configuration Data field in a Video Output Restriction Object is set to 0 or 1?
```

**Response (Agent Output)**

```
Mandatory requirements for a PlayReady product when the first byte of the Binary Configuration Data field in a Digital Video Output Restriction Object (Video Restriction ID {6CDA453D-BFBB-45d1-AEB7-37287B2403AE}) is set to:

- 0: No additional bytes may be specified. Before passing the video portion of uncompressed decrypted A/V Content to Digital Outputs, the PlayReady product must disengage Watermarking.
- 1: At least 19 total bytes must be specified. Before passing the video portion of uncompressed decrypted A/V Content to Digital Outputs, the PlayReady product must engage the Watermarking system in the Fourth through Nineteenth Bytes according to the specified bytes.
  
These bytes include Watermarking technology-specific GUIDs and possibly additional data required by the Watermarking Vendor. The second and third bytes (if required) must be a WORD in big-endian format with a value of 2000 or 3000, indicating enforcement inside or outside a PlayReady Trusted Execution Environment as described.

This is detailed in Section 6.6.5 of the PlayReady Compliance Rules for PlayReady Products【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
If the first byte is set to 0, no additional bytes may be specified, and the PlayReady product must disengage Watermarking before passing uncompressed decrypted A/V content to Digital Outputs. If the first byte is set to 1, at least 19 total bytes must be specified, and the product must engage the Watermarking system in the Fourth through Nineteenth Bytes before passing the video portion to Digital Outputs.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5877353623133964). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 4: Response correctness failure - What are the allowed values for the Output Protection Level Restriction Object in a WMD...
**Test Case ID:** `pdf004_q08_comp_rule`

**Query**

```
What are the allowed values for the Output Protection Level Restriction Object in a WMDRM-ND License for PlayReady products?
```

**Response (Agent Output)**

```
Allowed values for the Output Protection Level Restriction Object in a WMDRM-ND License for PlayReady products are as follows:

- Minimum Compressed Digital Audio Output Protection Level: 100, 150, 200, 250, 300  
- Minimum Uncompressed Digital Audio Output Protection Level: 100, 150, 200, 250, 300  
- Minimum Compressed Digital Video Output Protection Level: 400, 500  
- Minimum Uncompressed Digital Video Output Protection Level: 100, 150, 200, 250, 270, 300  
- Minimum Analog Video Output Protection Level: 100, 125, 150, 200  

These values must be limited to the ones listed in Table 8.10 of the PlayReady Compliance Rules document.
```

**Expected / Ground Truth**

```
The Output Protection Level Restriction Object in a WMDRM-ND License must have field values limited to those listed in Table 8.10. The allowed values for both Minimum Compressed and Minimum Uncompressed Digital Audio Output Protection Level are 100, 150, 200, 250, and 300.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.6912763405599361). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 5: Response correctness failure - What are the mandatory requirements for a PlayReady Product when verifying proximity an...
**Test Case ID:** `pdf005_q08_comp_rule`

**Query**

```
What are the mandatory requirements for a PlayReady Product when verifying proximity and security levels before transmitting to a WMDRM-ND Receiver?
```

**Response (Agent Output)**

```
Mandatory requirements for a PlayReady Product when verifying proximity and security levels before transmitting to a WMDRM-ND Receiver include:

- Implementing a timer with at least one (1) millisecond resolution.
- Verifying that the Certificate Security Level in the Device Certificate of the associated WMDRM-ND Receiver is not less than the License Security Level of the PlayReady License for the requested content. Transmission must not proceed if this verification fails.
- Enforcing a proximity detection policy that includes:
  - Round Trip Time (RTT) verification ensuring RTT is no more than seven (7) milliseconds.
  - Setting the Time To Live (TTL) to three (3) in the IPv4 header of the proximity challenge message when transmitting over IPv4 networks.
  - Setting the Hop Count to three (3) in the IPv6 header of the proximity challenge message when transmitting over IPv6 networks.
  - Only transmitting to a WMDRM-ND Receiver if it has successfully completed a proximity challenge at least once in the preceding forty-eight (48) hour period.
- Ensuring revocation data freshness such that transmission is allowed only if the Issued Time on the Revocation Data Timestamp is no more than ninety (90) days prior to the current date/time from a Secure Time Source.
- Limiting concurrent transmissions to no more than ten (10) WMDRM-ND Receivers, or one (1) if acting as a Microsoft OCUR.
- Implementing all WMDRM-ND Protocol messages consistent with the Microsoft Implementation.
- Verifying that the Nonce received from the WMDRM-ND Receiver matches the Nonce sent; if the nonce verification fails, transmission must not occur.

These requirements ensure secure and compliant transmission to a WMDRM-ND Receiver by a PlayReady Product.
```

**Expected / Ground Truth**

```
A PlayReady Product must verify that the Certificate Security Level in the Device Certificate of the associated WMDRM-ND Receiver is not less than the License Security Level of the PlayReady License. It must not transmit if this verification fails. Additionally, the Product must verify that the Round Trip Time (RTT) between itself and the WMDRM-ND Receiver is no more than seven milliseconds. It must also set the TTL to three in the IPv4 header or the Hop Count to three in the IPv6 header of the proximity challenge message when transmitting over respective networks.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5392313249044985). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 6: Response correctness failure - What are the mandatory requirements for content protection systems in the digital media...
**Test Case ID:** `pdf006_q08_comp_rule`

**Query**

```
What are the mandatory requirements for content protection systems in the digital media ecosystem?
```

**Response (Agent Output)**

```
Mandatory requirements for content protection systems in the digital media ecosystem include:

- License acquisition: A valid license must be acquired from a License Server or Proxy Server to play protected content. Licenses store keys, rights, and conditions for content access.
- License properties: Licenses contain a content encryption key, rights to use the content, and license restrictions such as expiration and security levels.
- Security level enforcement: The PlayReady client and license must meet minimum security levels (e.g., SL150, SL2000, SL3000) for license binding and content playback.
- Policy compliance: PlayReady clients must enforce all mandatory policies included in the license, such as expiration dates, begin dates, output protection levels, and minimum security level.
- Trusted clock: Clients must have a PlayReady Trusted Clock to enforce time-based restrictions like expiration and begin times.
- Output protection: Licenses may mandate output protection controls such as HDCP on HDMI outputs to prevent unauthorized copying.
- Communications: License acquisition involves secure client-server transactions typically over HTTP/HTTPS using SOAP.
- License persistence: Licenses may be persistent (stored for offline use) or non-persistent (in-memory only for current session).

These elements collectively define mandatory requirements to ensure secure license issuance, content encryption, policy enforcement, and playback protection in digital media ecosystems using PlayReady DRM【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
Content protection systems must be able to scale to the growing number of devices, be versatile enough to handle an increasing variety of consumption platforms, and maintain the robustness required to provide reliable security across all services and devices. They must also be flexible enough to handle various business scenarios in the expanding digital media ecosystem.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2129575611926025). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 7: Response correctness failure - What are the mandatory compliance requirements for devices to use PlayReady DRM technol...
**Test Case ID:** `pdf007_q08_comp_rule`

**Query**

```
What are the mandatory compliance requirements for devices to use PlayReady DRM technology?
```

**Response (Agent Output)**

```
Mandatory compliance requirements for devices to use PlayReady DRM technology include:

- All PlayReady Products must implement PlayReady or Windows Media DRM consistently with the Microsoft Implementation, with compliance rules taking precedence over conflicting implementation details.
- Devices must not circumvent or provide access inconsistent with PlayReady policy.
- Devices must use specified Root Public Keys when verifying certificate chains.
- Compliance with privacy and data protection legal requirements is mandatory.
- PlayReady Portable Devices, Device Bridges, PlayReady-ND Receivers, Transmitters, WMDRM-ND Receivers, and Transmitters must each execute on a single device and limit exposed content protection functions to decryption, encryption, and license management without enabling DRM circumvention or failure to comply.
- PlayReady-ND Transmitters must implement Anti-Rollback or Secure Clocks and transmit per the PlayReady-ND protocol.
- Device certificates must include required key usages and have assigned certificate security levels.
- PlayReady Portable Devices must implement PlayReady Data Stores, manage license acknowledgments, and handle cryptographic keys with cryptographically random generators.
- Timers with specific resolutions and proximity detection policies are required for network device communication.
- Revocation data must be validated routinely to ensure device security.

These points summarize key mandatory compliance rules devices must follow to integrate PlayReady DRM technology as set forth in the official PlayReady Compliance Rules document from November 2021.【4:0†source】【4:1†source】【4:2†source】
```

**Expected / Ground Truth**

```
Devices must be certified to use PlayReady DRM technology to ensure scalable, secure, and user-friendly protection of media content. Compliance includes supporting multiple media content distribution models, delivery options, and adhering to emerging and established international and industry standards such as MPEG-DASH, HTML5 media extensions, Smooth Streaming, and Apple HTTP Live Streaming (HLS).
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2273972711064824). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 8: Response correctness failure - What must developers do to build a PlayReady client for platforms other than Xbox 360?
**Test Case ID:** `pdf008_q08_comp_rule`

**Query**

```
What must developers do to build a PlayReady client for platforms other than Xbox 360?
```

**Response (Agent Output)**

```
To build a PlayReady client for platforms other than Xbox 360, developers must:

- Use the PlayReady SDK designed specifically for the target platform, such as Android or iOS.
- Alternatively, use the PlayReady Device Porting Kit, which provides portable, platform-independent source code and a comprehensive API for calling PlayReady functions.
- The porting kit supports a wide variety of system architectures, operating system environments, and device types.
- Developers can optimize the client for specific platforms using the source code and functions that accommodate differing device capabilities and configurations.
- The PlayReady Device Porting Kit offers a set of PlayReady APIs, platform-independent source code, a hardware abstraction layer, code samples, programming guides, test kits, and tools.
- For Microsoft platforms, PlayReady clients can be developed using platform-specific SDKs like the PlayReady Client SDK for Windows and Windows Phone.
- Web-based clients can be developed using Silverlight or technologies supporting MPEG-DASH, HTML5 Media Source Extensions (MSE), and Encrypted Media Extensions (EME).

This approach provides broad compatibility across device types and platforms, enabling the creation of PlayReady clients beyond Xbox 360 devices.  

For more details, see the "Developing PlayReady Clients" documentation sections related to SDKs, porting kit, and platform support.【4:0†source】【4:1†source】
```

**Expected / Ground Truth**

```
Developers must use a PlayReady SDK designed specifically for the target platform, such as Android or iOS, or utilize the PlayReady Device Porting Kit, which provides portable, platform-independent source code and a comprehensive API for calling PlayReady functions.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.4771860128576462). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 9: Response correctness failure - What mandatory compliance requirements must partners adhere to when working with PlayRe...
**Test Case ID:** `pdf009_q08_comp_rule`

**Query**

```
What mandatory compliance requirements must partners adhere to when working with PlayReady?
```

**Response (Agent Output)**

```
Mandatory compliance requirements for partners working with PlayReady include:

- All PlayReady Final Products must conform to the Compliance Rules and Robustness Rules.
- Companies must provide the Compliance Rules, Robustness Rules, and Device Assets and Revocation Provisions to those responsible for the design and manufacture of PlayReady Final Products.
- Documentation demonstrating how PlayReady Final Products conform to these rules must be maintained and provided to Microsoft upon request.
- Companies must not reverse engineer or access source code except as permitted by law or authorized by Microsoft.
- Certificates must be protected and not installed in Disabled Versions; if compromised, royalties become due.
- Company must adhere to rules about transfer and distribution of PlayReady Intermediate Products to authorized licensees and manage contractors appropriately.
- End-user notices about PlayReady technology usage and content protection must be included.
- Device keys and manufacturing secrets must be protected with rigorous confidentiality and access control.
- Upon suspicion of a material security problem, companies must cooperate with Microsoft for evaluation and remediation.
- Microsoft may revoke certificates associated with PlayReady Final Products if a material security problem or breach occurs.
- Regular reporting of distributed or activated PlayReady Final Products and royalty payments to Microsoft are mandatory.
- Audits may be conducted to verify compliance with licensing terms.

These requirements are detailed in the Microsoft PlayReady Final Product License agreement and related exhibits covering compliance, security, and revocation provisions【4:0†source】.
```

**Expected / Ground Truth**

```
Partners must comply with all PlayReady licensing terms and conditions as outlined in the compliance section. They are obligated to follow the specified rules to maintain their licensing and partnership status.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2966777026423037). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 10: Response correctness failure - What mandatory compliance requirements or obligations are mentioned in the terms of use...
**Test Case ID:** `pdf010_q08_comp_rule`

**Query**

```
What mandatory compliance requirements or obligations are mentioned in the terms of use and privacy statements linked in the document?
```

**Response (Agent Output)**

```
Mandatory compliance requirements and obligations in the PlayReady terms of use and privacy-related statements include:

- All PlayReady Final Products must conform to the Compliance Rules and Robustness Rules.
- Company must prevent reverse engineering of Developed Technology except as permitted by applicable law or authorized by Microsoft.
- Company shall not install Certificates in Disabled Versions and must prevent Certificates from being installed post-distribution.
- PlayReady Final Products must include specific labeling and end-user notices informing about the use of PlayReady technology and content protection.
- Company must provide Compliance Rules, Robustness Rules, Device Assets, and Revocation Provisions to those responsible for design and manufacture and maintain documentation of adherence.
- Microsoft may update Compliance and Robustness Rules with a requirement for new products released 18 months after notice to conform.
- Company must use commercially reasonable efforts to comply with these rules and cooperate with Microsoft audits and investigations.
- Company must pay royalties based on units distributed or activated and submit reports regularly.
- Microsoft may revoke Certificates associated with products in case of Material Security Problems, non-conformance, or breach.
- Company must protect Device Keys and Manufacturing Secrets with rigorous safeguards to prevent unauthorized access or compromise.
- Third party beneficiaries (such as content owners) have rights to enforce compliance related to PlayReady technology.

These obligations are established in the Final Product License, Compliance Rules, and related Exhibits covering security, reporting, revocation, and use restrictions as core mandatory compliance terms.  

If you need details on any specific obligation or section, please let me know.
```

**Expected / Ground Truth**

```
The document references several links including Terms of Use, Trademarks, Privacy Statement, and Consumer Health Privacy, which imply mandatory compliance with the rules and obligations stated in those links. Users must adhere to the Terms of Use, respect trademark guidelines, and comply with privacy policies as outlined in the provided URLs.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2118107678959488). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 11: Response correctness failure - What must be done for a user to be able to use a media file protected by PlayReady?
**Test Case ID:** `pdf011_q08_comp_rule`

**Query**

```
What must be done for a user to be able to use a media file protected by PlayReady?
```

**Response (Agent Output)**

```
Using a media file protected by PlayReady requires the following:

- The client device must first be activated, which allows licenses to be bound to the device. Activation is automatic on the first attempt to play protected content but can be done proactively to avoid lag.
- When the client requests a license, it authenticates using a unique device public key. The license server verifies the PlayReady client device and encrypts the content key with the device's public key.
- The client uses its private device key to decrypt the license and access the content.
- User authentication may be implemented by the content provider and integrated with the PlayReady license service through either proxy servers or authentication tokens.
- The issued license specifies rights and conditions for playback of the protected media.
- The device must support compatible media formats and adhere to PlayReady compliance and robustness rules.

In summary, for a user to use a PlayReady-protected media file:
1. The PlayReady client device must be activated.
2. The client must acquire a license from a compliant license server via authenticated requests.
3. The client uses the license and device keys to decrypt and play the protected content.

This process ensures that content is protected and playable only on authorized devices under permitted rights and conditions.  

This is outlined from PlayReady client activation, license acquisition, and encryption binding described in the PlayReady client development documentation【4:1†source】【4:2†source】.
```

**Expected / Ground Truth**

```
To use a media file protected by PlayReady, a user must have a valid license granted to a single client or domain. The license contains rights and restrictions that define how and under what conditions the content may be used, and the media file cannot be used without this license.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2871218347509348). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 12: Response correctness failure - What are the mandatory steps that must be followed for PlayReady license acquisition tr...
**Test Case ID:** `pdf012_q08_comp_rule`

**Query**

```
What are the mandatory steps that must be followed for PlayReady license acquisition transactions between the client and the server?
```

**Response (Agent Output)**

```
Mandatory steps for PlayReady license acquisition transactions between the client and the server are:

1. The client generates a challenge and sends it to the License Server.
2. The server processes the challenge and generates a license response.
3. The server sends the license response back to the client.

This transaction is typically done over HTTP or HTTPS and uses a SOAP-based protocol, which can be customized. The challenge from the client includes the content header and device information. The server uses a shared license key seed and key identifier to generate the content key, encrypts it, creates the license with the encrypted content key and policies, signs the license, and sends it back to the client. The client then verifies the signature and expiration date, stores the license, and uses it for content decryption and playback.

These steps ensure the client acquires the valid license necessary for playback of protected content【4:1†source】.
```

**Expected / Ground Truth**

```
PlayReady license acquisitions must involve a transaction consisting of a challenge generated by the client and sent to the server, followed by a response generated by the server and sent back to the client. This transaction usually occurs over HTTP or HTTPS using a protocol based on SOAP, and can be implemented asynchronously if needed.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.534251162167434). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 13: Response correctness failure - What are the mandatory steps that must be followed in the PlayReady rental content scen...
**Test Case ID:** `pdf013_q08_comp_rule`

**Query**

```
What are the mandatory steps that must be followed in the PlayReady rental content scenario?
```

**Response (Agent Output)**

```
Mandatory steps in the PlayReady rental content scenario are:

1. Content is protected with Microsoft PlayReady technology.

2. The service provider transfers content protection information to a License Server.

3. The service provider transfers protected content to a distribution Server.

4. A client requests content for streaming or download.

5. The client acquires a license and begins streaming or downloading the content.

The license specifies an expiration date and time, which the PlayReady Client uses with the device clock to enforce expiration. It is recommended to also set a begin date/time to help prevent clock rollback attacks.

Licenses may include restrictions like:
- Play right (right to decrypt and render content)
- Begin Time (usually the time user paid for content)
- Expiration Time
- Expiration After First Play (e.g., 48 hours after first play)

A PlayReady trusted clock is required to support these start and expiration times.

Rental content can be streamed or downloaded using standard protocols (SSTP, DASH, HLS, HTTP). Licenses can be persistent or non-persistent depending on streaming or download scenarios.

These steps ensure proper license acquisition, enforcement of time-limited usage, and playback control in rental content scenarios【4:1†source】.
```

**Expected / Ground Truth**

```
In the PlayReady rental content scenario, the content must be protected with Microsoft PlayReady technology. The service provider is required to transfer content protection information to a License Server and protected content to a Server for distribution. A client must request content and acquire a license before streaming or downloading the content, which it can then decrypt and play back continuously.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5372598213785302). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 14: Response correctness failure - What must an OEM, PlayReady Client developer, or PlayReady service provider do before d...
**Test Case ID:** `pdf015_q08_comp_rule`

**Query**

```
What must an OEM, PlayReady Client developer, or PlayReady service provider do before developing a PlayReady product?
```

**Response (Agent Output)**

```
Requirements Before Developing a PlayReady Product

- An OEM, PlayReady Client developer, or PlayReady service provider must first obtain a PlayReady license from Microsoft before beginning product development.
- This license grants access to all necessary materials for creating the product, whether it is an integrated circuit, device with embedded PlayReady Client, PlayReady application, or PlayReady Server.
- Separate licenses exist depending on the product type, such as device distribution, downloadable applications, or server applications servicing end-users.
- The license also provides intellectual property rights, protection, and indemnification.
- Content providers using third-party PlayReady Clients and Servers do not need a license to encrypt content or include PlayReady Header insertion in encryptors.

This process is mandatory to start developing any PlayReady product. For more details, see PlayReady Licensing Options provided by Microsoft【4:1†source】.
```

**Expected / Ground Truth**

```
They must first obtain a PlayReady license from Microsoft before beginning development. This license entitles them to receive all necessary materials from Microsoft to create their product.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5079043905188696). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 15: Response correctness failure - What are the mandatory requirements for packaging content to be PlayReady compliant?
**Test Case ID:** `pdf016_q08_comp_rule`

**Query**

```
What are the mandatory requirements for packaging content to be PlayReady compliant?
```

**Response (Agent Output)**

```
Mandatory requirements for packaging content to be PlayReady compliant include:

- Encrypt the content using AES-128 keys in either CTR (Counter) mode or CBC (Cipher Block Chaining) mode.
- Insert a PlayReady Header in the encrypted content that contains information such as key identifiers (KIDs), default license acquisition URL, and optional custom data.
- Use MP4-based formats, preferably CMAF for PlayReady Clients on Windows 10 and Xbox One.
- For MP4 ISO files, insert the PlayReady Header in a 'pssh' box as per the ISO format specification.
- For adaptive streaming, insert the PlayReady Header in the streaming manifest (e.g., MPEG-DASH manifest) using proper tags such as <mspr:pro>.
- Ensure the PlayReady Header has the correct version and includes elements such as KIDs, LA_URL (license acquisition URL), and optionally the domain service identifier.
- Support for encryption modes includes Common Encryption modes 'cenc' (AES-CTR) and 'cbcs' (AES-CBC) as defined in ISO/IEC 23001-7.

These requirements ensure that PlayReady clients can properly locate keys, request licenses, and decrypt the content for playback according to PlayReady compliance rules.【4:1†source】【4:2†source】
```

**Expected / Ground Truth**

```
PlayReady does not include a packager as part of its deliverables and instead provides specifications based on common encryption standards. The encryption format must follow the file format and commonly uses the Common Encryption ISO Standard format, ISO/IEC 23001-7. Content packagers must either create their own packager or use an open source encryptor or professional encoder that complies with these standards.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2211530332245573). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 16: Response correctness failure - What mandatory steps must be taken for decryption in PlayReady content encryption systems?
**Test Case ID:** `pdf017_q08_comp_rule`

**Query**

```
What mandatory steps must be taken for decryption in PlayReady content encryption systems?
```

**Response (Agent Output)**

```
Mandatory steps for decryption in PlayReady content encryption systems include:

- Acquiring a valid license for the content before playback.
- The client searches the License Store for a valid license; if none is found, it requests a license from the License Server via a license challenge.
- The License Server generates and delivers a signed license containing the encrypted content key and associated usage policies.
- The client verifies the license signature and expiration, then stores the license.
- The DRM component on the client decrypts content packets using the content key from the license.
- The client enforces license policies such as rights, restrictions, and security level requirements (e.g., minimum Security Level, expiration policies).
- The client must have a PlayReady Trusted Clock to enforce date/time-based restrictions.
- The license must be bound to the client or domain with the private key to decrypt the license's content protection information.

These steps are essential to ensure secure content decryption and policy enforcement in PlayReady systems【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
The license must be properly handled to decrypt the symmetric key. After this, the content can be decrypted using small and fast algorithms. This process ensures that once startup is complete, few CPU cycles or system resources are required for decryption.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2116756690499649). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 17: Response correctness failure - What are the mandatory requirements to create a PlayReady Header using the PlayReady Se...
**Test Case ID:** `pdf018_q08_comp_rule`

**Query**

```
What are the mandatory requirements to create a PlayReady Header using the PlayReady Server SDK?
```

**Response (Agent Output)**

```
[AGENT CALL FAILED: APIConnectionError: Connection error.]
```

**Expected / Ground Truth**

```
To create a PlayReady Header using the PlayReady Server SDK, you must have the KeyID(s) generated by the key management system, know the encryption type (AESCTR or AESCBC), and create the PlayReady header inside the PlayReady object using the Windows 10 PlayReadyContentHeader class.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.1705822569694384). Answer relevancy=FAIL, completeness=FAIL.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 18: Response correctness failure - What mandatory cryptographic algorithms must be used in a PlayReady license response si...
**Test Case ID:** `pdf019_q08_comp_rule`

**Query**

```
What mandatory cryptographic algorithms must be used in a PlayReady license response signature?
```

**Response (Agent Output)**

```
[AGENT CALL FAILED: APIConnectionError: Connection error.]
```

**Expected / Ground Truth**

```
The license response must use the canonicalization method algorithm 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315' and the signature method algorithm 'http://schemas.microsoft.com/DRM/2007/03/protocols#ecdsa-sha256'. Additionally, the digest method algorithm must be 'http://schemas.microsoft.com/DRM/2007/03/protocols#sha256'.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.1685668933210826). Answer relevancy=FAIL, completeness=FAIL.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 19: Response correctness failure - What must PlayReady products do to protect video data during transmission from unauthor...
**Test Case ID:** `pdf020_q08_comp_rule`

**Query**

```
What must PlayReady products do to protect video data during transmission from unauthorized interception?
```

**Response (Agent Output)**

```
PlayReady products must be designed to ensure that video data, when transmitted, is reasonably secure from unauthorized interception. Specifically:

- For video transmitted over a User Accessible Bus:
  - Uncompressed decrypted video content of certain resolution must be secure from unauthorized interception with difficulty, preventing typical consumers from intercepting it using widely available or specialized tools without risk of serious damage or injury.
  - Compressed decrypted video content must also be reasonably secure from unauthorized interception, again making interception difficult with widely available or specialized tools.
  
- For higher security levels (License Security Level 3000 or higher):
  - PlayReady products must use a PlayReady Trusted Execution Environment (TEE).
  - Decrypted audio/video content must not be readable or accessible outside the TEE.
  - Video data transmission must be secure from unauthorized interception using widely available, specialized, or professional software tools, and interception with professional hardware tools must be difficult and risky for typical consumers.

These protections aim to ensure that video data transmitted within the device or over accessible buses is robustly protected against interception using common or specialized tools, thereby preventing unauthorized access during transmission. 

This is summarized from the PlayReady Robustness Rules regarding Accessibility of Content and required levels of robustness for video data transmission security【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
PlayReady products must be designed so that when video portions of decrypted audio/video content are transmitted, the data is secure from unauthorized interception using widely available, specialized, or professional software tools. Additionally, interception using professional hardware tools should be difficult enough that a typical consumer cannot do so without risking serious damage or personal injury.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.4478476764284275). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 20: Response correctness failure - What is the mandatory requirement for updating PlayReady Server certificate revocation...
**Test Case ID:** `pdf021_q08_comp_rule`

**Query**

```
What is the mandatory requirement for updating PlayReady Server certificate revocation lists according to the Compliance Rules for PlayReady Products?
```

**Response (Agent Output)**

```
The mandatory requirement for updating PlayReady Server certificate revocation lists according to the Compliance Rules for PlayReady Products is that the company must update the PlayReady Server Software Development Kit (SDK) certificate revocation lists for each PlayReady Server once a week by accessing the certificate revocation lists at the specified Microsoft URL: https://go.microsoft.com/fwlink/?LinkId=110086.
```

**Expected / Ground Truth**

```
Companies operating a PlayReady Server must update the PlayReady Server Software Development Kit certificate revocation lists for each PlayReady Server once a week. This requirement ensures that any compromised client gets its license requests declined promptly after being added to the Revocation List by Microsoft.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5415934440603463). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 21: Response correctness failure - What mandatory actions must a player take when handling a license with a RealTimeExpira...
**Test Case ID:** `pdf022_q08_comp_rule`

**Query**

```
What mandatory actions must a player take when handling a license with a RealTimeExpiration restriction during playback?
```

**Response (Agent Output)**

```
Mandatory player actions for a license with a RealTimeExpiration restriction during playback are:

- The player must enforce the expiration not only at the beginning of a playback session but also at regular intervals during playback.
- The RealTimeExpiration restriction requires the player to check for expiration in real time during the playback session.
- This applies to PlayReady 3.0 or higher.
- Limited Duration Licenses (LDLs) with RealTimeExpiration are typically short duration and renewed frequently, with the player proactively acquiring a new license before the current one expires, allowing continuous playback.
- The player binds automatically and seamlessly to the renewed license at expiration.
- For LDLs, it is recommended to implement them as non-persistent for efficiency.
- The player should also clean up the license store periodically to remove expired licenses.

These requirements collectively ensure that playback stops promptly when the license expires according to real-time checks during playback, enforcing content usage rights accordingly.【4:1†source】
```

**Expected / Ground Truth**

```
A player must check for license expiration in real time during playback when handling a license with a RealTimeExpiration restriction. Additionally, the player must bind automatically and seamlessly to a renewed license to continue playback. It is also mandatory for device makers to design devices to clean up the license store periodically, such as daily or at every boot, to quickly remove expired licenses.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5855728349342065). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 22: Response correctness failure - What must OEMs or App Vendors do when releasing PlayReady Clients regarding communicati...
**Test Case ID:** `pdf023_q08_comp_rule`

**Query**

```
What must OEMs or App Vendors do when releasing PlayReady Clients regarding communication with services during PlayReady operations?
```

**Response (Agent Output)**

```
OEMs or App Vendors releasing PlayReady Clients may design their device or application to contact a service when performing PlayReady operations. A very common example is the remote provisioning service, which delivers a unique Client Certificate to a client the first time it performs a PlayReady operation. These services are specific to the client, owned by the device maker or app developer, and use ad-hoc protocols. Microsoft operates some of these services for the clients it owns, including Windows 10, Windows 8.1, Xbox, and Silverlight【4:1†source】.
```

**Expected / Ground Truth**

```
OEMs or App Vendors releasing PlayReady Clients must design their device or application to contact a service when performing PlayReady operations. This often involves a remote provisioning service that delivers a unique Client Certificate to the client the first time it performs a PlayReady operation.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5863102640523975). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 23: Response correctness failure - What must a PlayReady client do to inform the License Server about the features it supp...
**Test Case ID:** `pdf024_q08_comp_rule`

**Query**

```
What must a PlayReady client do to inform the License Server about the features it supports?
```

**Response (Agent Output)**

```
A PlayReady client informs the License Server about the features it supports by including a PlayReady Client Certificate in each license request. This certificate contains an ID and asymmetric key pairs. Additionally, for clients developed with PlayReady Device Porting Kit 3.0 or higher, the client certificate class supports a GetSupportedFeatures method that returns a collection of features to help define policies within the license handler. This allows the License Server to identify the client capabilities and adjust license policies accordingly. For example, the License Server can deliver different licenses or policies for clients supporting PlayReady 3.0 and higher features based on the supported features reported by the client certificate【4:1†source】.
```

**Expected / Ground Truth**

```
Starting with PlayReady Device Porting Kit Version 4.4, the client must send information about what features it supports, including both REE and TEE features, to the License Server as part of its license acquisition challenge.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2279221408807512). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 24: Response correctness failure - What mandatory steps must an application take before opening a DRM session using PlayRe...
**Test Case ID:** `pdf025_q08_comp_rule`

**Query**

```
What mandatory steps must an application take before opening a DRM session using PlayReady?
```

**Response (Agent Output)**

```
Mandatory steps before opening a DRM session in PlayReady are:

- The application must call setPropertyString to set the DeviceStoreName property before opening the session. This property points to the location of the device store used to store the HDS (Hardware Downstream Secure store), and it must be accessible to the app like its private data directory.
- The app then calls openSession, which will initialize the DRM Manager by creating the AppContext via Drm_Initialize, using the DeviceStoreName provided.
- The application should set the content header on the plug-in before attempting to create a Crypto object. The content header can be in various formats such as a byte array with PlayReady Object contents or XML headers.
- Optionally, the app can set other properties like LicenseChallengeCustomData before calls to getKeyRequest.

These steps ensure proper initialization and parameter setting before managing DRM sessions and license acquisition in PlayReady【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
Before opening a DRM session, the application must set the PropertyString on the plug-in to provide the path to the device store used for storing the HDS. Specifically, the application must call setPropertyString to set the DeviceStoreName, ensuring that a subsequent call to getPropertyString with DeviceStoreName returns a valid value. Additionally, when closing a DRM session, the application must call Drm_Uninitialize to release the AppContext.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.4271535991802396). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 25: Response correctness failure - What is mandatory when using the ISO Base Media File Format live profile for live encod...
**Test Case ID:** `pdf026_q08_comp_rule`

**Query**

```
What is mandatory when using the ISO Base Media File Format live profile for live encoding in DASH?
```

**Response (Agent Output)**

```
Mandatory when using the ISO Base Media File Format live profile for live encoding in DASH with PlayReady:

- The PlayReady ContentProtection Descriptor element SHALL be contained in an AdaptationSet element, not at the Representation level, to enable seamless adaptive bitrate switching.
- The PlayReady Object (PRO) SHALL be present either in the Media Presentation Description (MPD) or in the Initialization Segment, and may be present in both.
- The ContentProtection Descriptor with schemeIdUri="urn:mpeg:dash:mp4protection:2011" and value="cenc" SHALL always be present to indicate encrypted content.
- The PlayReady PlayReady Object in the ContentProtection Descriptor SHALL include license acquisition information and keys.
- For live streaming, license acquisition information is better included in the MPD using cenc:pssh rather than in every Initialization Segment to avoid simultaneous license requests at startup.
- The KID (Key Identifier) values in the PlayReady Object and Track Encryption Box MUST be equivalent and correctly byte-ordered according to PlayReady requirements.
- Track Encryption Box fields, especially default_KID, SHOULD be communicated in the MPD to identify the necessary license.

These requirements ensure proper signaling and license acquisition flow for PlayReady-protected live streaming content using the ISO Base Media File Format live profile in DASH. 

This is summarized from detailed PlayReady DASH content protection specification sections 2.1 and 2.2 with emphasis on the live profile usage and signaling conventions【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
When using the ISO Base media file format live profile for live encoding in DASH, each movie segment must be requested immediately after it is encoded using a template generated URL, as this profile is optimized for live encoding scenarios.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2103042765213511). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 26: Response correctness failure - What must PlayReady implementations and the software accessing them comply with to ensu...
**Test Case ID:** `pdf027_q08_comp_rule`

**Query**

```
What must PlayReady implementations and the software accessing them comply with to ensure proper content access and usage?
```

**Response (Agent Output)**

```
PlayReady implementations and the software accessing them must comply with the PlayReady Compliance Rules. These Compliance Rules specify the required behaviors of PlayReady implementations and software, describing how content may be accessed and passed using specific policy rules. This ensures proper content access and usage by enforcing the policies defined in the PlayReady licenses, which include rights, restrictions, and conditions under which the content can be used. The Compliance Rules also cover enforcement of output protection levels, security levels, expiration policies, and other rights and restrictions to prevent unauthorized use and maintain content protection. 

In summary:
- Compliance Rules specify required behaviors of PlayReady implementations and accessing software.
- They control content access and usage via policy rules in licenses.
- They enforce rights, restrictions, security levels, and output protection.
- They include policies such as expiration, minimum security level, and usage conditions.

These Compliance Rules are essential to ensure proper licensed access and secure usage of PlayReady-protected content.
```

**Expected / Ground Truth**

```
PlayReady implementations and the software accessing them must comply with Compliance Rules, which specify the required behaviors and describe how content may be accessed and passed using specific policy rules.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.6134494947925764). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 27: Response correctness failure - What are the mandatory steps I must follow to properly submit a signed wmla.ocx file fo...
**Test Case ID:** `pdf028_q08_comp_rule`

**Query**

```
What are the mandatory steps I must follow to properly submit a signed wmla.ocx file for PlayReady certification?
```

**Response (Agent Output)**

```
Mandatory steps to properly submit a signed wmla.ocx file for PlayReady certification:

1. Obtain an Extended Validation Code Signing Certificate (EV Certificate) from an accepted Certificate Authority such as Symantec, GlobalSign, Thawte, or DigiCert.
2. Download the WMLA.zip folder containing wmla.ocx and signcode.exe tools (link: http://go.microsoft.com/fwlink/?LinkID=148072).
3. Use signcode.exe to sign the wmla.ocx file with the obtained EV Certificate. Utilities from the Certificate Authority's website may also be used.
4. Do not sign any .exe files, only the wmla.ocx is accepted.
5. Send the signed wmla.ocx file to ipla@microsoft.com either within a compressed ZIP folder or via a shared folder (e.g., OneDrive) with a link provided.
6. Confirm the digital signature is correct by checking the file properties under Digital Signatures before submission.
7. Include your company name in the email for identification.
8. Microsoft will verify the signed file and respond by email.

Additional instructions are available at http://msdn2.microsoft.com/en-us/library/ms537364.aspx【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
You must use the signcode.exe tool or a similar utility to sign the wmla.ocx file with your certificate. Then, send the signed OCX file to ipla@microsoft.com either within a compressed ZIP folder or by uploading it to a shared folder like OneDrive and sharing the link. Additionally, include your company name in the email for clear identification. Finally, verify your signature by checking the file's Properties under Digital Signatures before submission.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.6771777476026003). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 28: Response correctness failure - What are the mandatory requirements for distributing PlayReady Intermediate Products to...
**Test Case ID:** `pdf029_q08_comp_rule`

**Query**

```
What are the mandatory requirements for distributing PlayReady Intermediate Products to Authorized Contractors and Microsoft PlayReady Device Licensees?
```

**Response (Agent Output)**

```
Mandatory requirements for distributing PlayReady Intermediate Products to Authorized Contractors and Microsoft PlayReady Device Licensees include:

- Company must check the Microsoft PlayReady Device Licensees list before distribution; if a Potential Authorized Licensee is not listed, Company must request authorization in writing from Microsoft.
- Company may distribute Developed Technology in source code form only to Microsoft PlayReady Device Licensees licensed under a Microsoft PlayReady Intermediate Product License or PlayReady Device Development and Intermediate Product Distribution License.
- Upon learning that a third party is no longer a Microsoft PlayReady Device Licensee, Company must cease distribution of PlayReady Intermediate Products to that party within 10 business days.
- Company must include this statement in agreements and product markings: “This product is subject to certain intellectual property rights of Microsoft and cannot be used or distributed further without the appropriate license(s) from Microsoft.”
- On reasonable request, Company must provide Microsoft with a report of all Microsoft PlayReady Device Licensees it distributed to and related product volumes. Microsoft may corroborate this information with reports from other licensees.
- If engaging Authorized Contractors, Company must notify Microsoft upon request, have agreements obligating contractors to the same terms, promptly correct breaches, and be liable for contractor acts or omissions.
- Company must provide Commercial Test Certificates for internal testing only and cannot distribute them except to authorized independent contractors.
- Company must provide Microsoft PlayReady Device Licensees receiving an Intermediate Product API access the right to close or restrict such access to their own applications.

These are outlined primarily in Sections 3.2 and 3.5 of the Microsoft PlayReady Intermediate Product License document【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
PlayReady Intermediate Products must be distributed in object code form to Authorized Contractors to reproduce, install, and test Developed Technology on or into the Company's Final Products, subject to the requirements in Section 3.9. Similarly, they must be distributed in object code form to Microsoft PlayReady Device Licensees to reproduce, install, and test Developed Technology on or into the Company's Final Products, subject to the requirements in Section 3.10.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2343523282004687). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 29: Response correctness failure - What compliance requirements must a company meet to benefit from Microsoft's patent cov...
**Test Case ID:** `pdf030_q08_comp_rule`

**Query**

```
What compliance requirements must a company meet to benefit from Microsoft's patent covenant under the PlayReady Intermediate Product License?
```

**Response (Agent Output)**

```
Compliance requirements under the PlayReady Intermediate Product License for a company to benefit from Microsoft's patent covenant include:

- The company must comply with all terms and conditions of the Agreement.
- Distribution of PlayReady Intermediate Products must only be to Microsoft PlayReady Device Licensees or Authorized Contractors under agreement.
- The company shall check the Microsoft PlayReady Device Licensee list prior to distribution to any third party.
- The company must ensure to cease distribution to any former licensees within ten business days upon learning of the status change.
- The company must include an intellectual property rights statement in agreements and product documentation.
- The company must make the Compliance Rules and Robustness Rules available to responsible persons for product design and manufacture.
- The company must document compliance aspects and provide such documentation to Microsoft and other licensees upon request.
- The company must cooperate with Microsoft and other licensees in analyzing and remedying any identified material security problems.
- If the company uses Authorized Contractors, it must notify Microsoft, ensure contractual obligations, and be liable for their actions.

While the patent covenant protects the company from infringement suits related to their use of Developed Technology in Intermediate Products, this is contingent upon their full compliance with these and other license conditions described in the Agreement and Sections 2 and 3 of the license document【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
The company must comply with all terms and conditions of the Intermediate Product License Agreement to benefit from Microsoft's covenant not to sue for infringement of a Microsoft Necessary Claim. This includes using Developed Technology in Intermediate Products and making, selling, or offering such technology solely for inclusion and further distribution as part of Final Products or other Intermediate Products, subject to specific provisions in the agreement.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.3158950297628612). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 30: Response correctness failure - Who should I contact for support related to PlayReady tool access and technical questions?
**Test Case ID:** `pdf031_q08_comp_rule`

**Query**

```
Who should I contact for support related to PlayReady tool access and technical questions?
```

**Response (Agent Output)**

```
For support related to PlayReady tool access and technical questions, you should contact PlayReady@microsoft.com. This contact is designated for access to the Microsoft Connect Business tool PlayReady and for technical questions. For signing-in and licensing questions, you may also contact ipla@microsoft.com. 

- PlayReady@microsoft.com: Access to Microsoft Connect Business, PlayReady tool, and technical questions.
- ipla@microsoft.com: Sign-in help, new agreements, amendments, contact change requests, and releasing deliverables.

These email contacts are provided for licensed companies requiring support with PlayReady tools and technical issues【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
For support related to PlayReady tool access and technical questions, you must contact PlayReady@microsoft.com.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.3603158867793778). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 31: Response correctness failure - What mandatory requirements must be followed to protect and deliver premium Live TV ser...
**Test Case ID:** `pdf032_q08_comp_rule`

**Query**

```
What mandatory requirements must be followed to protect and deliver premium Live TV services across multiple devices?
```

**Response (Agent Output)**

```
Mandatory requirements to protect and deliver premium Live TV services across multiple devices with PlayReady include:

- Frequent and dynamic rotation of content keys and policies, integrated with key management services and content encoders/packagers for robust security and contractual compliance.
- Use of scalable chained licenses, with root licenses containing multiple root keys and policies, and leaf licenses bound to specific root keys, to efficiently grant access to multiple services while minimizing key issuance.
- Embedding licenses in the media stream (using ISO Common Encryption Scheme) for real-time enforcement of key and policy changes without disrupting playback.
- Customizable access controls that allow flexible definition of channel packages, subscription types and levels, region-based policies, and support for blackout signaling based on geographic or other criteria.
- Compatibility across a wide range of devices and platforms, supporting multiscreen delivery including mobile, tablets, STBs, Smart TVs, and more.
- Support for dynamic ad insertion aligned with advertising metadata and national/local advertising decisions.
- An architecture combining PlayReady license services (scalable root and leaf license services), encryptor/packager, origin servers, advertising systems, and blackout decision services to securely manage content key delivery, licensing, and enforcement.

These requirements ensure scalable, studio-grade protection and delivery of Live TV content with flexibility for diverse business models and device ecosystems【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
To protect and deliver premium Live TV services, content protection systems must support a variety of internet-enabled and mobile devices, as well as multiple consumption platforms. The design must accommodate managed content experiences on unmanaged devices and handle content delivery across phones, tablets, game consoles, Smart TVs, IP streaming boxes, and connected Blu-ray players.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2226625579540518). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 32: Response correctness failure - What must PlayReady clients do if the DECRYPTORSETUP element is set to 'ONDEMAND' in a...
**Test Case ID:** `pdf033_q08_comp_rule`

**Query**

```
What must PlayReady clients do if the DECRYPTORSETUP element is set to 'ONDEMAND' in a DATA node?
```

**Response (Agent Output)**

```
If the DECRYPTORSETUP element is set to "ONDEMAND" in a DATA node, PlayReady clients should not expect the full license chain for the file to be available for acquisition or already present on the client device prior to setting up the media graph. This indicates that the license chain may be acquired on demand rather than being pre-available. 

This usage addresses Live TV scenarios delivering scalable root licenses and embedded scalable leaf licenses to clients, requiring streams to use WRMHeader version 4.1.0.0 or later with the DECRYPTORSETUP element set to "ONDEMAND" in the header's DATA node. 

In summary:
- Clients do not expect the full license chain to be present or acquired before media graph setup.
- The license chain may be obtained on demand during playback.

This is distinct from the scenario where this DECRYPTORSETUP element is not present, where clients expect the full license chain to be present or acquired before media graph setup【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
PlayReady clients must not expect the full license chain for the file to be available for acquisition or present on the client device when the DECRYPTORSETUP element is set to 'ONDEMAND' in a DATA node.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.4603033648286179). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 33: Response correctness failure - What must a company do when modifying the Licensed Technology under a Microsoft PlayRea...
**Test Case ID:** `pdf034_q08_comp_rule`

**Query**

```
What must a company do when modifying the Licensed Technology under a Microsoft PlayReady Intermediate Product License?
```

**Response (Agent Output)**

```
When modifying the Licensed Technology under a Microsoft PlayReady Intermediate Product License, a company must:

- Use the Licensed Technology and Deliverables solely to develop Developed Technology that decrypts, encrypts, acquires, and/or issues licenses for PlayReady Content as described in the Specifications.
- Not use or modify the Licensed Technology in any way that enables the Developed Technology to access and manipulate PlayReady Content without obtaining a Certificate from Microsoft (or a Microsoft Affiliate) under Section 3.4 or under a PlayReady Final Product Distribution License.
- Comply with the licensing terms which limit distribution to Microsoft PlayReady Device Licensees and provide proper notifications and documentation.
- Make the Compliance Rules and the Robustness Rules available to responsible persons and document which aspects of these rules the Developed Technology conforms to.
- Cooperate in addressing any Material Security Problems by making technical contacts available, sharing information, and promptly developing patches or fixes if the issue is attributable to the company's PlayReady Intermediate Product.
- If engaging Authorized Contractors for reproducing, installing, or testing Developed Technology, ensure they comply with the same obligations and be liable for their breaches.

These requirements are outlined to control and secure the use and modification of Licensed Technology under the Intermediate Product License agreement with Microsoft. 

For detailed operational steps on modifications, the company must also ensure proper licensing compliance and seek authorization for distribution to third parties listed as Microsoft PlayReady Device Licensees【4:1†source】.
```

**Expected / Ground Truth**

```
The company must modify the Licensed Technology solely for the purpose of enabling it to operate on or with Intermediate Products or on Final Products, as specified under the terms of a Microsoft PlayReady Intermediate Product License or similar agreements.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2335943158297792). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 34: Response correctness failure - What are the mandatory requirements for a Server Application under the PlayReady Server...
**Test Case ID:** `pdf035_q08_comp_rule`

**Query**

```
What are the mandatory requirements for a Server Application under the PlayReady Server Agreement?
```

**Response (Agent Output)**

```
Mandatory requirements for a PlayReady Server Application under the PlayReady Server Agreement include:

- The PlayReady Server must comply with all requirements in Section 2 (Requirements for All PlayReady Products) and Section 17 (Requirements for PlayReady Servers).
- The PlayReady Server may implement features described in Section 6 (Creating PlayReady Licenses) only if they conform to the Compliance Rules in that Section.
- Company must update the PlayReady Server Software Development Kit certificate revocation lists weekly by accessing the revocation lists at https://go.microsoft.com/fwlink/?LinkId=110086.
- Company may use only Service IDs obtained from Microsoft.

These requirements ensure proper compliance with certificate revocation, license creation, and authorized use of identifiers in PlayReady Server operations.【4:4†source】 
```

**Expected / Ground Truth**

```
A Server Application must run on a server operating system version specified by the then-current Specifications and use the Licensed Technology to encrypt PlayReady Content, set PlayReady Policy, and issue licenses containing PlayReady Policy and encrypted keys used to decrypt the associated PlayReady Content.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2220880076377686). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 35: Response correctness failure - What must licensees do to comply with PlayReady licensing requirements?
**Test Case ID:** `pdf036_q08_comp_rule`

**Query**

```
What must licensees do to comply with PlayReady licensing requirements?
```

**Response (Agent Output)**

```
To comply with PlayReady licensing requirements, licensees must:

- Follow the PlayReady Compliance and Robustness Rules, including meeting the security requirements defined by PlayReady Security Levels such as SL3000.
- Conduct a security review of Intermediate Products, documenting verification against SL3000 requirements and communicating this to Final Product Licensees.
- Ensure Final Products utilize SL3000 Conformant Intermediate Products and conform to SL3000 Compliance and Robustness rules.
- Implement design requirements such as using a PlayReady Trusted Execution Environment (TEE) for content protection.
- Protect decrypted content and application secrets within the PlayReady TEE.
- Secure video transmission against interception using various tools.
- Protect device, protocol, application secrets, content keys, license integrity keys, and root public keys against unauthorized access or modification.
- Follow requirements for secure clocks, secure boot processes, secure update processes, remote provisioning, and output protection within the PlayReady TEE.
- Verify and comply with specific requirements when transmitting to or receiving from PlayReady-ND or WMDRM-ND receivers, including security level verification, timer implementation, proximity detection policies, revocation data checks, and use of cryptographically random nonces.
- Limit concurrent transmissions to Ten PlayReady-ND or WMDRM-ND receivers (with exceptions for specific transmitter types).

This summary is based on detailed compliance and robustness rules found in the PlayReady licensing documentation.【4:0†source】【4:1†source】【4:2†source】
```

**Expected / Ground Truth**

```
Licensees must follow the licensing process outlined on the IPLA Licensing homepage at https://aka.ms/IPLA. They are required to obtain the appropriate licenses as Intermediate Product licensees and/or Final Product licensees to use PlayReady products.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2134628341728638). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 36: Response correctness failure - What are the mandatory compliance requirements specified for PlayReady implementations?
**Test Case ID:** `pdf037_q08_comp_rule`

**Query**

```
What are the mandatory compliance requirements specified for PlayReady implementations?
```

**Response (Agent Output)**

```
Mandatory compliance requirements for PlayReady implementations include:

- Transmitting to PlayReady-ND Receiver requires adherence to key usage, timer resolution, security level verification, proximity detection policies, revocation data validation, and restrictions on concurrent receivers.
- Receiving from PlayReady-ND Transmitters involves processing policies for metering, expiration, domain ID, and restrictions on transmitting received content.
- Transmitting to WMDRM-ND Receivers mandates timer resolution, security level checks, proximity detection, revocation data freshness, concurrency limits, protocol message implementation, and nonce validation.
- Requirements for PlayReady Devices cover architecture, use of clocks, encryption keys, certificate metadata, serial numbers, persistent storage, and adherence to designated compliance sections.
- Specific rules exist for PlayReady Portable Devices, PlayReady Device Bridges, PlayReady PC Applications, PlayReady Servers, PlayReady Secure Codecs for PC, and PlayReady Trusted Execution Environments with detailed mandates on clock accuracy, license handling, unique identifiers, secure storage, and interfaces.

These rules ensure secure transmission, playback, and licensing consistency across devices and applications in compliance with Microsoft's defined standards for PlayReady Products【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
Compliance Rules specify the required behaviors of PlayReady implementations and the software accessing the implementations. These rules describe how content may be accessed and passed using specific policy rules, ensuring mandatory compliance with content protection and usage.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2556118728106169). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 37: Response correctness failure - What must a server application do to handle revoked client certificates in PlayReady ve...
**Test Case ID:** `pdf039_q08_comp_rule`

**Query**

```
What must a server application do to handle revoked client certificates in PlayReady version 4.3?
```

**Response (Agent Output)**

```
Handling revoked client certificates in PlayReady version 4.3 requires the server application to explicitly request that one or more revoked client certificates be treated as if they were not revoked. To do this, the server application must:

- Create an XML file listing the certificate hashes to ignore, matching the revoked model or company certificates.
- Add a new entry referencing this XML file in the web.config file of the RMSDK implementation.

For .NET Core-based RMSDK deployments, the XML file should be added as an item project and the RevocationAllowFile string in config/RMSDKConfig.cs updated with the XML file path.

For IIS-based RMSDK deployments, a new key named "REVOCATIONALLOWFILE" must be added to the web.config file, pointing to the XML file.

This feature allows companies to continue issuing content to revoked clients selectively, providing more control over content distribution.

Example XML format for ignoring entries:

```xml
<?xml version="1.0" ENCODING="utf-8"?> 
<RevAllowInfo> 
  <AllowList> 
    <CertificateHash>hash_value_1</CertificateHash> 
    <CertificateHash>hash_value_2</CertificateHash> 
  </AllowList> 
</RevAllowInfo>
```

Example web.config entry:

```xml
<add key="RevocationAllowFile" value="REVOCATIONALLOWSAMPLE.XML">
```

These steps are detailed in the PlayReady Revocation documentation for version 4.3.【4:2†source】【4:0†source】
```

**Expected / Ground Truth**

```
In PlayReady version 4.3, a server application can explicitly request that one or more revoked client certificates be treated as if they were not revoked. This means the server must make such a request if it wants to override the revocation status of client certificates.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.2920022347440933). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 38: Response correctness failure - What are the mandatory compliance requirements for handling metering and secure stop da...
**Test Case ID:** `pdf041_q08_comp_rule`

**Query**

```
What are the mandatory compliance requirements for handling metering and secure stop data in the .NET Framework SDK compared to the .NET Standard SDK?
```

**Response (Agent Output)**

```
PlayReady compliance requirements for handling metering and secure stop data in the .NET Framework SDK versus the .NET Standard SDK are summarized as follows:

- Both SDKs implement metering and secure stop handling interfaces with the same names (IMeteringHandler, ISecureStopHandler, etc.).
- In the .NET Framework SDK, handler interfaces use synchronous methods (e.g., GetMeteringCertificateAsync and ProcessMeteringDataAsync are synchronous), whereas in the .NET Standard SDK, these methods are asynchronous, adhering to modern async programming patterns.
- The .NET Framework SDK provides some additional method overloads not found in the .NET Standard SDK. For example, the GetSecureStopData method overload that takes an ISecureStop2Handler exists only in the .NET Framework SDK; the .NET Standard SDK loads this handler like any other.
- The overall compliance behavior requirements for secure stop—such as tracking secure stop data, closing and destroying decryptor objects on stop state, and failing decryption if a secure stop entry has been marked—are consistent with the Microsoft Implementation and apply to PlayReady Products regardless of SDK used, per Compliance Rules for PlayReady Products.

Hence, the main compliance differences relate to API design (sync vs async) and some method availability, while mandatory secure stop and metering tracking, handling, and response requirements are consistent across both SDKs.

References:
- PlayReady Server SDK 4.5 differences in handler interfaces (sync vs async) and method availability for secure stop and metering handlers.
- Compliance Rules for PlayReady Products Section 3.3 Secure Stop compliance mandates consistent implementation, tracking, and cryptographic enforcement of secure stop data handling.
- IMeteringHandler and ISecureStopHandler interfaces exist in both SDKs with synchronous methods in .NET Framework and asynchronous in .NET Standard.【4:0†source】【4:1†source】【4:4†source】
```

**Expected / Ground Truth**

```
In the .NET Framework SDK, methods like GetMeteringCertificateAsync, ProcessMeteringDataAsync, and ProcessSecureStopDataAsync are synchronous, whereas in the .NET Standard SDK, these are handled differently. Additionally, the GetSecureStopData method overload that takes an ISecureStop2Handler exists only in the .NET Framework SDK, while the .NET Standard SDK loads this handler like any other. These distinctions imply that developers must comply with synchronous processing in the .NET Framework SDK and adapt to different handler loading mechanisms in the .NET Standard SDK.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.3364007040890671). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---

## BUG 39: Response correctness failure - What must developers do to ensure proper handling of KeyExchangeLicense with multiple a...
**Test Case ID:** `pdf042_q08_comp_rule`

**Query**

```
What must developers do to ensure proper handling of KeyExchangeLicense with multiple algorithms in PlayReady 4.6?
```

**Response (Agent Output)**

```
Handling KeyExchangeLicense with multiple algorithms in PlayReady 4.6 requires:

- Checking if the challenge's ReeFeatureList contains LicenseChallengeReeFeatures.KeyExchangeMultiple.
- Calling the KeyExchangeLicense class method AddRight multiple times with different KeyExchangeRight instances that have different algorithms.

This ensures that a single KeyExchangeLicense with multiple keys using different algorithms is properly handled in the server SDK. The LicenseChallengeReeFeatures enum now includes KeyExchangeMultiple to support this functionality. This allows the server to include multiple keys with different algorithms in one Key Exchange license properly.  

These points are explicitly stated in the PlayReady 4.6 update overview and server API documentation【4:0†source】【4:1†source】.
```

**Expected / Ground Truth**

```
Developers must ensure that a single KeyExchangeLicense containing multiple different algorithms is properly handled, as the update in PlayReady 4.6 fixes this issue to support such scenarios correctly.
```

**Actual Result**

```
Response Correctness evaluator = FAIL (score=0.5975500199088178). Answer relevancy=PASS, completeness=PASS.
```

**Severity:** High
**Priority:** P1
**Bug Type:** Functional – Incorrect Response

---
