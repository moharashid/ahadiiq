import re

from app.models import extracted_text
class Validator:
    def _check_completeness(self, clause):
        if clause.clause_type is None or clause.clause_text is None:
            return False
        if clause.clause_type in ("renewal", "termination") and clause.notice_period is None:
            return False
        if clause.clause_type == "payment" and clause.amount is None:
            return False
        return True
    
    def _check_format(self, clause):
        if clause.amount is not None and clause.amount < 0:
            return False
        if clause.notice_period is not None and clause.notice_period <= 0:
            return False
        return True
    
    def _check_clause(self, clause, extracted_text):
        def norm(s):
            return re.sub(r'\s+', ' ', s).strip().lower()
        return norm(clause.clause_text) in norm(extracted_text)
    
    def validate_clause(self, clause, extracted_text):
        completeness = self._check_completeness(clause)
        formating = self._check_format(clause)
        clause_check = self._check_clause(clause, extracted_text)
        checks = [completeness,formating,clause_check]
        total_checks = len(checks)
        passed_checks = sum(checks)
        score = (passed_checks / total_checks) * 100
        # print(f"Completeness: {completeness}")
        # print(f"Formating: {formating}")
        # print(f"Clause Check: {clause_check}")
        # print("clause text:", repr(clause.clause_text[:80]))
        # print("in source?:", clause.clause_text[:80] in extracted_text)
        # print("Source text:", repr(extracted_text[:80]))
        if not clause_check or score < 75:
            return score, "needs_review"
        return score, "validated"
    
    def validate_agreement(self, agreement, clauses,extracted_text):
        needs_review = False
        for clause in clauses:
            validation_score, status = self.validate_clause(clause, extracted_text)
            clause.confidence_score = validation_score
            clause.status = status
            if status == "needs_review":
                needs_review = True
        
        if needs_review:
            agreement.status = "needs_review"
        else:
            agreement.status = "validated"
        return agreement.status
        
        

validator = Validator()  