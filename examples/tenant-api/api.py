"""Fixture sintética, sem servidor ou banco de produção."""
def get_invoice(actor, invoice_id, invoices):
    invoice = invoices[invoice_id]
    if actor['tenant'] != invoice['tenant']:
        raise PermissionError('tenant mismatch')
    return invoice['amount']


def get_invoice_unsafe(actor, invoice_id, invoices):
    invoice = invoices[invoice_id]
    return invoice['amount']
