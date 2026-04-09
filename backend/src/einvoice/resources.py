"""Where the vendored KoSIT files live (backend/vendor/, committed; see NOTICE)."""

from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parents[2] / "vendor"
CONFIG_DIR = VENDOR_DIR / "xrechnung-config"
VISUALIZATION_DIR = VENDOR_DIR / "xrechnung-visualization"
TESTSUITE_DIR = VENDOR_DIR / "xrechnung-testsuite"

CONFIG_RELEASE = "v2026-01-31"
CEN_RULES_VERSION = "1.3.15"  # from the configuration's CHANGELOG for this release

SCENARIOS = CONFIG_DIR / "scenarios.xml"
UBL_INVOICE_XSD = CONFIG_DIR / "resources/ubl/2.1/xsd/maindoc/UBL-Invoice-2.1.xsd"
UBL_CREDIT_NOTE_XSD = CONFIG_DIR / "resources/ubl/2.1/xsd/maindoc/UBL-CreditNote-2.1.xsd"
CII_XSD = CONFIG_DIR / "resources/cii/16b/xsd/CrossIndustryInvoice_100pD16B.xsd"
EN16931_UBL_XSL = CONFIG_DIR / "resources/ubl/2.1/xsl/EN16931-UBL-validation.xsl"
EN16931_CII_XSL = CONFIG_DIR / "resources/cii/16b/xsl/EN16931-CII-validation.xsl"
XRECHNUNG_UBL_XSL = CONFIG_DIR / "resources/xrechnung/3.0.2/xsl/XRechnung-UBL-validation.xsl"
XRECHNUNG_CII_XSL = CONFIG_DIR / "resources/xrechnung/3.0.2/xsl/XRechnung-CII-validation.xsl"

UBL_INVOICE_TO_XR_XSL = VISUALIZATION_DIR / "xsl/ubl-invoice-xr.xsl"
UBL_CREDIT_NOTE_TO_XR_XSL = VISUALIZATION_DIR / "xsl/ubl-creditnote-xr.xsl"
CII_TO_XR_XSL = VISUALIZATION_DIR / "xsl/cii-xr.xsl"
XR_TO_HTML_XSL = VISUALIZATION_DIR / "xsl/xrechnung-html.xsl"
