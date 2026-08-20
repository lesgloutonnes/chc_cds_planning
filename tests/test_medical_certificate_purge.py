from odoo.tests.common import SavepointCase


class TestMedicalCertificatePurge(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sick_type = cls.env["hr.leave.type"].create(
            {
                "name": "Congé maladie DPO",
                "requires_allocation": "no",
                "leave_validation_type": "no_validation",
                "request_unit": "day",
            }
        )
        if "support_document" in cls.sick_type._fields:
            cls.sick_type.support_document = True
        cls.annual_type = cls.env["hr.leave.type"].create(
            {
                "name": "Congés payés",
                "requires_allocation": "no",
                "leave_validation_type": "no_validation",
                "request_unit": "day",
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Employé DPO"})

    def test_disable_support_document_on_sick_types_only(self):
        if "support_document" not in self.sick_type._fields:
            self.skipTest("support_document absent de cette base")
        self.annual_type.support_document = True
        self.env["hr.leave.type"]._chc_disable_sick_leave_documents()
        self.assertFalse(self.sick_type.support_document)
        self.assertTrue(self.annual_type.support_document)

    def test_purge_removes_sick_leave_attachments_only(self):
        sick_leave = self.env["hr.leave"].create(
            {
                "name": "Arrêt",
                "employee_id": self.employee.id,
                "holiday_status_id": self.sick_type.id,
                "request_date_from": "2026-01-05",
                "request_date_to": "2026-01-05",
            }
        )
        annual_leave = self.env["hr.leave"].create(
            {
                "name": "Vacances",
                "employee_id": self.employee.id,
                "holiday_status_id": self.annual_type.id,
                "request_date_from": "2026-02-02",
                "request_date_to": "2026-02-02",
            }
        )
        sick_att = self.env["ir.attachment"].create(
            {
                "name": "certificat.pdf",
                "type": "binary",
                "datas": "dGVzdA==",
                "res_model": "hr.leave",
                "res_id": sick_leave.id,
                "mimetype": "application/pdf",
            }
        )
        annual_att = self.env["ir.attachment"].create(
            {
                "name": "justificatif.pdf",
                "type": "binary",
                "datas": "dGVzdA==",
                "res_model": "hr.leave",
                "res_id": annual_leave.id,
                "mimetype": "application/pdf",
            }
        )

        deleted = self.env["hr.leave"]._chc_purge_medical_certificate_attachments()
        self.assertEqual(deleted, 1)
        self.assertFalse(sick_att.exists())
        self.assertTrue(annual_att.exists())
