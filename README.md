# LinkGuard

**LinkGuard** is a lightweight desktop application that automatically removes tracking parameters from URLs, helping protect your privacy while browsing the web.

## Features

- **Automatic URL cleaning:** Detects and removes known tracking parameters.
- **Clipboard monitoring:** Automatically cleans copied URLs and replaces the original clipboard contents with the cleaned URL.
- **Manual cleaning:** Paste or type a URL directly into the application.
- **Suspicious link warnings:** Identifies potentially suspicious links, including shortened URLs, redirects and unusual hostnames.
- **Local processing:** URL analysis and cleaning happen entirely on your device.

## How to use

1. Start LinkGuard.
2. Copy a URL as you normally would.
3. LinkGuard automatically detects and removes known tracking parameters.
4. The cleaned URL replaces the original in your clipboard.

Alternatively, you can paste or type a URL directly into the application to clean it manually.

## Privacy

LinkGuard is designed with privacy in mind.

- **No network connections:** LinkGuard does not send URLs or personal data to external servers.
- **Local processing:** All URL analysis and cleaning happens on your device.
- **Clipboard:** Only standalone HTTP and HTTPS URLs are inspected when clipboard monitoring is enabled.
- **History:** Link history is stored in memory only and disappears when the application closes.
- **Settings:** Application settings are stored locally on your device.
- **No tracking or analytics:** LinkGuard does not collect usage statistics or track its users.

**Your URLs stay on your device.**

## Security warnings

Some security services, including VirusTotal, may flag LinkGuard as a Trojan or potentially unwanted application. Browsers such as Firefox and Google Chrome may also display security warnings when downloading or running it.

These detections may be related to LinkGuard's clipboard-monitoring functionality, which can trigger security heuristics commonly associated with suspicious software.

### Unsigned application

LinkGuard is currently not digitally signed. I have chosen not to purchase a code-signing certificate, as this would introduce additional costs for a free project.

As a result, Windows and some browsers may display warnings when downloading or launching the application. The absence of a digital signature also means that the publisher's identity cannot be verified through a code-signing certificate.

### Source code

LinkGuard's source code is publicly available in this repository, allowing anyone to inspect how the application works and review its behaviour.

Users who have security concerns are encouraged to examine the source code before running the application.

## Downloads

Download the latest version from the [Releases](../../releases/latest) page.

Available versions:

- **Windows:** `.exe`
- **Linux:** `.AppImage`

## Contact
You can contact me at help@still-broken.net if you have any questions or find any problems with the application
https://still-broken.net

## License

LinkGuard is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md).

Commercial use is not permitted without separate permission from the copyright holder.
