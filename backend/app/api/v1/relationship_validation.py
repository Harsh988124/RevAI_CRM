
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Company, Contact, Deal, Lead


def validate_crm_links(
    db: Session,
    company_id: int | None = None,
    contact_id: int | None = None,
    lead_id: int | None = None,
    deal_id: int | None = None,
) -> None:
    company = db.get(Company, company_id) if company_id is not None else None
    contact = db.get(Contact, contact_id) if contact_id is not None else None
    lead = db.get(Lead, lead_id) if lead_id is not None else None
    deal = db.get(Deal, deal_id) if deal_id is not None else None

    if company_id is not None and company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if contact_id is not None and contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    if lead_id is not None and lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    if deal_id is not None and deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    linked_company_ids = set()

    if company is not None:
        linked_company_ids.add(company.id)

    for record in (contact, lead, deal):
        if record is not None and record.company_id is not None:
            linked_company_ids.add(record.company_id)

    if len(linked_company_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="Linked CRM records must belong to the same company",
        )
