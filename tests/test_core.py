from pathlib import Path
import unittest

from openpyxl import Workbook

from company_enricher.core.excel import load_records
from company_enricher.core.validators import extract_emails, extract_spanish_phones, normalize_spanish_phone


class CoreTests(unittest.TestCase):
    def test_spanish_phone_validation_filters_mobile(self) -> None:
        self.assertEqual(normalize_spanish_phone("91 123 45 67"), "+34 911 23 45 67")
        self.assertIsNone(normalize_spanish_phone("612 345 678"))

    def test_email_extraction_filters_noise(self) -> None:
        emails = extract_emails("Contacto info@empresa.es y noreply@empresa.es")
        self.assertEqual(emails, ["info@empresa.es"])

    def test_excel_column_detection_with_flexible_headers(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            wb = Workbook()
            ws = wb.active
            ws.append(["Razón social", "Municipio", "Correo electrónico", "Tel."])
            ws.append(["ACME Servicios SL", "Madrid", "info@acme.es", "911234567"])
            path = Path(tmp) / "empresas.xlsx"
            wb.save(path)

            _, mapping, records = load_records(path)

            self.assertEqual(mapping.company, "Razón social")
            self.assertEqual(mapping.email, "Correo electrónico")
            self.assertEqual(mapping.phone, "Tel.")
            self.assertEqual(records[0].company_name, "ACME Servicios SL")


if __name__ == "__main__":
    unittest.main()
