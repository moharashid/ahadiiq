from datetime import timedelta,date
from app import models
STATUS = ["pending", "completed","overdue"]
class ObligationService:
    def generate_obligation(self, clause, agreement):
        if clause.clause_type == "renewal":
            if clause.notice_period is None or agreement.expiry_date is None:
                return None
            due_date = agreement.expiry_date - timedelta(days=clause.notice_period)
            obligation = models.Obligation(
                agreement_id=agreement.id,
                tenant_id=agreement.tenant_id,
                clause_id=clause.id,
                obligation_type=clause.clause_type,
                due_date=due_date,
                assignee = agreement.owner_id
            )
            return obligation
        else:
            return None
            
    def generate_obligations(self, clauses, agreement):
        obligations = []
        for clause in clauses:
            if clause.status != "validated":
                continue                      # skip unvalidated clauses — the spec guard
            obligation = self.generate_obligation(clause, agreement)
            if obligation is not None:
                obligations.append(obligation)   # collect the real ones
        return obligations


obligation_service = ObligationService()